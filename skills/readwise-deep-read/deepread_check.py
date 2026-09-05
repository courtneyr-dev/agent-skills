#!/usr/bin/env python3
"""
deepread_check.py — the CHECKER half of the readwise-deep-read maker/checker loop.

Why this exists: the deep-read pipeline has several steps (save, full 18-section notes,
inline highlights, TOPIC TAGS, backlog log). Running it manually across a long session,
the maker (me) declared docs "done" from memory and silently skipped document-level topic
tags on article saves. That is a maker grading its own homework. This script is the
deterministic, independent check — it re-derives completion from Reader's actual state,
not from any claim that the work was done. Deterministic facts (tags present? notes
contain the deep-read marker? at least one inline highlight?) need no second agent — the
script IS the check.

It does NOT fix anything. It reports PASS/FAIL per doc so the maker can fix what's missing.
Topic-tag assignment needs content judgment, so the checker flags absence; the human/maker
supplies the tags.

Usage:
  source ~/.youtube_api_keys
  python3 deepread_check.py --location new            # check the inbox
  python3 deepread_check.py --since 2026-06-17        # check docs saved since a date
  python3 deepread_check.py --ids <id1> <id2> ...     # check specific docs

Exit code is non-zero if any doc FAILs (so it can gate automation).
"""
import argparse, json, os, re, sys, time, urllib.error, urllib.parse, urllib.request

TOKEN = os.environ.get("READWISE_TOKEN")
BASE = "https://readwise.io/api/v3/list/"

# Vault-side check. This script used to verify Reader state ONLY, so a batch
# could pass green while none of it had reached Obsidian — which is exactly what
# happened on 2026-07-29 (12 docs complete in Reader, 0 mirrored, gate green).
# Reader-complete is not done; the published page reads from the vault.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    from mirror_notes import build_index, find_file, CALLOUT_HEAD
    VAULT_OK = True
except Exception:
    VAULT_OK = False


def vault_state(doc, index):
    """Locate this doc's vault file and confirm the notes actually landed —
    fully, in the right folder, with a cover image.

    Reuses mirror_notes.find_file rather than matching titles here: it is
    already strict, and it skips the raw-transcript copies under
    `Full Document Contents/` that a naive recursive glob picks up.
    Returns (status, detail) where status is one of:
      ok | nofile | nonotes | truncated | wrongfolder | nocover
    Checks run in this order and return on first failure — folder/cover are
    checked even when notes are fine, so a doc can independently FAIL on
    either without masking the other.
    """
    path = find_file(doc, index)
    if not path:
        return "nofile", None
    try:
        body = open(path, encoding="utf-8", errors="ignore").read()
    except OSError:
        return "nofile", None
    rel = os.path.basename(path)
    if CALLOUT_HEAD not in body or ("Refactor Appendix" not in body and not is_light_touch(body)):
        return "nonotes", rel

    # Diagnosed 2026-08-16: the Readwise plugin's own native sync can write a
    # callout that DOES contain "Refactor Appendix" as literal text inside a
    # still-truncated document only in rare cases, but far more often cuts off
    # well before it — however relying on that string alone missed at least
    # one case this session where the plugin wrote a shorter callout that
    # coincidentally still lacked "Refactor Appendix" but wasn't re-checked
    # for weeks. Cheap extra guard: the live `notes` field is already in
    # hand (this function is only called when notes are non-empty) — if the
    # vault file's total length is suspiciously small relative to it, flag
    # truncation even though the markers matched.
    live_notes = doc.get("notes") or ""
    if live_notes and len(body) < 0.5 * len(live_notes):
        return "truncated", rel

    # Mandatory per the user 2026-08-16: everything the deep-read pipeline
    # saves (articles AND YouTube videos) must land in the Articles folder,
    # not Books/Podcasts/wherever the plugin's category mapping would
    # otherwise put it, and must carry a featured image.
    cat = doc.get("category")
    if cat in ("article", "video") and "/Readwise/Articles/" not in path:
        return "wrongfolder", rel
    head = body[:2000]
    m = re.search(r"^cover:\s*(\S.*)$", head, re.MULTILINE)
    if not m or not m.group(1).strip():
        return "nocover", rel

    return "ok", rel

