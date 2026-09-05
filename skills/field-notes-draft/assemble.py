#!/usr/bin/env python3
"""Build a conservative Field Notes candidate scaffold from the synthesis backlog."""

from __future__ import annotations
import os

import argparse
import datetime as dt
import json
from pathlib import Path
import re
import sys


VAULT = Path(os.path.expanduser(os.environ.get("VAULT_DIR", "~/Documents/Notes")))
BACKLOG = VAULT / "_Synthesis Backlog.md"
STATE = Path(__file__).resolve().parent / "state.json"

# A hard exclusion requires an explicit scope signal in the title or type. Notes can
# mention faith or family while discussing a professional topic, so notes never cause
# a hard exclusion on their own.
EXPLICIT_SCOPE = (
    r"\bbible\b", r"\bbiblical\b", r"\bscriptur", r"\btheolog", r"\bsermon\b",
    r"\bgospel\b", r"\beucharist", r"\bliturg", r"\bpentecost", r"\bapostolic\b",
    r"passion translation", r"new apostolic reformation", r"sermon brainwave",
    r"wired word", r"\bintercessory\b", r"bethel church", r"\bdeacon\b",
    r"\bparish\b", r"\bdiscipleship\b", r"\becclesiast", r"personalsite",
    r"\bhomeschool",
)
AMBIGUOUS_SCOPE = (
    r"\bchurch\b", r"\bevangelism\b", r"\bprophe(t|cy|tic)\b", r"\bfaith\b",
    r"\bnar\b", r"\brevival", r"\bdeconstruct", r"\bspiritual\b",
    r"\bdevotional\b", r"\bucc\b", r"\bparenting\b", r"\bfamily\b",
)
EXPLICIT_RE = tuple(re.compile(pattern, re.IGNORECASE) for pattern in EXPLICIT_SCOPE)
AMBIGUOUS_RE = tuple(re.compile(pattern, re.IGNORECASE) for pattern in AMBIGUOUS_SCOPE)

THEMES = (
    (
        "WordPress",
        (
            "wordpress", "gutenberg", "woocommerce", "plugin", "block editor", "block mcp",
            "automattic", "wp engine", "wpe", "yoast", "playground", "ollie", "wp-cli",
            "five for the future", "wp.org", "wordpress 7.1",
        ),
    ),
    (
        "AI developer tools",
        (
            " ai ", "llm", "claude", "chatgpt", "gpt", "gemini", "mcp", "agent",
            "prompt", "model", "rag", "copilot", "notebooklm", "vibe code", "skill",
        ),
    ),
    (
        "Open source and DevRel",
        (
            "devrel", "developer relation", "open source", "oss", "community", "contributor",
            "foundation", "governance", "license", "ambassador", "advocacy", "maintainer",
            "teaching labor", "ospo", "funding",
        ),
    ),
    (
        "Security and supply chain",
        (
            "security", "supply chain", "malware", "vulnerability", "cve", "sbom",
            "dependency", "incident", "exploit", "rce",
        ),
    ),
    (
        "Developer education",
        (
            "education", "teaching", "learning", "curriculum", "documentation", "tutorial",
            "onboarding", "training", "workshop",
        ),
    ),
)


def load_state() -> dict:
    if not STATE.exists():
        return {"last_issue_date": None, "featured_doc_ids": []}
    with STATE.open(encoding="utf-8") as handle:
        return json.load(handle)


def parse_backlog() -> list[dict]:
    rows_by_id = {}
    if not BACKLOG.exists():
        return []
    with BACKLOG.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.startswith("|"):
                continue
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if len(cells) < 8:
                continue
            date, title, doc_id, kind, atoms, moc, read, notes = cells[:8]
            if date in ("Date", "---") or not re.match(r"\d{4}-\d{2}-\d{2}", date):
                continue
            row = {
                "date": date,
                "title": title,
                "doc_id": doc_id,
                "type": kind,
                "read": read,
                "notes": notes,
            }
            prior = rows_by_id.get(doc_id)
            if prior is None or row["date"] >= prior["date"]:
                rows_by_id[doc_id] = row
    return list(rows_by_id.values())


def matching_patterns(text: str, patterns: tuple[re.Pattern, ...]) -> list[str]:
    return sorted({pattern.pattern for pattern in patterns if pattern.search(text)})


def scope(row: dict) -> tuple[str, list[str]]:
    title_and_type = f"{row['title']} {row['type']}"
    explicit = matching_patterns(title_and_type, EXPLICIT_RE)
    if explicit:
        return "exclude_explicit", explicit

    title_ambiguous = matching_patterns(title_and_type, AMBIGUOUS_RE)
    note_ambiguous = matching_patterns(row["notes"], AMBIGUOUS_RE)
    if (
        title_ambiguous == [r"\bparenting\b"]
        and re.search(r"\b(ai|claude|agent|prompt|code|developer)\b", row["title"], re.IGNORECASE)
    ):
        title_ambiguous = []
    if title_ambiguous or len(note_ambiguous) >= 2:
        return "review_scope", sorted(set(title_ambiguous + note_ambiguous))
    return "candidate", []


