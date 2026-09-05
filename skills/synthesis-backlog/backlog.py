#!/usr/bin/env python3
"""Synthesis backlog — the on-disk memory spine for the Readwise → Obsidian synthesis loop.

Osmani's rule: "the model forgets everything between runs so the memory has to be on disk
and not in the context. The agent forgets, the repo doesn't." This file IS that memory —
"what's processed but not yet synthesized" lives here, surviving every session boundary,
instead of being re-loaded into chat by hand each time.

The deep-read pipeline logs each processed doc (`add`); synthesis updates status (`set`);
`triage` reports what's still outstanding. The backlog is a normal Obsidian markdown table
(the user can read/edit it); hidden HTML-comment markers make append/update robust.

Commands:
  backlog.py add  --doc-id ID --title "T" [--type article] [--read no] [--atoms pending] [--moc pending] [--notes "..."]
  backlog.py set  --doc-id ID [--atoms STATE] [--moc STATE] [--read STATE] [--notes "..."]
  backlog.py list [--pending]
  backlog.py triage [--reader] [--days N]
  backlog.py reconcile [--apply "TITLE"]   # find duplicate-title rows; --apply keeps the
                                           # best row of that one group, marks the rest skip

States: pending | done | skip | —
"""
import argparse
import datetime
import os
import re

BACKLOG = os.path.join(os.path.expanduser(os.environ.get("VAULT_DIR", "~/Documents/Notes")), "_Synthesis Backlog.md")
COLS = ["Date", "Title", "doc_id", "Type", "Atoms", "MOC", "Read", "Notes"]
START = "<!-- BACKLOG:ACTIVE:START -->"
END = "<!-- BACKLOG:ACTIVE:END -->"

SCAFFOLD = f"""# Synthesis Backlog

Working memory for the Readwise → Obsidian synthesis loop. The deep-read pipeline appends a
row when a doc is processed; triage and synthesis update the status columns. **This file is
the loop's spine** — it lives on disk so "what still needs synthesis" survives between
sessions instead of living in chat. *The agent forgets; the repo doesn't.*

**Status legend:** `pending` = not done yet · `done` = complete · `skip` = deliberately skipped · `—` = n/a
**Columns:** Atoms = did this spawn permanent note(s)? · MOC = wired into a MOC? · Read = have you actually read/synthesized it (comprehension-debt guard)?

## Last triage

_(run `triage my backlog` to populate)_

## Active

{START}
| {" | ".join(COLS)} |
| {" | ".join("---" for _ in COLS)} |
{END}

## Done

_(fully-resolved rows can be moved here to keep Active focused)_
"""


def load():
    if not os.path.exists(BACKLOG):
        with open(BACKLOG, "w", encoding="utf-8") as f:
            f.write(SCAFFOLD)
    return open(BACKLOG, encoding="utf-8").read()


def save(text):
    with open(BACKLOG, "w", encoding="utf-8") as f:
        f.write(text)


def clean(s):
    """Make a value table-safe: no pipes/newlines, trimmed."""
    return re.sub(r"\s+", " ", (s or "").replace("|", "/")).strip()


def parse_rows(text):
    """Return list of dicts for data rows between the markers (skips header+separator)."""
    seg = text.split(START, 1)[1].split(END, 1)[0]
    rows = []
    for ln in seg.splitlines():
        if not ln.strip().startswith("|"):
            continue
        cells = [c.strip() for c in ln.strip().strip("|").split("|")]
        if cells == COLS or all(set(c) <= set("-") for c in cells):
            continue  # header or separator
        if len(cells) == len(COLS):
            rows.append(dict(zip(COLS, cells)))
    return rows


def row_to_line(r):
    return "| " + " | ".join(r[c] for c in COLS) + " |"


def write_rows(text, rows):
    head = text.split(START, 1)[0]
    tail = text.split(END, 1)[1]
    body = [START,
            "| " + " | ".join(COLS) + " |",
            "| " + " | ".join("---" for _ in COLS) + " |"]
    body += [row_to_line(r) for r in rows]
    body.append(END)
    return head + "\n".join(body) + tail


