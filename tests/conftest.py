"""Helpers that write small raw files, shaped like fetch.py's, into a temp data folder."""
import json

import pytest

from watcher.fetch import write_raw


def greenhouse_env(source, jobs, fetched_at="2026-11-01T12:00:00Z", employer=None):
    """A Greenhouse-style envelope. jobs: list of (id, title) or (id, title, location)."""
    listed = []
    for job in jobs:
        jid, title, *rest = job
        listed.append({"id": jid, "title": title, "location": {"name": rest[0] if rest else "New York, NY"},
                       "absolute_url": f"https://example.com/{source}/{jid}",
                       "first_published": None})
    return {
        "source": source, "employer": employer or source.title(), "ats": "greenhouse",
        "board": source, "board_url": f"https://boards.greenhouse.io/{source}", "search": "",
        "fetched_at": fetched_at,
        "responses": [{"request": {"method": "GET", "url": "jobs"}, "json": {"jobs": listed}},
                      {"request": {"method": "GET", "url": "departments"}, "json": {"departments": []}}],
    }


@pytest.fixture
def make_env():
    return greenhouse_env


@pytest.fixture
def data_dir(tmp_path):
    d = tmp_path / "data"
    (d / "raw").mkdir(parents=True)
    return d


@pytest.fixture
def put(data_dir):
    """put(day, source, jobs) writes data/raw/<day>/<source>.json.gz."""
    def _put(day, source, jobs, **kw):
        env = greenhouse_env(source, jobs, fetched_at=f"{day}T12:00:00Z", **kw)
        write_raw(env, data_dir / "raw" / day / f"{source}.json.gz")
    return _put


@pytest.fixture
def log(data_dir):
    """log(day, [(name, ok, count), ...]) writes the run log fetch.py would write."""
    def _log(day, results, run_time=None):
        entries = [{"name": n, "employer": n.title(), "ats": "greenhouse", "search": "", "ok": ok,
                    "count": count, "error": "" if ok else "HTTPError: 503", "requests": 1, "seconds": 0.1}
                   for n, ok, count in results]
        path = data_dir / "runs" / f"{day}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"run_time": run_time or f"{day}T13:00:00Z", "date": day,
                                    "sources": entries}), encoding="utf-8")
    return _log
