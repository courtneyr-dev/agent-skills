#!/usr/bin/env python3
"""Vault-hygiene checker — the mechanical half of the maker/checker split.

Read-only audit of Obsidian notes. Runs the objective checks that need zero
judgment (dead wikilinks, MOC registration, duplicate titles) so a human review
can focus on the judgment checks (ungrounded claims, semantic duplicates).

Usage:
  check_vault.py --since 2026-06-05            # notes whose frontmatter `created` >= date
  check_vault.py --days 2                      # notes with created/mtime within N days
  check_vault.py --files "Note A.md" "Note B.md"   # explicit basenames or paths
  check_vault.py --scope "Resources/Permanent Notes"   # restrict target dir (default: this)

Targets default to the Permanent Notes folder; the link/dup index always spans the whole vault.
Every run also spot-checks random backlog atoms:done rows against the vault (--audit-sample N).
"""
import argparse
import os
import random
import re
import sys
from datetime import datetime, timedelta

VAULT = os.path.expanduser(os.environ.get("VAULT_DIR", "~/Documents/Notes"))
PERM = "Resources/Permanent Notes"
LIT_DIR = "Resources/Literature Notes"
MOC_DIR = "Resources/MOCs"
BACKLOG = os.path.join(VAULT, "_Synthesis Backlog.md")

# Allows balanced single [brackets] inside a target (Readwise titles like
# "The Human in the Loop [01knvtp06bs16p928wzy44r429]") — the old [^\]]+ capture
# stopped at the first ']' and mangled those targets into unresolvable stems.
WIKILINK = re.compile(r"\[\[([^\[\]]*(?:\[[^\[\]]*\][^\[\]]*)*)\]\]")
CREATED = re.compile(r"^created:\s*(\d{4}-\d{2}-\d{2})", re.M)
TITLE_H1 = re.compile(r"^#\s+(.+)$", re.M)
STOP = set("the a an is are be to of in on for and or not it its as at by we you "
           "i how what why that this with from into more just than only do does "
           "your their our s t".split())


def md_files(root):
    """Yield .md paths, skipping dot-directories.

    A bare os.walk also indexes `.claude/` (git worktrees can hold a full second copy
    of the vault), `.trash/`, and `.obsidian/`. Measured 2026-08-31: 175k files indexed
    instead of 58k, and 6 basenames existing ONLY in those areas would falsely resolve
    as live wikilink targets -- including two `.trash/` MOC snapshots and two zero-byte
    interrupted-copy artifacts. Obsidian ignores dot-folders; the index must too, or a
    link whose target was deleted from the vault still reports as alive.
    """
    for dp, dns, fns in os.walk(root):
        dns[:] = [d for d in dns if not d.startswith(".")]
        for fn in fns:
            if fn.endswith(".md"):
                yield os.path.join(dp, fn)


def build_index(vault):
    """basename(lower, no ext) -> set(relpaths); also relpath(lower, no ext) -> relpath."""
    by_base, by_path = {}, {}
    for f in md_files(vault):
        rel = os.path.relpath(f, vault)
        stem = rel[:-3]                       # drop .md
        base = os.path.basename(stem)
        by_base.setdefault(base.lower(), set()).add(rel)
        by_path[stem.lower()] = rel
    return by_base, by_path


def norm_link(raw):
    """Strip alias (|) and heading/block (#) anchor; return target stem.

    A '#' is a heading separator EXCEPT when it's the first char of the final
    path segment — there it's a literal filename char (e.g. podcast '#219 ...').
    """
    t = raw.split("|", 1)[0].strip()
    head, sep, seg = t.rpartition("/")
    if seg.startswith("#"):                   # leading # is part of the filename
        rest = seg[1:]
        seg = "#" + rest.split("#", 1)[0] if "#" in rest else seg
        t = head + sep + seg
    else:
        t = t.split("#", 1)[0].strip()
    if t.endswith(".md"):
        t = t[:-3]
    return t.strip()


def near_key(s):
    """Fold the near-miss variants seen in real dead links: curly vs straight
    apostrophes/quotes and trailing dots ("…138.." link vs "…138." file)."""
    s = s.lower().replace("’", "'").replace("‘", "'")
    s = s.replace("“", '"').replace("”", '"')
    return s.rstrip(" .")


def fragile_reason(name):
    """Why a link whose target file EXISTS still can't resolve in Obsidian."""
    if name.startswith("#"):
        return "leading '#' — Obsidian reads the whole link as a heading anchor"
    if "#" in name:
        return "'#' mid-name — Obsidian cuts the link at the '#' and misses the file"
    return "'[' or ']' in the filename breaks wikilink parsing"


