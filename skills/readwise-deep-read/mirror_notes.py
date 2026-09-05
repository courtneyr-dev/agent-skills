#!/usr/bin/env python3
"""
Mirror the full Reader `notes` into the canonical local Readwise vault file as a
`> [!note]+ Document Notes` callout.

Why this exists
---------------
Obsidian Publish renders the Document Notes dropdown from the callout in the
local file. That callout comes from the v2 book's `document_note`, which has two
independent failure modes:

  1. Notes supplied at CREATION time (`/api/v3/save/` payload or
     `reader_create_document(notes=...)`) never reach `document_note` at all —
     it stays empty and no callout is ever written.
  2. Notes supplied LATE (`reader_bulk_edit_document_metadata`) do reach it, but
     are truncated at 8191 bytes — roughly the first quarter of an 18-section
     deep read, cut mid-word.

`document_note` is read-only (`OPTIONS /api/v2/books/<id>/` confirms), so neither
is fixable through the API. Writing the callout locally is the only way to get
the complete notes onto the published page. The Readwise Official plugin
preserves locally modified files and appends future highlight deltas.

Usage
-----
    python3 mirror_notes.py --ids <doc_id> [<doc_id> ...] [--dry-run]
    python3 mirror_notes.py --since 2026-07-01 [--dry-run]     # all locations
    python3 mirror_notes.py --location new [--dry-run]         # one bucket only

Requires READWISE_TOKEN in the environment (source ~/.youtube_api_keys).
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

VAULT = os.path.expanduser("~/Documents/Notes")
READWISE_DIR = os.path.join(VAULT, "Resources/Readwise")
EXCLUDE_DIR = "Full Document Contents"
CALLOUT_HEAD = "> [!note]+ Document Notes"

# Obsidian Publish (and the Obsidian outline pane) index only TOP-LEVEL headings.
# Every heading nested inside a callout is invisible to both. Measured 2026-08-28:
# all 9,884 deep-read files had exactly ONE indexed heading — the plugin's own
# `## Highlights` — because the 10-26 analysis headings all sat inside the callout
# as `> ## ...`. So the published page offered no way to reach any section.
#
# Fix: the callout keeps only the provenance head (stamp, title, attribution notes);
# every `## ` section is emitted at top level below it, bracketed by these markers so
# a re-mirror can find and replace its own previous output. HTML comments render as
# nothing in Obsidian and in Publish.
SECTIONS_START = "<!-- deep-read:sections start -->"
SECTIONS_END = "<!-- deep-read:sections end -->"


def api(path, token, **params):
    """GET with 429 backoff. Readwise rate-limits the v3 list endpoint; a long
    sweep will hit it. Honors Retry-After when present."""
    url = "https://readwise.io/api/v3/" + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"Authorization": f"Token {token}"})
    for attempt in range(6):
        try:
            return json.loads(urllib.request.urlopen(req).read())
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 5:
                raise
            wait = int(e.headers.get("Retry-After") or 0) or min(60, 5 * 2 ** attempt)
            print(f"    (429 — waiting {wait}s)", flush=True)
            time.sleep(wait)
    raise RuntimeError("unreachable")


def fetch_docs(token, ids=None, location=None, since=None, cache=None):
    """ids: exact lookup. location: one triage bucket. since: ISO date, spans
    ALL locations — use this for repair sweeps, since processed docs do not stay
    in `new` (an account-side rule may auto-archive them shortly after save)."""
    out = []
    if ids:
        for i in ids:
            r = api("list/", token, id=i)
            out += r.get("results", [])
        return out
    cache_path = None
    if cache:
        cache_path = os.path.expanduser(cache)
        if os.path.exists(cache_path):
            with open(cache_path, encoding="utf-8") as fh:
                st = json.load(fh)
            if st.get("done"):
                print(f"  (using cached doc list: {len(st['docs'])} docs)")
                return st["docs"]
            out, cursor = st["docs"], st.get("cursor")
            print(f"  (resuming: {len(out)} docs cached)")
        else:
            cursor = None
    else:
        cursor = None

    page = 0
    while True:
        p = {"pageSize": 100}
        if location:
            p["location"] = location
        if since:
            # API requires a full ISO 8601 datetime; accept a bare YYYY-MM-DD too
            p["updatedAfter"] = since if "T" in since else since + "T00:00:00Z"
        if cursor:
            p["pageCursor"] = cursor
        r = api("list/", token, **p)
        out += r.get("results", [])
        cursor = r.get("nextPageCursor")
        page += 1
        if cache_path:
            tmp = cache_path + ".tmp"
            with open(tmp, "w", encoding="utf-8") as fh:
                json.dump({"docs": out, "cursor": cursor, "done": not cursor}, fh)
            os.replace(tmp, cache_path)
        if page % 10 == 0:
            print(f"  fetched {len(out)} docs...", flush=True)
        if not cursor:
            break
    return out


def candidate_files():
    for dp, _, fns in os.walk(READWISE_DIR):
        if EXCLUDE_DIR in os.path.relpath(dp, READWISE_DIR).split(os.sep):
            continue
        for fn in fns:
            if fn.endswith(".md"):
                yield os.path.join(dp, fn)


FRONTMATTER_SOURCE = re.compile(r'^source:\s*"?([^"\n]+)"?\s*$', re.M)


def _norm(s):
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def build_index():
    """Two exact-match dicts: frontmatter source URL -> path, normalized title
    -> path. Built once; lookup is O(1). A linear scan per document made a
    full-history sweep O(docs x files) and took hours."""
    by_source, by_title = {}, {}
    for path in candidate_files():
        try:
            head = open(path, encoding="utf-8", errors="ignore").read(2000)
        except OSError:
            continue
        m = FRONTMATTER_SOURCE.search(head)
        if m:
            by_source.setdefault(m.group(1).strip(), path)
        by_title.setdefault(_norm(os.path.basename(path)[:-3]), path)
    return by_source, by_title


def find_file(doc, index):
    """Match on the frontmatter `source:` field, then on an exact normalized
    title.

    Deliberately strict. An earlier version searched for the source_url
    anywhere in the body, which silently mis-matched any document whose URL
    merely appeared as a link *inside another note* — it put the "Exploit
    brokers pay $500,000" analysis into the Wordfence wp2shell file. A loose
    title-prefix fallback had the same hazard. Returning None is correct and
    recoverable; returning the wrong file overwrites real content.
    """
    by_source, by_title = index
    src = (doc.get("source_url") or "").strip()
    if src and src in by_source:
        return by_source[src]
    norm = _norm((doc.get("title") or "").strip())
    return by_title.get(norm) if norm else None


RULE_LINE = {"---", "***", "___", "- - -", "* * *"}


TEMPLATE_LIBRARY = re.compile(r"^\s*#{1,4}\s*🧰\s*Template Library")


def drop_template_library(src):
    """Cut the 🧰 Template Library section and everything after it.

    article_template.txt marks that section DO-NOT-EMIT — it is Note Refactor
    plugin reference material for humans, and the model is told to stop emitting
    after the Fleeting Queue closes. It has been emitted anyway. Measured
    2026-08-01: 916 vault files carried it, ~5.4 KB each, and it is the single
    source of the vault's `[[{{author}}]]`, `[[{{publisher_or_journal}}]]`,
    `[[Parent-Concept]]`, `[[Source-Literature-Note]]` and `[[[MISSING]]]` links
    — roughly 13,000 unresolvable wikilinks in total.

    Stripping here rather than in the notes means the fix survives re-mirroring
    without needing 900+ API writes back to Reader. Reader keeps the raw notes;
    the vault (and therefore Obsidian Publish) gets the clean version.
    """
    for i, ln in enumerate(src):
        if TEMPLATE_LIBRARY.match(ln):
            # also drop a trailing rule/blank separator left above it
            while i and src[i - 1].strip() in ("", "---", "***", "___"):
                i -= 1
            return src[:i]
    return src


NOTE_REFACTOR_GOAL = re.compile(r"^\s*(>\s*)?Goal: Use Note Refactor")
NOTE_REFACTOR_END = re.compile(r"\{\{new_note_title\}\}")
BLOCK_DELIM = re.compile(r"^\s*(>\s*)?(```|<!--|-->)\s*$")


def drop_note_refactor_block(src):
    """Cut the Note Refactor how-to block out of the Refactor Appendix.

    This is the Template Library's sibling and the second half of the same
    DO-NOT-EMIT defect: plugin instructions for a human, emitted into the notes.
    It ends on a `Note Link Template` line carrying `[[{{new_note_title}}]]` and
    `[[{{title}}]]`, which is where the vault's remaining `{{...}}` wikilinks
    came from — 417 of each, measured 2026-08-01 after the Template Library
    cleanup had already run.

    Anchor on the prose, not the delimiter. The block ships wrapped four
    different ways across the corpus — `<!-- -->`, a ``` fence, one of those
    with the opener truncated away, and a bare space-indented run with no
    prefix at all — because it is mirrored both into the `>` callout and into
    the plugin's own body render. Matching delimiters caught only 376 of 406
    files; matching the `Goal:` line caught all of them.
    """
    out, i = [], 0
    while i < len(src):
        if NOTE_REFACTOR_GOAL.match(src[i]):
            j = i
            while j < len(src) and not NOTE_REFACTOR_END.search(src[j]):
                j += 1
            if j < len(src) and j - i <= 30:
                if out and BLOCK_DELIM.match(out[-1]):
                    out.pop()
                end = j + 1
                if end < len(src) and BLOCK_DELIM.match(src[end]):
                    end += 1
                i = end
                continue
        out.append(src[i])
        i += 1
    return out


def _prepare(notes):
    """Shared preprocessing for both halves of the mirrored output."""
    src = notes.rstrip().split("\n")
    src = drop_template_library(src)
    src = drop_note_refactor_block(src)
    # `by [[MISSING]] via [[YouTube]]` — the literal the template emits when the
    # author is unknown. As a wikilink it invents a shared "MISSING" note that 425
    # unrelated sources all point at; as prose it just reads as missing metadata.
    src = [ln.replace("[[MISSING]]", "an unnamed author") for ln in src]
    # drop the two delimiters of a leading YAML frontmatter block, keep content
    if src and src[0].strip() == "---":
        for j in range(1, len(src)):
            if src[j].strip() == "---":
                src = src[1:j] + src[j + 1:]
                break
    return src


# First top-level section heading. Everything above it is provenance and stays in
# the callout; everything from it down is the analysis and gets unwrapped.
_FIRST_SECTION = re.compile(r"^#{2,4}\s+\S")


def _split_head_sections(src):
    for i, ln in enumerate(src):
        if _FIRST_SECTION.match(ln):
            return src[:i], src[i:]
    return src, []


def build_callout(notes):
    """Render the provenance head as a blockquote callout, defusing rule lines.

    A `> ---` directly under a quoted text line is parsed as a SETEXT HEADING
    UNDERLINE, which terminates the callout — the dropdown then shows only the
    text above it and the rest of the analysis spills onto the page outside the
    dropdown. The deep-read template opens with YAML frontmatter, so its closing
    `---` sat under `date created:` and truncated every callout in the vault
    (measured 2026-07-24: 6,025 of 6,068 files).

    Since 2026-08-28 this carries only the head — see SECTIONS_START.
    """
    head, _ = _split_head_sections(_prepare(notes))
    out = [CALLOUT_HEAD]
    for ln in head:
        if ln.strip() in RULE_LINE and out[-1].strip() not in (">", CALLOUT_HEAD):
            out.append(">")
        out.append(("> " + ln).rstrip())
    return "\n".join(out)


def build_sections(notes):
    """Render the analysis sections at top level, bracketed by markers.

    Returns "" when the notes carry no `## ` section at all, so a doc whose notes
    are a bare paragraph still mirrors exactly as before.

    Rule lines are defused here too, for a different reason than in the callout:
    outside a blockquote a `---` immediately under a text line is still a setext
    H2, which would inject a junk heading straight into the published TOC.
    """
    _, sections = _split_head_sections(_prepare(notes))
    if not sections:
        return ""
    out = [SECTIONS_START]
    for ln in sections:
        if ln.strip() in RULE_LINE and out and out[-1].strip() not in ("", SECTIONS_START):
            out.append("")
        out.append(ln.rstrip())
    out.append(SECTIONS_END)
    return "\n".join(out)


def strip_existing(body):
    """Remove any existing Document Notes callout and any previously-written
    top-level sections block, so a re-mirror replaces rather than duplicates."""
    if SECTIONS_START in body:
        pre, rest = body.split(SECTIONS_START, 1)
        post = rest.split(SECTIONS_END, 1)[1] if SECTIONS_END in rest else ""
        body = pre.rstrip("\n") + "\n" + post.lstrip("\n")
    lines = body.split("\n")
    out, i = [], 0
    while i < len(lines):
        if lines[i].startswith(CALLOUT_HEAD):
            i += 1
            while i < len(lines) and (lines[i].startswith(">") or lines[i].strip() == ""):
                # stop at a blank line that is followed by a non-quote line
                if lines[i].strip() == "":
                    j = i
                    while j < len(lines) and lines[j].strip() == "":
                        j += 1
                    if j < len(lines) and not lines[j].startswith(">"):
                        break
                i += 1
            continue
        out.append(lines[i])
        i += 1
    return "\n".join(out)


def insert(body, callout, sections=""):
    """Place the callout (and, below it, the unwrapped sections) after the
    🔗 Source line, else before 📄 Full text / ## Highlights, else append."""
    block = callout if not sections else callout + "\n\n" + sections
    callout = block
    lines = body.split("\n")
    anchor = None
    for idx, ln in enumerate(lines):
        if ln.startswith("🔗 **Source:**"):
            anchor = idx + 1
    if anchor is None:
        for idx, ln in enumerate(lines):
            if ln.startswith("📄 **Full text:**") or ln.startswith("## Highlights"):
                anchor = idx
                break
    if anchor is None:
        return body.rstrip() + "\n\n" + callout + "\n"
    head = lines[:anchor]
    tail = lines[anchor:]
    while head and head[-1].strip() == "":
        head.pop()
    while tail and tail[0].strip() == "":
        tail.pop(0)
    return "\n".join(head + ["", callout, ""] + tail)


