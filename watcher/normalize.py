"""Convert one raw file (one source, one day) into rows with the common columns.

Every raw file is an envelope written by fetch.py:

    {"source": ..., "employer": ..., "ats": ..., "board_url": ..., "search": ...,
     "fetched_at": "2026-11-09T13:05:00Z",
     "responses": [{"request": {...}, "json": <what the board returned>}, ...]}

Each ATS has one converter. A converter reads only the envelope, so the
history can always be rebuilt from the raw files alone. Every posting the
board returned is kept; the role rule is applied later, in build.py.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timedelta, timezone

COLUMNS = ["posting_id", "source", "source_id", "employer", "title", "location",
           "department", "posted_date", "url"]

US_COUNTRY = {"united states", "united states of america", "usa", "us"}
US_STATES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR", "california": "CA",
    "colorado": "CO", "connecticut": "CT", "delaware": "DE", "district of columbia": "DC",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID", "illinois": "IL",
    "indiana": "IN", "iowa": "IA", "kansas": "KS", "kentucky": "KY", "louisiana": "LA",
    "maine": "ME", "maryland": "MD", "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
    "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK", "oregon": "OR",
    "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC", "south dakota": "SD",
    "tennessee": "TN", "texas": "TX", "utah": "UT", "vermont": "VT", "virginia": "VA",
    "washington": "WA", "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
}


def clean(value) -> str:
    """Collapse whitespace (including newlines) so every value fits on one CSV line."""
    if value is None:
        return ""
    return " ".join(str(value).split())


def clean_location(value) -> str:
    """Make one board's location text comparable with another's.

    'LONDON, LONDON, United Kingdom' -> 'London, United Kingdom'
    'Purchase, New York'             -> 'Purchase, NY'
    'Columbus, OH, United States'    -> 'Columbus, OH'
    'New York, NY (HQ)'              -> 'New York, NY'
    'Sao Paulo, , Brazil'            -> 'Sao Paulo, Brazil'
    """
    text = re.sub(r"\s*\(HQ\)$|\s+HQ$", "", clean(value))
    parts = []
    for part in (p.strip() for p in text.split(",")):
        if len(part) > 3 and part.isupper():
            part = part.title()
        if part and not (parts and parts[-1].lower() == part.lower()):
            parts.append(part)
    if len(parts) > 1 and parts[-1].lower() in US_COUNTRY:
        parts.pop()
    if len(parts) == 2 and parts[1].lower() in US_STATES:
        parts[1] = US_STATES[parts[1].lower()]
    return ", ".join(parts)


def utc_date(value) -> str:
    """ISO timestamp (any offset) or epoch milliseconds -> UTC date 'YYYY-MM-DD'."""
    if value in (None, ""):
        return ""
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc).date().isoformat()
    text = str(value).strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return text
    try:
        stamp = datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError:
        return ""
    if stamp.tzinfo is None:
        stamp = stamp.replace(tzinfo=timezone.utc)
    return stamp.astimezone(timezone.utc).date().isoformat()


def workday_posted(text: str, fetched: date) -> str:
    """Workday lists a relative age ('Posted Today', 'Posted 3 Days Ago').

    Turn it into a date using the day the raw file was fetched. 'Posted 30+
    Days Ago' has no exact date, so it is left empty.
    """
    t = (text or "").lower()
    if "today" in t:
        return fetched.isoformat()
    if "yesterday" in t:
        return (fetched - timedelta(days=1)).isoformat()
    m = re.search(r"(\d+)(\+?)\s+days?\s+ago", t)
    if m and not m.group(2):
        return (fetched - timedelta(days=int(m.group(1)))).isoformat()
    return ""


def _row(env: dict, source_id, title, location, department, posted_date, url) -> dict:
    sid = clean(source_id)
    return {
        "posting_id": f"{env['source']}:{sid}",
        "source": env["source"],
        "source_id": sid,
        "employer": env["employer"],
        "title": clean(title),
        "location": clean_location(location),
        "department": clean(department),
        "posted_date": posted_date or "",
        "url": clean(url),
    }


def _payloads(env: dict):
    return [r["json"] for r in env["responses"]]


# ---------------------------------------------------------------- Greenhouse
def greenhouse(env: dict) -> list[dict]:
    """responses[0] = /jobs, responses[1] = /departments (maps job id -> department)."""
    payloads = _payloads(env)
    jobs = payloads[0]["jobs"]
    dept_of: dict[int, list[str]] = {}
    for payload in payloads[1:]:
        for dept in payload.get("departments", []):
            for job in dept.get("jobs", []):
                dept_of.setdefault(job["id"], []).append(clean(dept["name"]))
    rows = []
    for job in jobs:
        rows.append(_row(env, job["id"], job.get("title"),
                         (job.get("location") or {}).get("name"),
                         "; ".join(dept_of.get(job["id"], [])),
                         utc_date(job.get("first_published")),
                         job.get("absolute_url")))
    return rows


# --------------------------------------------------------------------- Lever
def lever(env: dict) -> list[dict]:
    rows = []
    for payload in _payloads(env):
        for job in payload:
            cats = job.get("categories") or {}
            rows.append(_row(env, job["id"], job.get("text"), cats.get("location"),
                             cats.get("department") or cats.get("team"),
                             utc_date(job.get("createdAt")), job.get("hostedUrl")))
    return rows


# --------------------------------------------------------------------- Ashby
def ashby(env: dict) -> list[dict]:
    rows = []
    for payload in _payloads(env):
        for job in payload.get("jobs", []):
            rows.append(_row(env, job["id"], job.get("title"), job.get("location"),
                             job.get("department"), utc_date(job.get("publishedAt")),
                             job.get("jobUrl")))
    return rows


# ----------------------------------------------------------- SmartRecruiters
def smartrecruiters(env: dict) -> list[dict]:
    rows = []
    for payload in _payloads(env):
        for job in payload.get("content", []):
            loc = job.get("location") or {}
            where = loc.get("fullLocation") or ", ".join(
                p for p in (loc.get("city"), loc.get("region"), (loc.get("country") or "").upper()) if p)
            company = (job.get("company") or {}).get("identifier") or env.get("board", "")
            rows.append(_row(env, job["id"], job.get("name"), where,
                             (job.get("department") or {}).get("label"),
                             utc_date(job.get("releasedDate")),
                             f"https://jobs.smartrecruiters.com/{company}/{job['id']}"))
    return rows


# ------------------------------------------------------------------- Workday
def workday_id(external_path: str) -> str:
    """'/job/New-York-NY/Financial-Analyst_R123456-1' -> 'R123456-1'."""
    tail = external_path.rstrip("/").rsplit("/", 1)[-1]
    return tail.rsplit("_", 1)[-1] if "_" in tail else tail


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (text or "").lower()).strip("-")


def workday(env: dict) -> list[dict]:
    """Workday's list gives a title, a link path, a location and a relative age.

    A posting open in several places shows only '3 Locations'; its link path
    starts with the primary location ('/job/Charlotte-NC/...'), which is used
    instead, matched back to that board's own spelling of the place.
    """
    fetched = date.fromisoformat(utc_date(env["fetched_at"]))
    base = env["board_url"].rstrip("/")
    jobs = [j for p in _payloads(env) for j in (p.get("jobPostings") or []) if j.get("externalPath")]
    spelled = {}
    for job in jobs:
        spelled.setdefault(_slug(job.get("locationsText")), job.get("locationsText"))
    rows = []
    for job in jobs:
        path, where = job["externalPath"], job.get("locationsText") or ""
        if re.fullmatch(r"\d+ Locations", where.strip()):
            primary = path.split("/")[2] if path.startswith("/job/") else ""
            where = spelled.get(_slug(primary)) or primary.replace("-", " ")
        rows.append(_row(env, workday_id(path), job.get("title"), where,
                         "", workday_posted(job.get("postedOn"), fetched), base + path))
    return rows


# -------------------------------------------------------------------- Oracle
def oracle(env: dict) -> list[dict]:
    base = env["board_url"].rstrip("/")
    rows = []
    for payload in _payloads(env):
        for item in payload.get("items", []):
            for job in item.get("requisitionList") or []:
                rows.append(_row(env, job["Id"], job.get("Title"), job.get("PrimaryLocation"),
                                 job.get("JobFunction") or job.get("JobFamily"),
                                 utc_date(job.get("PostedDate")), f"{base}/job/{job['Id']}"))
    return rows


CONVERTERS = {
    "greenhouse": greenhouse,
    "lever": lever,
    "ashby": ashby,
    "smartrecruiters": smartrecruiters,
    "workday": workday,
    "oracle": oracle,
}


def normalize(env: dict) -> list[dict]:
    """All postings in one raw file, in the common columns, one row per posting_id."""
    rows, seen = [], set()
    for row in CONVERTERS[env["ats"]](env):
        if row["source_id"] and row["posting_id"] not in seen:
            seen.add(row["posting_id"])
            rows.append(row)
    return rows
