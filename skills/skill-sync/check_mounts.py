#!/usr/bin/env python3
"""Mount-integrity check for ~/.agents/skills (no model dependency).

Why this exists: `~/.agents/skills` is the neutral mount that Codex, Cursor and OpenClaw read.
The architecture says it carries symlinks into the git-backed canonical store, plus real
directories for skills that only exist there. Nothing enforced that. On 2026-09-20 a fresh-agent
routing test followed the mount to `readwise-deep-read`, got a pre-split physical copy — 107-line
checker against canonical's 489, no link-claim check at all — and would have reported an enforced
rule as prose-only. `audit_skills.py` checks dangling symlinks, but only under ~/.claude/skills;
the mount was unaudited.

Source of truth is derived, not maintained:
  * canonical store  = ~/.claude/claude-config/skills/<name>   (target-architecture.md)
  * plugin/github    = entries in ~/.agents/.skill-lock.json   (skill-sync's own manifest)
  * anything else    = .agents-only, legitimately a real directory
There is deliberately no hand-written list of "skills that should be symlinks" — that list would
drift exactly the way the mount did.

Usage:
  python3 check_mounts.py            # report; exit 1 if any FAIL
  python3 check_mounts.py --quiet    # one-line summary (for the weekly job)
  python3 check_mounts.py --fix      # repair only the unambiguous cases
"""
import argparse
import filecmp
import json
import os
import shutil
import subprocess
import sys
from datetime import date

HOME = os.path.expanduser("~")
MOUNT = os.path.join(HOME, ".agents", "skills")
CANON = os.path.join(HOME, ".claude", "claude-config", "skills")
LOCK = os.path.join(HOME, ".agents", ".skill-lock.json")
BACKUP = os.path.join(HOME, ".agents", f"_mount-repair-backup-{date.today()}")


def locked_names():
    try:
        with open(LOCK) as fh:
            return set(json.load(fh).get("skills", {}))
    except Exception:
        return set()


def unique_files(phys, canon):
    """Relative paths present in the physical mount but absent from canonical.

    These are what a repair would destroy, so they decide whether --fix may touch it.
    __pycache__ is build residue, never unique content.
    """
    out = []
    for root, dirs, files in os.walk(phys):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), phys)
            if not os.path.exists(os.path.join(canon, rel)):
                out.append(rel)
    return sorted(out)


def differing_files(phys, canon):
    out = []
    for root, dirs, files in os.walk(phys):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for f in files:
            rel = os.path.relpath(os.path.join(root, f), phys)
            twin = os.path.join(canon, rel)
            if os.path.exists(twin) and not filecmp.cmp(os.path.join(root, f), twin, shallow=False):
                out.append(rel)
    return sorted(out)


def audit():
    locked = locked_names()
    rows = []
    for name in sorted(os.listdir(MOUNT)):
        # A skill directory is never dot-prefixed; dotted entries are backup residue
        # (e.g. .personal-brand-engagement.bak-20260829) and are not advertised to any agent.
        if name.startswith("."):
            continue
        p = os.path.join(MOUNT, name)
        canon = os.path.join(CANON, name)
        has_canon = os.path.isdir(canon)

        if os.path.islink(p):
            target = os.path.realpath(p)
            if not os.path.exists(target):
                rows.append(("FAIL", name, "broken symlink",
                             f"points at {os.readlink(p)}, which does not exist", []))
            elif has_canon and target != os.path.realpath(canon):
                rows.append(("FAIL", name, "symlink off-target",
                             f"resolves to {target}, canonical is {canon}", []))
            elif not has_canon and not target.startswith(CANON):
                rows.append(("WARN", name, "symlink outside canonical store",
                             f"resolves to {target}; no canonical twin — intentional?", []))
            else:
                rows.append(("OK", name, "symlink -> canonical", "", []))
            continue

        if not os.path.isdir(p):
            rows.append(("FAIL", name, "not a directory or symlink", f"{p} is a plain file", []))
            continue

        entries = [e for e in os.listdir(p) if e != "__pycache__"]
        if not entries:
            rows.append(("WARN", name, "empty directory",
                         "advertises nothing and inflates the mount count", []))
            continue

        if has_canon:
            uniq = unique_files(p, canon)
            diff = differing_files(p, canon)
            detail = f"physical copy shadows canonical; {len(diff)} file(s) differ"
            if uniq:
                detail += f", {len(uniq)} file(s) exist ONLY here: {', '.join(uniq[:4])}"
            rows.append(("FAIL", name, "physical dir where a symlink belongs", detail, uniq))
        # no canonical twin: plugin mirror or .agents-only — both legitimately physical
        elif name in locked:
            rows.append(("OK", name, "plugin/github mirror", "", []))
        else:
            rows.append(("OK", name, ".agents-only", "", []))
    return rows


