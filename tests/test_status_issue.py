"""The status file and the daily issue body."""
from watcher.build import build_history, read_history, write_history
from watcher.issue import render
from watcher.status import build_status

D1, D2, D3 = "2026-11-01", "2026-11-02", "2026-11-03"


def build(data_dir):
    write_history(build_history(data_dir / "raw"), data_dir / "history.csv")


def test_status_counts(put, log, data_dir):
    put(D1, "acme", [(1, "Data Analyst"), (2, "Teller"), (3, "Clerk")])
    put(D2, "acme", [(1, "Data Analyst"), (2, "Teller"), (4, "Financial Analyst"), (5, "Cook")])
    put(D2, "zeta", [(9, "BI Analyst")])  # zeta's first file: first-run, not new
    log(D2, [("acme", True, 4), ("zeta", True, 1), ("omega", False, 0)])
    build(data_dir)
    s = build_status(data_dir)
    assert s["run_time"] == f"{D2}T13:00:00Z" and s["run_date"] == D2
    assert s["first_run_date"] == D1
    assert s["days_with_success"] == 2
    assert s["open"] == 5            # 1, 2, 4, 5, 9
    assert s["new_today"] == 2       # 4 and 5; zeta:9 is a first-run posting
    assert s["removed_today"] == 1   # 3
    assert s["in_role"] == {"open": 3, "new_today": 1, "removed_today": 0}
    assert s["sources"][2] == {"name": "omega", "employer": "Omega", "ats": "greenhouse",
                               "ok": False, "count": 0, "error": "HTTPError: 503"}
    assert set(s) >= {"run_time", "first_run_date", "days_with_success", "open", "new_today",
                      "removed_today", "sources"}


def test_day_with_every_source_failing_is_not_a_success(put, log, data_dir):
    put(D1, "acme", [(1, "A")])
    (data_dir / "raw" / D2).mkdir()
    log(D2, [("acme", False, 0)])
    build(data_dir)
    s = build_status(data_dir)
    assert s["days_with_success"] == 1
    assert s["run_date"] == D2 and s["new_today"] == 0 and s["open"] == 1


def status_and_rows(put, log, data_dir):
    put(D1, "acme", [(1, "Data Analyst"), (2, "Teller [Part-time]")])
    put(D2, "acme", [(1, "Data Analyst"), (3, "Financial Analyst"), (4, "Cook")])
    log(D2, [("acme", True, 3), ("zeta", False, 0)])
    build(data_dir)
    return build_status(data_dir), read_history(data_dir / "history.csv")


def test_issue_lists_new_and_removed_with_links(put, log, data_dir):
    status, rows = status_and_rows(put, log, data_dir)
    body = render(status, rows, "https://site/")
    assert "## New postings (2)" in body
    assert "- [Financial Analyst](https://example.com/acme/3) — Acme · New York, NY" in body
    assert "- [Cook](https://example.com/acme/4)" in body
    assert "## Removed postings (1)" in body
    assert "- [Teller \\[Part-time\\]](https://example.com/acme/2)" in body  # brackets escaped
    assert "Data Analyst](" not in body  # neither new nor removed
    assert "Zeta (greenhouse): HTTPError: 503" in body


def test_issue_on_a_quiet_day_still_has_a_body(put, log, data_dir):
    put(D1, "acme", [(1, "A")])
    log(D1, [("acme", True, 1)])
    build(data_dir)
    body = render(build_status(data_dir), read_history(data_dir / "history.csv"), "https://site/")
    assert "## New postings (0)" in body and "## Removed postings (0)" in body
    assert "_None._" in body


def test_issue_body_is_truncated_to_fit(put, log, data_dir):
    put(D1, "acme", [(1, "Seed")])
    put(D2, "acme", [(1, "Seed")] + [(i, f"Long posting title number {i}") for i in range(2, 600)])
    log(D2, [("acme", True, 599)])
    build(data_dir)
    body = render(build_status(data_dir), read_history(data_dir / "history.csv"), "https://site/",
                  limit=5000)
    assert len(body) <= 5000
    assert "more on the site" in body
    assert "## New postings (598)" in body
