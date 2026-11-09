"""The fetch step: one failing source never stops the run, and reruns replace the day."""
import json
from datetime import datetime, timezone

import pytest
import requests

import watcher.fetch as fetch
from watcher.fetch import SourceError, read_raw

NOW = datetime(2026, 11, 9, 13, 5, tzinfo=timezone.utc)
DAY = "2026-11-09"


def src(name):
    return {"name": name, "employer": name.title(), "ats": "greenhouse", "board": name}


@pytest.fixture
def boards(monkeypatch):
    """Fake Greenhouse: boards[name] = list of titles, or an exception to raise."""
    boards = {}

    def fake(source, client):
        listing = boards[source["name"]]
        if isinstance(listing, Exception):
            raise listing
        jobs = [{"id": i, "title": t, "location": {"name": "Remote"}, "absolute_url": f"u/{i}"}
                for i, t in enumerate(listing, 1)]
        client.responses.append({"request": {"method": "GET", "url": "jobs"}, "json": {"jobs": jobs}})
        client.responses.append({"request": {"method": "GET", "url": "departments"},
                                 "json": {"departments": []}})

    monkeypatch.setitem(fetch.FETCHERS, "greenhouse", fake)
    return boards


def test_one_failing_source_does_not_stop_the_run(boards, tmp_path):
    boards.update(good=["Data Analyst", "Teller"], bad=requests.ConnectionError("refused"),
                  other=["Financial Analyst"])
    log = fetch.run(tmp_path, [src("good"), src("bad"), src("other")], now=NOW)
    day = tmp_path / "raw" / DAY
    assert sorted(p.name for p in day.iterdir()) == ["good.json.gz", "other.json.gz"]
    results = {r["name"]: r for r in log["sources"]}
    assert results["good"]["ok"] and results["good"]["count"] == 2
    assert results["other"]["ok"] and results["other"]["count"] == 1
    assert not results["bad"]["ok"] and results["bad"]["count"] == 0
    assert "ConnectionError" in results["bad"]["error"]
    # every result, success or failure, is recorded in the run log
    saved = json.loads((tmp_path / "runs" / f"{DAY}.json").read_text(encoding="utf-8"))
    assert [r["name"] for r in saved["sources"]] == ["good", "bad", "other"]
    assert saved["run_time"] == "2026-11-09T13:05:00Z"


def test_raw_file_keeps_what_the_board_returned(boards, tmp_path):
    boards.update(good=["Data Analyst"])
    fetch.run(tmp_path, [src("good")], now=NOW)
    env = read_raw(tmp_path / "raw" / DAY / "good.json.gz")
    assert env["source"] == "good" and env["ats"] == "greenhouse"
    assert env["fetched_at"] == "2026-11-09T13:05:00Z"
    assert env["responses"][0]["json"]["jobs"][0]["title"] == "Data Analyst"


def test_empty_board_counts_as_a_failure(boards, tmp_path):
    boards.update(empty=[])
    log = fetch.run(tmp_path, [src("empty")], now=NOW)
    assert not log["sources"][0]["ok"]
    assert "no postings" in log["sources"][0]["error"]
    assert not (tmp_path / "raw" / DAY / "empty.json.gz").exists()


def test_second_run_same_day_replaces_the_days_files(boards, tmp_path):
    boards.update(a=["X"], b=["Y"])
    fetch.run(tmp_path, [src("a"), src("b")], now=NOW)
    boards.update(b=RuntimeError("down"))
    log = fetch.run(tmp_path, [src("a"), src("b")], now=NOW.replace(hour=20))
    assert [p.name for p in (tmp_path / "raw" / DAY).iterdir()] == ["a.json.gz"]
    assert log["run_time"] == "2026-11-09T20:05:00Z"
    assert [r["ok"] for r in log["sources"]] == [True, False]


def test_partial_run_replaces_only_named_sources(boards, tmp_path):
    boards.update(a=["X"], b=RuntimeError("down"))
    fetch.run(tmp_path, [src("a"), src("b")], now=NOW)
    boards.update(b=["Y"])
    log = fetch.run(tmp_path, [src("b")], now=NOW, whole_day=False)
    assert sorted(p.name for p in (tmp_path / "raw" / DAY).iterdir()) == ["a.json.gz", "b.json.gz"]
    assert {r["name"]: r["ok"] for r in log["sources"]} == {"a": True, "b": True}


def test_boards_over_5000_need_a_search_term():
    with pytest.raises(SourceError, match="search term"):
        fetch._check_size({"name": "big"}, 7075)
    fetch._check_size({"name": "big", "search": "analyst"}, 7075)  # allowed with a term
    fetch._check_size({"name": "small"}, 5000)


def test_every_configured_source_has_a_fetcher_and_a_converter():
    from watcher import config
    from watcher.normalize import CONVERTERS
    names = [s["name"] for s in config.SOURCES]
    assert len(names) == len(set(names)) >= 15
    assert len({s["employer"] for s in config.SOURCES}) >= 15
    for s in config.SOURCES:
        assert s["ats"] in fetch.FETCHERS and s["ats"] in CONVERTERS
        assert fetch.board_url(s).startswith("https://")