def stamp_doc_id(body, doc_id):
    """Record the Reader doc_id in the file's own YAML frontmatter.

    Without this, verifying "did the mirror land?" has to match on title or on
    note content, and both fail in ways that look like real defects:

      - Title matching hits the raw-transcript copies under
        `Full Document Contents/`, and near-duplicate titles ("You Ask, I
        Answer …") resolve to the wrong article.
      - Content matching on the head of `notes` fails because build_callout()
        drops the leading frontmatter delimiters, so the stored text never
        starts where Reader's does.

    An exact id lookup removes the whole class. Inserted directly after the
    opening delimiter so it can't be absorbed into the `tags:` list.
    """
    lines = body.split("\n")
    if not lines or lines[0].strip() != "---":
        return body
    key = f"readwise_doc_id: {doc_id}"
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            break
        if lines[i].startswith("readwise_doc_id:"):
            if lines[i] == key:
                return body
            lines[i] = key
            return "\n".join(lines)
    return "\n".join([lines[0], key] + lines[1:])


def unquote(block_lines):
    """Turn a rendered callout body back into raw note text."""
    out = []
    for ln in block_lines:
        if ln.startswith("> "):
            out.append(ln[2:])
        elif ln.startswith(">"):
            out.append(ln[1:])
        else:
            out.append(ln)
    return "\n".join(out)


