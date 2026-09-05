#!/usr/bin/env python3
"""
Push a local 18-section analysis file into a Reader document's `notes` field.

Why this exists
---------------
The MCP tool `reader_bulk_edit_document_metadata` is the only sanctioned write
path, and it requires the entire notes body to be inlined as a tool argument.
For a full deep-read that is 50-80KB of markdown, which costs roughly 20k
output tokens PER DOCUMENT just to transmit text that already exists on disk.

This script PATCHes the same field directly via /api/v3/update/<id>/, reading
the body from a file. Same result, no inlining.

Requires an allow rule (see below) because the auto-mode classifier blocks
unrecognised network writes.

    "Bash(python3 $HOME/.claude/skills/readwise-deep-read/push_notes.py:*)"

Usage
-----
    push_notes.py <doc_id> <path-to-md> [--tags a,b,c] [--author "Name"] [--dry-run]

Token
-----
Read from ~/.youtube_api_keys (READWISE_TOKEN=...). Never printed, never logged.
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

KEYFILE = os.path.expanduser("~/.youtube_api_keys")
API = "https://readwise.io/api/v3"


def token():
    """Pull READWISE_TOKEN out of the keyfile. Never echo the value."""
    if not os.path.exists(KEYFILE):
        sys.exit(f"ERROR: {KEYFILE} not found")
    pat = re.compile(r'^\s*(?:export\s+)?READWISE_TOKEN\s*=\s*["\']?([^"\'\s]+)')
    with open(KEYFILE) as fh:
        for line in fh:
            m = pat.match(line)
            if m:
                return m.group(1)
    sys.exit("ERROR: READWISE_TOKEN not found in keyfile")


def request(method, url, tok, payload=None, timeout=120):
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Authorization": f"Token {tok}"}
    if data:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                body = r.read().decode()
                return r.status, (json.loads(body) if body.strip() else {})
        except urllib.error.HTTPError as e:
            if e.code == 429:
                wait = int(e.headers.get("Retry-After", 20))
                print(f"  429 rate-limited, sleeping {wait}s", flush=True)
                time.sleep(wait)
                continue
            sys.exit(f"HTTP {e.code}: {e.read().decode()[:400]}")
        except urllib.error.URLError as e:
            if attempt == 4:
                sys.exit(f"Network error after retries: {e}")
            time.sleep(5 * (attempt + 1))
    sys.exit("Exhausted retries")


def create_from_transcript(args):
    """
    Fallback step 4: Reader scraped nothing (empty-subtitle sentinel) and the API
    will not let us update html_content. So save a NEW doc with the transcript
    embedded, which is the only way to get anchorable text for inline highlights.

    Reads the transcript from a file rather than inlining it as a tool argument —
    same reason the rest of this script exists.
    """
    if not os.path.exists(args.transcript):
        sys.exit(f"ERROR: {args.transcript} not found")
    body = open(args.transcript).read()
    if len(body.strip()) < 500:
        sys.exit(f"ERROR: {args.transcript} is only {len(body)} chars — refusing")

    payload = {"url": args.url, "should_clean_html": False, "html": _as_html(body)}
    if args.title:
        payload["title"] = args.title
    if args.author:
        payload["author"] = args.author
    if args.tags:
        payload["tags"] = [t.strip() for t in args.tags.split(",") if t.strip()]

    print(f"transcript: {args.transcript}")
    print(f"size      : {len(body):,} chars -> {len(payload['html']):,} chars html")
    if args.dry_run:
        print("DRY RUN — nothing sent.")
        return

    tok = token()
    status, data = request("POST", f"{API}/save/", tok, payload)
    new_id = (data or {}).get("id")
    print(f"POST      : HTTP {status}")
    print(f"new doc   : {new_id}")
    print(f"url       : {(data or {}).get('url')}")

    time.sleep(3)
    _, chk = request("GET", f"{API}/list/?id={new_id}&withHtmlContent=true", tok)
    res = (chk.get("results") or [])
    if res:
        h = res[0].get("html_content") or ""
        words = len(re.sub(r"<[^>]+>", " ", h).split())
        print(f"verified  : {words:,} words of html_content"
              f"{'  [anchorable]' if words > 200 else '  [** STILL EMPTY **]'}")


def _as_html(text):
    """Wrap plain transcript text in paragraphs so highlights have anchors."""
    import html as _h
    paras = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if len(paras) < 5:  # single blob — split on sentence runs instead
        sentences = re.split(r"(?<=[.?!])\s+", text)
        paras, buf = [], []
        for s in sentences:
            buf.append(s)
            if sum(len(x) for x in buf) > 700:
                paras.append(" ".join(buf)); buf = []
        if buf:
            paras.append(" ".join(buf))
    return "\n".join(f"<p>{_h.escape(p)}</p>" for p in paras)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("doc_id")
    ap.add_argument("path", nargs="?", default="")
    ap.add_argument("--tags", default="", help="comma-separated")
    ap.add_argument("--author", default="")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--force", action="store_true",
                    help="push despite missing required sections (deliberate exceptions only)")
    # Fallback-step-4 mode: create a new doc with transcript embedded.
    ap.add_argument("--create-from-transcript", dest="transcript", default="")
    ap.add_argument("--url", default="")
    ap.add_argument("--title", default="")
    args = ap.parse_args()

    if args.transcript:
        if not args.url:
            sys.exit("ERROR: --create-from-transcript requires --url")
        return create_from_transcript(args)

    if not args.path:
        sys.exit("ERROR: path is required unless using --create-from-transcript")
    if not os.path.exists(args.path):
        sys.exit(f"ERROR: {args.path} not found")
    notes = open(args.path).read()
    if len(notes.strip()) < 500:
        sys.exit(f"ERROR: {args.path} is only {len(notes)} chars — refusing to push a stub")

    # Completeness is a HARD GATE, not a warning (the user, 2026-08-28: "I want all
    # of them every time, and I'm tired of the drifting happening").
    #
    # This used to print "WARNING: fewer than 15 '## ' sections" and push anyway, so
    # every incomplete analysis still reached Reader and, from there, the vault and
    # the published page. Refusing at the write is the only rung that actually holds:
    # the nightly sweeper has correctly reported 600-900 failures a day for weeks and
    # nothing changed, because a permanently-red dashboard carries no signal.
    #
    # The section list is imported rather than restated — one definition, so the
    # writer and the checker can never disagree about what "complete" means.
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from deepread_check import missing_sections, REQUIRED_SECTIONS

    missing = missing_sections(notes)
    stamped = "[!info]" in notes
    print(f"file      : {args.path}")
    print(f"size      : {len(notes):,} chars")
    print(f"sections  : {len(REQUIRED_SECTIONS) - len(missing)}/{len(REQUIRED_SECTIONS)}")
    print(f"stamped   : {stamped}")
    if not stamped:
        print("  WARNING: no '[!info]' provenance callout found")
    if missing:
        if not args.force:
            sys.exit(
                f"REFUSED: {len(missing)} required section(s) missing — "
                + ", ".join(missing)
                + "\n  Write them, then re-run. Use --force only for a source where a"
                  " section genuinely cannot apply, and say so in the section body"
                  ' ("Not applicable to this source" plus a one-line reason).'
            )
        print(f"  FORCED: pushing with {len(missing)} section(s) missing — "
              + ", ".join(missing))

    payload = {"notes": notes}
    if args.tags:
        payload["tags"] = [t.strip() for t in args.tags.split(",") if t.strip()]
    if args.author:
        payload["author"] = args.author

    if args.dry_run:
        print("DRY RUN — nothing sent.")
        print("would set:", ", ".join(payload.keys()))
        return

    tok = token()
    status, _ = request("PATCH", f"{API}/update/{args.doc_id}/", tok, payload)
    print(f"PATCH     : HTTP {status}")

    # Verify by reading the field back rather than trusting the write.
    time.sleep(2)
    _, data = request("GET", f"{API}/list/?id={args.doc_id}&withHtmlContent=false", tok)
    results = data.get("results") or []
    if not results:
        print("  WARNING: could not read back document to verify")
        return
    d = results[0]
    server_len = len(d.get("notes") or "")
    tags = sorted((d.get("tags") or {}).keys())
    # Reader strips trailing whitespace on write, so compare rstripped lengths.
    local_len = len(notes.rstrip())
    print(f"verified  : {server_len:,} chars on server", end="")
    if len((d.get("notes") or "").rstrip()) == local_len:
        print("  [match]")
    else:
        print(f"  [MISMATCH — local {len(notes):,}]")
    print(f"author    : {d.get('author')}")
    print(f"tags      : {', '.join(tags) if tags else '(none)'}")


if __name__ == "__main__":
    main()
