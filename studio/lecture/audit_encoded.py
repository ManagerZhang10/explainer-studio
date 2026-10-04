import json
import subprocess

from PIL import Image, ImageChops, ImageDraw, ImageStat

import build_video as production


def audit():
    directory = production.WORK / "qc" / "encoded"
    directory.mkdir(parents=True, exist_ok=True)
    chapters = []
    for day in range(1, 15):
        script = json.loads((production.SCRIPTS / f"day{day:02d}.json").read_text())
        video = production.OUT / f"day{day:02d}_{script['title']}.mp4"
        timeline = json.loads((production.WORK / "video" / f"day{day:02d}" / "timeline.json").read_text())
        frames, observations = [], []
        for index, scene in enumerate(timeline["scenes"]):
            timestamp = scene["t0"] + scene["dur"] * 0.5
            path = directory / f"day{day:02d}_scene{index:02d}.png"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-threads", "1", "-ss", str(timestamp),
                            "-i", str(video), "-frames:v", "1", "-filter_threads", "1", "-threads", "1", str(path)], check=True)
            actual = Image.open(path).convert("RGB")
            expected = Image.open(production.WORK / "qc" / "repaired" / path.name).convert("RGB")
            difference = ImageChops.difference(actual, expected)
            overall = sum(ImageStat.Stat(difference).mean) / 3
            diagram = sum(ImageStat.Stat(difference.crop((60, 186, 1220, 550))).mean) / 3
            observations.append({"scene": index, "timestamp": timestamp,
                                 "mean_absolute_pixel_error": round(overall, 4),
                                 "diagram_pixel_error": round(diagram, 4),
                                 "matches_audited_page": overall < 3 and diagram < 4})
            actual.thumbnail((480, 270))
            frames.append((actual.copy(), f"{index}: {timestamp:.1f}s"))
        sheet = Image.new("RGB", (1440, ((len(frames) + 2) // 3) * 302), "#e8e8ea")
        drawing = ImageDraw.Draw(sheet)
        for index, (frame, label) in enumerate(frames):
            left, top = index % 3 * 480, index // 3 * 302
            sheet.paste(frame, (left, top))
            drawing.text((left + 12, top + 278), label, fill="black")
        sheet.save(directory / f"day{day:02d}_contact.png")
        chapter = {"day": day, "all_match": all(observation["matches_audited_page"] for observation in observations),
                   "observations": observations}
        chapters.append(chapter)
        print(json.dumps({"day": day, "all_match": chapter["all_match"],
                          "worst_pixel_error": max(observation["mean_absolute_pixel_error"] for observation in observations)}), flush=True)
    (directory / "audit.json").write_text(json.dumps(chapters, ensure_ascii=False, indent=2), encoding="utf-8")
    return all(chapter["all_match"] for chapter in chapters)


if __name__ == "__main__":
    raise SystemExit(0 if audit() else 1)