def fix_structure(dry_run):
    """Repair callout STRUCTURE in place across the whole vault — no API calls.

    Two jobs:
      1. Defuse setext-terminating rule lines and strip frontmatter delimiters.
      2. **Migrate to the 2026-08-28 layout** — lift every `> ## ` analysis heading
         out of the callout to top level so Obsidian Publish and the outline pane
         can index it. See SECTIONS_START.

    It cannot restore content that was never written, so a callout truncated at
    8191 bytes stays truncated; use --since/--ids for those.
    """
    fixed = ok = 0
    for path in candidate_files():
        body = open(path, encoding="utf-8", errors="ignore").read()
        if CALLOUT_HEAD not in body:
            continue
        # Recover the doc's notes from whatever the file already holds — the
        # callout body, plus any sections block a previous migration wrote.
        # Reassembling both is what makes this idempotent AND non-destructive:
        # rebuilding from the callout alone would silently drop the sections of
        # an already-migrated file.
        lines = body.split("\n")
        start = next(i for i, l in enumerate(lines) if l.startswith(CALLOUT_HEAD))
        end = start + 1
        while end < len(lines) and (lines[end].startswith(">") or
                                    (lines[end].strip() == "" and
                                     end + 1 < len(lines) and lines[end + 1].startswith(">"))):
            end += 1
        notes = unquote(lines[start + 1:end])
        if SECTIONS_START in body:
            seg = body.split(SECTIONS_START, 1)[1].split(SECTIONS_END, 1)[0]
            notes = notes.rstrip("\n") + "\n" + seg.strip("\n")
        new = insert(strip_existing(body), build_callout(notes), build_sections(notes))
        if new == body:
            ok += 1
            continue
        if not dry_run:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(new)
        fixed += 1
    tag = " (dry run)" if dry_run else ""
    print(f"  {fixed} files migrated/restructured, {ok} already clean{tag}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ids", nargs="+")
    ap.add_argument("--location")
    ap.add_argument("--since", help="ISO date, e.g. 2026-07-01; spans all locations")
    ap.add_argument("--fix-structure", action="store_true",
                    help="repair callout structure vault-wide, offline (no API)")
    ap.add_argument("--cache", help="JSON file to cache/resume the doc list")
    ap.add_argument("--allow-shrink", action="store_true",
                    help="permit overwriting a callout that is LONGER than Reader's notes")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    if args.fix_structure:
        fix_structure(args.dry_run)
        return

    token = os.environ.get("READWISE_TOKEN")
    if not token:
        sys.exit("READWISE_TOKEN not set (source ~/.youtube_api_keys)")
    if not (args.ids or args.location or args.since):
        sys.exit("pass --ids, --location, or --since")

    allow_shrink = args.allow_shrink
    docs = fetch_docs(token, args.ids, args.location, args.since, args.cache)
    index = build_index()

    done = skipped = missing = shrink = 0
    for d in docs:
        notes = d.get("notes") or ""
        title = (d.get("title") or "")[:52]
        if not notes.strip():
            print(f"  SKIP     {title:52} (no notes)")
            skipped += 1
            continue
        path = find_file(d, index)
        if not path:
            print(f"  NO FILE  {title:52} (not synced yet?)")
            missing += 1
            continue
        body = open(path, encoding="utf-8").read()
        had = CALLOUT_HEAD in body
        new = stamp_doc_id(insert(strip_existing(body), build_callout(notes),
                                  build_sections(notes)), d["id"])
        if new == body:
            print(f"  OK       {title:52} (already current)")
            skipped += 1
            continue

        # Never silently shrink an existing callout. Some vault files hold a
        # LONGER analysis than Reader currently returns (notes edited or
        # replaced Reader-side after the mirror). Overwriting those destroys
        # content that exists nowhere else. Compare unquoted text, since the
        # rendered callout carries two extra chars per line.
        if had and not allow_shrink:
            lines = body.split("\n")
            s = next(i for i, l in enumerate(lines) if l.startswith(CALLOUT_HEAD))
            e = s + 1
            while e < len(lines) and lines[e].startswith(">"):
                e += 1
            existing = unquote(lines[s + 1:e]).strip()
            # Since the 2026-08-28 unwrap the callout holds only the provenance
            # head, so comparing it alone would make every file look like a
            # shrink-safe no-op. Count the sections block too.
            if SECTIONS_START in body:
                seg = body.split(SECTIONS_START, 1)[1]
                existing += "\n" + seg.split(SECTIONS_END, 1)[0]
            if len(existing.strip()) > len(notes.strip()):
                print(f"  SHRINK?  {title:52} vault={len(existing)} > reader={len(notes.strip())} — skipped")
                shrink += 1
                continue
        if not args.dry_run:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(new)
        verb = "REPLACED" if had else "ADDED"
        print(f"  {verb:8} {title:52} {len(notes)} chars -> {os.path.relpath(path, VAULT)}")
        done += 1

    tag = " (dry run)" if args.dry_run else ""
    print(f"\n  {done} written, {skipped} unchanged, {shrink} skipped-would-shrink, {missing} unmatched{tag}")


if __name__ == "__main__":
    main()
