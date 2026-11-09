"""Pipeline step 3: write data/status.json, which describes the latest run.

    python -m watcher.status

Reads the latest run log (data/runs/<date>.json, written by fetch.py), the
raw folders, and data/history.csv. Keys:

  run_time            UTC time of the latest run
  run_date            its UTC date
  first_run_date      date of the earliest raw file
  days_with_success   number of different dates with a raw file
  open                open postings
  new_today           postings first seen on run_date, leaving out first-run postings
  removed_today       postings removed on run_date
  in_role             the same three counts for postings in the role
  sources             one entry per source: name, employer, ats, ok, count, error
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import config
from .build import raw_days, read_history


def latest_log(data_dir: Path) -> dict:
    logs = sorted((data_dir / "runs").glob("*.json"))
    if not logs:
        raise SystemExit("no run log in data/runs; run `python -m watcher.fetch` first")
    return json.loads(logs[-1].read_text(encoding="utf-8"))


def counts(rows: list[dict], day: str) -> dict:
    return {
        "open": sum(r["status"] == "open" for r in rows),
        "new_today": sum(r["first_seen"] == day and r["first_run"] == "false" for r in rows),
        "removed_today": sum(r["removed_date"] == day for r in rows),
    }


def build_status(data_dir: Path) -> dict:
    log = latest_log(data_dir)
    rows = read_history(data_dir / "history.csv")
    days = [d for d, _ in raw_days(data_dir / "raw")]
    day = log["date"]
    return {
        "run_time": log["run_time"],
        "run_date": day,
        "first_run_date": days[0] if days else None,
        "days_with_success": len(days),
        **counts(rows, day),
        "in_role": counts([r for r in rows if r["in_role"] == "true"], day),
        "sources": [{"name": s["name"], "employer": s["employer"], "ats": s["ats"],
                     "ok": s["ok"], "count": s["count"], "error": s["error"]}
                    for s in log["sources"]],
    }


def write_status(status: dict, path: Path) -> None:
    path.write_text(json.dumps(status, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", type=Path, default=config.DATA_DIR)
    args = ap.parse_args(argv)
    status = build_status(args.data_dir)
    write_status(status, args.data_dir / "status.json")
    ok = sum(s["ok"] for s in status["sources"])
    print(f"status.json: run {status['run_time']}, {ok}/{len(status['sources'])} sources ok, "
          f"{status['open']} open, +{status['new_today']} new, -{status['removed_today']} removed, "
          f"{status['days_with_success']} days with a successful run")
    return 0


if __name__ == "__main__":
    sys.exit(main())
