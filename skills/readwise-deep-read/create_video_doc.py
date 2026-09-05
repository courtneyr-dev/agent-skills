#!/usr/bin/env python3
"""Create a Reader doc with a transcript embedded, for videos whose transcript
Reader could not scrape itself.

Phase 0 of readwise-deep-read says a transcript-less doc must never be left in the
inbox: recover the transcript, then re-create the doc with it embedded. This is the
"re-create" half, scripted so it is not hand-done per video.

Usage:
  create_video_doc.py --url URL --title T --transcript FILE --notes FILE \
                      [--tags a,b,c] [--author A] [--location new]

Reads READWISE_TOKEN from the environment (source ~/.youtube_api_keys first).
Prints the new doc_id to stdout as `doc_id=<id>` so a caller can grep it.

The transcript is wrapped one <p> per line so Phase 2 has paragraph-sized anchors
to attach inline highlights to; a single giant <p> would make anchoring useless.
"""
import argparse
import html
import json
import os
import re
import sys
import urllib.error
import urllib.request

SAVE_URL = "https://readwise.io/api/v3/save/"


def normalize_reader_title(title):
    """Reader titles become Obsidian filenames via the Readwise plugin; '#' and
    '['/']' in a filename break wikilinks to it. Unescape entities first, drop
    '#', brackets -> parens. Same rule as youtube_to_readwise.py and
    normalize_titles.py."""
    title = html.unescape(title)
    title = title.replace("#", "").replace("[", "(").replace("]", ")")
    return re.sub(r"\s+", " ", title).strip()


def wrap_transcript(text, per_para=2):
    """Group transcript lines into <p> blocks of ~per_para lines each.

    Keep this small. Phase 2 anchors inline highlights to whole <p> elements, so
    a large per_para produces paragraphs that swallow several distinct atoms and
    make the highlights useless as anchors — measured at per_para=6, two separate
    claims landed in the same block.
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    paras, buf = [], []
    for ln in lines:
        buf.append(html.escape(ln))
        if len(buf) >= per_para:
            paras.append("<p>" + " ".join(buf) + "</p>")
            buf = []
    if buf:
        paras.append("<p>" + " ".join(buf) + "</p>")
    return "\n".join(paras)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--transcript", required=True)
    ap.add_argument("--notes", required=True)
    ap.add_argument("--tags", default="")
    ap.add_argument("--author", default="")
    ap.add_argument("--location", default="new")
    ap.add_argument("--category", default="video")
    args = ap.parse_args()

    token = os.environ.get("READWISE_TOKEN")
    if not token:
        sys.exit("READWISE_TOKEN not set — source ~/.youtube_api_keys first")

    transcript = open(args.transcript, encoding="utf-8").read()
    notes = open(args.notes, encoding="utf-8").read()
    if not transcript.strip():
        sys.exit("refusing to create a doc with an empty transcript")

    payload = {
        "url": args.url,
        "title": normalize_reader_title(args.title),
        "html": wrap_transcript(transcript),
        "notes": notes,
        "location": args.location,
        "category": args.category,
        "should_clean_html": False,
    }
    if args.author:
        payload["author"] = args.author
    tags = [t.strip() for t in args.tags.split(",") if t.strip()]
    if tags:
        payload["tags"] = tags

    req = urllib.request.Request(
        SAVE_URL,
        data=json.dumps(payload).encode(),
        method="POST",
        headers={"Authorization": f"Token {token}",
                 "Content-Type": "application/json"},
    )
    try:
        resp = urllib.request.urlopen(req)
        body = json.loads(resp.read())
    except urllib.error.HTTPError as e:
        sys.exit(f"save failed {e.code}: {e.read()[:400]}")

    doc_id = body.get("id")
    print(f"doc_id={doc_id}")
    print(f"   url={body.get('url')}")
    print(f"   status={resp.status} (201=created, 200=already existed)")

    # Same-URL re-save is idempotent and will NOT re-scrape, so a 200 here means
    # the html we just sent was ignored. Say so rather than reporting success.
    if resp.status == 200:
        print("   WARNING: doc already existed; embedded html was NOT applied.")
        print("   Use a unique URL (e.g. append #transcript) to force a new doc.")


if __name__ == "__main__":
    main()
