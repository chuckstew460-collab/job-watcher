"""Pipeline step 1: call every source and save what it returns.

    python -m watcher.fetch            # today's UTC date
    python -m watcher.fetch --only stripe,ramp

For each source that succeeds, the board's JSON responses are saved, gzip-
compressed, to data/raw/<date>/<source>.json.gz. A source that fails writes no
raw file. Every source's result (ok, count, error) is recorded in
data/runs/<date>.json, which status.py turns into the status file.

A second run on the same date replaces that date's raw files and log.
"""
from __future__ import annotations

import argparse
import gzip
import json
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import requests

from . import config
from .normalize import normalize


class SourceError(Exception):
    """The source answered, but not with a complete, usable job list."""


class Client:
    """Small HTTP helper: JSON only, retries on throttling and server errors,
    and keeps every response so it can be saved as the raw file."""

    def __init__(self, timeout: int = 60, tries: int = 4):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": config.USER_AGENT, "Accept": "application/json"})
        self.timeout, self.tries = timeout, tries
        self.responses: list[dict] = []

    def call(self, method: str, url: str, *, params: dict | None = None, body: dict | None = None,
             drop: tuple[str, ...] = ()):
        """Make one request and keep its JSON. Keys named in `drop` are not kept
        (used only for Workday's filter menu, which repeats on every page)."""
        for attempt in range(1, self.tries + 1):
            try:
                resp = self.session.request(method, url, params=params, json=body, timeout=self.timeout)
                if resp.status_code in (429, 500, 502, 503, 504) and attempt < self.tries:
                    time.sleep(2 ** attempt)
                    continue
                resp.raise_for_status()
                data = resp.json()  # a non-JSON answer (an HTML page) is a failure
                break
            except (requests.ConnectionError, requests.Timeout):
                if attempt == self.tries:
                    raise
                time.sleep(2 ** attempt)
        request = {"method": method, "url": url}
        if params:
            request["params"] = params
        if body:
            request["body"] = body
        kept = {k: v for k, v in data.items() if k not in drop} if drop and isinstance(data, dict) else data
        self.responses.append({"request": request, "json": kept})
        return data


def _check_size(src: dict, total: int) -> None:
    if total > config.MAX_UNFILTERED and not src.get("search"):
        raise SourceError(f"board lists {total} postings (> {config.MAX_UNFILTERED}); "
                          "add a search term for this source")


# ---------------------------------------------------------------- one fetcher per ATS
def fetch_greenhouse(src: dict, c: Client) -> None:
    base = f"https://boards-api.greenhouse.io/v1/boards/{src['board']}"
    jobs = c.call("GET", f"{base}/jobs")["jobs"]
    _check_size(src, len(jobs))
    c.call("GET", f"{base}/departments")  # department names are only listed here


def fetch_lever(src: dict, c: Client) -> None:
    jobs = c.call("GET", f"https://api.lever.co/v0/postings/{src['board']}", params={"mode": "json"})
    _check_size(src, len(jobs))


def fetch_ashby(src: dict, c: Client) -> None:
    data = c.call("GET", f"https://api.ashbyhq.com/posting-api/job-board/{src['board']}")
    _check_size(src, len(data["jobs"]))


def fetch_smartrecruiters(src: dict, c: Client) -> None:
    url = f"https://api.smartrecruiters.com/v1/companies/{src['board']}/postings"
    offset, total = 0, None
    while True:
        params = {"limit": 100, "offset": offset}
        if src.get("search"):
            params["q"] = src["search"]
        data = c.call("GET", url, params=params)
        if total is None:
            total = data.get("totalFound", 0)
            _check_size(src, total)
        offset += 100
        if not data.get("content") or offset >= total:
            break


def fetch_workday(src: dict, c: Client) -> None:
    url = f"https://{src['host']}/wday/cxs/{src['tenant']}/{src['site']}/jobs"
    page = 20  # the largest page Workday accepts

    def one_pass() -> tuple[int, set]:
        seen, total, offset = set(), None, 0
        while True:
            # The facet list (the board's filter menu) is identical on every
            # page and can be 200 KB; keep it on the first page only.
            data = c.call("POST", url, body={"appliedFacets": {}, "limit": page, "offset": offset,
                                             "searchText": src.get("search", "")},
                          drop=("facets",) if offset else ())
            if total is None:  # only the first page reliably carries the total
                total = data.get("total", 0)
                _check_size(src, total)
            posts = data.get("jobPostings") or []
            # A few entries carry only a requisition number (no title or link);
            # they count toward the total but are not postings anyone can open.
            seen.update(p.get("externalPath") or repr(p.get("bulletFields")) for p in posts)
            offset += page
            if not posts or offset >= total or offset > 6000:
                return total, seen

    total, seen = one_pass()
    if len(seen) < total:
        # Postings added or closed during paging shift the pages; a second
        # pass picks up anything the first one skipped.
        _, again = one_pass()
        seen |= again
    if len(seen) < 0.97 * total:
        raise SourceError(f"incomplete listing: {len(seen)} of {total} postings")


def fetch_oracle(src: dict, c: Client) -> None:
    url = f"https://{src['host']}/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
    limit, offset, total = 100, 0, None
    while True:
        finder = (f"findReqs;siteNumber={src['site']},limit={limit},offset={offset},"
                  "sortBy=POSTING_DATES_DESC")
        if src.get("search"):
            finder += f',keyword="{src["search"]}"'
        data = c.call("GET", url, params={"onlyData": "true", "expand": "requisitionList",
                                          "finder": finder})
        item = (data.get("items") or [{}])[0]
        if total is None:
            total = item.get("TotalJobsCount") or 0
            _check_size(src, total)
        offset += limit
        if not item.get("requisitionList") or offset >= total:
            break


