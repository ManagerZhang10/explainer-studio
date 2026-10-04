#!/usr/bin/env python3
"""Render a few stills from a built page at given timestamps (fast visual check)."""
import json
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright
import build_video as B


def shots(day, times, scale=1.0, outdir=None):
    vdir = B.WORK / "video" / f"day{day:02d}"
    html = vdir / "page.html"
    tl = json.loads(html.read_text(encoding="utf-8").split("window.__TL__ = ")[1].split(";</script>")[0])
    outdir = Path(outdir or (B.WORK / "qc" / f"day{day:02d}"))
    outdir.mkdir(parents=True, exist_ok=True)
    made = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": B.W, "height": B.H}, device_scale_factor=scale)
        pg.goto(html.as_uri())
        pg.wait_for_function("window.__ready === true", timeout=30000)
        for t in times:
            pg.evaluate("t => window.__seek(t)", t)
            f = outdir / f"t{t:06.1f}.png"
            pg.screenshot(path=str(f))
            made.append(f)
        b.close()
    return made, tl["total"]


if __name__ == "__main__":
    day = int(sys.argv[1])
    if len(sys.argv) > 2 and sys.argv[2] != "auto":
        times = [float(x) for x in sys.argv[2].split(",")]
    else:
        # one frame per scene, 60% through each one
        sys.path.insert(0, str(B.WORK / "video" / f"day{day:02d}"))
        html = (B.WORK / "video" / f"day{day:02d}" / "page.html").read_text(encoding="utf-8")
        tl = json.loads(html.split("window.__TL__ = ")[1].split(";</script>")[0])
        times = [round(s["t0"] + s["dur"] * 0.6, 1) for s in tl["scenes"]]
    made, total = shots(day, times)
    print(f"total={total:.1f}s  shots={len(made)}")
    for m in made:
        print(m)
