"""The title rule: is a posting a financial analyst or data analyst role?

A title is in the role when, ignoring case, it

  1. contains the word "analyst" (or "analysts"), and
  2. names the role, in one of two ways:
     - finance: "financial analyst", "finance analyst", "analyst, finance",
       "financial analysis", "financial planning", "FP&A",
       "finance & strategy", "financial reporting"
     - data: the word "data", "analytics", "business intelligence" or "BI"
  3. and does not name a different specialty that shares those words:
     crime (financial crimes), AML, KYC / know your customer,
     security / cyber, data center, data entry.

"Finance" on its own is not enough, because banks name business lines and
advisory groups with it ("Public Finance - Analyst", "Trade Finance - Client
Service Analyst", "M&A and Corporate Finance - Analyst").

In the role:      Financial Analyst; Senior Data Analyst; FP&A Analyst;
                  Analyst, Financial Planning & Analysis; Analyst - Finance;
                  Business Intelligence Analyst; Data Insights Analyst
Not in the role:  Data Scientist; Credit Analyst; Investment Banking Analyst;
                  Public Finance - Analyst; Analyst - Financial Institutions
                  Ratings; Financial Crimes Analyst;
                  Cybersecurity Data Analyst; Finance Manager
"""
import re

ANALYST = re.compile(r"\banalysts?\b", re.I)
FINANCE = re.compile(
    r"\bfinancial analy|\bfinance analyst|\banalysts?\W+finance\b|\bfinancial planning"
    r"|\bfp\s*&\s*a\b|\bfinance\s*(&|and)\s*strategy\b|\bfinancial reporting\b",
    re.I)
DATA = re.compile(r"\bdata\b|\banalytics\b|\bbusiness intelligence\b|\bbi\b", re.I)
EXCLUDE = re.compile(r"crime|\baml\b|\bkyc\b|know your customer|security|cyber|data cent(er|re)"
                     r"|data entry", re.I)


def in_role(title: str) -> bool:
    t = title or ""
    return bool(ANALYST.search(t) and (FINANCE.search(t) or DATA.search(t)) and not EXCLUDE.search(t))
