"""Pipeline step 4: open the day's GitHub Issue and close the previous one.

    python -m watcher.issue             # needs GITHUB_TOKEN and GITHUB_REPOSITORY
    python -m watcher.issue --dry-run   # print the issue instead

The issue is titled with the run date (YYYY-MM-DD) and lists the postings
first seen that day (first-run postings left out) and the postings removed
that day, each with a link. It is opened every day, even with no changes. A
second run on the same date edits that date's issue instead of opening a new
one. Every other open daily issue is closed.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

import requests

from . import config
from .build import read_history

LABEL = "daily-report"
API = "https://api.github.com"
BODY_LIMIT = 60000  # GitHub rejects issue bodies over 65,536 characters


def _md(text: str) -> str:
    return text.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


def _line(row: dict) -> str:
    where = f" · {_md(row['location'])}" if row["location"] else ""
    return f"- [{_md(row['title'])}]({row['url']}) — {_md(row['employer'])}{where}"


def _sorted(rows: list[dict]) -> list[dict]:
    return sorted(rows, key=lambda r: (r["employer"], r["title"], r["posting_id"]))


def _section(heading: str, rows: list[dict], cap: int | None = None) -> list[str]:
    out = [f"### {heading} ({len(rows)})", ""]
    if not rows:
        return out + ["_None._", ""]
    shown = rows if cap is None else rows[:cap]
    out += [_line(r) for r in shown]
    if len(shown) < len(rows):
        out.append(f"- …and {len(rows) - len(shown)} more on the site")
    return out + [""]


def render(status: dict, rows: list[dict], site_url: str, limit: int = BODY_LIMIT) -> str:
    day = status["run_date"]
    new = _sorted([r for r in rows if r["first_seen"] == day and r["first_run"] == "false"])
    gone = _sorted([r for r in rows if r["removed_date"] == day])
    ok = [s for s in status["sources"] if s["ok"]]
    failed = [s for s in status["sources"] if not s["ok"]]
    role = status["in_role"]

    head = [
        f"Run at **{status['run_time'].replace('T', ' ').replace('Z', ' UTC')}** · "
        f"{len(ok)}/{len(status['sources'])} sources ok · "
        f"[Today]({site_url}) · [Browse]({site_url}browse.html) · [Market]({site_url}market.html)",
        "",
        "| | All postings | Financial / data analyst |",
        "|---|---:|---:|",
        f"| Open | {status['open']:,} | {role['open']:,} |",
        f"| New today | {status['new_today']:,} | {role['new_today']:,} |",
        f"| Removed today | {status['removed_today']:,} | {role['removed_today']:,} |",
        "",
    ]
    if failed:
        head += ["**Failed sources** (no raw file today; their postings are unchanged):", ""]
        head += [f"- {s['employer']} ({s['ats']}): {s['error']}" for s in failed] + [""]

    def body(cap_new: int | None, cap_gone: int | None) -> str:
        parts = head + [f"## New postings ({len(new)})", ""]
        parts += _section("Financial / data analyst", [r for r in new if r["in_role"] == "true"])
        parts += _section("Other roles", [r for r in new if r["in_role"] != "true"], cap_new)
        parts += [f"## Removed postings ({len(gone)})", ""]
        parts += _section("Financial / data analyst", [r for r in gone if r["in_role"] == "true"])
        parts += _section("Other roles", [r for r in gone if r["in_role"] != "true"], cap_gone)
        return "\n".join(parts).rstrip() + "\n"

    text = body(None, None)
    cap_new = cap_gone = max(len(new), len(gone))
    while len(text) > limit and (cap_new > 0 or cap_gone > 0):
        cap_new, cap_gone = int(cap_new * 0.8), int(cap_gone * 0.8)
        text = body(cap_new, cap_gone)
    return text


class GitHub:
    def __init__(self, repo: str, token: str):
        self.repo = repo
        self.s = requests.Session()
        self.s.headers.update({"Authorization": f"Bearer {token}",
                               "Accept": "application/vnd.github+json",
                               "X-GitHub-Api-Version": "2022-11-28"})

    def req(self, method: str, path: str, **kw):
        r = self.s.request(method, f"{API}/repos/{self.repo}{path}", timeout=30, **kw)
        if r.status_code >= 400 and not (method == "POST" and path == "/labels" and r.status_code == 422):
            r.raise_for_status()
        return r.json() if r.content else None

    def publish(self, day: str, body: str) -> str:
        self.req("POST", "/labels", json={"name": LABEL, "color": "1f6feb",
                                          "description": "Daily job-watcher report"})
        issues = self.req("GET", "/issues", params={"labels": LABEL, "state": "all",
                                                    "per_page": 100, "sort": "created"})
        today = next((i for i in issues if i["title"] == day and "pull_request" not in i), None)
        if today:
            self.req("PATCH", f"/issues/{today['number']}", json={"body": body, "state": "open"})
            action, number = "updated", today["number"]
        else:
            made = self.req("POST", "/issues", json={"title": day, "body": body, "labels": [LABEL]})
            action, number = "opened", made["number"]
        for i in issues:
            if i["state"] == "open" and i["number"] != number:
                self.req("PATCH", f"/issues/{i['number']}",
                         json={"state": "closed", "state_reason": "completed"})
                print(f"closed issue #{i['number']} ({i['title']})")
        return f"{action} issue #{number} ({day})"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data-dir", type=Path, default=config.DATA_DIR)
    ap.add_argument("--dry-run", action="store_true", help="print the issue body; touch nothing")
    args = ap.parse_args(argv)
    status = json.loads((args.data_dir / "status.json").read_text(encoding="utf-8"))
    rows = read_history(args.data_dir / "history.csv")
    body = render(status, rows, config.SITE_URL)
    token, repo = os.environ.get("GITHUB_TOKEN"), os.environ.get("GITHUB_REPOSITORY")
    if args.dry_run or not (token and repo):
        sys.stdout.reconfigure(encoding="utf-8")
        print(f"# {status['run_date']}\n\n{body}")
        return 0
    print(GitHub(repo, token).publish(status["run_date"], body))
    return 0


if __name__ == "__main__":
    sys.exit(main())
