#!/usr/bin/env python3
"""File a discernment-<slug>.md decision record into the Obsidian vault.

Handles the mechanical half of the decision-sync skill: destination routing, vault frontmatter,
timestamp ID, and the Decision Log index row. The model handles the judgment half (which project,
what to link, whether the decision is actually finished).
"""
import os, re, sys, argparse, datetime

VAULT   = os.path.expanduser('~/Documents/Notes')
AREAS   = os.path.join(VAULT, 'Areas', 'Decisions')
PROJECTS= os.path.join(VAULT, 'Projects')
INDEX   = os.path.join(AREAS, 'Decision Log.md')

def slugify(t):
    return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', t.lower())).strip('-')

def resolve_project(name):
    """Match a project folder case-insensitively; never create one."""
    if not name:
        return None
    want = name.lower()
    try:
        entries = os.listdir(PROJECTS)
    except OSError:
        return None
    for e in entries:
        if e.lower() == want and os.path.isdir(os.path.join(PROJECTS, e)):
            return os.path.join(PROJECTS, e, 'decisions')
    for e in entries:
        if want in e.lower() and os.path.isdir(os.path.join(PROJECTS, e)):
            return os.path.join(PROJECTS, e, 'decisions')
    return None

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('source')
    ap.add_argument('--title', required=True)
    ap.add_argument('--project')
    ap.add_argument('--status', default='decided', choices=['decided', 'revisit'])
    ap.add_argument('--dry-run', action='store_true')
    a = ap.parse_args()

    if not os.path.isfile(a.source):
        sys.exit(f"error: source not found: {a.source}")
    body = open(a.source).read()

    # Strip any frontmatter the working file carried; the vault note gets its own.
    body = re.sub(r'\A---\n.*?\n---\n', '', body, flags=re.S)

    if '## Own' not in body:
        sys.exit("error: source has no '## Own' section — the decision isn't captured yet. "
                 "Run the `own` skill first, or pass a finished record.")

    dest_dir = resolve_project(a.project) if a.project else None
    if a.project and not dest_dir:
        sys.exit(f"error: no project folder matching '{a.project}' under Projects/. "
                 f"Re-run without --project to file under Areas/Decisions/.")
    dest_dir = dest_dir or AREAS

    now  = datetime.datetime.now()
    stamp= now.strftime('%Y%m%d%H%M')
    today= now.date().isoformat()
    path = os.path.join(dest_dir, f"{today} — {a.title}.md")

    fm = (f"---\ntype: decision\nid: {stamp}\nstatus: {a.status}\ncreated: {today}\n"
          f"origin: \"{os.path.abspath(a.source)}\"\ntags: [decision, discernment]\n---\n\n")
    note = f"{fm}# {a.title}\n\n{body.strip()}\n"

    if a.dry_run:
        print(f"would write: {path}\n\n{fm}")
        return

    os.makedirs(dest_dir, exist_ok=True)
    if os.path.exists(path):
        sys.exit(f"error: refusing to overwrite existing note: {path}")
    with open(path, 'w') as fh:
        fh.write(note)

    rel = os.path.relpath(path, VAULT)
    os.makedirs(AREAS, exist_ok=True)
    if not os.path.exists(INDEX):
        with open(INDEX, 'w') as fh:
            fh.write("---\ntype: index\ntags: [decision]\n---\n\n# Decision Log\n\n"
                     "Decisions captured through the `aim` → `cross-check` → `own` discernment "
                     "skills and filed by `decision-sync`.\n\n"
                     "| Date | Decision | Status | Record |\n|---|---|---|---|\n")
    with open(INDEX, 'a') as fh:
        fh.write(f"| {today} | {a.title} | {a.status} | [[{rel[:-3]}]] |\n")

    print(f"filed: {path}\nindexed: {INDEX}")

if __name__ == '__main__':
    main()