FETCHERS = {
    "greenhouse": fetch_greenhouse,
    "lever": fetch_lever,
    "ashby": fetch_ashby,
    "smartrecruiters": fetch_smartrecruiters,
    "workday": fetch_workday,
    "oracle": fetch_oracle,
}


def board_url(src: dict) -> str:
    """Public board address; Workday and Oracle posting links are built from it."""
    if src.get("board_url"):
        return src["board_url"]
    if src["ats"] == "workday":
        return f"https://{src['host']}/{src['site']}"
    if src["ats"] == "oracle":
        return f"https://{src['host']}/hcmUI/CandidateExperience/en/sites/{src['site']}"
    return {
        "greenhouse": "https://boards.greenhouse.io/{}",
        "lever": "https://jobs.lever.co/{}",
        "ashby": "https://jobs.ashbyhq.com/{}",
        "smartrecruiters": "https://jobs.smartrecruiters.com/{}",
    }[src["ats"]].format(src["board"])


def fetch_source(src: dict, fetched_at: str) -> tuple[dict, dict | None]:
    """Fetch one source. Returns (result for the run log, raw envelope or None)."""
    started = time.monotonic()
    result = {"name": src["name"], "employer": src["employer"], "ats": src["ats"],
              "search": src.get("search", ""), "ok": False, "count": 0, "error": ""}
    client = Client()
    try:
        FETCHERS[src["ats"]](src, client)
        envelope = {
            "source": src["name"], "employer": src["employer"], "ats": src["ats"],
            "board": src.get("board", ""), "board_url": board_url(src),
            "search": src.get("search", ""), "fetched_at": fetched_at,
            "responses": client.responses,
        }
        count = len(normalize(envelope))
        if count == 0:
            # An empty board would mark every open posting as removed; treat
            # it as a failed fetch instead.
            raise SourceError("board returned no postings")
        result.update(ok=True, count=count)
    except Exception as exc:  # one source failing must not stop the run
        envelope = None
        result["error"] = f"{type(exc).__name__}: {exc}"[:300]
    result["requests"] = len(client.responses)
    result["seconds"] = round(time.monotonic() - started, 1)
    return result, envelope


def write_raw(envelope: dict, path: Path) -> None:
    payload = json.dumps(envelope, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(gzip.compress(payload, compresslevel=9, mtime=0))


def read_raw(path: Path) -> dict:
    return json.loads(gzip.decompress(path.read_bytes()).decode("utf-8"))


def run(data_dir: Path = config.DATA_DIR, sources: list[dict] | None = None,
        now: datetime | None = None, workers: int = 8, whole_day: bool = True) -> dict:
    """Fetch the sources and write that day's raw files and run log.

    whole_day=True (the daily run) replaces everything saved for the date, so a
    rerun leaves no stale files. whole_day=False (--only) replaces just the
    named sources and keeps the rest of the day.
    """
    sources = config.SOURCES if sources is None else sources
    now = now or datetime.now(timezone.utc)
    run_time = now.strftime("%Y-%m-%dT%H:%M:%SZ")
    day = now.date().isoformat()

    with ThreadPoolExecutor(max_workers=workers) as pool:
        outcomes = list(pool.map(lambda s: fetch_source(s, run_time), sources))

    day_dir = data_dir / "raw" / day
    log_path = data_dir / "runs" / f"{day}.json"
    kept = []
    if whole_day:
        if day_dir.exists():
            shutil.rmtree(day_dir)
    else:
        names = {s["name"] for s in sources}
        for name in names:
            (day_dir / f"{name}.json.gz").unlink(missing_ok=True)
        if log_path.exists():
            old = json.loads(log_path.read_text(encoding="utf-8"))["sources"]
            kept = [r for r in old if r["name"] not in names]
    for result, envelope in outcomes:
        if envelope is not None:
            write_raw(envelope, day_dir / f"{result['name']}.json.gz")

    order = {s["name"]: i for i, s in enumerate(config.SOURCES)}
    results = sorted(kept + [r for r, _ in outcomes], key=lambda r: order.get(r["name"], len(order)))
    log = {"run_time": run_time, "date": day, "sources": results}
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(json.dumps(log, indent=2) + "\n", encoding="utf-8")
    return log


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", type=Path, default=config.DATA_DIR)
    ap.add_argument("--only", help="comma-separated source names; replaces only their files for the day")
    args = ap.parse_args(argv)
    sources = config.SOURCES
    if args.only:
        wanted = set(args.only.split(","))
        sources = [s for s in sources if s["name"] in wanted]
    log = run(args.data_dir, sources, whole_day=not args.only)
    ok = sum(r["ok"] for r in log["sources"])
    print(f"{log['run_time']}: {ok}/{len(log['sources'])} sources ok")
    for r in log["sources"]:
        mark = "ok  " if r["ok"] else "FAIL"
        print(f"  {mark} {r['name']:16} {r['count']:6} postings  {r['requests']:4} requests  "
              f"{r['seconds']:6}s  {r['error']}")
    return 0  # failed sources are recorded, not fatal


if __name__ == "__main__":
    sys.exit(main())