def repair(name, uniq):
    """Automatic repair only when the mount copy is byte-identical to canonical.

    The old rule was "nothing unique exists here", which is not the same as "nothing is
    lost here": a copy whose content merely DIFFERED was relinked and that version
    discarded. On 2026-09-20 a blind --fix would have rewritten 43 diverging copies.
    Divergence is not evidence of staleness — proving a copy is stale takes an external
    check (e.g. that every differing file matches a committed revision of canonical), and
    that judgement is deliberately not automated here.

    Also refuses when canonical is itself a symlink into the mount. For find-skills and
    wp-playground the mount IS canonical and claude-config points at it; relinking those
    builds a cycle. The FAIL report cannot see that on its own.
    """
    p = os.path.join(MOUNT, name)
    canon = os.path.join(CANON, name)
    if uniq:
        return False, "refused — has files that exist only here"
    if os.path.islink(canon):
        return False, "refused — canonical is itself a symlink; relinking would make a cycle"
    diff = differing_files(p, canon)
    if diff:
        return False, f"refused — {len(diff)} file(s) differ from canonical; resolve the difference first"
    os.makedirs(BACKUP, exist_ok=True)
    shutil.copytree(p, os.path.join(BACKUP, name), dirs_exist_ok=True)
    shutil.rmtree(p)
    os.symlink(canon, p)
    return True, f"relinked (backup in {BACKUP})"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--fix", action="store_true",
                    help="relink physical dirs that hold nothing unique; never touches the rest")
    ap.add_argument("--quiet", action="store_true", help="one-line summary only")
    a = ap.parse_args()

    if not os.path.isdir(MOUNT):
        print(f"no mount at {MOUNT}")
        return 0

    rows = audit()
    fails = [r for r in rows if r[0] == "FAIL"]
    warns = [r for r in rows if r[0] == "WARN"]

    if a.fix:
        for _, name, kind, _, uniq in list(fails):
            if kind != "physical dir where a symlink belongs":
                continue
            ok, msg = repair(name, uniq)
            print(f"{'FIXED' if ok else 'SKIP '} {name}: {msg}")
        rows = audit()
        fails = [r for r in rows if r[0] == "FAIL"]
        warns = [r for r in rows if r[0] == "WARN"]

    if a.quiet:
        print(f"skill mounts: {len(rows)} entries, {len(fails)} FAIL, {len(warns)} WARN")
        return 1 if fails else 0

    print(f"\nSKILL MOUNT INTEGRITY — {MOUNT}")
    print(f"canonical: {CANON}")
    print(f"{len(rows)} entries | {len(fails)} FAIL | {len(warns)} WARN | "
          f"{sum(1 for r in rows if r[0] == 'OK')} OK\n")

    for status in ("FAIL", "WARN"):
        group = [r for r in rows if r[0] == status]
        if not group:
            continue
        print(f"--- {status} ({len(group)}) ---")
        for _, name, kind, detail, _ in group:
            print(f"  {name}")
            print(f"      {kind}: {detail}")
        print()

    if fails:
        print("Repair. Byte-identical copies only (a differing copy is NOT auto-repaired):")
        print("  python3 ~/.claude/skills/skill-sync/check_mounts.py --fix")
        print("It refuses anything that differs from canonical or holds files that exist")
        print("nowhere else. Review those by hand:")
        print(f"  diff -rq {MOUNT}/<name> {CANON}/<name>")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