SUCCESSOR_STAMP = re.compile(r"^readwise_doc_id:\s*(\S+)", re.M)


def find_successor(doc, index):
    """Find the doc that REPLACED this one, if any.

    When Reader's scrape fails (the 71-byte no-subtitles sentinel, or a doc that
    comes back `word_count: None`), the fix is not repair — `html_content` is
    write-once, so the doc gets recreated at `<original url>#transcript` and the
    real analysis lands on a NEW doc_id. The original is then archived and stays
    permanently incomplete by every measure this script takes.

    Everything here is keyed on doc_id, so without this lookup a superseded
    original FAILs forever while the finished work sits one id away. That is not
    hypothetical: on 2026-08-22 a reconciliation of `needs_analysis` reported 4
    docs outstanding when only 1 was — the other 3 had completed successors and
    the queue was still holding the dead ids. Two subagents were dispatched to
    redo work that already existed.

    Matched through the vault index rather than the API because v3/list has no
    source_url filter — passing `source_url=` or `sourceUrl=` is silently ignored
    and returns the entire library (verified 2026-08-22, count=10000 either way).
    The vault is the right place to look anyway: a successor that has been
    mirrored is a successor whose work actually landed.
    """
    src = (doc.get("source_url") or "").strip()
    if not src or "#" in src:
        return None
    by_source, _ = index
    for cand_url, path in by_source.items():
        if cand_url.startswith(src + "#"):
            try:
                head = open(path, encoding="utf-8", errors="ignore").read(2000)
            except OSError:
                head = ""
            m = SUCCESSOR_STAMP.search(head)
            return {"id": m.group(1) if m else None, "file": os.path.basename(path)}
    return None


# Reader tag policy (reader_tag_policy): topic tags only.
# Forbidden: dated, pipeline-state, single-letter, source-format meta.
FORMAT_META = {"youtube","video","video-notes","article","processed","podcast",
               "transcript","audio-notes","email","rss","tweet","pdf","epub"}
PIPELINE = {"deep-read","deep-read-restored","lean","full","deepread-batch","inbox","processed"}

# The 18 sections every deep-read must carry (the user, 2026-08-28: "I want all of
# them every time, and I'm tired of the drifting happening").
#
# Why this exists: until now the only completeness test was `"Refactor Appendix" in
# notes`. A 2.5KB doc carrying Summary + Notes + Conclusion + an appendix stub passed
# green — measured on 'Why Is It So Difficult to Connect More Than One...' (2026-08-27),
# which was missing 15 of the 18 and was never flagged.
#
# Matching is on the heading NAME with the emoji optional. The first version of this
# check required the emoji and reported 1,827 recent docs as missing all 18 — wrong,
# because older notes use plain `## Summary`. Emoji are decoration the template has
# changed at least once; the name is the stable part.
REQUIRED_SECTIONS = [
    "summary", "main content", "notes", "references", "paraphrase", "newsletter",
    "action items", "hypotheses", "methodology", "questions", "future research",
    "implications", "learning styles", "accessibility assessment", "deib assessment",
    "logical validity", "darvo", "conclusion",
]

# A heading line, inside the vault callout (`> ## x`) or bare (`## x`), at any level.
_HEADING = re.compile(r"^>?[ \t]*#{1,4}[ \t]+(.+?)[ \t]*$", re.M)


def _heading_names(notes):
    """Normalized heading names: emoji and leading punctuation stripped, lowercased.

    A leading non-alphanumeric strip rather than an emoji range — the template has used 🗒️, 🧠, ✅ and plain text
    for the same headings across revisions, and the variation-selector suffixes
    (U+FE0F) make explicit ranges fragile.
    """
    out = []
    for raw in _HEADING.findall(notes):
        name = re.sub(r"^[^0-9A-Za-z]+", "", raw).strip().lower()
        if name:
            out.append(name)
    return out


