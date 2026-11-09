"""The history build: first_seen, last_seen, removed, reopened, first_run, and rebuilds."""
import watcher.build as build
from watcher.build import COLUMNS, build_history, read_history, write_history

D1, D2, D3, D4 = "2026-11-01", "2026-11-02", "2026-11-03", "2026-11-04"


def history(data_dir):
    return {r["posting_id"]: r for r in build_history(data_dir / "raw")}


def test_first_seen_and_last_seen(put, data_dir):
    put(D1, "acme", [(1, "Data Analyst"), (2, "Teller")])
    put(D2, "acme", [(1, "Data Analyst"), (2, "Teller"), (3, "Financial Analyst")])
    h = history(data_dir)
    assert h["acme:1"]["first_seen"] == D1 and h["acme:1"]["last_seen"] == D2
    assert h["acme:3"]["first_seen"] == D2 and h["acme:3"]["last_seen"] == D2
    assert all(r["status"] == "open" and r["removed_date"] == "" for r in h.values())


def test_first_run_marks_postings_in_the_sources_first_raw_file(put, data_dir):
    put(D1, "acme", [(1, "A")])
    put(D2, "acme", [(1, "A"), (2, "B")])
    put(D2, "zeta", [(9, "Z")])  # zeta's first raw file is on D2
    put(D3, "zeta", [(9, "Z"), (10, "Y")])
    h = history(data_dir)
    assert h["acme:1"]["first_run"] is True
    assert h["acme:2"]["first_run"] is False
    assert h["zeta:9"]["first_run"] is True and h["zeta:9"]["first_seen"] == D2
    assert h["zeta:10"]["first_run"] is False


def test_posting_no_longer_listed_is_removed(put, data_dir):
    put(D1, "acme", [(1, "A"), (2, "B")])
    put(D2, "acme", [(1, "A")])
    h = history(data_dir)
    assert h["acme:2"]["status"] == "removed"
    assert h["acme:2"]["removed_date"] == D2
    assert h["acme:2"]["last_seen"] == D1  # last day it was listed
    assert h["acme:1"]["status"] == "open"


def test_removed_posting_listed_again_reopens(put, data_dir):
    put(D1, "acme", [(1, "A"), (2, "B")])
    put(D2, "acme", [(1, "A")])
    put(D3, "acme", [(1, "A"), (2, "B")])
    row = history(data_dir)["acme:2"]
    assert row["status"] == "open"
    assert row["removed_date"] == ""
    assert row["first_seen"] == D1  # unchanged
    assert row["last_seen"] == D3
    assert row["first_run"] is True


def test_source_without_a_raw_file_changes_nothing(put, data_dir):
    put(D1, "acme", [(1, "A")])
    put(D1, "zeta", [(9, "Z")])
    put(D2, "acme", [(1, "A")])  # zeta failed on D2: no raw file
    put(D3, "acme", [(1, "A")])
    put(D3, "zeta", [(9, "Z")])
    h = history(data_dir)
    assert h["zeta:9"]["status"] == "open"
    assert h["zeta:9"]["last_seen"] == D3
    put(D4, "acme", [])  # an empty listing does remove (fetch.py refuses to save one)
    h = history(data_dir)
    assert h["acme:1"]["status"] == "removed" and h["acme:1"]["removed_date"] == D4
    assert h["zeta:9"]["status"] == "open"  # zeta has no D4 file


def test_removal_only_touches_its_own_source(put, data_dir):
    put(D1, "acme", [(1, "A")])
    put(D1, "zeta", [(1, "A")])  # same source id, different source
    put(D2, "acme", [(1, "A")])
    put(D2, "zeta", [(2, "B")])
    h = history(data_dir)
    assert h["acme:1"]["status"] == "open"
    assert h["zeta:1"]["status"] == "removed"


def test_latest_title_wins_and_in_role_follows_it(put, data_dir):
    put(D1, "acme", [(1, "Analyst")])
    put(D2, "acme", [(1, "Senior Data Analyst", "Chicago, IL")])
    row = history(data_dir)["acme:1"]
    assert row["title"] == "Senior Data Analyst"
    assert row["location"] == "Chicago, IL"
    assert row["in_role"] is True


def test_posted_date_keeps_first_value(data_dir, make_env):
    from watcher.fetch import write_raw
    for day, published in ((D1, "2026-10-30T12:00:00Z"), (D2, None), (D3, "2026-11-03T12:00:00Z")):
        env = make_env("acme", [(1, "A")], fetched_at=f"{day}T12:00:00Z")
        env["responses"][0]["json"]["jobs"][0]["first_published"] = published
        write_raw(env, data_dir / "raw" / day / "acme.json.gz")
    assert history(data_dir)["acme:1"]["posted_date"] == "2026-10-30"


def test_rows_sorted_by_posting_id(put, data_dir):
    put(D1, "zeta", [(5, "E"), (1, "A")])
    put(D1, "acme", [(30, "C"), (4, "D")])
    ids = [r["posting_id"] for r in build_history(data_dir / "raw")]
    assert ids == sorted(ids) == ["acme:30", "acme:4", "zeta:1", "zeta:5"]


def test_csv_columns_and_values(put, data_dir):
    put(D1, "acme", [(1, "Data Analyst"), (2, "Teller")])
    put(D2, "acme", [(1, "Data Analyst")])
    path = data_dir / "history.csv"
    write_history(build_history(data_dir / "raw"), path)
    assert path.read_text(encoding="utf-8").splitlines()[0] == ",".join(COLUMNS)
    rows = {r["posting_id"]: r for r in read_history(path)}
    assert rows["acme:1"]["in_role"] == "true" and rows["acme:1"]["first_run"] == "true"
    assert rows["acme:2"]["in_role"] == "false"
    assert rows["acme:2"]["status"] == "removed" and rows["acme:2"]["removed_date"] == D2
    assert b"\r\n" not in path.read_bytes()


def test_rebuild_reproduces_the_same_file(put, data_dir):
    put(D1, "acme", [(1, "Data Analyst"), (2, "Teller, Part-time \"Float\"")])
    put(D2, "acme", [(1, "Data Analyst"), (3, "Financial Analyst")])
    put(D2, "zeta", [(9, "BI Analyst", "London, United Kingdom")])
    path = data_dir / "history.csv"
    write_history(build_history(data_dir / "raw"), path)
    first = path.read_bytes()
    path.unlink()
    write_history(build_history(data_dir / "raw"), path)
    assert path.read_bytes() == first


def test_title_rule_change_applies_to_every_day(put, data_dir, monkeypatch):
    put(D1, "acme", [(1, "Teller")])
    put(D2, "acme", [(2, "Data Analyst")])
    monkeypatch.setattr(build, "in_role", lambda title: "Teller" in title)
    h = history(data_dir)
    assert h["acme:1"]["in_role"] is True and h["acme:2"]["in_role"] is False


def test_folders_that_are_not_dates_or_are_empty_are_ignored(put, data_dir):
    put(D1, "acme", [(1, "A")])
    (data_dir / "raw" / "notes").mkdir()
    (data_dir / "raw" / D2).mkdir()  # a day where every source failed
    put(D3, "acme", [(1, "A")])
    days = [d for d, _ in build.raw_days(data_dir / "raw")]
    assert days == [D1, D3]
