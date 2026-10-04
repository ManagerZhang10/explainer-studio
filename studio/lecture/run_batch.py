import argparse
import concurrent.futures
import hashlib
import json
import time

import build_video as production


def run(days, prepare, workers):
    started = time.time()
    fingerprints = {str(day): hashlib.sha256((production.SCRIPTS / f"day{day:02d}.json").read_bytes()).hexdigest()
                    for day in days}
    outcomes = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        pending = {executor.submit(production.main, day, False, 2 / 3, prepare): day for day in days}
        for future in concurrent.futures.as_completed(pending):
            day = pending[future]
            try:
                result = future.result()
                current = hashlib.sha256((production.SCRIPTS / f"day{day:02d}.json").read_bytes()).hexdigest()
                if current != fingerprints[str(day)]:
                    raise RuntimeError("script changed during production; rebuild this chapter")
                outcome = {"day": day, "ok": True, "artifact": str(result[0] if prepare else result)}
            except Exception as error:
                outcome = {"day": day, "ok": False, "error": str(error)}
            outcomes.append(outcome)
            print(json.dumps(outcome, ensure_ascii=False), flush=True)
    report = {"started": started, "finished": time.time(), "prepare_only": prepare,
              "workers": workers, "script_sha256": fingerprints, "outcomes": outcomes}
    report_path = production.WORK / ("prepare_report.json" if prepare else "render_report.json")
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return all(outcome["ok"] for outcome in outcomes)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--prepare", action="store_true")
    parser.add_argument("--workers", type=int, choices=(1, 2), default=2)
    parser.add_argument("--days", nargs="+", type=int, default=list(range(1, 15)))
    arguments = parser.parse_args()
    raise SystemExit(0 if run(arguments.days, arguments.prepare, arguments.workers) else 1)
