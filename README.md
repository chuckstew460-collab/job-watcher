# Job Watcher

[![Tests](https://github.com/chuckstew460-collab/job-watcher/actions/workflows/tests.yml/badge.svg)](https://github.com/chuckstew460-collab/job-watcher/actions/workflows/tests.yml)
[![Daily pipeline](https://github.com/chuckstew460-collab/job-watcher/actions/workflows/daily.yml/badge.svg)](https://github.com/chuckstew460-collab/job-watcher/actions/workflows/daily.yml)

**Live site:** https://chuckstew460-collab.github.io/job-watcher/ ·
**Daily issues:** https://github.com/chuckstew460-collab/job-watcher/issues

A tool that watches the job market for **financial analyst and data analyst** roles. Once a day, on
its own, GitHub Actions pulls every open posting from the job boards of 20 employers, compares them
with what it saw the day before, records what is new and what is gone, opens a GitHub Issue with the
changes, commits the data, and the site (GitHub Pages) shows the result.

## Watch list: 20 employers on 6 applicant tracking systems

Every board is read through the JSON API of the applicant tracking system (ATS) that hosts it, with
a plain request and no login. No HTML page is ever parsed.

| Source key | Employer | ATS | Endpoint (JSON) | Search term |
|---|---|---|---|---|
| `jpmorgan` | JPMorgan Chase | Oracle Cloud HCM | `jpmc.fa.oraclecloud.com/hcmRestApi/resources/latest/recruitingCEJobRequisitions` (site CX_1001) | **`analyst`** |
| `bank-of-america` | Bank of America | Workday | `ghr.wd1.myworkdayjobs.com/wday/cxs/ghr/lateral-us/jobs` | |
| `wells-fargo` | Wells Fargo | Workday | `wd1.myworkdaysite.com/wday/cxs/wf/WellsFargoJobs/jobs` | |
| `morgan-stanley` | Morgan Stanley | Workday | `ms.wd5.myworkdayjobs.com/wday/cxs/ms/External/jobs` | |
| `capital-one` | Capital One | Workday | `capitalone.wd12.myworkdayjobs.com/wday/cxs/capitalone/Capital_One/jobs` | |
| `us-bank` | U.S. Bank | Workday | `usbank.wd1.myworkdayjobs.com/wday/cxs/usbank/US_Bank_Careers/jobs` | |
| `state-street` | State Street | Workday | `statestreet.wd1.myworkdayjobs.com/wday/cxs/statestreet/Global/jobs` | |
| `northern-trust` | Northern Trust | Workday | `ntrs.wd1.myworkdayjobs.com/wday/cxs/ntrs/northerntrust/jobs` | |
| `fidelity` | Fidelity Investments | Workday | `fmr.wd1.myworkdayjobs.com/wday/cxs/fmr/FidelityCareers/jobs` | |
| `blackrock` | BlackRock | Workday | `blackrock.wd1.myworkdayjobs.com/wday/cxs/blackrock/BlackRock_Professional/jobs` | |
| `mastercard` | Mastercard | Workday | `mastercard.wd1.myworkdayjobs.com/wday/cxs/mastercard/CorporateCareers/jobs` | |
| `sp-global` | S&P Global | Workday | `spgi.wd5.myworkdayjobs.com/wday/cxs/spgi/SPGI_Careers/jobs` | |
| `stripe` | Stripe | Greenhouse | `boards-api.greenhouse.io/v1/boards/stripe/jobs` (+ `/departments`) | |
| `coinbase` | Coinbase | Greenhouse | `boards-api.greenhouse.io/v1/boards/coinbase/jobs` (+ `/departments`) | |
| `robinhood` | Robinhood | Greenhouse | `boards-api.greenhouse.io/v1/boards/robinhood/jobs` (+ `/departments`) | |
| `point72` | Point72 | Greenhouse | `boards-api.greenhouse.io/v1/boards/point72/jobs` (+ `/departments`) | |
| `ramp` | Ramp | Ashby | `api.ashbyhq.com/posting-api/job-board/ramp` | |
| `plaid` | Plaid | Ashby | `api.ashbyhq.com/posting-api/job-board/plaid` | |
| `palantir` | Palantir | Lever | `api.lever.co/v0/postings/palantir?mode=json` | |
| `experian` | Experian | SmartRecruiters | `api.smartrecruiters.com/v1/companies/Experian/postings` | |

**Search term.** JPMorgan Chase's board lists about 7,000 postings, more than 5,000, so it is
requested with the search term **`analyst`** (about 1,000 postings). Every other board is read in full.
The fetcher refuses any board over 5,000 postings that has no search term (`MAX_UNFILTERED` in
`watcher/config.py`).

## The title rule (`watcher/role.py`)

A posting is **in the role** (`in_role = true`) when its title, ignoring case:

1. contains the word **analyst** (or analysts), **and**
2. names the role in one of two ways:
   - **finance:** "financial analyst", "finance analyst", "analyst, finance", "financial analysis",
     "financial planning", "FP&A", "finance & strategy", or "financial reporting";
   - **data:** the word "data", "analytics", "business intelligence", or "BI";
3. **and** does not name a different specialty that shares those words: crime (financial crimes),
   AML, KYC / know your customer, security / cyber, data center, data entry.

"Finance" on its own is not enough, because banks name business lines and advisory groups with it
("Public Finance – Analyst", "Trade Finance – Client Service Analyst", "M&A and Corporate Finance –
Analyst"). In the role: *Financial Analyst, Senior Data Analyst, FP&A Analyst, Analyst – Financial
Planning & Analysis, Business Intelligence Analyst, Data Insights Analyst*. Not in it: *Data
Scientist, Credit Analyst, Investment Banking Analyst, Financial Crimes Analyst, Cybersecurity Data
Analyst*. The rule is applied when the history is built, so changing it re-labels every day of the
history.

## The pipeline

`.github/workflows/daily.yml` runs once a day at 12:17 UTC (and on demand from the Actions tab).
Each run takes the UTC date of the moment it starts and:

1. **Fetches every source** (`python -m watcher.fetch`) in parallel and saves what each board returned,
   gzip-compressed, to `data/raw/<date>/<source>.json.gz`. One source failing does not stop the run:
   a failed source writes no raw file that day, and every source's result (ok, count, error) is
   recorded in `data/runs/<date>.json` and in `status.json`. A board that returns no postings, or a
   Workday board whose paging comes back more than 3% short of its own total, counts as failed, so a
   glitch can never mark a whole employer's postings as removed.
2. **Builds the history** (`python -m watcher.build`) from the raw files alone (see below).
3. **Writes the status file** (`python -m watcher.status`).
4. **Opens the day's GitHub Issue** (`python -m watcher.issue`), titled with the date, listing the new
   and the removed postings with links (role postings first), and closes the previous day's issue. It
   is opened every day, even with no changes.
5. **Commits** the raw files, the history file, the status file and the run log.

A run that finishes and commits is a successful run, even if some sources failed. A second run on the
same day replaces that day's raw files and run log, rebuilds the history, and edits that day's issue
instead of opening another, so each day counts once.

### Build the history file from the raw files

```bash
python -m watcher.build
```

This reads every `data/raw/<date>/<source>.json.gz` in date order and writes `data/history.csv`. It
depends on the raw files alone, so running it again produces the same file byte for byte. The Tests
workflow checks this on every push by rebuilding and comparing with the committed file. Day by day:

- every posting from every source is converted to the common columns (`watcher/normalize.py`); every
  posting the board returns is kept, not only the ones in the role;
- each posting is marked in the role or not with the title rule;
- a posting seen for the first time gets that day as `first_seen`;
- every posting its source lists that day gets that day as `last_seen`;
- an open posting is marked `removed`, with that day as `removed_date`, when its source has a raw file
  for that day and no longer lists it (a source with no raw file that day changes nothing);
- a removed posting that its source lists again becomes `open` again, with `removed_date` cleared and
  `first_seen` unchanged;
- rows are sorted by `posting_id`.

## Data files

**`data/history.csv`**, one row per posting:

| Column | Meaning |
|---|---|
| `posting_id` | `<source>:<source_id>`, e.g. `capital-one:R232131-1` |
| `source`, `source_id` | the source key and the board's own ID for the posting |
| `employer`, `title`, `location`, `department` | from the board (latest listing); `department` is empty for Workday, whose list has none |
| `posted_date` | the board's posting date, UTC (first non-empty value seen); empty when the board gives none |
| `url` | the posting's page, where you apply |
| `in_role` | `true` / `false`, the title rule |
| `first_run` | `true` if the posting was listed in its source's first raw file (already open when watching began) |
| `first_seen`, `last_seen` | first and latest date its source listed it |
| `status`, `removed_date` | `open` or `removed`, and the date it was removed |

All dates are UTC dates written `YYYY-MM-DD`.

**`data/status.json`** describes the latest run: `run_time` (UTC), `run_date`, `first_run_date` (date of
the earliest raw file), `days_with_success` (number of different dates with a raw file), `open`,
`new_today` (first seen in the latest run, first-run postings left out), `removed_today`, `in_role` (the
same three counts for the role), and `sources` (one entry per source: `name`, `employer`, `ats`, `ok`,
`count`, `error`).

**`data/raw/<date>/<source>.json.gz`** is one envelope per source per day:
`{source, employer, ats, board, board_url, search, fetched_at, responses: [{request, json}, ...]}`,
where `responses` holds each JSON answer exactly as the board sent it (every page of a paged board).
One exception keeps the repository small: Workday repeats its whole filter menu (`facets`, up to
200 KB for Bank of America) on every page, so it is kept on the first page only.

**`data/runs/<date>.json`** is the run log: each source's result, error, request count and time.

### How each ATS maps to the common columns

| ATS | `source_id` | `title` | `location` | `department` | `posted_date` | `url` |
|---|---|---|---|---|---|---|
| Greenhouse | `id` | `title` | `location.name` | from the `/departments` endpoint | `first_published` | `absolute_url` |
| Lever | `id` | `text` | `categories.location` | `categories.department` or `team` | `createdAt` (epoch ms) | `hostedUrl` |
| Ashby | `id` | `title` | `location` | `department` | `publishedAt` | `jobUrl` |
| SmartRecruiters | `id` | `name` | `location.fullLocation` (or city, region, country) | `department.label` | `releasedDate` | `jobs.smartrecruiters.com/<company>/<id>` |
| Workday | requisition ID at the end of `externalPath` | `title` | `locationsText`; for "3 Locations", the primary location from the link | (none) | from "Posted N Days Ago" and the fetch date; "30+ Days Ago" is empty | board URL + `externalPath` |
| Oracle HCM | `Id` | `Title` | `PrimaryLocation` | `JobFunction` or `JobFamily` | `PostedDate` | candidate-experience URL + `/job/<Id>` |

Text is trimmed to one line. Locations are tidied so boards can be compared: a trailing
"United States" is dropped, US state names become codes ("Purchase, New York" → "Purchase, NY"),
repeated or empty parts and "(HQ)" are removed, and all-caps words get title case.

## The site

Three pages share one navigation bar, one set of fonts (IBM Plex Sans and Mono) and one set of colors,
with a light and a dark theme. Each page loads `data/history.csv` and `data/status.json` in the browser
and does its calculations there.

- **Today** (`index.html`): time of the last run, the status of every source, the four counts from
  the status file (days with a successful run, open, new today, removed today), and the new and
  removed postings of the latest run.
- **Browse** (`browse.html`): open postings, with a switch between the role (default) and all
  postings, filters for employer, location and days open, a title search, a sort by first-seen date,
  an Apply link on every posting, and a star that saves a posting to a shortlist kept in the browser
  (`localStorage`), which survives a reload.
- **Market** (`market.html`): six sections computed from the history file, each with a heading that
  states the finding, a paragraph and a chart (plus a table of the numbers): new postings per day
  (all and in the role), removed postings per day, open postings per employer, median days open,
  the share removed within seven days, and top locations. First-run postings are left out where the
  definitions say so.

**Installable.** `manifest.webmanifest` and the service worker `sw.js` make the site an app the
browser can install. Online, every request goes to the network first, so pages and data are fresh;
the service worker keeps a copy of each answer. Offline, it serves those copies, so the site still
opens and shows the last data it loaded.

## Tests

```bash
python -m pytest
```

The pytest suite covers the conversion of each of the six ATS formats to the common columns
(`tests/test_normalize.py`, using raw fixtures in `tests/fixtures/`), the title rule
(`tests/test_role.py`), the first-seen, last-seen, removed and reopened logic and reproducible
rebuilds (`tests/test_history.py`), failure isolation and same-day reruns in the fetcher
(`tests/test_fetch.py`), and the status file and issue body (`tests/test_status_issue.py`).
`.github/workflows/tests.yml` runs them on every push and after every daily run.

## Run it locally

```bash
python -m venv .venv && .venv/Scripts/activate      # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python -m watcher.run                 # fetch + build + status into data/
python -m watcher.run --skip-fetch    # rebuild history and status from the raw files only
python -m watcher.issue --dry-run     # print the day's issue instead of posting it
python -m watcher.fetch --only stripe,ramp --data-dir scratch/data   # try a few sources elsewhere
python -m http.server                 # then open http://localhost:8000
```

## Every file

| File | What it does |
|---|---|
| `README.md` | This document. |
| `requirements.txt` | Python dependencies: `requests` (HTTP) and `pytest` (tests). |
| `pytest.ini` | pytest settings: test folder and import path. |
| `.gitignore` | Keeps the virtual environment, caches and `scratch/` out of git. |
| `.gitattributes` | LF line endings everywhere (so the history rebuilds byte-identically on any OS); `.gz`/`.png` are binary. |
| `.nojekyll` | Tells GitHub Pages to serve the files as they are, without Jekyll. |
| `watcher/__init__.py` | Marks `watcher` as a Python package. |
| `watcher/config.py` | The watch list (20 sources with ATS, board and search term), paths, site URL, the 5,000 cap. |
| `watcher/fetch.py` | Step 1: one fetcher per ATS (paging, retries, completeness checks); writes raw files and the run log. |
| `watcher/normalize.py` | One converter per ATS from a raw file to the common columns; date and location cleaning. |
| `watcher/role.py` | The title rule. |
| `watcher/build.py` | Step 2: replays the raw files into `data/history.csv`. |
| `watcher/status.py` | Step 3: writes `data/status.json`. |
| `watcher/issue.py` | Step 4: opens or updates the day's GitHub Issue and closes the previous one. |
| `watcher/run.py` | Runs steps 1–3 (and optionally 4) in one command. |
| `tests/conftest.py` | Test helpers that write small raw files and run logs into a temporary folder. |
| `tests/test_normalize.py` | Conversion of each ATS to the common columns; location, date and Workday helpers. |
| `tests/test_role.py` | Titles in and out of the role. |
| `tests/test_history.py` | first_seen / last_seen / removed / reopened / first_run, sorting, reproducible rebuild. |
| `tests/test_fetch.py` | A failing source is isolated; empty boards fail; same-day reruns replace files; 5,000 cap. |
| `tests/test_status_issue.py` | Status counts and the daily issue body (links, empty days, truncation). |
| `tests/fixtures/*.json` | One sample raw file per ATS (greenhouse, lever, ashby, smartrecruiters, workday, oracle). |
| `tests/fixtures/make_fixtures.py` | Regenerates those fixtures. |
| `.github/workflows/daily.yml` | The daily schedule: fetch, build, status, issue, commit. |
| `.github/workflows/tests.yml` | Runs pytest on every push and after each daily run, and checks the history rebuilds from the raw files. |
| `index.html` | The Today page. |
| `browse.html` | The Browse page. |
| `market.html` | The Market page. |
| `manifest.webmanifest` | Web app manifest (name, icons, start URL) that makes the site installable. |
| `sw.js` | Service worker: network-first with an offline copy of pages and data. |
| `assets/css/site.css` | The shared look: color tokens (light and dark), nav bar, cards, lists, charts. |
| `assets/js/common.js` | Shared code: nav bar, theme switch, data loading, CSV parser, dates, shortlist, service worker registration. |
| `assets/js/charts.js` | Chart kit for the Market page: column chart, ranked bars, segmented bar, tooltip, table view. |
| `assets/js/today.js` | Builds the Today page. |
| `assets/js/browse.js` | Builds the Browse page (filters, search, sort, stars). |
| `assets/js/market.js` | Computes the six Market sections from the history file. |
| `assets/icons/favicon.svg` | Site icon. |
| `assets/icons/icon-192.png`, `icon-512.png`, `maskable-512.png`, `apple-touch-icon.png` | App icons for installing. |
| `data/history.csv` | The history file (one row per posting), written by the build. |
| `data/status.json` | The status of the latest run. |
| `data/raw/<date>/<source>.json.gz` | What each board returned that day, compressed. |
| `data/runs/<date>.json` | Every source's result for that day's run. |