# A deliberately abbreviated read is not drift. the user asks for light-touch notes on
# follow-ups and thin sources; forcing those to 18 sections would pad them to satisfy a
# checker. Recognized markers, in the notes body:
#   <!-- deep-read: light-touch -->        (preferred, explicit)
#   "not a full deep-read"                 (the prose form already in use, 2026-08)
# Marked docs are exempt from the section check everywhere at once — the checker, the
# push_notes write gate and the PreToolUse MCP hook all route through missing_sections().
LIGHT_TOUCH = re.compile(r"<!--\s*deep-read:\s*light-touch\s*-->|not a full deep-read", re.I)


def is_light_touch(notes):
    return bool(LIGHT_TOUCH.search(notes or ""))


def missing_sections(notes):
    """Return the required section names absent from `notes`.

    A section counts as present when some heading name starts with it, so
    '📚 References' and '🔗 References (in-page)' both satisfy 'references', and
    '🧠 Learning Styles Assessment' satisfies 'learning styles'.
    """
    if is_light_touch(notes):
        return []
    names = _heading_names(notes)
    return [want for want in REQUIRED_SECTIONS
            if not any(n.startswith(want) for n in names)]


def get(url):
    """GET with 429 backoff. Readwise rate-limits v3/list (~20 req/min) and this
    script fires one request per --ids entry, so any batch beyond a handful will
    trip it. Same retry policy as mirror_notes.api(); honors Retry-After."""
    req = urllib.request.Request(url, headers={"Authorization": f"Token {TOKEN}"})
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

def fetch_docs(args):
    if args.ids:
        out = []
        for i in args.ids:
            r = get(f"{BASE}?id={urllib.parse.quote(i)}&withHtmlContent=false")
            out += r.get("results", [])
        return out
    params = {"withHtmlContent": "false"}
    if args.location: params["location"] = args.location
    if args.since: params["updatedAfter"] = args.since + "T00:00:00Z"
    docs, cursor = [], None
    while True:
        u = BASE + "?" + urllib.parse.urlencode(params) + (f"&pageCursor={cursor}" if cursor else "")
        r = get(u); docs += r.get("results", [])
        cursor = r.get("nextPageCursor")
        if not cursor: break
    return docs

def tag_violations(tags):
    bad = []
    for t in tags:
        tl = t.lower().strip()
        if len(tl) <= 1: bad.append(f"{t}(single-letter)")
        elif re.search(r"\d{2,}|\d{4}-\d\d|/20\d\d", tl) or re.fullmatch(r"\d+", tl): bad.append(f"{t}(dated)")
        elif tl in PIPELINE: bad.append(f"{t}(pipeline)")
        elif tl in FORMAT_META: bad.append(f"{t}(format-meta)")
    return bad

