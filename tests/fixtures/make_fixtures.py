"""Writes the raw-file fixtures used by test_normalize.py.

Each fixture is one raw envelope, shaped exactly like the files fetch.py saves,
holding a few real-looking records from one ATS (descriptions trimmed).
Run `python tests/fixtures/make_fixtures.py` to regenerate them.
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def env(source, employer, ats, board_url, responses, board="", search=""):
    return {"source": source, "employer": employer, "ats": ats, "board": board, "board_url": board_url,
            "search": search, "fetched_at": "2026-11-09T13:05:00Z", "responses": responses}


FIXTURES = {}

FIXTURES["greenhouse"] = env("stripe", "Stripe", "greenhouse", "https://boards.greenhouse.io/stripe", [
    {"request": {"method": "GET", "url": "https://boards-api.greenhouse.io/v1/boards/stripe/jobs"},
     "json": {"jobs": [
         {"absolute_url": "https://stripe.com/jobs/search?gh_jid=7370967", "internal_job_id": 3537063,
          "location": {"name": "New York, NY"}, "metadata": None, "id": 7370967,
          "updated_at": "2026-11-08T22:10:00-04:00", "requisition_id": "R-1", "title": "Data Analyst",
          "company_name": "Stripe", "first_published": "2026-11-08T21:50:29-04:00"},
         {"absolute_url": "https://stripe.com/jobs/search?gh_jid=8172510", "internal_job_id": 3537064,
          "location": {"name": "Seattle, San Francisco, New York City"}, "metadata": None, "id": 8172510,
          "updated_at": "2026-10-29T10:42:09-04:00", "requisition_id": "R-2",
          "title": "  Abuse\n Investigator ", "company_name": "Stripe", "first_published": None}],
         "meta": {"total": 2}}},
    {"request": {"method": "GET", "url": "https://boards-api.greenhouse.io/v1/boards/stripe/departments"},
     "json": {"departments": [
         {"id": 81946, "name": "Data Science", "parent_id": None, "child_ids": [],
          "jobs": [{"id": 7370967, "title": "Data Analyst"}]},
         {"id": 0, "name": "No Department", "parent_id": None, "child_ids": [], "jobs": []}]}},
], board="stripe")

FIXTURES["lever"] = env("palantir", "Palantir", "lever", "https://jobs.lever.co/palantir", [
    {"request": {"method": "GET", "url": "https://api.lever.co/v0/postings/palantir",
                 "params": {"mode": "json"}},
     "json": [
         {"id": "6ed76ce8-4156-4b60-b120-403538bd66cd", "text": "Financial Analyst",
          "categories": {"commitment": "Full-time", "location": "Denver, CO", "team": "Finance",
                         "department": "Business Operations", "allLocations": ["Denver, CO"]},
          "createdAt": 1762650000000, "descriptionPlain": "Long text...",
          "hostedUrl": "https://jobs.lever.co/palantir/6ed76ce8-4156-4b60-b120-403538bd66cd",
          "applyUrl": "https://jobs.lever.co/palantir/6ed76ce8-4156-4b60-b120-403538bd66cd/apply"},
         {"id": "2cd25c0b-088d-4a5c-9b96-1165a33fe652", "text": "Backend Software Engineer",
          "categories": {"commitment": "Full-time", "location": "London, United Kingdom", "team": "Dev"},
          "createdAt": 1775467200000, "descriptionPlain": "Long text...",
          "hostedUrl": "https://jobs.lever.co/palantir/2cd25c0b-088d-4a5c-9b96-1165a33fe652"}]},
], board="palantir")

FIXTURES["ashby"] = env("ramp", "Ramp", "ashby", "https://jobs.ashbyhq.com/ramp", [
    {"request": {"method": "GET", "url": "https://api.ashbyhq.com/posting-api/job-board/ramp"},
     "json": {"apiVersion": "1", "jobs": [
         {"id": "34413f8d-26bf-4bbc-8ade-eb309a0e2245", "title": " Security Engineer, Cloud",
          "department": "Engineering", "team": "Backend", "employmentType": "FullTime",
          "location": "New York, NY (HQ)", "publishedAt": "2026-04-07T17:12:35.753+00:00",
          "isListed": True,
          "jobUrl": "https://jobs.ashbyhq.com/ramp/34413f8d-26bf-4bbc-8ade-eb309a0e2245",
          "descriptionPlain": "Long text..."},
         {"id": "9a1f0c2e-0000-4000-8000-000000000001", "title": "Strategic Finance Analyst",
          "department": "Finance", "team": "FP&A", "employmentType": "FullTime",
          "location": "Remote (US)", "publishedAt": "2026-11-09T23:30:00.000-05:00", "isListed": True,
          "jobUrl": "https://jobs.ashbyhq.com/ramp/9a1f0c2e-0000-4000-8000-000000000001"}]}},
], board="ramp")

SR_URL = "https://api.smartrecruiters.com/v1/companies/Experian/postings"
FIXTURES["smartrecruiters"] = env("experian", "Experian", "smartrecruiters",
                                  "https://jobs.smartrecruiters.com/Experian", [
    {"request": {"method": "GET", "url": SR_URL, "params": {"limit": 100, "offset": 0}},
     "json": {"offset": 0, "limit": 100, "totalFound": 2, "content": [
         {"id": "744000158367609", "name": "Data & Reporting Analyst", "refNumber": "REF1",
          "company": {"identifier": "Experian", "name": "Experian"},
          "releasedDate": "2026-10-28T09:00:00.000Z",
          "location": {"city": "London", "region": "London", "country": "gb", "remote": False,
                       "fullLocation": "LONDON, LONDON, United Kingdom"},
          "department": {"id": "1", "label": "Sales & Business Development"}}]}},
    {"request": {"method": "GET", "url": SR_URL, "params": {"limit": 100, "offset": 100}},
     "json": {"offset": 100, "limit": 100, "totalFound": 2, "content": [
         {"id": "744000160689629", "name": "Product Operations Coordinator", "refNumber": "REF2",
          "company": {"identifier": "Experian", "name": "Experian"},
          "releasedDate": "2026-11-09T18:17:19.039Z",
          "location": {"city": "Charlotte", "region": "North Carolina", "country": "us",
                       "remote": False}}]}},
], board="Experian")

WD_URL = "https://bank.wd1.myworkdayjobs.com/wday/cxs/bank/External/jobs"
FIXTURES["workday"] = env("bank", "Example Bank", "workday", "https://bank.wd1.myworkdayjobs.com/External", [
    {"request": {"method": "POST", "url": WD_URL,
                 "body": {"appliedFacets": {}, "limit": 20, "offset": 0, "searchText": ""}},
     "json": {"total": 5, "facets": [{"facetParameter": "locations", "values": []}],
              "userAuthenticated": False, "jobPostings": [
         {"title": "Senior Financial Analyst",
          "externalPath": "/job/Charlotte-NC/Senior-Financial-Analyst_R-12345",
          "locationsText": "Charlotte, NC", "postedOn": "Posted Today", "bulletFields": ["R-12345"]},
         {"title": "Data Analyst", "externalPath": "/job/New-York-NY/Data-Analyst_R-22222-1",
          "locationsText": "3 Locations", "postedOn": "Posted 3 Days Ago", "bulletFields": ["R-22222"]},
         {"title": "Teller", "externalPath": "/job/New-York-NY/Teller_R-33333",
          "locationsText": "New York, NY", "postedOn": "Posted 30+ Days Ago",
          "bulletFields": ["R-33333"]},
         {"bulletFields": ["R-44444"]}]}},
    {"request": {"method": "POST", "url": WD_URL,
                 "body": {"appliedFacets": {}, "limit": 20, "offset": 20, "searchText": ""}},
     "json": {"total": 5, "userAuthenticated": False, "jobPostings": [
         {"title": "Senior Financial Analyst",
          "externalPath": "/job/Charlotte-NC/Senior-Financial-Analyst_R-12345",
          "locationsText": "Charlotte, NC", "postedOn": "Posted Today", "bulletFields": ["R-12345"]},
         {"title": "Branch Manager", "externalPath": "/job/Austin-TX/Branch-Manager_R-55555",
          "locationsText": "2 Locations", "postedOn": "Posted Yesterday",
          "bulletFields": ["R-55555"]}]}},
])

ORA_URL = "https://jpmc.fa.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions"
FIXTURES["oracle"] = env("jpmorgan", "JPMorgan Chase", "oracle",
                         "https://jpmc.fa.oraclecloud.com/hcmUI/CandidateExperience/en/sites/CX_1001", [
    {"request": {"method": "GET", "url": ORA_URL, "params": {
        "onlyData": "true", "expand": "requisitionList",
        "finder": 'findReqs;siteNumber=CX_1001,limit=100,offset=0,sortBy=POSTING_DATES_DESC,keyword="analyst"'}},
     "json": {"items": [{"SearchId": 1, "TotalJobsCount": 2, "requisitionList": [
         {"Id": "210690282", "Title": "Asset Management - Data Analyst", "PostedDate": "2026-11-09",
          "PrimaryLocation": "New York, NY, United States", "JobFamily": "Analysts",
          "JobFunction": "Data & Analytics", "ShortDescriptionStr": "..."},
         {"Id": "210788771", "Title": "Client Advisor", "PostedDate": "2026-10-07",
          "PrimaryLocation": "Singapore, Singapore", "JobFamily": "Client Management",
          "JobFunction": None}]}],
              "count": 1, "hasMore": False}},
], search="analyst")


if __name__ == "__main__":
    for name, envelope in FIXTURES.items():
        text = json.dumps(envelope, indent=1, ensure_ascii=False) + "\n"
        (HERE / f"{name}.json").write_text(text, encoding="utf-8", newline="\n")
    print("wrote", ", ".join(sorted(FIXTURES)))
