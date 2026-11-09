"""The title rule (watcher/role.py)."""
import pytest

from watcher.role import in_role


@pytest.mark.parametrize("title", [
    "Financial Analyst",
    "Senior Financial Analyst",
    "Associate Financial Analyst",
    "Finance Analyst",
    "Analyst, Finance",
    "Institutional Billing & Controllers, Analyst, Finance",
    "FP&A Analyst",
    "FP & A Analyst",
    "Senior Analyst, Financial Planning & Analysis",
    "Analyst, Financial Analysis",
    "Financial Planning Analyst",
    "Finance & Strategy Analyst, Product",
    "Financial Reporting Analyst",
    "Data Analyst",
    "Senior Data Analyst",
    "Data Analyst, Intern",
    "Data Insights Analyst",
    "Analyst, Data Governance & Quality",
    "Business Intelligence Analyst",
    "BI Analyst",
    "Strategy & Analytics Analyst, Assistant Vice President",
    "DATA ANALYST",
    "Data Analysts - Talent Community",
])
def test_in_role(title):
    assert in_role(title)


@pytest.mark.parametrize("title", [
    "Data Scientist",                      # not an analyst title
    "Analytics Engineer",
    "Finance Manager",
    "Credit Analyst",                      # analyst, but another field
    "Investment Banking Analyst",
    "Business Analyst",
    "Public Finance - Investor Marketing - Analyst",     # 'finance' as a business line
    "Treasury & Trade Finance - Client Service Analyst",
    "Investment Banking - M&A and Corporate Finance - Analyst",
    "Senior Analyst - Financial Institutions Ratings",
    "Financial Crimes Analyst",            # excluded specialties
    "AML Data Analyst",
    "Know Your Customer: Client Data Analyst",
    "Cybersecurity Data Analyst",
    "Data Security Analyst",
    "Data Center Analyst",
    "Data Entry Analyst",
    "Catalyst Program Manager",            # 'analyst' only as part of another word
    "",
])
def test_not_in_role(title):
    assert not in_role(title)
