"""Run the daily pipeline in one command: fetch, build, status (and the issue).

    python -m watcher.run                 # fetch + build + status
    python -m watcher.run --issue         # ...then open/update the day's issue
    python -m watcher.run --skip-fetch    # rebuild history and status from the raw files

GitHub Actions runs the same steps one by one (see .github/workflows/daily.yml)
and then commits the data.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import build, config, fetch, issue, status


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", type=Path, default=config.DATA_DIR)
    ap.add_argument("--skip-fetch", action="store_true")
    ap.add_argument("--issue", action="store_true")
    args = ap.parse_args(argv)
    d = ["--data-dir", str(args.data_dir)]
    if not args.skip_fetch:
        fetch.main(d)
    build.main(d)
    status.main(d)
    if args.issue:
        issue.main(d)
    return 0


if __name__ == "__main__":
    sys.exit(main())
