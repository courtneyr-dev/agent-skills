#!/usr/bin/env python3
"""skill-sync: keep standalone skills in ~/.claude/skills updated from their GitHub source repos.

Three-way compare per skill: snapshot (last synced) vs local vs upstream.
- local == snapshot, upstream changed  -> safe update (applied by `apply`)
- local != snapshot, upstream same     -> local edits, left alone
- both changed                         -> conflict, reported only
- no snapshot yet                      -> unbaselined; use `adopt` or `baseline`

Commands: check | apply | add | list | adopt | baseline | remove
State lives in ~/.claude/skill-sync/ (override with SKILL_SYNC_HOME).
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

HOME = Path(os.environ.get("SKILL_SYNC_HOME", str(Path.home() / ".claude" / "skill-sync")))
SKILLS_DIR = Path(os.environ.get("SKILL_SYNC_SKILLS_DIR", str(Path.home() / ".claude" / "skills")))
# Manifest lives beside the script so the git-backed skills repo carries it across
# machines; tests that set SKILL_SYNC_HOME get an isolated manifest instead.
MANIFEST = (HOME / "sources.json") if "SKILL_SYNC_HOME" in os.environ else (Path(__file__).resolve().parent / "sources.json")
REPOS = HOME / "repos"
STATE = HOME / "state"
REPORTS = HOME / "reports"

IGNORE = {".git", ".DS_Store", "__pycache__", ".gitignore"}


def load_manifest():
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text())
    return {}


def save_manifest(m):
    HOME.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(m, indent=2, sort_keys=True) + "\n")


def run(cmd, cwd=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)


def repo_dir(repo):
    return REPOS / repo.replace("/", "__")


def repo_paths(manifest, repo):
    """Sparse-checkout dirs for a repo, from ALL manifest entries (not just the ones
    being synced) so a partial run never drops other entries' paths from the worktree.
    Returns None (full checkout) if any entry for the repo needs the repo root."""
    paths = set()
    for e in manifest.values():
        if e["repo"] == repo:
            if not e.get("path"):
                return None
            paths.add(e["path"])
    return sorted(paths)


def refresh_repo(repo, ref, paths=None):
    """Shallow-clone or update the repo cache; sparse-checkout when paths given. Returns (ok, message)."""
    d = repo_dir(repo)
    url = f"https://github.com/{repo}.git"
    if not (d / ".git").exists():
        d.parent.mkdir(parents=True, exist_ok=True)
        cmd = ["git", "clone", "--depth", "1", "--branch", ref]
        if paths:
            cmd += ["--filter=blob:none", "--no-checkout"]
        r = run(cmd + [url, str(d)])
        if r.returncode != 0:
            return False, f"clone failed: {r.stderr.strip().splitlines()[-1] if r.stderr else 'unknown'}"
        if paths:
            r = run(["git", "sparse-checkout", "set"] + paths, cwd=d)
            if r.returncode != 0:
                return False, "sparse-checkout failed"
            r = run(["git", "checkout", ref], cwd=d)
            if r.returncode != 0:
                return False, "checkout failed"
        return True, "cloned"
    if paths:
        r = run(["git", "sparse-checkout", "set"] + paths, cwd=d)
        if r.returncode != 0:
            return False, "sparse-checkout failed"
    r = run(["git", "fetch", "--depth", "1", "origin", ref], cwd=d)
    if r.returncode != 0:
        return False, f"fetch failed: {r.stderr.strip().splitlines()[-1] if r.stderr else 'unknown'}"
    r = run(["git", "reset", "--hard", "FETCH_HEAD"], cwd=d)
    if r.returncode != 0:
        return False, "reset failed"
    return True, "fetched"


def head_sha(repo):
    r = run(["git", "rev-parse", "--short", "HEAD"], cwd=repo_dir(repo))
    return r.stdout.strip() if r.returncode == 0 else "?"


def file_map(root: Path):
    """Relative path -> sha256 for every file under root, skipping IGNORE names."""
    out = {}
    if not root.is_dir():
        return out
    for p in sorted(root.rglob("*")):
        if any(part in IGNORE for part in p.relative_to(root).parts):
            continue
        if p.is_file():
            out[str(p.relative_to(root))] = hashlib.sha256(p.read_bytes()).hexdigest()
    return out


def copy_tree(src: Path, dst: Path):
    if dst.exists():
        shutil.rmtree(dst)
    shutil.copytree(src, dst, ignore=shutil.ignore_patterns(*IGNORE))


def upstream_path(entry):
    d = repo_dir(entry["repo"])
    return d / entry["path"] if entry.get("path") else d


def target_dir(name, entry):
    """Where the skill lives locally. Default ~/.claude/skills/<name>; override with 'dest' for skills that live elsewhere (e.g. ~/.agents/skills)."""
    if entry.get("dest"):
        return Path(entry["dest"]).expanduser()
    return SKILLS_DIR / name


def classify(name, entry):
    """Returns (status, detail). Assumes repo cache is fresh."""
    up = upstream_path(entry)
    local = target_dir(name, entry)
    snap = STATE / name
    if not up.is_dir():
        return "missing-upstream", f"path '{entry.get('path', '')}' not found in {entry['repo']}"
    up_map, local_map, snap_map = file_map(up), file_map(local), file_map(snap)
    if not local_map:
        return "not-installed", "skill dir missing locally; `adopt` will install it"
    if not snap_map:
        if local_map == up_map:
            return "baseline-auto", "local matches upstream; baseline recorded"
        return "unbaselined", "no baseline yet and local differs from upstream; run `adopt` (take upstream) or `baseline` (keep local as base)"
    local_clean = local_map == snap_map
    upstream_same = up_map == snap_map
    if local_clean and upstream_same:
        return "up-to-date", ""
    if local_clean and not upstream_same:
        changed = sorted(set(up_map) ^ set(snap_map) | {k for k in set(up_map) & set(snap_map) if up_map[k] != snap_map[k]})
        return "update-available", ", ".join(changed[:5]) + ("…" if len(changed) > 5 else "")
    if not local_clean and upstream_same:
        return "local-edits", "local modified, upstream unchanged; leaving alone"
    return "conflict", "both local and upstream changed since last sync; resolve manually then `adopt` or `baseline`"


def do_sync(names, apply_updates, notify=False):
    manifest = load_manifest()
    if not manifest:
        print(f"No skills registered. Add one:\n  {sys.argv[0]} add <skill-name> <owner/repo> [--path skills/<name>] [--ref main]")
        return 0
    targets = {n: manifest[n] for n in (names or manifest) if n in manifest}
    unknown = [n for n in (names or []) if n not in manifest]
    for n in unknown:
        print(f"SKIP {n}: not in manifest")

    lines, updated, conflicts, errors = [], [], [], []
    fetched = set()
    for name, entry in sorted(targets.items()):
        key = (entry["repo"], entry.get("ref", "main"))
        if key not in fetched:
            ok, msg = refresh_repo(*key, paths=repo_paths(manifest, entry["repo"]))
            if not ok:
                errors.append(name)
                lines.append(f"ERROR       {name}: {msg}")
                continue
            fetched.add(key)
        status, detail = classify(name, entry)
        if status == "baseline-auto":
            copy_tree(upstream_path(entry), STATE / name)
            status = "up-to-date"
            detail = f"baseline recorded @ {head_sha(entry['repo'])}"
        elif status == "update-available" and apply_updates:
            copy_tree(upstream_path(entry), target_dir(name, entry))
            copy_tree(upstream_path(entry), STATE / name)
            status = "updated"
            detail = f"-> {head_sha(entry['repo'])} ({detail})"
            updated.append(name)
        elif status == "conflict":
            conflicts.append(name)
        elif status == "missing-upstream":
            errors.append(name)
        lines.append(f"{status:<17} {name}" + (f": {detail}" if detail else ""))

    report = "\n".join(lines)
    print(report)

    REPORTS.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M %Z")
    mode = "apply" if apply_updates else "check"
    body = f"# skill-sync {mode} — {stamp}\n\n```\n{report}\n```\n"
    (REPORTS / "latest.md").write_text(body)
    (REPORTS / f"{datetime.now().strftime('%Y-%m-%d')}.md").write_text(body)

    if notify and (updated or conflicts or errors):
        parts = []
        if updated:
            parts.append(f"{len(updated)} updated")
        if conflicts:
            parts.append(f"{len(conflicts)} conflict(s)")
        if errors:
            parts.append(f"{len(errors)} error(s)")
        msg = ", ".join(parts) + " — see ~/.claude/skill-sync/reports/latest.md"
        run(["osascript", "-e", f'display notification "{msg}" with title "skill-sync"'])
    return 1 if (conflicts or errors) else 0


def cmd_add(args):
    manifest = load_manifest()
    entry = {"repo": args.repo, "ref": args.ref}
    if args.path:
        entry["path"] = args.path
    if args.dest:
        entry["dest"] = args.dest
    manifest[args.skill] = entry
    save_manifest(manifest)
    print(f"Registered {args.skill} <- github.com/{args.repo}" + (f" path={args.path}" if args.path else "") + f" ref={args.ref}")
    ok, msg = refresh_repo(args.repo, args.ref, paths=repo_paths(manifest, args.repo))
    if not ok:
        print(f"WARNING: {msg}")
        return 1
    status, detail = classify(args.skill, entry)
    if status == "baseline-auto":
        copy_tree(upstream_path(entry), STATE / args.skill)
        print("Local copy matches upstream; baseline recorded.")
    else:
        print(f"Status: {status}" + (f" ({detail})" if detail else ""))
    return 0


def cmd_adopt(args):
    manifest = load_manifest()
    entry = manifest.get(args.skill)
    if not entry:
        print(f"{args.skill} not in manifest; run `add` first")
        return 1
    ok, msg = refresh_repo(entry["repo"], entry.get("ref", "main"), paths=repo_paths(manifest, entry["repo"]))
    if not ok:
        print(msg)
        return 1
    up = upstream_path(entry)
    if not up.is_dir():
        print(f"upstream path not found in {entry['repo']}")
        return 1
    copy_tree(up, target_dir(args.skill, entry))
    copy_tree(up, STATE / args.skill)
    print(f"{args.skill}: local replaced with upstream @ {head_sha(entry['repo'])}; baseline recorded")
    return 0


def cmd_baseline(args):
    manifest = load_manifest()
    if args.skill not in manifest:
        print(f"{args.skill} not in manifest; run `add` first")
        return 1
    local = target_dir(args.skill, manifest[args.skill])
    if not local.is_dir():
        print(f"{local} does not exist")
        return 1
    copy_tree(local, STATE / args.skill)
    print(f"{args.skill}: current local copy recorded as baseline; future upstream changes will overwrite it on `apply`")
    return 0


def cmd_remove(args):
    manifest = load_manifest()
    if manifest.pop(args.skill, None) is None:
        print(f"{args.skill} not in manifest")
        return 1
    save_manifest(manifest)
    snap = STATE / args.skill
    if snap.exists():
        shutil.rmtree(snap)
    print(f"{args.skill}: untracked (skill files left in place)")
    return 0


def cmd_list(_):
    manifest = load_manifest()
    if not manifest:
        print("No skills registered.")
        return 0
    for name, e in sorted(manifest.items()):
        print(f"{name:<30} github.com/{e['repo']}" + (f"  path={e['path']}" if e.get("path") else "") + f"  ref={e.get('ref', 'main')}")
    return 0


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd")

    for c in ("check", "apply"):
        s = sub.add_parser(c, help="report upstream changes" if c == "check" else "apply safe updates")
        s.add_argument("skills", nargs="*", help="limit to these skills (default: all)")
        s.add_argument("--notify", action="store_true", help="macOS notification if anything changed or conflicted")

    s = sub.add_parser("add", help="register a skill's GitHub source")
    s.add_argument("skill")
    s.add_argument("repo", help="owner/name")
    s.add_argument("--path", default=None, help="subdirectory in the repo holding the skill (default: repo root)")
    s.add_argument("--ref", default="main")
    s.add_argument("--dest", default=None, help="local dir the skill lives in (default: ~/.claude/skills/<name>)")

    for c in ("adopt", "baseline", "remove"):
        s = sub.add_parser(c)
        s.add_argument("skill")

    sub.add_parser("list", help="show registered skills")

    args = p.parse_args()
    if args.cmd in ("check", "apply"):
        return do_sync(args.skills, apply_updates=(args.cmd == "apply"), notify=args.notify)
    if args.cmd == "add":
        return cmd_add(args)
    if args.cmd == "adopt":
        return cmd_adopt(args)
    if args.cmd == "baseline":
        return cmd_baseline(args)
    if args.cmd == "remove":
        return cmd_remove(args)
    if args.cmd == "list":
        return cmd_list(args)
    p.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
