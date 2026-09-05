#!/usr/bin/env python3
"""Inbox triage — the heartbeat at the FRONT of the synthesis loop.

The backlog tracks docs after processing. This scores NEW Reader-inbox docs
*before* processing, against the threads you're actively building (your MOCs),
and proposes a deep-read shortlist. Discovery + triage, findings come to you —
you stay the decision gate. Read-only: it proposes, it never processes.

The signal: a doc that hits an active MOC thread (its headings + the notes it
links) ranks high, and the report names WHICH thread it hits. Docs already
logged in the backlog or already deep-read are excluded.

Usage:
  source ~/.youtube_api_keys            # needs READWISE_TOKEN
  inbox_triage.py [--top N] [--location new] [--min-read N]
"""
import argparse
import json
import os
import re
import urllib.request

VAULT = os.path.expanduser(os.environ.get("VAULT_DIR", "~/Documents/Notes"))
MOC_DIR = os.path.join(VAULT, "Resources/MOCs")
PERM_DIR = os.path.join(VAULT, "Resources/Permanent Notes")
BACKLOG = os.path.join(VAULT, "_Synthesis Backlog.md")

STOP = set("""the a an is are be to of in on for and or not it its as at by we you i that this with from into
more do does your their our he you they them his your was were have has had will would can could been being there
here what who why how when which about over under after before they're you're it's a's new now get got make made
just only also so but if then than too very can't don't more most some any all out up off down -- — · 2026 2025
how-to into onto your you we's wordpress""".split())


def toks(s):
    return {w for w in re.findall(r"[a-z0-9]{4,}", (s or "").lower()) if w not in STOP}


def read(p):
    return open(p, encoding="utf-8", errors="ignore").read()


def md_files(root):
    return [os.path.join(root, f) for f in os.listdir(root) if f.endswith(".md")]


def build_moc_models():
    """Per-MOC token set = headings + linked note basenames + title. Focused, not full prose."""
    models = {}
    for f in md_files(MOC_DIR):
        name = os.path.basename(f)[:-3]
        body = read(f)
        headings = " ".join(re.findall(r"^#{1,4}\s+(.+)$", body, re.M))
        links = " ".join(os.path.basename(t) for t in re.findall(r"\[\[([^\]|#]+)", body))
        models[name] = toks(name + " " + headings + " " + links)
    return models


def known_authors():
    """Author surnames already present in the vault (PN sources + filenames) → 'new author' signal."""
    names = set()
    for f in md_files(PERM_DIR):
        names |= toks(os.path.basename(f)[:-3])
    return names


def logged_doc_ids():
    if not os.path.exists(BACKLOG):
        return set()
    body = read(BACKLOG)
    seg = body.split("BACKLOG:ACTIVE:START", 1)[-1].split("BACKLOG:ACTIVE:END", 1)[0]
    ids = set()
    for ln in seg.splitlines():
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if len(cells) >= 3 and re.match(r"^01[a-z0-9]{24}$", cells[2]):
            ids.add(cells[2])
    return ids


def inbox(location, tok):
    req = urllib.request.Request(
        f"https://readwise.io/api/v3/list/?location={location}&pageSize=100",
        headers={"Authorization": f"Token {tok}"})
    return json.loads(urllib.request.urlopen(req).read().decode(), strict=False).get("results", [])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=5, help="cap the deep-read shortlist")
    ap.add_argument("--location", default="new")
    ap.add_argument("--min-read", type=int, default=2, help="min shared tokens to count as a thread hit")
    args = ap.parse_args()

    tok = os.environ.get("READWISE_TOKEN")
    if not tok:
        print("No READWISE_TOKEN. Run: source ~/.youtube_api_keys")
        return

    mocs = build_moc_models()
    authors = known_authors()
    logged = logged_doc_ids()
    docs = inbox(args.location, tok)

    scored = []
    excluded = 0
    for d in docs:
        if d["id"] in logged:
            excluded += 1
            continue
        notes = d.get("notes") or ""
        if "Refactor Appendix" in notes:          # already deep-read
            excluded += 1
            continue
        tags = d.get("tags") or {}
        tagstr = " ".join(tags.keys()) if isinstance(tags, dict) else " ".join(tags or [])
        dt = toks(" ".join([d.get("title") or "", d.get("summary") or "",
                             tagstr, d.get("site_name") or ""]))
        # best-matching MOC thread
        best_moc, best_hits = None, 0
        for name, mt in mocs.items():
            h = len(dt & mt)
            if h > best_hits:
                best_moc, best_hits = name, h
        author = d.get("author") or ""
        new_author = bool(author) and not (toks(author) & authors)
        scored.append({
            "id": d["id"], "title": (d.get("title") or "")[:70],
            "author": author[:30], "cat": d.get("category"),
            "moc": best_moc, "hits": best_hits, "new_author": new_author,
            "url": d.get("url") or d.get("source_url"),
        })

    scored.sort(key=lambda x: x["hits"], reverse=True)
    deep = [s for s in scored if s["hits"] >= max(3, args.min_read + 1)][:args.top]
    maybe = [s for s in scored if s not in deep and s["hits"] >= args.min_read]
    skip = [s for s in scored if s["hits"] < args.min_read]

    print(f"# Inbox triage — {len(scored)} unprocessed in '{args.location}' ({excluded} already logged/deep-read)\n")

    print(f"## 🔥 Deep-read shortlist (top {len(deep)})")
    for s in deep:
        na = " · 🆕 new author" if s["new_author"] else ""
        print(f"- **{s['title']}** — matches *{s['moc']}* ({s['hits']} thread hits){na}\n  `{s['id']}`  {s['author']}")
    if not deep:
        print("- none cleared the bar ✓")

    print(f"\n## 🤔 Maybe — weaker thread match ({len(maybe)})")
    for s in maybe:
        print(f"- {s['title']} — *{s['moc']}* ({s['hits']})  `{s['id']}`")
    if not maybe:
        print("- none")

    print(f"\n## ⏭️ Low fit — skip or archive ({len(skip)})")
    for s in skip:
        na = " 🆕" if s["new_author"] else ""
        print(f"- {s['title']}{na}  `{s['id']}`")
    if not skip:
        print("- none")

    print("\n> Approve a shortlist and I'll run the deep-read pipeline on those IDs, then they auto-log to the backlog.")


if __name__ == "__main__":
    main()
