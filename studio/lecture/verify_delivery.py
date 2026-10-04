import hashlib
import json
import re
import subprocess
from pathlib import Path

import build_video as production


def verify():
    chapters = []
    for day in range(1, 15):
        script_path = production.SCRIPTS / f"day{day:02d}.json"
        script = json.loads(script_path.read_text())
        video = production.OUT / f"day{day:02d}_{script['title']}.mp4"
        chapter = {"day": day, "title": script["title"], "video": str(video), "errors": []}
        if not video.is_file():
            chapter["errors"].append("missing video")
            chapters.append(chapter)
            continue
        information = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(video)],
                                     capture_output=True, text=True).stderr
        match = re.search(r"Duration: (\d+):(\d+):([\d.]+)", information)
        duration = int(match[1]) * 3600 + int(match[2]) * 60 + float(match[3]) if match else None
        chapter.update({"duration_seconds": duration, "bytes": video.stat().st_size,
                        "sha256": hashlib.sha256(video.read_bytes()).hexdigest(),
                        "script_sha256": hashlib.sha256(script_path.read_bytes()).hexdigest()})
        if duration is None or not 120 <= duration <= 180:
            chapter["errors"].append("duration outside 120-180 seconds")
        if not re.search(r"Video: h264.*1280x720.*30 fps", information):
            chapter["errors"].append("unexpected video codec, size or frame rate")
        if "Audio: aac" not in information:
            chapter["errors"].append("missing AAC audio")
        decoding = subprocess.run(["ffmpeg", "-v", "error", "-threads", "1", "-i", str(video),
                                   "-f", "null", "-"], capture_output=True, text=True)
        if decoding.returncode or decoding.stderr.strip():
            chapter["errors"].append("full decoding failed: " + decoding.stderr[-500:])
        timeline_path = production.WORK / "video" / f"day{day:02d}" / "timeline.json"
        timeline = json.loads(timeline_path.read_text())
        if duration is not None and abs(duration - timeline["total"]) > 0.1:
            chapter["errors"].append("timeline/video duration mismatch")
        if not all(scene.get("visual") for scene in script["scenes"]):
            chapter["errors"].append("scene missing teaching visual")
        chapter["scene_count"] = len(timeline["scenes"])
        chapters.append(chapter)
        print(json.dumps(chapter, ensure_ascii=False), flush=True)
    result = {"chapters": chapters, "all_pass": all(not chapter["errors"] for chapter in chapters),
              "scope": "Track A 14 chapters; container, duration, complete decoding and visual schema checks. Human visual review is separate."}
    (production.WORK / "verify.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result["all_pass"]


if __name__ == "__main__":
    raise SystemExit(0 if verify() else 1)