def norm_title(s):
    return re.sub(r"[^a-z0-9]+", "", s.lower())


def backlog_atoms_done():
    """(date, title, doc_id) for active-backlog rows marked atoms: done."""
    if not os.path.exists(BACKLOG):
        return []
    rows, in_active = [], False
    for line in open(BACKLOG, encoding="utf-8"):
        if "BACKLOG:ACTIVE:START" in line:
            in_active = True
            continue
        if "BACKLOG:ACTIVE:END" in line:
            break
        if not in_active or not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) < 7 or cells[0] == "Date" or set(cells[0]) <= set("-"):
            continue
        if cells[4] == "done":
            rows.append((cells[0], cells[1], cells[2]))
    return rows


def audit_backlog_sample(n, by_base):
    """Spot-check N random atoms:done rows against the vault — a done-row whose
    title matches no Literature/Permanent note is a possible phantom (2026-08-21
    found ~7 rows marked done with no file behind them)."""
    rows = backlog_atoms_done()
    if not rows:
        return [], 0, 0
    note_norms = set()
    for b, rels in by_base.items():
        if any(r.startswith(PERM) or r.startswith(LIT_DIR) for r in rels):
            note_norms.add(norm_title(b))
            # older Literature notes carry a "Lit · " naming prefix
            note_norms.add(norm_title(re.sub(r"(?i)^lit\s*·\s*", "", b)))
    sample = random.sample(rows, min(n, len(rows)))
    unmatched = []
    for date, title, doc_id in sample:
        t = norm_title(title)
        hit = t in note_norms or any(
            (s.startswith(t) or t.startswith(s)) and min(len(s), len(t)) >= 12
            for s in note_norms)
        if not hit:
            unmatched.append((date, title, doc_id))
    return unmatched, len(rows), len(sample)


# "Note-2" / "Note 2" -> "Note". Single digit 2-9 only: plugin re-imports use
# " 2"/"-2", while episode numbering ("This Week in WordPress 376") is 2+ digits
# and flagged as false siblings when this matched \d+ (seen 2026-08-24 after the
# '#'-stripping renames).
DUP_SUFFIX = re.compile(r"^(.*?)[ \-][2-9]$")
LINKS_HEADING = re.compile(r"^##\s+Links[ \t]*$", re.M)


def insert_reciprocal_links(path, mocs, stamp):
    """Append missing MOC backlinks to a note's '## Links' section (create it if absent).

    Links carry a placeholder annotation instead of an invented relationship — the
    checker never fabricates the semantic connection; the maker fills it in. Returns
    True if the file was modified.
    """
    body = open(path, encoding="utf-8", errors="ignore").read()
    block = "\n".join(
        f"- [[{m}]] — ⚠️ reciprocal link auto-added {stamp}; annotate the relationship"
        for m in mocs
    )
    m = LINKS_HEADING.search(body)
    if m:
        new = body[:m.end()] + "\n" + block + body[m.end():]
    else:
        sep = "" if body.endswith("\n") else "\n"
        new = body + sep + "\n## Links\n\n" + block + "\n"
    if new != body:
        open(path, "w", encoding="utf-8").write(new)
        return True
    return False


def resolve(target, by_base, by_path):
    if not target:                            # pure heading link [[#section]]
        return True
    key = target.lower()
    if key in by_path:
        return True
    base = os.path.basename(key)
    return base in by_base


def tokens(s):
    return {w for w in re.findall(r"[a-z0-9]+", s.lower()) if w not in STOP and len(w) > 2}


