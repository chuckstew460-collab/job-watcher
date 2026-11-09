"""Watch list and shared settings.

Every source is one employer's job board, read through the applicant tracking
system (ATS) that hosts it. Each board answers a plain HTTP request, with no
login, in JSON. The `name` is the source key used in file names and in
posting_id; `employer` is the display name.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"

USER_AGENT = "job-watcher/1.0 (+https://github.com/chuckstew460-collab/job-watcher)"

# A board that lists more than this many postings must be read with a search term.
MAX_UNFILTERED = 5000

SOURCES = [
    # --- Oracle Cloud HCM (Candidate Experience REST API) ---
    # JPMorgan's board lists ~7,000 postings, above the 5,000 cap, so it is
    # requested with the search term "analyst".
    {"name": "jpmorgan", "employer": "JPMorgan Chase", "ats": "oracle",
     "host": "jpmc.fa.oraclecloud.com", "site": "CX_1001", "search": "analyst"},

    # --- Workday (cxs JSON API behind *.myworkdayjobs.com) ---
    {"name": "bank-of-america", "employer": "Bank of America", "ats": "workday",
     "host": "ghr.wd1.myworkdayjobs.com", "tenant": "ghr", "site": "lateral-us"},
    {"name": "wells-fargo", "employer": "Wells Fargo", "ats": "workday",
     "host": "wd1.myworkdaysite.com", "tenant": "wf", "site": "WellsFargoJobs",
     "board_url": "https://wd1.myworkdaysite.com/recruiting/wf/WellsFargoJobs"},
    {"name": "morgan-stanley", "employer": "Morgan Stanley", "ats": "workday",
     "host": "ms.wd5.myworkdayjobs.com", "tenant": "ms", "site": "External"},
    {"name": "capital-one", "employer": "Capital One", "ats": "workday",
     "host": "capitalone.wd12.myworkdayjobs.com", "tenant": "capitalone", "site": "Capital_One"},
    {"name": "us-bank", "employer": "U.S. Bank", "ats": "workday",
     "host": "usbank.wd1.myworkdayjobs.com", "tenant": "usbank", "site": "US_Bank_Careers"},
    {"name": "state-street", "employer": "State Street", "ats": "workday",
     "host": "statestreet.wd1.myworkdayjobs.com", "tenant": "statestreet", "site": "Global"},
    {"name": "northern-trust", "employer": "Northern Trust", "ats": "workday",
     "host": "ntrs.wd1.myworkdayjobs.com", "tenant": "ntrs", "site": "northerntrust"},
    {"name": "fidelity", "employer": "Fidelity Investments", "ats": "workday",
     "host": "fmr.wd1.myworkdayjobs.com", "tenant": "fmr", "site": "FidelityCareers"},
    {"name": "blackrock", "employer": "BlackRock", "ats": "workday",
     "host": "blackrock.wd1.myworkdayjobs.com", "tenant": "blackrock", "site": "BlackRock_Professional"},
    {"name": "mastercard", "employer": "Mastercard", "ats": "workday",
     "host": "mastercard.wd1.myworkdayjobs.com", "tenant": "mastercard", "site": "CorporateCareers"},
    {"name": "sp-global", "employer": "S&P Global", "ats": "workday",
     "host": "spgi.wd5.myworkdayjobs.com", "tenant": "spgi", "site": "SPGI_Careers"},

    # --- Greenhouse (boards-api.greenhouse.io) ---
    {"name": "stripe", "employer": "Stripe", "ats": "greenhouse", "board": "stripe"},
    {"name": "coinbase", "employer": "Coinbase", "ats": "greenhouse", "board": "coinbase"},
    {"name": "robinhood", "employer": "Robinhood", "ats": "greenhouse", "board": "robinhood"},
    {"name": "point72", "employer": "Point72", "ats": "greenhouse", "board": "point72"},

    # --- Ashby (api.ashbyhq.com posting API) ---
    {"name": "ramp", "employer": "Ramp", "ats": "ashby", "board": "ramp"},
    {"name": "plaid", "employer": "Plaid", "ats": "ashby", "board": "plaid"},

    # --- Lever (api.lever.co postings API) ---
    {"name": "palantir", "employer": "Palantir", "ats": "lever", "board": "palantir"},

    # --- SmartRecruiters (api.smartrecruiters.com posting API) ---
    {"name": "experian", "employer": "Experian", "ats": "smartrecruiters", "board": "Experian"},
]
