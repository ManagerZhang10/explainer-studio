import concurrent.futures
import difflib
import hashlib
import json
import re
import subprocess
import sys

import build_video as production

sys.path.insert(0, str(production.config.REPO / "studio" / "refs"))
import openai_transcribe as transcription


def chinese(text):
    return "".join(character for character in text if "一" <= character <= "鿿")


def audit_chapter(day):
    script = json.loads((production.SCRIPTS / f"day{day:02d}.json").read_text())
    directory = production.WORK / "qc" / "audio_api"
    directory.mkdir(parents=True, exist_ok=True)
    expected = "".join([script["hook"], *[scene["narration"] for scene in script["scenes"]], script["outro"]])
    fingerprint = hashlib.sha256(expected.encode("utf-8")).hexdigest()
    cache = directory / f"day{day:02d}_{fingerprint[:12]}.json"
    audio = directory / f"day{day:02d}_{fingerprint[:12]}.m4a"
    if cache.exists():
        result = json.loads(cache.read_text())
    else:
        voice = production.WORK / "video" / f"day{day:02d}" / "audio" / "voice.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-threads", "1", "-i", str(voice),
                        "-c:a", "aac", "-b:a", "64k", "-threads", "1", str(audio)], check=True)
        result = transcription.transcribe(str(audio), "whisper-1")
        cache.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    actual = result.get("text", "")
    matcher = difflib.SequenceMatcher(None, chinese(expected), chinese(actual), autojunk=False)
    differences = [{"expected": matcher.a[first_start:first_end], "recognized": matcher.b[second_start:second_end]}
                   for operation, first_start, first_end, second_start, second_end in matcher.get_opcodes()
                   if operation != "equal"]
    ratio = matcher.ratio()
    return {"day": day, "provider": "OpenAI API", "model": "whisper-1", "expected_cn": len(matcher.a),
            "recognized_cn": len(matcher.b), "chinese_similarity": round(ratio, 4),
            "review_needed": ratio < 0.90, "differences": differences,
            "transcript": str(cache.relative_to(production.ROOT)),
            "limitation": "ASR consistency check, not a human listening or beginner comprehension test."}


if __name__ == "__main__":
    reports = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        pending = {executor.submit(audit_chapter, day): day for day in range(1, 15)}
        for future in concurrent.futures.as_completed(pending):
            try:
                report = future.result()
            except Exception as error:
                report = {"day": pending[future], "error": str(error), "review_needed": True}
            reports.append(report)
            print(json.dumps({key: value for key, value in report.items() if key != "differences"}, ensure_ascii=False), flush=True)
    path = production.WORK / "qc" / "audio_api" / "audit.json"
    path.write_text(json.dumps(sorted(reports, key=lambda report: report["day"]), ensure_ascii=False, indent=2), encoding="utf-8")
    raise SystemExit(1 if any(report["review_needed"] for report in reports) else 0)
