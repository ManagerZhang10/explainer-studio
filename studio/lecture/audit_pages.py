import hashlib
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw
from playwright.sync_api import sync_playwright

import build_video as production


def audit(days):
    directory = production.WORK / "qc" / "repaired"
    directory.mkdir(parents=True, exist_ok=True)
    reports = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(args=["--disable-gpu"])
        page = browser.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=2 / 3)
        for day in days:
            errors = []
            listener = lambda error: errors.append(str(error))
            page.on("pageerror", listener)
            path = production.WORK / "video" / f"day{day:02d}" / "page.html"
            page.goto(path.as_uri())
            page.wait_for_function("window.__ready === true")
            page.evaluate("document.fonts.ready")
            timeline = page.evaluate("window.__TL__")
            scenes = []
            thumbnails = []
            for index, scene in enumerate(timeline["scenes"]):
                observations = []
                for fraction in (0.05, 0.5, 0.92):
                    timestamp = scene["t0"] + scene["dur"] * fraction
                    page.evaluate("time => window.__seek(time)", timestamp)
                    observation = page.evaluate("""() => {
                        const slide = document.querySelector('.slide.active');
                        const visible = element => {
                            const style = getComputedStyle(element);
                            return style.display !== 'none' && Number(style.opacity) > 0;
                        };
                        const caption = document.querySelector('.capline.on');
                        const cap = caption && caption.getBoundingClientRect();
                        const overflow = [...slide.querySelectorAll('h1,.sub,.tblwrap,.stats,.gloss,.diagbox')]
                            .filter(visible).filter(element => {
                                const bounds = element.getBoundingClientRect();
                                return bounds.left < -1 || bounds.right > 1921 || bounds.bottom > 1081;
                            }).map(element => element.className || element.tagName);
                        const arrows = [...slide.querySelectorAll('[data-from][data-to]')];
                        return {
                            overflow,
                            empty_arrows: arrows.filter(element => !element.getAttribute('d')).length,
                            broken_images: [...slide.querySelectorAll('img')].filter(element => !element.complete || !element.naturalWidth).length,
                            caption_outside: Boolean(cap && (cap.left < 0 || cap.right > 1920)),
                            caption_lines: document.querySelectorAll('.capline.on').length,
                            running_animations: document.getAnimations().filter(animation => animation.playState === 'running').length
                        };
                    }""")
                    observations.append(observation)
                    if fraction == 0.5:
                        screenshot = directory / f"day{day:02d}_scene{index:02d}.png"
                        page.screenshot(path=str(screenshot), animations="allow")
                        thumbnail = Image.open(screenshot).convert("RGB")
                        thumbnail.thumbnail((480, 270))
                        thumbnails.append((thumbnail, f"{index}: {timestamp:.1f}s"))
                scenes.append({"index": index, "observations": observations})
            timestamp = timeline["scenes"][1]["t0"] + 2
            page.evaluate("time => window.__seek(time)", timestamp)
            first_capture = page.screenshot()
            first_hash = hashlib.sha256(first_capture).hexdigest()
            page.evaluate("time => window.__seek(time)", timeline["total"] - 1)
            page.evaluate("time => window.__seek(time)", timestamp)
            second_capture = page.screenshot()
            second_hash = hashlib.sha256(second_capture).hexdigest()
            if first_hash != second_hash:
                (directory / f"day{day:02d}_seek_first.png").write_bytes(first_capture)
                (directory / f"day{day:02d}_seek_second.png").write_bytes(second_capture)
            sheet = Image.new("RGB", (1440, ((len(thumbnails) + 2) // 3) * 302), "#e8e8ea")
            drawing = ImageDraw.Draw(sheet)
            for index, (thumbnail, label) in enumerate(thumbnails):
                left, top = index % 3 * 480, index // 3 * 302
                sheet.paste(thumbnail, (left, top))
                drawing.text((left + 12, top + 278), label, fill="black")
            sheet.save(directory / f"day{day:02d}_contact.png")
            report = {"day": day, "duration": timeline["total"], "errors": errors,
                      "deterministic": first_hash == second_hash, "scenes": scenes}
            reports.append(report)
            page.remove_listener("pageerror", listener)
            print(json.dumps({key: value for key, value in report.items() if key != "scenes"}), flush=True)
        browser.close()
    (directory / "audit.json").write_text(json.dumps(reports, ensure_ascii=False, indent=2))
    return reports


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("days", nargs="*", type=int)
    parser.add_argument("--project-dir", type=Path)
    arguments = parser.parse_args()
    if arguments.project_dir:
        production.WORK = arguments.project_dir.resolve() / "work"
    reports = audit(arguments.days or list(range(1, 15)))
    failures = any(report["errors"] or not report["deterministic"] or
                   any(observation["overflow"] or observation["empty_arrows"] or
                       observation["broken_images"] or observation["caption_outside"] or
                       observation["running_animations"] or observation["caption_lines"] > 1
                       for scene in report["scenes"] for observation in scene["observations"])
                   for report in reports)
    raise SystemExit(1 if failures else 0)