def check(doc, explicit=False, index=None):
    cat = doc.get("category")
    # never grade highlight/note children or RSS/feed items — they're not deep-read outputs
    if cat in ("highlight", "note", "rss", "feed"): return None
    tags = list((doc.get("tags") or {}).keys()) if isinstance(doc.get("tags"), dict) else list(doc.get("tags") or [])
    notes = doc.get("notes") or ""
    # What makes a doc a deep-read is the ANALYSIS, not the Refactor Appendix.
    #
    # The appendix is section 22 — outside the required 18 — and the template
    # stopped emitting it after the reflib split on 2026-08-22. Gating on it sent
    # every complete deep-read down the "incomplete" branch, so the real section
    # check below never ran: 954 of 1,473 docs were reported failing on
    # 2026-08-28 while carrying all 18 sections. Fixed 2026-08-28.
    miss = missing_sections(notes)
    has_deepread = len(miss) < len(REQUIRED_SECTIONS)
    # A doc with no deep-read notes is an un-processed save, not a FAILED deep-read.
    # Skip it unless the user checked it explicitly by --ids (then we still report).
    if not notes.strip() and not explicit: return None
    fails = []
    if not has_deepread:
        # Before calling this incomplete, check whether it was superseded — a
        # recreated doc carries the analysis under a different id and this one is
        # just a dead pointer. Reporting it as a FAIL sends someone off to redo
        # finished work; see find_successor().
        succ = find_successor(doc, index) if index is not None else None
        if succ:
            return {"id": doc.get("id"), "title": (doc.get("title") or "")[:55],
                    "cat": cat, "tags": tags, "fails": [], "vault": None,
                    "superseded": succ}
        fails.append("no deep-read analysis in notes (none of the 18 sections present)")
    else:
        # Structural completeness against the canonical 18.
        if miss:
            fails.append(f"INCOMPLETE — missing {len(miss)}/18 sections: " + ", ".join(miss))
    if not tags: fails.append("NO TAGS")
    else:
        v = tag_violations(tags)
        if v: fails.append("BAD TAGS: " + ", ".join(v))
    vault = None
    if index is not None and has_deepread:
        status, rel = vault_state(doc, index)
        vault = rel
        if status == "nofile":
            fails.append("NOT MIRRORED to vault (sync Readwise in Obsidian, then mirror_notes.py)")
        elif status == "nonotes":
            fails.append(f"vault file has no Document Notes callout: {rel}")
        elif status == "truncated":
            fails.append(f"vault file callout looks TRUNCATED vs live Reader notes (re-run mirror_notes.py --ids {doc.get('id')}): {rel}")
        elif status == "wrongfolder":
            fails.append(f"vault file is NOT in the Readwise/Articles/ folder: {rel}")
        elif status == "nocover":
            fails.append(f"vault file has no cover/featured image in frontmatter: {rel}")
    return {"id": doc.get("id"), "title": (doc.get("title") or "")[:55],
            "cat": cat, "tags": tags, "fails": fails, "vault": vault,
            "superseded": None}

def main():
    if not TOKEN:
        print("ERROR: source ~/.youtube_api_keys (READWISE_TOKEN missing)"); sys.exit(2)
    ap = argparse.ArgumentParser()
    ap.add_argument("--location"); ap.add_argument("--since"); ap.add_argument("--ids", nargs="*")
    ap.add_argument("--no-vault", action="store_true",
                    help="skip the vault-mirror check (Reader-side only)")
    a = ap.parse_args()
    if not (a.location or a.since or a.ids): a.location = "new"
    index = None
    if not a.no_vault and VAULT_OK:
        try:
            index = build_index()
        except Exception as e:
            print(f"(vault check unavailable: {e})")
    rows = [r for r in (check(d, explicit=bool(a.ids), index=index) for d in fetch_docs(a)) if r]
    nsup = sum(1 for r in rows if r.get("superseded"))
    npass = sum(1 for r in rows if not r["fails"] and not r.get("superseded"))
    nfail = len(rows) - npass - nsup
    scope = "Reader+vault" if index is not None else "Reader only"
    tail = f" / {nsup} SUPERSEDED" if nsup else ""
    print(f"\nDEEP-READ COMPLETION CHECK ({scope}) — {len(rows)} doc(s) | {npass} PASS / {nfail} FAIL{tail}\n")
    for r in sorted(rows, key=lambda x: bool(x["fails"]), reverse=True):
        if r.get("superseded"):
            s = r["superseded"]
            print(f"⏭  {r['title']:55} [{r['cat']}] {r['id']}")
            print(f"      └─ SUPERSEDED by {s['id'] or '(unstamped)'} — analysis lives there, "
                  f"this id is a dead pointer; drop it from needs_analysis")
            print(f"      vault: {s['file']}")
            continue
        mark = "✅" if not r["fails"] else "❌"
        print(f"{mark} {r['title']:55} [{r['cat']}] {r['id']}")
        for f in r["fails"]: print(f"      └─ {f}")
        if not r["fails"]:
            print(f"      tags: {', '.join(r['tags'])}")
            if r["vault"]: print(f"      vault: {r['vault']}")
    # Superseded is not a failure — the work exists, the pointer is stale.
    sys.exit(1 if nfail else 0)

if __name__ == "__main__":
    main()
