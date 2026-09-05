#!/usr/bin/env python3
"""Deterministic half of the weekly Readwise methods review.

The model fetches from the Readwise MCP server (no local token exists, so this
script cannot fetch) and dumps the raw list responses to JSON files. This script
does everything after that: window arithmetic, the saved_at/last_moved_at rule,
video+article dedup, thinness screening, and the source-inventory table.

    # 1. print the exact window to pass to reader_list_documents
    python3 triage.py window

    # 2. after dumping MCP responses to files:
    python3 triage.py triage inbox.json archive1.json archive2.json
"""
import json
import sys
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TZ = ZoneInfo("America/New_York")
THIN_WORDS = 60  # below this, a text item is link-only or a reaction


def window(now=None):
    end = now or datetime.now(TZ)
    return end - timedelta(days=7), end


def cmd_window():
    start, end = window()
    print(f"start_local  {start:%Y-%m-%d %H:%M:%S %Z}")
    print(f"end_local    {end:%Y-%m-%d %H:%M:%S %Z}")
    print(f"updated_after {start.astimezone(ZoneInfo('UTC')):%Y-%m-%dT%H:%M:%SZ}")
    print(f"end_utc       {end.astimezone(ZoneInfo('UTC')):%Y-%m-%dT%H:%M:%SZ}")
    print(f"filename      weekly-review-{end:%Y-%m-%d}.md")


def parse(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00")) if ts else None


def in_window(row, start, end):
    """An item counts if it ENTERED or MOVED in the window.

    The API only filters on updated_at, which fires on any metadata touch (a tag
    edit pulls in months-old items). Read-state fields are unusable: first_opened_at
    is null for most items and reading_progress is 0 almost everywhere. So this is
    the honest ceiling -- it does not capture "was read but not moved."
    """
    for key in ("saved_at", "last_moved_at"):
        t = parse(row.get(key))
        if t and start <= t <= end:
            return True
    return False


def cmd_triage(paths):
    start, end = window()
    rows, seen_ids = [], set()
    for p in paths:
        data = json.load(open(p))
        for r in data.get("results", []):
            if r["id"] not in seen_ids:
                seen_ids.add(r["id"])
                rows.append(r)

    kept = [r for r in rows if in_window(r, start, end)]
    dropped_window = [r for r in rows if not in_window(r, start, end)]

    # Dedup: the deep-read pipeline saves each YouTube URL twice, once as `video`
    # and once as `article` (the transcript). Same title, different id. Keep the
    # record that actually has retrievable text.
    groups = {}
    for r in kept:
        groups.setdefault(r["title"].strip(), []).append(r)
    unique, dup_pairs = [], 0
    for title, members in groups.items():
        if len(members) > 1:
            dup_pairs += 1
            members.sort(key=lambda r: (r.get("word_count") or 0), reverse=True)
        unique.append(members[0])

    inaccessible, thin, assessable = [], [], []
    for r in unique:
        wc = r.get("word_count")
        if not r["title"].strip() or "sign in" in r["title"].strip().lower():
            inaccessible.append(r)
        elif wc is not None and wc < THIN_WORDS:
            thin.append(r)
        else:
            assessable.append(r)

    print(f"# Coverage receipt — {start:%Y-%m-%d %H:%M} to {end:%Y-%m-%d %H:%M} {end:%Z}\n")
    print(f"| Metric | Count |\n|---|---|")
    print(f"| Returned by API filter | {len(rows)} |")
    print(f"| In window (saved_at or last_moved_at) | {len(kept)} |")
    print(f"| Out of window (updated_at only) | {len(dropped_window)} |")
    print(f"| Duplicate pairs collapsed | {dup_pairs} |")
    print(f"| Unique logical items | {len(unique)} |")
    print(f"| Excluded, too thin | {len(thin)} |")
    print(f"| Inaccessible | {len(inaccessible)} |")
    print(f"| Assessable | {len(assessable)} |")

    if dropped_window:
        print("\n## Out of window\n")
        for r in dropped_window:
            print(f"- {r['title'][:70]} — saved {r['saved_at'][:10]}, "
                  f"moved {(r.get('last_moved_at') or '—')[:10]}")

    for label, bucket in (("Inaccessible", inaccessible), ("Excluded, too thin", thin)):
        if bucket:
            print(f"\n## {label}\n")
            for r in bucket:
                print(f"- {r['title'][:70] or '(empty title)'} "
                      f"({r.get('author') or '?'}, {r['category']}, "
                      f"{r.get('word_count') or '—'}w)")

    print("\n## Source inventory\n")
    print("| Title | Author | Type | Saved | Decision | Rationale |")
    print("|---|---|---|---|---|---|")
    for r in sorted(assessable, key=lambda r: r["saved_at"], reverse=True):
        title = r["title"].strip().replace("|", "\\|")[:72]
        author = (r.get("author") or "—").replace("|", "\\|")[:26]
        dup = " *(dup pair)*" if len(groups[r["title"].strip()]) > 1 else ""
        print(f"| {title} | {author} | {r['category']}{dup} | "
              f"{r['saved_at'][:10]} |  |  |")
    print("\n<!-- Fill Decision (HV/US/AC/WG/IR) and Rationale by hand. "
          "Do not delete rows. -->")


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] == "window":
        cmd_window()
    elif sys.argv[1] == "triage":
        if len(sys.argv) < 3:
            sys.exit("usage: triage.py triage <dump.json> [dump2.json ...]")
        cmd_triage(sys.argv[2:])
    else:
        sys.exit(__doc__)
