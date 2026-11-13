#!/usr/bin/env python3
"""Where an improvement to a skill goes: which repo, which path in it, and how a change lands.

    python3 skill_owner.py <skill>          # e.g. docs-style-review, team-skills:writing-skills
    python3 skill_owner.py <skill> --json

Flows:
  pr              open a pull request against `repo` (from your fork when `fork` is set)
  rfc-pr          a repo in `rfc_repos`: follow the skill named in `rfc_process_skill`
  fork-commit     commit to your own fork of a third-party pack; never upstream
  upstream-issue  third-party skill: draft an issue for the maintainers, no PR
  unknown         nothing resolved; ask the user where the skill came from

Lookup order: config `owners` overrides, plugin skills (`plugin:skill`), the skill-sync manifest,
then the git checkout the skill's SKILL.md resolves into. Settings come from config.local.json
beside this script (gitignored); see config.example.json.
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULTS = {
    # Your employer's GitHub orgs: their repos get PRs, like your own.
    "employer_orgs": [],
    # Repos that take skill changes through a proposal process instead of a plain PR.
    "rfc_repos": [],
    "rfc_process_skill": None,
    # Per-org commit rules, e.g. {"my-employer": "conventional, signed"}.
    "commit_styles": {},
    "own_orgs": [],
    "fork_repos": [],
    "skills_dirs": ["~/.claude/skills", "~/.agents/skills"],
    "plugins_dir": "~/.claude/plugins",
    "sync_manifest": None,
    "owners": {},
    # Synced plugins name a few marketplaces without an owner/repo.
    "marketplace_repos": {"knowledge-work-plugins": "anthropics/knowledge-work-plugins"},
}


def load_config(path=None):
    cfg = dict(DEFAULTS)
    p = Path(path) if path else HERE / "config.local.json"
    if p.is_file():
        cfg.update(json.loads(p.read_text()))
    return cfg


def expand(p):
    return Path(os.path.expanduser(p))


def repo_from_url(url):
    m = re.search(r"github\.com[:/]+([^/]+)/([^/\s]+?)(?:\.git)?/?$", url or "")
    return f"{m.group(1)}/{m.group(2)}" if m else None


def git(cwd, *args):
    r = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True)
    return r.stdout.strip() if r.returncode == 0 else None


def classify(repo, cfg, fork=None):
    """Flow for a change to `repo`. `fork` is the user's fork the PR comes from, if any."""
    owner = repo.split("/")[0].lower()
    if repo in cfg["rfc_repos"]:
        flow = "rfc-pr"
    elif repo in cfg["fork_repos"]:
        flow = "fork-commit"
    elif owner in [o.lower() for o in cfg["employer_orgs"] + cfg["own_orgs"]]:
        flow = "pr"
    elif fork:
        flow = "pr"
    else:
        flow = "upstream-issue"
    styles = {k.lower(): v for k, v in cfg["commit_styles"].items()}
    out = {
        "flow": flow,
        "employer": owner in [o.lower() for o in cfg["employer_orgs"]],
        "commit_style": styles.get(owner, "match the repo's git log"),
    }
    if flow == "rfc-pr":
        out["rfc_process_skill"] = cfg["rfc_process_skill"]
    return out


def result(skill, source, repo, path=None, local=None, fork=None, cfg=None, **extra):
    out = {"skill": skill, "source": source, "repo": repo, "path": path, "local": str(local) if local else None}
    if fork:
        out["fork"] = fork
    out.update(classify(repo, cfg, fork) if repo else {"flow": "unknown", "employer": False, "commit_style": None})
    out.update(extra)
    return out


