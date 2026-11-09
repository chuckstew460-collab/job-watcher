"""Conversion of each source (ATS) to the common columns."""
import json
from pathlib import Path

import pytest

from watcher.normalize import (COLUMNS, clean_location, normalize, utc_date, workday_id,
                               workday_posted)
from datetime import date

FIXTURES = Path(__file__).parent / "fixtures"


def load(name):
    return json.loads((FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def by_id(rows):
    return {r["source_id"]: r for r in rows}


def test_every_row_has_exactly_the_common_columns():
    for ats in ("greenhouse", "lever", "ashby", "smartrecruiters", "workday", "oracle"):
        for row in normalize(load(ats)):
            assert list(row) == COLUMNS, ats
            assert row["posting_id"] == f"{row['source']}:{row['source_id']}"


def test_greenhouse():
    rows = by_id(normalize(load("greenhouse")))
    assert rows["7370967"] == {
        "posting_id": "stripe:7370967", "source": "stripe", "source_id": "7370967",
        "employer": "Stripe", "title": "Data Analyst", "location": "New York, NY",
        "department": "Data Science",
        "posted_date": "2026-11-09",  # 21:50 at UTC-4 is 01:50 UTC the next day
        "url": "https://stripe.com/jobs/search?gh_jid=7370967",
    }
    other = rows["8172510"]
    assert other["title"] == "Abuse Investigator"  # whitespace and newline collapsed
    assert other["department"] == ""  # not in any department
    assert other["posted_date"] == ""  # board gave no date
    assert other["location"] == "Seattle, San Francisco, New York City"


def test_lever():
    rows = by_id(normalize(load("lever")))
    assert rows["6ed76ce8-4156-4b60-b120-403538bd66cd"] == {
        "posting_id": "palantir:6ed76ce8-4156-4b60-b120-403538bd66cd", "source": "palantir",
        "source_id": "6ed76ce8-4156-4b60-b120-403538bd66cd", "employer": "Palantir",
        "title": "Financial Analyst", "location": "Denver, CO", "department": "Business Operations",
        "posted_date": "2025-11-09",  # createdAt is epoch milliseconds
        "url": "https://jobs.lever.co/palantir/6ed76ce8-4156-4b60-b120-403538bd66cd",
    }
    # no department category -> falls back to team
    assert rows["2cd25c0b-088d-4a5c-9b96-1165a33fe652"]["department"] == "Dev"
    assert rows["2cd25c0b-088d-4a5c-9b96-1165a33fe652"]["posted_date"] == "2026-04-06"


def test_ashby():
    rows = by_id(normalize(load("ashby")))
    assert rows["34413f8d-26bf-4bbc-8ade-eb309a0e2245"] == {
        "posting_id": "ramp:34413f8d-26bf-4bbc-8ade-eb309a0e2245", "source": "ramp",
        "source_id": "34413f8d-26bf-4bbc-8ade-eb309a0e2245", "employer": "Ramp",
        "title": "Security Engineer, Cloud", "location": "New York, NY", "department": "Engineering",
        "posted_date": "2026-04-07",
        "url": "https://jobs.ashbyhq.com/ramp/34413f8d-26bf-4bbc-8ade-eb309a0e2245",
    }
    late = rows["9a1f0c2e-0000-4000-8000-000000000001"]
    assert late["posted_date"] == "2026-11-10"  # 23:30 at UTC-5 is the next UTC day
    assert late["location"] == "Remote (US)"


def test_smartrecruiters_reads_every_page():
    rows = by_id(normalize(load("smartrecruiters")))
    assert set(rows) == {"744000158367609", "744000160689629"}
    assert rows["744000158367609"] == {
        "posting_id": "experian:744000158367609", "source": "experian",
        "source_id": "744000158367609", "employer": "Experian", "title": "Data & Reporting Analyst",
        "location": "London, United Kingdom",  # 'LONDON, LONDON, United Kingdom' tidied
        "department": "Sales & Business Development", "posted_date": "2026-10-28",
        "url": "https://jobs.smartrecruiters.com/Experian/744000158367609",
    }
    # no fullLocation: built from city/region/country, US state shortened
    assert rows["744000160689629"]["location"] == "Charlotte, NC"
    assert rows["744000160689629"]["department"] == ""


def test_workday():
    rows = normalize(load("workday"))
    got = by_id(rows)
    # the entry with no link is skipped; the posting repeated on page 2 is kept once
    assert [r["source_id"] for r in rows] == ["R-12345", "R-22222-1", "R-33333", "R-55555"]
    assert got["R-12345"] == {
        "posting_id": "bank:R-12345", "source": "bank", "source_id": "R-12345",
        "employer": "Example Bank", "title": "Senior Financial Analyst", "location": "Charlotte, NC",
        "department": "",  # Workday's list has no department
        "posted_date": "2026-11-09",  # 'Posted Today' on a file fetched 2026-11-09
        "url": "https://bank.wd1.myworkdayjobs.com/External/job/Charlotte-NC/Senior-Financial-Analyst_R-12345",
    }
    # '3 Locations' -> primary location from the link, in the board's own spelling
    assert got["R-22222-1"]["location"] == "New York, NY"
    assert got["R-22222-1"]["posted_date"] == "2026-11-06"
    assert got["R-33333"]["posted_date"] == ""  # 'Posted 30+ Days Ago' has no exact date
    # primary location never spelled out elsewhere on the board -> de-slugged
    assert got["R-55555"]["location"] == "Austin TX"
    assert got["R-55555"]["posted_date"] == "2026-11-08"


def test_oracle():
    rows = by_id(normalize(load("oracle")))
    assert rows["210690282"] == {
        "posting_id": "jpmorgan:210690282", "source": "jpmorgan", "source_id": "210690282",
        "employer": "JPMorgan Chase", "title": "Asset Management - Data Analyst",
        "location": "New York, NY", "department": "Data & Analytics", "posted_date": "2026-11-09",
        "url": "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001/job/210690282",
    }
    assert rows["210788771"]["department"] == "Client Management"  # falls back to JobFamily
    assert rows["210788771"]["location"] == "Singapore"


@pytest.mark.parametrize("raw, expected", [
    ("New York, NY", "New York, NY"),
    ("Columbus, OH, United States", "Columbus, OH"),
    ("Purchase, New York", "Purchase, NY"),
    ("O'Fallon, Missouri, United States of America", "O'Fallon, MO"),
    ("LONDON, LONDON, United Kingdom", "London, United Kingdom"),
    ("São Paulo, , Brazil", "São Paulo, Brazil"),
    ("New York, NY (HQ)", "New York, NY"),
    ("San Francisco HQ", "San Francisco"),
    ("  Remote -\n USA ", "Remote - USA"),
    ("Washington, D.C.", "Washington, D.C."),
    ("", ""),
    (None, ""),
])
def test_clean_location(raw, expected):
    assert clean_location(raw) == expected


@pytest.mark.parametrize("raw, expected", [
    ("2026-11-09T23:30:00-05:00", "2026-11-10"),
    ("2026-11-09T01:00:00Z", "2026-11-09"),
    ("2026-11-09", "2026-11-09"),
    (1762650000000, "2025-11-09"),
    (None, ""),
    ("not a date", ""),
])
def test_utc_date(raw, expected):
    assert utc_date(raw) == expected


@pytest.mark.parametrize("text, expected", [
    ("Posted Today", "2026-11-09"),
    ("Posted Yesterday", "2026-11-08"),
    ("Posted 1 Day Ago", "2026-11-08"),
    ("Posted 12 Days Ago", "2026-10-28"),
    ("Posted 30+ Days Ago", ""),
    ("", ""),
])
def test_workday_posted(text, expected):
    assert workday_posted(text, date(2026, 11, 9)) == expected


def test_workday_id():
    assert workday_id("/job/London-Eng/Lead-Engineer---Services_R232131-1") == "R232131-1"
    assert workday_id("/job/San-Mateo-CA/Associate_JR042962") == "JR042962"
    assert workday_id("/job/Somewhere/NoUnderscore") == "NoUnderscore"
