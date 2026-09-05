#!/usr/bin/env python3
"""Weekly skill-library audit (no model dependency). Reproduces the 2026-09-04 audit's inventory pass:
listing cost against the Claude Code budget, description length, dangling symlinks, stale paths,
Cursor vocabulary, aggressive trigger words, name/dir mismatches, and pointers to skills that don't exist.
Writes ~/.claude/skill-sync/reports/skill-audit-YYYY-MM-DD.md and prints a one-line summary."""
import os, re, glob, json, sys, datetime
HOME = os.path.expanduser('~')
SKILLS = os.path.join(HOME, '.claude', 'skills')
REPORTS = os.path.join(HOME, '.claude', 'skill-sync', 'reports')
SETTINGS = os.path.join(HOME, '.claude', 'settings.json')
CONTEXT_WINDOW = int(os.environ.get('SKILL_AUDIT_CONTEXT_WINDOW', '200000'))
# gstack installs most of its skills as symlinks (detected below) but copies these two aliases in;
# both are upstream files that ./setup rewrites, so findings in them are not the user's to fix.
THIRD_PARTY_COPIES = {'_gstack-command', 'connect-chrome'}

def frontmatter(text):
    m = re.match(r'---\n(.*?)\n---', text, re.S)
    if not m: return {}
    d, key, buf = {}, None, []
    for line in m.group(1).split('\n'):
        mm = re.match(r'^([A-Za-z_-]+):\s*(.*)$', line)
        if mm and not line.startswith(' '):
            if key: d[key] = '\n'.join(buf).strip()
            key, v = mm.group(1), mm.group(2)
            buf = [v] if v not in ('>-', '>', '|', '|-') else []
        elif key: buf.append(line.strip())
    if key: d[key] = '\n'.join(buf).strip()
    return d

def main():
    try: tracked=set(json.load(open(os.path.join(HOME,'.claude','skills','skill-sync','sources.json'))).keys())
    except Exception: tracked=set()
    upstream_notes=[]
    try: fraction = json.load(open(SETTINGS)).get('skillListingBudgetFraction', 0.01)
    except Exception: fraction = 0.01
    budget = int(CONTEXT_WINDOW * 4 * fraction)
    rows, dangling, issues = [], [], []
    names = set()
    for d in sorted(glob.glob(os.path.join(SKILLS, '*'))):
        name = os.path.basename(d)
        if name == 'gstack': continue
        f = os.path.join(d, 'SKILL.md')
        if os.path.islink(f) and not os.path.exists(f): dangling.append(name); continue
        if not os.path.isfile(f): continue
        names.add(name)
        text = open(f, encoding='utf-8', errors='replace').read()
        fm = frontmatter(text)
        desc = (fm.get('description') or '').strip().strip('"').strip("'").replace('\n', ' ')
        dmi = str(fm.get('disable-model-invocation', '')).lower() == 'true'
        entry = len(name) + 4 + min(len(desc), 1536)
        rows.append((name, len(desc), entry, dmi, len(text.split())))
        linked_out = os.path.islink(f) and os.path.realpath(f).find(os.path.join(SKILLS,name)+os.sep) != 0
        sink = upstream_notes if (name in tracked or linked_out or name in THIRD_PARTY_COPIES) else issues
        if fm.get('name') and fm['name'] != name: sink.append(f'{name}: name field is "{fm["name"]}", directory is {name}')
        if not desc: sink.append(f'{name}: no description')
        if 'triggers' in fm: sink.append(f'{name}: inert triggers: key')
        body = text
        if name == 'poteto-mode':
            body = re.sub(r'.*models\.md.*\n?', '', body)
        for pat, label in [(r'/Users/[a-z]', 'hardcoded home path'), (r'/sessions/[a-z-]+/mnt', 'sandbox mount path'),
                           (r'\bTask tool\b|subagent_type: *"?generalPurpose|readonly: *(true|false)|AskQuestion\b|~/\.cursor', 'Cursor vocabulary'),
                           (r'thinking-max|sol-max|fast-xhigh|thinking-xhigh', 'stale model string')]:
            n = len(re.findall(pat, body, re.M))
            if n: sink.append(f'{name}: {n} {label} line(s)')
        agg = len(re.findall(r'\b(CRITICAL|EXTREMELY IMPORTANT|MUST ALWAYS|ALWAYS|NEVER|MANDATORY)\b', re.sub(r'\*\*(CRITICAL|MAJOR|MINOR)\*\*\s+—', '', body)))
        if agg >= 5: sink.append(f'{name}: {agg} shouted words (MUST/ALWAYS/NEVER/CRITICAL)')
        for ref in set(re.findall(r'`([a-z0-9][a-z0-9-]{2,})/SKILL\.md`|~/\.claude/skills/([a-z0-9][a-z0-9-]{2,})', body)):
            r = ref[0] or ref[1]
            if r and r not in names and not os.path.isdir(os.path.join(SKILLS, r)): sink.append(f'{name}: points at missing skill {r}')
    visible = [r for r in rows if not r[3]]
    cost = sum(r[2] for r in visible)
    long_desc = sorted([(r[1], r[0]) for r in rows if r[1] > 300], reverse=True)
    today = datetime.date.today().isoformat()
    os.makedirs(REPORTS, exist_ok=True)
    out = os.path.join(REPORTS, f'skill-audit-{today}.md')
    with open(out, 'w') as w:
        w.write(f'# Skill audit {today}\n\n')
        w.write(f'- skills with SKILL.md: {len(rows)}; model-visible: {len(visible)}; slash-only: {len(rows)-len(visible)}\n')
        w.write(f'- listing cost if every visible skill carried its description: {cost:,} chars vs budget {budget:,} chars (fraction {fraction}, window {CONTEXT_WINDOW:,}) → {"FITS" if cost <= budget else "OVER by " + format(cost-budget, ",")}\n')
        w.write(f'- descriptions over 300 chars: {len(long_desc)}\n')
        for l, n in long_desc: w.write(f'  - {l} {n}\n')
        w.write(f'- dangling symlink skills: {len(dangling)} {dangling}\n')
        w.write(f'- issues: {len(issues)}\n')
        for i in issues: w.write(f'  - {i}\n')
        w.write(f'- third-party (skill-sync tracked, fix upstream): {len(upstream_notes)}\n')
        for i in upstream_notes: w.write(f'  - {i}\n')
        w.write('\nBiggest bodies (words):\n')
        for words, n in sorted([(r[4], r[0]) for r in rows], reverse=True)[:10]: w.write(f'  - {words} {n}\n')
    print(f'skill-audit: {len(rows)} skills, cost {cost:,}/{budget:,} chars ({"fits" if cost<=budget else "OVER"}), {len(long_desc)} long descriptions, {len(dangling)} dangling, {len(issues)} issues → {out}')
    return 0

if __name__ == '__main__': sys.exit(main())
