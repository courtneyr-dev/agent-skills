#!/usr/bin/env python3
"""Copy a skill directory into the public repo, stripping personal and employer-specific content.

Fails loudly rather than publishing something dirty: after rewriting, it re-scans the output and
reports any residual marker so a human decides, instead of silently shipping it.
"""
import os, re, sys, shutil, argparse

# Order matters: longer/more specific patterns first.
RULES = [
    (re.compile(r'/private/tmp/claude-\d+/[^\s`"\')]+'), '/tmp/scratch'),
    (re.compile(r'/Users/[A-Za-z0-9._-]+'), '$HOME'),
    (re.compile(r'\bcom\.courtney\.'), 'com.example.'),
    (re.compile(r'\bcourtney[_-]([a-z_]+)'), r'\1'),
    (re.compile(r"\bRobertson's Home\b"), 'a separate personal site'),
    (re.compile(r'\brobertsonshome\b', re.I), 'personalsite'),
    (re.compile(r'\bCourtney Robertson\b'), 'the user'),
    (re.compile(r"\bCourtney's\b"), "the user's"),
    (re.compile(r'\bCourtney\b'), 'the user'),
    (re.compile(r'\bcourtneyr\.dev\b', re.I), 'example.com'),
    (re.compile(r'\bcourtneyr-dev/', re.I), 'your-org/'),
    (re.compile(r'\bcourane01\b'), 'you'),
    (re.compile(r'\bcourtneyr\b'), 'you'),
]
# Any file or line matching these is employer-confidential and never ships.
EMPLOYER = re.compile(r'godaddy|\bairo\b', re.I)
# Residual markers to report after rewriting.
AUDIT = {
    'employer': EMPLOYER,
    'personal-name': re.compile(r'courtney|robertson|courane', re.I),
    'abs-path': re.compile(r'/Users/[A-Za-z0-9._-]+'),
    'hostname': re.compile(r'elestio|\.vm\.|ssh\s+\S+@'),
}
TEXT_EXT = ('.md', '.py', '.sh', '.yml', '.yaml', '.json', '.txt', '.toml', '.plist')
# Stale local backups and editor droppings: never part of a published skill.
SKIP_FILE = re.compile(r'(\.bak[-.]|\.backup[-.]|\.orig$|~$|^\.DS_Store$|\.swp$)')

def public_name(fn):
    """Filenames can carry the author's identity too (com.courtney.x.plist)."""
    return re.sub(r'(?i)courtney(r)?[-._]?', 'example.' if fn.startswith('com.') else '', fn) or fn

def scrub_text(t):
    kept = []
    dropped = 0
    for line in t.splitlines(True):
        if EMPLOYER.search(line):
            dropped += 1
            continue
        for pat, rep in RULES:
            line = pat.sub(rep, line)
        kept.append(line)
    return ''.join(kept), dropped

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('src'); ap.add_argument('dst')
    ap.add_argument('--exclude-file', action='append', default=[])
    a = ap.parse_args()
    if os.path.exists(a.dst): shutil.rmtree(a.dst)
    total_dropped = 0
    findings = {}
    for root, dirs, files in os.walk(a.src):
        dirs[:] = [d for d in dirs if d not in (
                '.git', 'node_modules', '__pycache__', '.venv', 'venv', '.mypy_cache',
                '.pytest_cache', '.ruff_cache', 'dist', 'build', '.DS_Store')]
        for fn in files:
            if fn in a.exclude_file or fn.startswith('._') or SKIP_FILE.search(fn):
                continue
            s = os.path.join(root, fn)
            rel = os.path.relpath(s, a.src)
            rel = os.path.join(os.path.dirname(rel), public_name(os.path.basename(rel)))
            d = os.path.join(a.dst, rel)
            os.makedirs(os.path.dirname(d), exist_ok=True)
            if fn.endswith(TEXT_EXT):
                try: t = open(s, errors='replace').read()
                except OSError: continue
                t, dropped = scrub_text(t)
                total_dropped += dropped
                open(d, 'w').write(t)
                for k, p in AUDIT.items():
                    n = len(p.findall(t))
                    if n: findings[k] = findings.get(k, 0) + n
            else:
                shutil.copy2(s, d)
    name = os.path.basename(a.dst)
    resid = ' '.join(f"{k}={v}" for k, v in sorted(findings.items())) or 'clean'
    print(f"{name:<34} lines-dropped={total_dropped:<4} {resid}")
    return 1 if findings else 0

if __name__ == '__main__':
    sys.exit(main())
