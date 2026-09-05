#!/usr/bin/env python3
"""Weekly skill-usage audit (no model dependency). Counts real invocations from Claude Code
transcripts and reports most-used, dormant, and never-run skills — the usage half that
audit_skills.py (inventory: listing cost, descriptions, symlinks, trigger words) does not cover.

Signals counted, per skill:
  1. Skill tool_use records            {"name":"Skill","input":{"skill":"<name>"}}
  2. skill-backed slash commands       <command-name>/<name></command-name>
  3. reference reads (separate)        Read tool on ~/.claude/skills/<name>/**

Reads are tracked apart from invocations on purpose: a skill can be legitimately consumed as a
reference by another skill without ever firing itself. "Never invoked AND never read" is the only
combination that means dead weight.

Writes ~/.claude/skill-sync/reports/skill-usage-YYYY-MM-DD.md and prints a one-line summary.
"""
import os, re, json, glob, sys, datetime, collections

HOME     = os.path.expanduser('~')
SKILLS   = os.path.join(HOME, '.claude', 'skills')
PROJECTS = os.path.join(HOME, '.claude', 'projects')
REPORTS  = os.path.join(HOME, '.claude', 'skill-sync', 'reports')
DORMANT_DAYS = int(os.environ.get('SKILL_USAGE_DORMANT_DAYS', '30'))
# A freshly installed skill has not had a fair chance to fire yet; judging it as dead weight is noise.
# Install age is only knowable for skill-sync-tracked skills (the adopt time in state/). File mtimes
# and git history in ~/.claude/skills are checkout and bulk-commit artifacts, NOT install dates.
NEW_DAYS     = int(os.environ.get('SKILL_USAGE_NEW_DAYS', '14'))
STATE        = os.path.join(HOME, '.claude', 'skill-sync', 'state')

# Always-on or harness-injected; never "invoked" so absence is not a signal.
EXEMPT = {'superpowers:using-superpowers'}

def installed_skills():
    """Standalone skills: a directory under ~/.claude/skills holding a SKILL.md.
    Value is install age in days, or None when unknowable (skill not tracked by skill-sync)."""
    now = datetime.datetime.now().timestamp()
    out = {}
    for p in sorted(glob.glob(os.path.join(SKILLS, '*', 'SKILL.md'))):
        name = os.path.basename(os.path.dirname(p))
        try:
            out[name] = int((now - os.stat(os.path.join(STATE, name)).st_mtime) / 86400)
        except OSError:
            out[name] = None
    return out

def scan_transcripts():
    """Return (counts, first_seen, last_seen, sessions, cwds, n_files, n_lines)."""
    counts   = collections.Counter()
    reads    = collections.Counter()
    first    = {}
    last     = {}
    sessions = collections.defaultdict(set)
    cwds     = collections.defaultdict(collections.Counter)
    files = glob.glob(os.path.join(PROJECTS, '**', '*.jsonl'), recursive=True)
    n_lines = 0
    cmd_re  = re.compile(r'<command-name>/([A-Za-z0-9:_-]+)')
    read_re = re.compile(r'[/.]claude/skills/([A-Za-z0-9_-]+)/')

    def record(name, ts, sid, cwd):
        counts[name] += 1
        if ts:
            if name not in first or ts < first[name]: first[name] = ts
            if name not in last  or ts > last[name]:  last[name]  = ts
        if sid: sessions[name].add(sid)
        if cwd: cwds[name][cwd] += 1

    for f in files:
        try:
            with open(f, 'r', errors='replace') as fh:
                for line in fh:
                    n_lines += 1
                    has_skill = '"name":"Skill"' in line
                    has_cmd   = '<command-name>' in line
                    has_read  = 'claude/skills/' in line
                    if not (has_skill or has_cmd or has_read):
                        continue
                    try:
                        d = json.loads(line)
                    except Exception:
                        continue
                    ts  = d.get('timestamp')
                    sid = d.get('sessionId')
                    cwd = d.get('cwd')
                    content = (d.get('message') or {}).get('content')
                    if isinstance(content, list):
                        for c in content:
                            if not isinstance(c, dict):
                                continue
                            if has_skill and c.get('type') == 'tool_use' and c.get('name') == 'Skill':
                                nm = (c.get('input') or {}).get('skill')
                                if isinstance(nm, str) and nm:
                                    record(nm.strip(), ts, sid, cwd)
                            if has_read and c.get('type') == 'tool_use' and c.get('name') in ('Read', 'Grep', 'Glob'):
                                inp = c.get('input') or {}
                                for field in ('file_path', 'path', 'pattern'):
                                    m = read_re.search(str(inp.get(field) or ''))
                                    if m:
                                        reads[m.group(1)] += 1
                                        break
                            if has_cmd and c.get('type') == 'text':
                                for m in cmd_re.finditer(c.get('text') or ''):
                                    record(m.group(1), ts, sid, cwd)
                    elif has_cmd and isinstance(content, str):
                        for m in cmd_re.finditer(content):
                            record(m.group(1), ts, sid, cwd)
        except (OSError, IOError):
            continue
    return counts, reads, first, last, sessions, cwds, len(files), n_lines

def days_ago(iso, now):
    try:
        t = datetime.datetime.fromisoformat(iso.replace('Z', '+00:00'))
        return (now - t).days
    except Exception:
        return None