def cmd_add(a):
    text = load()
    rows = parse_rows(text)
    if any(r["doc_id"] == a.doc_id for r in rows):
        print(f"already logged: {a.doc_id} (skipped)")
        return
    # Same title under a new doc_id is how duplicates enter (Reader doc recreated
    # mid-session gets a fresh id). Titles aren't unique, so log anyway — but warn.
    same_title = [r["doc_id"] for r in rows
                  if r["Title"].lower() == clean(a.title)[:70].lower()]
    if same_title:
        print(f"note: title matches existing row(s) {', '.join(same_title)} — "
              f"run `reconcile` if this is the same doc re-saved")
    rows.append({
        "Date": a.date or datetime.date.today().isoformat(),
        "Title": clean(a.title)[:70],
        "doc_id": a.doc_id,
        "Type": a.type,
        "Atoms": a.atoms,
        "MOC": a.moc,
        "Read": a.read,
        "Notes": clean(a.notes),
    })
    save(write_rows(text, rows))
    print(f"logged: {clean(a.title)[:70]}  [{a.doc_id}]")


def cmd_set(a):
    text = load()
    rows = parse_rows(text)
    hit = False
    for r in rows:
        if r["doc_id"] == a.doc_id:
            hit = True
            if a.atoms: r["Atoms"] = a.atoms
            if a.moc: r["MOC"] = a.moc
            if a.read: r["Read"] = a.read
            if a.notes is not None: r["Notes"] = clean(a.notes)
    if not hit:
        print(f"not found: {a.doc_id}")
        return
    save(write_rows(text, rows))
    print(f"updated: {a.doc_id}")


def cmd_list(a):
    rows = parse_rows(load())
    if a.pending:
        rows = [r for r in rows if "pending" in (r["Atoms"], r["MOC"]) or r["Read"] == "no"]
    for r in rows:
        print(f"{r['Date']} | {r['Title'][:50]:50} | atoms={r['Atoms']:7} moc={r['MOC']:7} read={r['Read']}")
    print(f"\n{len(rows)} row(s)")


def cmd_reconcile(a):
    """Find duplicate-title rows (same source logged under two doc_ids).

    Report-only by default. Same titles CAN be genuinely different docs
    ("Exhibit A", "make.wordpress.org"), so --apply resolves one named group at
    a time rather than everything at once: the best row is kept (atoms done
    first, then oldest) and the rest are marked skip with a duplicate-of note.
    """
    text = load()
    rows = parse_rows(text)
    groups = {}
    for r in rows:
        groups.setdefault(r["Title"].lower(), []).append(r)
    dups = {t: g for t, g in groups.items()
            if len([r for r in g if r["Atoms"] != "skip"]) > 1}
    if not dups:
        print("no duplicate titles among non-skip rows ✓")
        return

    # Keeper = most progress first (a done/done row beats an older moc:pending one),
    # never a row self-described as superseded, then oldest.
    def rank(r):
        return (r["Atoms"] != "done", r["MOC"] != "done",
                "superseded duplicate" in r["Notes"].lower(), r["Date"], r["doc_id"])

    for t in sorted(dups):
        g = sorted(dups[t], key=rank)
        print(f"\n{g[0]['Title']}")
        for i, r in enumerate(g):
            tag = "keep" if i == 0 else ("skip" if r["Atoms"] == "skip" else "dup?")
            note = f"  · {r['Notes']}" if r["Notes"] else ""
            print(f"  {tag}: {r['Date']} `{r['doc_id']}` atoms={r['Atoms']} moc={r['MOC']}{note}")
    if a.apply:
        key = a.apply.lower()
        if key not in dups:
            print(f"\n--apply: no duplicate group titled {a.apply!r}")
            return
        g = sorted(dups[key], key=rank)
        keeper, changed, dropped = g[0], 0, []
        for r in g[1:]:
            if r["doc_id"] == keeper["doc_id"]:
                dropped.append(r)          # literally the same record twice — remove it
            elif r["Atoms"] != "skip":
                r["Atoms"] = r["MOC"] = "skip"
                r["Notes"] = clean((r["Notes"] + " · " if r["Notes"] else "")
                                   + f"duplicate of {keeper['doc_id']}")
                changed += 1
        rows = [r for r in rows if not any(r is d for d in dropped)]
        save(write_rows(text, rows))
        print(f"\n--apply: kept `{keeper['doc_id']}`, marked {changed} duplicate row(s) skip"
              + (f", removed {len(dropped)} identical row(s)" if dropped else ""))
    else:
        print("\n(verify each group is really the same doc, then "
              "`reconcile --apply \"TITLE\"` to resolve that one group)")