def pick_targets(args, by_path):
    perm_root = os.path.join(VAULT, args.scope)
    if args.files:
        out = []
        for f in args.files:
            stem = f[:-3] if f.endswith(".md") else f
            # try exact path under scope, else search vault basename index
            cand = os.path.join(perm_root, stem + ".md")
            if os.path.exists(cand):
                out.append(cand)
            else:
                hits = [os.path.join(VAULT, p) for p in by_path.values()
                        if os.path.basename(p)[:-3].lower() == os.path.basename(stem).lower()]
                out.extend(hits)
        return out
    targets = []
    cutoff = None
    if args.days is not None:
        cutoff = datetime.now() - timedelta(days=args.days)
    for f in md_files(perm_root):
        body = open(f, encoding="utf-8", errors="ignore").read()
        m = CREATED.search(body)
        keep = False
        if args.since and m and m.group(1) >= args.since:
            keep = True
        elif args.days is not None:
            if m:
                try:
                    keep = datetime.strptime(m.group(1), "%Y-%m-%d") >= cutoff
                except ValueError:
                    pass
            if not keep and datetime.fromtimestamp(os.path.getmtime(f)) >= cutoff:
                keep = True
        elif not args.since and args.days is None:
            keep = True                       # no filter -> all notes in scope
        if keep:
            targets.append(f)
    return targets


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--since")
    ap.add_argument("--days", type=int)
    ap.add_argument("--files", nargs="*")
    ap.add_argument("--scope", default=PERM)
    ap.add_argument("--dup-threshold", type=float, default=0.55,
                    help="title token-overlap ratio above which two notes are flagged as possible dups")
    ap.add_argument("--audit-sample", type=int, default=10, metavar="N",
                    help="spot-check N random backlog rows marked atoms:done and report any "
                         "with no matching Literature/Permanent note (0 disables; default 10)")
    ap.add_argument("--fix-reciprocal", action="store_true",
                    help="WRITE missing note→MOC reciprocal backlinks into each target note's "
                         "## Links section (default: report only). Inserted links carry a ⚠️ placeholder "
                         "annotation for the maker to replace with the real relationship.")
    args = ap.parse_args()

    by_base, by_path = build_index(VAULT)
    targets = pick_targets(args, by_path)
    if not targets:
        print("No target notes matched. Check --since/--days/--files.")
        return

    # MOC reference index: MOC basename -> set of referenced note basenames (lower).
    # moc_refs stays a flat union for the "not registered in any MOC" check.
    moc_to_notes = {}
    for f in md_files(os.path.join(VAULT, MOC_DIR)):
        moc_base = os.path.basename(f)[:-3]
        refs = set()
        for raw in WIKILINK.findall(open(f, encoding="utf-8", errors="ignore").read()):
            refs.add(os.path.basename(norm_link(raw)).lower())
        moc_to_notes[moc_base] = refs
    moc_refs = set().union(*moc_to_notes.values()) if moc_to_notes else set()

    # all permanent-note titles for dup check
    perm_titles = {}
    for f in md_files(os.path.join(VAULT, PERM)):
        base = os.path.basename(f)[:-3]
        body = open(f, encoding="utf-8", errors="ignore").read()
        h1 = TITLE_H1.search(body)
        perm_titles[base] = tokens(h1.group(1) if h1 else base)

    dead, no_moc, dups, fragile, missing_recip = [], [], [], [], []
    for f in sorted(targets):
        rel = os.path.relpath(f, VAULT)
        base = os.path.basename(f)[:-3]
        body = open(f, encoding="utf-8", errors="ignore").read()

        link_bases = set()
        for raw in WIKILINK.findall(body):
            literal = raw.split("|", 1)[0].strip()   # alias off; '#'/'[' kept literal
            if literal.endswith(".md"):
                literal = literal[:-3]
            tgt = norm_link(raw)
            link_bases.add(os.path.basename(tgt).lower())
            # [[#Heading]] with no matching literal '#…' file is a same-file anchor —
            # valid Obsidian syntax, never a dead-file link.
            if literal.startswith("#") and "/" not in literal \
                    and not resolve(literal, by_base, by_path):
                continue
            if resolve(tgt, by_base, by_path):
                name = os.path.basename(tgt)
                if name.startswith("#") or "[" in name or "]" in name:
                    fragile.append((base, raw.strip(), fragile_reason(name)))
            elif resolve(literal, by_base, by_path):
                # file exists only when '#'/brackets are read literally: fragile, not dead
                fragile.append((base, raw.strip(),
                                fragile_reason(os.path.basename(literal))))
            else:
                dead.append((base, raw.strip(), tgt))

        # Convention checks apply only to Literature/Permanent notes (+ MOC-index
        # registration for MOCs). Same-basename Readwise mirrors scooped in by
        # --files carry neither ## Links nor MOC registration by design — flagging
        # them was the 2026-08-21 reciprocal-link false positive.
        is_note = rel.startswith(PERM) or rel.startswith(LIT_DIR)

        if (is_note or rel.startswith(MOC_DIR)) and base.lower() not in moc_refs:
            no_moc.append(base)

        # reciprocal note→MOC backlinks: MOCs that reference this note but that the
        # note doesn't link back to (notes use short-form [[X MOC]] basename links).
        if is_note:
            missing_mocs = sorted(m for m, refs in moc_to_notes.items()
                                  if base.lower() in refs and m.lower() not in link_bases)
            if missing_mocs:
                missing_recip.append((base, f, missing_mocs))

        my = perm_titles.get(base, tokens(base))
        for other, ot in perm_titles.items():
            if other == base or not my or not ot:
                continue
            overlap = len(my & ot) / min(len(my), len(ot))
            if overlap >= args.dup_threshold:
                pair = tuple(sorted((base, other)))
                if pair not in {d[0] for d in dups}:
                    dups.append((pair, round(overlap, 2)))

    # duplicate-import siblings among the linked targets + their folders
    dup_files = []
    seen_dupcheck = set()
    for f in sorted(targets):
        body = open(f, encoding="utf-8", errors="ignore").read()
        for raw in WIKILINK.findall(body):
            tgt = norm_link(raw)
            base = os.path.basename(tgt)
            m = DUP_SUFFIX.match(base)
            stem = m.group(1) if m else base
            folder = os.path.dirname(tgt)
            sibs = sorted({p for p in by_path.values()
                           if os.path.dirname(p) == folder
                           and (os.path.basename(p)[:-3] == stem
                                or DUP_SUFFIX.sub(r"\1", os.path.basename(p)[:-3]) == stem)})
            if len(sibs) > 1 and folder not in seen_dupcheck:
                for s in sibs:
                    if DUP_SUFFIX.match(os.path.basename(s)[:-3]):
                        dup_files.append((stem, [os.path.basename(x) for x in sibs]))
                        seen_dupcheck.add(folder)
                        break

    # near-miss index: catches dead links whose target exists under a name that
    # differs only by apostrophe style or a trailing dot — those need the LINK
    # edited, not a new note written.
    near_index = {}
    for b in by_base:
        near_index.setdefault(near_key(b), set()).add(b)

    print(f"# Vault hygiene report — {len(targets)} target note(s)\n")
    print(f"## 🔗 Dead wikilinks ({len(dead)})")
    if dead:
        for note, link, tgt in dead:
            tb = os.path.basename(tgt).lower()
            hints = near_index.get(near_key(tb), set()) - {tb}
            extra = (f"; near-miss of existing file {sorted(hints)[0]!r} — fix the link"
                     if hints else "")
            print(f"- **{note}** → `[[{link}]]`  (target file not found{extra})")
    else:
        print("- none ✓")
    print(f"\n## ⚠️ Fragile links — file exists but the wikilink can't reach it ({len(fragile)})")
    if fragile:
        for note, link, why in fragile:
            print(f"- **{note}** → `[[{link}]]`  ({why})")
    else:
        print("- none ✓")
    if dup_files:
        print(f"\n## 🧬 Duplicate-import files among linked sources ({len(dup_files)})")
        for stem, sibs in dup_files:
            print(f"- **{stem}** → {sibs}")
    print(f"\n## 🗺️ Not registered in any MOC ({len(no_moc)})")
    if no_moc:
        for n in no_moc:
            print(f"- **{n}**")
    else:
        print("- none ✓")
    print(f"\n## 👯 Possible duplicate titles (≥{args.dup_threshold} token overlap, {len(dups)})")
    if dups:
        for (a, b), score in sorted(dups, key=lambda x: -x[1]):
            print(f"- {score}: **{a}**  ⟷  **{b}**")
    else:
        print("- none ✓")

    print(f"\n## ♻️ Missing note→MOC reciprocal links ({len(missing_recip)})")
    if missing_recip:
        for base, _f, mocs in missing_recip:
            joined = ", ".join(f"[[{m}]]" for m in mocs)
            print(f"- **{base}** → should link back to {joined}")
    else:
        print("- none ✓")

    if args.audit_sample:
        unmatched, total, sampled = audit_backlog_sample(args.audit_sample, by_base)
        print(f"\n## 🎲 Backlog sample audit — {sampled} random atoms:done row(s) of {total}")
        if not total:
            print("- backlog not found or has no atoms:done rows")
        elif unmatched:
            for date, title, doc_id in unmatched:
                print(f"- **{title}** ({date}, `{doc_id}`) — no Literature/Permanent note "
                      f"matches this title; possible phantom done-row")
        else:
            print("- every sampled row matched a Literature/Permanent note ✓")

    if args.fix_reciprocal and missing_recip:
        stamp = datetime.now().strftime("%Y-%m-%d")
        written = sum(insert_reciprocal_links(path, mocs, stamp)
                      for _b, path, mocs in missing_recip)
        print(f"\n  ✍️  --fix-reciprocal: inserted backlinks in {written} note(s). Each carries a "
              f"⚠️ placeholder — have the maker replace it with the real relationship, then re-run to confirm.")
    elif missing_recip:
        print("\n  (run with --fix-reciprocal to insert these as placeholder-annotated backlinks)")


if __name__ == "__main__":
    main()
