"""Pipeline step 2: build data/history.csv from the raw files alone.

    python -m watcher.build

The build reads every data/raw/<date>/<source>.json.gz in date order (and
source order within a date) and replays them:

  * every posting is converted to the common columns (normalize.py);
  * a posting seen for the first time gets that date as first_seen, and
    first_run = true if that date is the date of its source's first raw file;
  * every posting its source lists that day gets that date as last_seen;
  * an open posting whose source has a raw file that day but no longer lists
    it becomes removed, with removed_date = that date;
  * a removed posting that its source lists again becomes open again: the
    removed_date is cleared and first_seen is kept.

A source with no raw file for a date (it failed that day) changes nothing.
The descriptive columns take the latest listing's values, except posted_date,
which keeps the first non-empty value. in_role applies the title rule
(role.py) to the final title, so a rule change reaches every day of the
history. Rows are sorted by posting_id. The same raw files always produce the
same file, byte for byte.
"""
from __future__ import annotations

import argparse
import csv
import re
import sys
from collections import defaultdict
from pathlib import Path

from . import config
from .fetch import read_raw
from .normalize import normalize
from .role import in_role

COLUMNS = ["posting_id", "source", "source_id", "employer", "title", "location", "department",
           "posted_date", "url", "in_role", "first_run", "first_seen", "last_seen", "status",
           "removed_date"]

_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def raw_days(raw_dir: Path) -> list[tuple[str, list[Path]]]:
    """[(date, [raw files])] for every date folder that holds at least one raw file."""
    if not raw_dir.exists():
        return []
    days = []
    for folder in sorted(p for p in raw_dir.iterdir() if p.is_dir() and _DAY.match(p.name)):
        files = sorted(folder.glob("*.json.gz"))
        if files:
            days.append((folder.name, files))
    return days


def apply_day(history: dict, open_ids: dict, first_day: dict, day: str, env: dict) -> None:
    """Fold one source's listing for one day into the history (in place)."""
    source = env["source"]
    first_day.setdefault(source, day)
    listed = set()
    for posting in normalize(env):
        pid = posting["posting_id"]
        listed.add(pid)
        row = history.get(pid)
        if row is None:
            history[pid] = dict(posting, first_run=(day == first_day[source]), first_seen=day,
                                last_seen=day, status="open", removed_date="")
            continue
        posted = row["posted_date"] or posting["posted_date"]
        row.update(posting)
        row["posted_date"] = posted
        row["last_seen"] = day
        if row["status"] == "removed":
            row["status"], row["removed_date"] = "open", ""
    for pid in open_ids[source] - listed:
        history[pid]["status"], history[pid]["removed_date"] = "removed", day
    open_ids[source] = listed


def build_history(raw_dir: Path) -> list[dict]:
    history: dict[str, dict] = {}
    open_ids: dict[str, set] = defaultdict(set)
    first_day: dict[str, str] = {}
    for day, files in raw_days(raw_dir):
        for path in files:
            apply_day(history, open_ids, first_day, day, read_raw(path))
    rows = sorted(history.values(), key=lambda r: r["posting_id"])
    for row in rows:
        row["in_role"] = in_role(row["title"])
    return rows


def _cell(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return value


def write_history(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f, lineterminator="\n")
        writer.writerow(COLUMNS)
        for row in rows:
            writer.writerow([_cell(row[c]) for c in COLUMNS])


def read_history(path: Path) -> list[dict]:
    with open(path, encoding="utf-8", newline="") as f:
        return list(csv.DictReader(f))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", type=Path, default=config.DATA_DIR)
    args = ap.parse_args(argv)
    rows = build_history(args.data_dir / "raw")
    write_history(rows, args.data_dir / "history.csv")
    n_open = sum(r["status"] == "open" for r in rows)
    n_role = sum(r["in_role"] and r["status"] == "open" for r in rows)
    print(f"history.csv: {len(rows)} postings, {n_open} open, {n_role} open in role")
    return 0


if __name__ == "__main__":
    sys.exit(main())