def reader_inbox_unlogged(logged_ids):
    """Discovery: inbox docs not yet in the backlog that lack notes/tags. Needs READWISE_TOKEN."""
    tok = os.environ.get("READWISE_TOKEN")
    if not tok:
        return None
    import json, urllib.request
    req = urllib.request.Request(
        "https://readwise.io/api/v3/list/?location=new&pageSize=100",
        headers={"Authorization": f"Token {tok}"})
    data = json.loads(urllib.request.urlopen(req).read().decode(), strict=False)
    out = []
    for r in data.get("results", []):
        if r["id"] in logged_ids:
            continue
        notes = r.get("notes") or ""
        tags = r.get("tags") or {}
        thin = "Refactor Appendix" not in notes
        if thin or not tags:
            out.append((r["id"], (r.get("title") or "")[:55], r.get("category"),
                        "no-notes" if thin else "no-tags"))
    return out


def cmd_triage(a):
    text = load()
    rows = parse_rows(text)
    cutoff = None
    if a.days:
        cutoff = (datetime.date.today() - datetime.timedelta(days=a.days)).isoformat()
        rows = [r for r in rows if r["Date"] >= cutoff]

    pend_atoms = [r for r in rows if r["Atoms"] == "pending"]
    pend_moc = [r for r in rows if r["MOC"] == "pending"]
    unread = [r for r in rows if r["Read"] == "no"]

    lines = []
    scope = f" (last {a.days}d)" if a.days else ""
    lines.append(f"# Backlog triage{scope} — {len(rows)} tracked\n")

    lines.append(f"## 🧪 Needs atoms — processed, no permanent note yet ({len(pend_atoms)})")
    lines += [f"- {r['Title']}  `{r['doc_id']}`  {('· ' + r['Notes']) if r['Notes'] else ''}" for r in pend_atoms] or ["- none ✓"]

    lines.append(f"\n## 🗺️ Needs a MOC home ({len(pend_moc)})")
    lines += [f"- {r['Title']}  `{r['doc_id']}`" for r in pend_moc] or ["- none ✓"]

    lines.append(f"\n## 📖 Comprehension debt — processed but unread ({len(unread)})")
    lines += [f"- {r['Title']}  ({r['Type']})" for r in unread] or ["- none ✓"]

    if a.reader:
        disc = reader_inbox_unlogged({r["doc_id"] for r in parse_rows(text)})
        lines.append(f"\n## 🆕 In inbox, not logged + thin ({0 if disc is None else len(disc)})")
        if disc is None:
            lines.append("- (no READWISE_TOKEN — `source ~/.youtube_api_keys` to enable inbox discovery)")
        else:
            lines += [f"- {t}  `{i}`  ({cat}, {why})" for i, t, cat, why in disc] or ["- none ✓"]

    lines.append("\n> For link/duplicate/orphan verification, run the **vault-hygiene-checker** skill.")
    report = "\n".join(lines)
    print(report)

    # write a short summary into the file's "Last triage" section
    stamp = datetime.date.today().isoformat()
    summary = (f"_Last run {stamp}{scope}:_ "
               f"**{len(pend_atoms)}** need atoms · **{len(pend_moc)}** need a MOC home · "
               f"**{len(unread)}** unread.")
    new = re.sub(r"(## Last triage\n\n).*?(\n\n## Active)",
                 rf"\1{summary}\2", text, flags=re.S)
    save(new)


def main():
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="cmd", required=True)

    a = sub.add_parser("add")
    a.add_argument("--doc-id", required=True)
    a.add_argument("--title", required=True)
    a.add_argument("--type", default="article")
    a.add_argument("--read", default="no")
    a.add_argument("--atoms", default="pending")
    a.add_argument("--moc", default="pending")
    a.add_argument("--notes", default="")
    a.add_argument("--date", default="")
    a.set_defaults(func=cmd_add)

    s = sub.add_parser("set")
    s.add_argument("--doc-id", required=True)
    s.add_argument("--atoms")
    s.add_argument("--moc")
    s.add_argument("--read")
    s.add_argument("--notes")
    s.set_defaults(func=cmd_set)

    l = sub.add_parser("list")
    l.add_argument("--pending", action="store_true")
    l.set_defaults(func=cmd_list)

    t = sub.add_parser("triage")
    t.add_argument("--reader", action="store_true")
    t.add_argument("--days", type=int)
    t.set_defaults(func=cmd_triage)

    rc = sub.add_parser("reconcile")
    rc.add_argument("--apply", metavar="TITLE",
                    help="resolve the duplicate group with this exact title: keep the best "
                         "row, mark the others skip with a duplicate-of note")
    rc.set_defaults(func=cmd_reconcile)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