def main():
    now = datetime.datetime.now(datetime.timezone.utc)
    inst = installed_skills()
    counts, reads, first, last, sessions, cwds, n_files, n_lines = scan_transcripts()

    # Built-in slash commands and non-skill commands pollute the command-name signal; keep
    # only names that are installed standalone skills or namespaced plugin skills.
    known = lambda n: n in inst or ':' in n
    counts = collections.Counter({k: v for k, v in counts.items() if known(k)})

    used     = {k: v for k, v in counts.items() if v}
    standalone_used = {k: v for k, v in used.items() if k in inst}
    plugin_used     = {k: v for k, v in used.items() if k not in inst}

    never   = [k for k in inst if k not in used and k not in EXEMPT]
    fresh   = sorted(k for k in never if inst[k] is not None and inst[k] <= NEW_DAYS)
    settled = [k for k in never if not (inst[k] is not None and inst[k] <= NEW_DAYS)]
    zero    = sorted(k for k in settled if not reads.get(k))          # never invoked, never read
    ref_only= sorted((k, reads[k]) for k in settled if reads.get(k))  # never invoked, but read
    dormant = []
    active  = []
    for k, v in standalone_used.items():
        d = days_ago(last.get(k, ''), now)
        (dormant if (d is not None and d > DORMANT_DAYS) else active).append((k, v, d))
    dormant.sort(key=lambda r: (-(r[2] or 0), r[0]))
    ranked = sorted(standalone_used.items(), key=lambda kv: (-kv[1], kv[0]))

    span = ''
    all_ts = [t for t in first.values() if t] + [t for t in last.values() if t]
    if all_ts:
        span = f"{min(all_ts)[:10]} → {max(all_ts)[:10]}"

    os.makedirs(REPORTS, exist_ok=True)
    today = datetime.date.today().isoformat()
    path = os.path.join(REPORTS, f'skill-usage-{today}.md')
    L = []
    A = L.append
    A(f"# Skill usage audit — {today}\n")
    A(f"Scanned **{n_files} transcripts** ({n_lines:,} records), window **{span}**.  ")
    A(f"Installed standalone skills: **{len(inst)}**. Invoked at least once: **{len(standalone_used)}** "
      f"({len(standalone_used)*100//max(len(inst),1)}%). Never invoked: **{len(never)}** — of those, "
      f"**{len(ref_only)}** are read as references, **{len(fresh)}** installed too recently to judge, "
      f"**{len(zero)}** show no use of any kind.  ")
    A(f"Thresholds: dormant after {DORMANT_DAYS} days, too-new under {NEW_DAYS} days. "
      f"Install age is known only for skill-sync-tracked skills (adopt time); file mtimes and git "
      f"history in ~/.claude/skills are checkout artifacts, so untracked skills are judged on the "
      f"scanned window alone.\n")

    A("## Most used\n")
    A("| Skill | Runs | Sessions | Reads | Last used |")
    A("|---|---:|---:|---:|---|")
    for k, v in ranked[:25]:
        d = days_ago(last.get(k, ''), now)
        A(f"| `{k}` | {v} | {len(sessions[k])} | {reads.get(k,0)} | "
          f"{'today' if d==0 else f'{d}d ago' if d is not None else '—'} |")
    A("")

    if dormant:
        A(f"## Dormant — used once, then not in {DORMANT_DAYS}+ days\n")
        A("| Skill | Runs | Last used |")
        A("|---|---:|---|")
        for k, v, d in dormant:
            A(f"| `{k}` | {v} | {d}d ago |")
        A("")

    if ref_only:
        A(f"## Never invoked, but read as a reference ({len(ref_only)})\n")
        A("Working as designed if they exist to be read by other skills. Not dead weight — but they "
          "still cost listing budget, so a reference-only skill may belong in `references/` instead.\n")
        A("| Skill | Reads |")
        A("|---|---:|")
        for k, v in sorted(ref_only, key=lambda kv: -kv[1]):
            A(f"| `{k}` | {v} |")
        A("")

    if fresh:
        A(f"## Installed within {NEW_DAYS} days — too new to judge ({len(fresh)})\n")
        A("Adopt time from skill-sync state, so these are real install dates.\n")
        A(', '.join(f"`{k}`" for k in fresh) + "\n")

    A(f"## Never invoked and never read ({len(zero)})\n")
    A(f"Not seen once across the scanned window ({span}). "
      "Listing-budget cost with no observed return of any kind. Candidates to retire, merge, or "
      "re-describe — a skill that never fires is usually a description problem, not a value problem.\n")
    for k in zero:
        A(f"- `{k}`")
    A("")

    if plugin_used:
        A("## Plugin / namespaced skills invoked\n")
        A("Not in `~/.claude/skills`, so not counted against the standalone inventory above.\n")
        A("| Skill | Runs |")
        A("|---|---:|")
        for k, v in sorted(plugin_used.items(), key=lambda kv: -kv[1]):
            A(f"| `{k}` | {v} |")
        A("")

    with open(path, 'w') as fh:
        fh.write('\n'.join(L) + '\n')
    latest = os.path.join(REPORTS, 'skill-usage-latest.md')
    try:
        if os.path.islink(latest) or os.path.exists(latest): os.remove(latest)
        os.symlink(path, latest)
    except OSError:
        pass

    top = ', '.join(f"{k}({v})" for k, v in ranked[:3]) or 'none'
    print(f"skill-usage: {len(standalone_used)}/{len(inst)} invoked, {len(ref_only)} read-only, "
          f"{len(zero)} never-run, {len(fresh)} too-new, {len(dormant)} dormant. Top: {top}. -> {path}")

if __name__ == '__main__':
    sys.exit(main())