def theme_of(row: dict) -> str:
    text = f" {row['title']} {row['notes']} ".lower()
    scores = []
    for name, terms in THEMES:
        score = sum(term in text for term in terms)
        scores.append((score, name))
    score, name = max(scores, key=lambda item: item[0])
    return name if score else "Other"


def readiness(row: dict) -> dict:
    notes = row["notes"].strip().lower()
    read = row["read"].strip().lower()
    needs_full_read = not notes or notes in {"-", "none", "n/a"} or read in {"", "0", "false", "no"}
    return {
        "state": "captured",
        "flags": [
            flag
            for flag, active in (
                ("needs full read", needs_full_read),
                ("needs the user's take", True),
            )
            if active
        ],
    }


def enrich(row: dict) -> dict:
    return {**row, "theme": theme_of(row), "readiness": readiness(row)}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int)
    parser.add_argument("--since", type=dt.date.fromisoformat)
    parser.add_argument("--through", type=dt.date.fromisoformat)
    parser.add_argument("--record", nargs=2, metavar=("DATE", "DOC_IDS"))
    return parser.parse_args()


def date_window(args: argparse.Namespace, state: dict) -> tuple[dt.date, dt.date]:
    today = dt.date.today()
    through = args.through or today
    if args.since:
        since = args.since
    elif args.days is not None:
        since = through - dt.timedelta(days=args.days)
    elif state.get("last_issue_date"):
        since = dt.date.fromisoformat(state["last_issue_date"])
    else:
        since = through - dt.timedelta(days=7)
    if since > through:
        raise ValueError("--since must not be after --through")
    return since, through


def record_issue(issue_date: str, ids_text: str) -> None:
    issue = dt.date.fromisoformat(issue_date)
    state = load_state()
    ids = [value.strip() for value in ids_text.split(",") if value.strip()]
    state["last_issue_date"] = issue.isoformat()
    state["featured_doc_ids"] = sorted(set(state.get("featured_doc_ids", []) + ids))
    with STATE.open("w", encoding="utf-8") as handle:
        json.dump(state, handle, indent=2)
        handle.write("\n")
    print(f"recorded issue {issue}: {len(ids)} featured document IDs", file=sys.stderr)


def main() -> int:
    args = parse_args()
    if args.record:
        record_issue(*args.record)
        return 0

    state = load_state()
    since, through = date_window(args, state)
    featured = set(state.get("featured_doc_ids", []))
    fresh = [
        row
        for row in parse_backlog()
        if since <= dt.date.fromisoformat(row["date"]) <= through and row["doc_id"] not in featured
    ]

    groups: dict[str, list[dict]] = {}
    excluded_explicit = []
    review_scope = []
    review_other = []

    for row in fresh:
        verdict, matches = scope(row)
        item = enrich(row)
        if verdict == "exclude_explicit":
            excluded_explicit.append({**item, "scope_matches": matches})
        elif verdict == "review_scope":
            review_scope.append({**item, "scope_matches": matches})
        elif item["theme"] == "Other":
            review_other.append(item)
        else:
            groups.setdefault(item["theme"], []).append(item)

    counts = {
        "fresh": len(fresh),
        "grouped_candidates": sum(len(items) for items in groups.values()),
        "excluded_explicit": len(excluded_explicit),
        "review_scope": len(review_scope),
        "review_other": len(review_other),
    }
    scaffold = {
        "generated": dt.date.today().isoformat(),
        "window": {"since_inclusive": since.isoformat(), "through_inclusive": through.isoformat()},
        "counts": counts,
        "groups": groups,
        "review_scope": review_scope,
        "review_other": review_other,
        "excluded_explicit": excluded_explicit,
    }
    print(json.dumps(scaffold, indent=2))
    print(
        f"[Field Notes] {since}..{through} inclusive | fresh={counts['fresh']} "
        f"grouped={counts['grouped_candidates']} excluded={counts['excluded_explicit']} "
        f"review_scope={counts['review_scope']} review_other={counts['review_other']}",
        file=sys.stderr,
    )
    if excluded_explicit:
        print("  explicit faith or family titles kept out:", file=sys.stderr)
        for item in excluded_explicit:
            print(f"    - {item['title'][:70]}", file=sys.stderr)
    if review_scope:
        print("  context review required:", file=sys.stderr)
        for item in review_scope:
            print(f"    - {item['title'][:70]}", file=sys.stderr)
    if not fresh:
        print("  no unfeatured backlog rows in this window", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
