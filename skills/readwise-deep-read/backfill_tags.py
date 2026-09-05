#!/usr/bin/env python3
"""Backfill Reader document-level topic tags from the tags already in each doc's notes.

Phase 2.5 of readwise-deep-read ("MANDATORY, easy to forget") applies topic tags to the
Reader doc. When it is skipped, the analysis still carries its own `tags:` in the notes
YAML — the tags exist, they just never reached Reader's tag field. Measured 2026-08-28:
675 docs in a 7-day window, several of them 70-140K of finished analysis.

Nothing here invents a tag. It reads what the analysis already declared, drops anything
the Reader tag policy forbids (dated, pipeline-state, single-letter, source-format), and
applies the rest. A doc whose notes declare no usable tag is reported and skipped.

  python3 backfill_tags.py --since 2026-07-01 [--limit N] [--dry-run]
"""
import argparse, json, os, re, sys, time, urllib.error, urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from deepread_check import tag_violations

API = "https://readwise.io/api/v3"
KEYFILE = os.path.expanduser("~/.youtube_api_keys")


def token():
    t = os.environ.get("READWISE_TOKEN")
    if t:
        return t
    with open(KEYFILE) as fh:
        for line in fh:
            m = re.match(r'\s*(?:export\s+)?READWISE_TOKEN=["\']?([^"\'\s]+)', line)
            if m:
                return m.group(1)
    sys.exit("ERROR: READWISE_TOKEN not found")


def request(method, url, tok, payload=None, tries=5):
    data = json.dumps(payload).encode() if payload is not None else None
    for i in range(tries):
        req = urllib.request.Request(url, data=data, method=method, headers={
            "Authorization": f"Token {tok}", "Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.status, json.loads(r.read().decode() or "{}")
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = int(e.headers.get("Retry-After", 60))
                print(f"    rate limited, sleeping {wait}s", flush=True)
                time.sleep(wait)
                continue
            return e.code, {}
        except urllib.error.URLError:
            time.sleep(5 * (i + 1))
    return 0, {}


# `tags: [a, b, c]` or a YAML block list, inside the notes frontmatter only.
TAGS_INLINE = re.compile(r"^tags:\s*\[([^\]]*)\]", re.M)
TAGS_BLOCK = re.compile(r"^tags:\s*\n((?:\s*-\s*\S.*\n)+)", re.M)


def tags_from_notes(notes):
    head = notes[:4000]                       # frontmatter only; never the body
    m = TAGS_INLINE.search(head)
    if m:
        raw = [t.strip().strip("'\"") for t in m.group(1).split(",")]
    else:
        m = TAGS_BLOCK.search(head)
        if not m:
            return []
        raw = [l.strip().lstrip("-").strip().strip("'\"") for l in m.group(1).splitlines()]
    raw = [t for t in raw if t and not t.startswith("readwise/")]
    bad = {b.split("(")[0] for b in tag_violations(raw)}
    return [t for t in raw if t not in bad][:8]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    tok = token()

    docs, cursor = [], None
    while True:
        url = f"{API}/list/?updatedAfter={args.since}T00:00:00Z"
        if cursor:
            url += f"&pageCursor={cursor}"
        st, body = request("GET", url, tok)
        if st != 200:
            sys.exit(f"list failed: HTTP {st}")
        docs.extend(body.get("results", []))
        cursor = body.get("nextPageCursor")
        print(f"  listed {len(docs)}…", flush=True)
        if not cursor:
            break

    todo = []
    for d in docs:
        if d.get("category") in ("highlight", "note", "rss"):
            continue
        tags = list((d.get("tags") or {}).keys()) if isinstance(d.get("tags"), dict) else (d.get("tags") or [])
        if tags:
            continue
        notes = d.get("notes") or ""
        if "Refactor Appendix" not in notes and "[!info]" not in notes:
            continue                          # not a deep-read; not this script's job
        want = tags_from_notes(notes)
        if want:
            todo.append((d, want))
        else:
            print(f"  NO-TAGS-IN-NOTES  {(d.get('title') or '')[:52]}")

    print(f"\n{len(todo)} doc(s) have usable tags in their own notes\n")
    if args.limit:
        todo = todo[:args.limit]

    done = failed = 0
    for d, want in todo:
        if args.dry_run:
            print(f"  would tag  {(d.get('title') or '')[:46]:48} -> {', '.join(want)}")
            done += 1
            continue
        st, _ = request("PATCH", f"{API}/update/{d['id']}/", tok, {"tags": want})
        if st in (200, 201):
            print(f"  TAGGED     {(d.get('title') or '')[:46]:48} -> {', '.join(want)}", flush=True)
            done += 1
        else:
            print(f"  FAILED {st} {(d.get('title') or '')[:46]}", flush=True)
            failed += 1
    print(f"\n  {done} tagged, {failed} failed{' (dry run)' if args.dry_run else ''}")


if __name__ == "__main__":
    main()