def from_plugin(skill, cfg):
    plugin, _, name = skill.partition(":")
    root = expand(cfg["plugins_dir"])
    for meta in sorted(root.glob("synced/*/*.meta.json")):
        if meta.name.split(".meta.json")[0].split("~")[0] != plugin:
            continue
        market = json.loads(meta.read_text()).get("marketplace_name", "")
        repo = market if "/" in market else cfg["marketplace_repos"].get(market)
        local = next((d for d in sorted(meta.parent.glob(f"{plugin}*/skills/{name}")) if d.is_dir()), None)
        return result(skill, f"synced plugin ({market})", repo, None, local, cfg=cfg, plugin=plugin)
    installed = root / "installed_plugins.json"
    if installed.is_file():
        for pid, entries in json.loads(installed.read_text()).get("plugins", {}).items():
            pname, _, market = pid.partition("@")
            if pname != plugin:
                continue
            repo = marketplace_repo(root, market, pname)
            local = Path(entries[0]["installPath"]) / "skills" / name if entries else None
            return result(skill, f"marketplace plugin ({pid})", repo, repo_path_in_clone(root / "marketplaces" / market, name),
                          local, cfg=cfg, plugin=plugin)
    return result(skill, f"plugin {plugin} not found locally", None, cfg=cfg)


def marketplace_repo(root, market, pname):
    """The repo a marketplace plugin's files come from: its own URL source, else the marketplace repo."""
    known = root / "known_marketplaces.json"
    market_repo = None
    if known.is_file():
        src = json.loads(known.read_text()).get(market, {}).get("source", {})
        market_repo = src.get("repo") or repo_from_url(src.get("url"))
    catalog = root / "marketplaces" / market / ".claude-plugin" / "marketplace.json"
    if catalog.is_file():
        for p in json.loads(catalog.read_text()).get("plugins", []):
            if p.get("name") == pname and isinstance(p.get("source"), dict):
                return repo_from_url(p["source"].get("url")) or p["source"].get("repo") or market_repo
    return market_repo


def repo_path_in_clone(clone, name):
    """Path of <name>/SKILL.md's folder in a marketplace clone that is also the plugin repo, else None."""
    hits = sorted(p.parent for p in clone.glob(f"**/{name}/SKILL.md") if ".git" not in p.parts)
    return str(hits[0].relative_to(clone)) if len(hits) == 1 else None


def from_manifest(skill, cfg):
    path = cfg.get("sync_manifest")
    if not path or not expand(path).is_file():
        return None
    entry = json.loads(expand(path).read_text()).get(skill)
    if not entry:
        return None
    local = expand(entry["dest"]) if entry.get("dest") else find_local(skill, cfg)
    # A lesson about the user's own overlay (kept files, appended SKILL.local.md) lands locally, not upstream.
    overlay = sorted(set(entry.get("keep", [])) | set(entry.get("frontmatter", {})))
    extra = {"overlay": overlay} if overlay else {}
    return result(skill, "skill-sync manifest", entry["repo"], entry.get("path"), local, cfg=cfg, **extra)


def find_local(skill, cfg):
    for d in cfg["skills_dirs"]:
        p = expand(d) / skill
        if (p / "SKILL.md").exists():
            return p
    return None


def from_git(skill, cfg):
    local = find_local(skill, cfg)
    if not local:
        return None
    real = (local / "SKILL.md").resolve().parent
    top = git(real, "rev-parse", "--show-toplevel")
    if not top:
        return result(skill, "local, not in a git checkout", None, None, local, cfg=cfg)
    origin = repo_from_url(git(top, "remote", "get-url", "origin"))
    upstream = repo_from_url(git(top, "remote", "get-url", "upstream"))
    rel = str(real.relative_to(Path(top).resolve()))
    if upstream and origin and upstream != origin:
        return result(skill, f"git checkout {top} (fork of {upstream})", upstream, rel, local, fork=origin, cfg=cfg)
    return result(skill, f"git checkout {top}", origin, rel, local, cfg=cfg)


def lookup(skill, cfg):
    override = cfg["owners"].get(skill)
    if override:
        return result(skill, "config override", override["repo"], override.get("path"), find_local(skill, cfg),
                      fork=override.get("fork"), cfg=cfg)
    if ":" in skill:
        return from_plugin(skill, cfg)
    return from_manifest(skill, cfg) or from_git(skill, cfg) or result(skill, "not found", None, cfg=cfg)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("skill")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--config", default=None)
    args = ap.parse_args()
    out = lookup(args.skill, load_config(args.config))
    if args.json:
        print(json.dumps(out, indent=2))
    else:
        for k, v in out.items():
            if v not in (None, ""):
                print(f"{k:13} {v}")
    return 0 if out["flow"] != "unknown" else 1


if __name__ == "__main__":
    sys.exit(main())
