#!/usr/bin/env python3
"""Check the company-fleets source ledger and capability matrix against the installed rig.

Exit 0: consistent. Exit 1: findings (drift, dangling links, registry disagreement, uncovered requirements).
Exit 2: the ledger, matrix or requirements file is unreadable or breaks the schema.

Checks:
- ledger: repo pins are full SHAs; every status is one of STATUSES; installed items name a tree hash.
- installed items: the skill-sync registry agrees on repo and path, and the installed tree hashes to the
  pinned tree hash. A hidden item keeps `disable-model-invocation: true` in SKILL.md and in its registry pin.
- pinned clones (when present): HEAD equals the pinned revision, and the pinned path rendered the way
  skill-sync installs it (registry pins and kept files applied) hashes the same as the ledger.
- relative links that leave a skill directory resolve, unless the ledger lists them under dangling_links.
- matrix: every requirement id appears exactly once with one disposition from DISPOSITIONS and the fields
  that disposition needs; every skill it names is installed (upstream), present in a skill root (existing)
  or, for original-local rows, present in the rig (with --strict a missing one is a finding, otherwise planned).
"""

import argparse
import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path

SKILLS_ROOT = Path(__file__).resolve().parents[2]  # the skills root that holds company-fleets
sys.path.insert(0, str(SKILLS_ROOT / "skill-sync"))
import sync_skills  # noqa: E402  one renderer and one frontmatter parser for installs and for this check

# An older skill-sync lacks the renderer this check shares with it.
MISSING = [f for f in ("read_tree", "frontmatter_blocks", "render", "apply_pins") if not hasattr(sync_skills, f)]

STATUSES = {"installed-and-verified", "installed-inactive", "source-only",
            "blocked-authentication", "blocked-platform", "verification-failed"}
INSTALLED = {"installed-and-verified", "installed-inactive", "verification-failed"}
DISPOSITIONS = {"existing-skill", "upstream-skill", "original-local", "blocker"}
BUILDERS = {"foundation", "corporate-and-agency", "hosting", "product-and-consultancies", "devrel-and-community", "education"}
SHA = re.compile(r"^[0-9a-f]{40}$")
LINK = re.compile(r"\]\(([^)#\s]+)|`(\.\./[^`\s]+)`")
HIDE = "disable-model-invocation"


class SchemaError(Exception):
    pass


def digest(files):
    """sha256 over (relative path, file sha256) pairs, sorted by path."""
    h = hashlib.sha256()
    for rel in sorted(files):
        h.update(rel.encode() + b"\0" + hashlib.sha256(files[rel]).digest())
    return h.hexdigest()


def tree_hash(root):
    return digest(sync_skills.read_tree(Path(root)))


def escaping_links(skill_dir):
    """(file, link, resolved target) for relative links that leave skill_dir."""
    out = []
    root = skill_dir.resolve()
    for p in sorted(skill_dir.rglob("*.md")):
        for a, b in LINK.findall(p.read_text(errors="replace")):
            link = a or b
            if link.startswith(("http:", "https:", "mailto:", "/", "$", "{", "~")):
                continue
            target = (p.parent / link).resolve()
            if root not in target.parents and target != root:
                out.append((p.relative_to(skill_dir).as_posix(), link, target))
    return out


def hidden(skill_md):
    blocks = sync_skills.frontmatter_blocks(skill_md.read_text(errors="replace")) or []
    return any(k == HIDE and "\n".join(lines).split(":", 1)[1].strip().lower() == "true" for k, lines in blocks)


def load(path, kind):
    try:
        return json.loads(Path(path).read_text())
    except (OSError, ValueError) as e:
        raise SchemaError(f"{kind} {path}: {e}")


def need(obj, keys, where):
    missing = [k for k in keys if not obj.get(k)]
    if missing:
        raise SchemaError(f"{where}: missing {', '.join(missing)}")


def check_item(it, reg, skills_root, repo):
    findings = []
    if not reg or reg.get("repo") != it["repo"] or reg.get("path") != it["path"]:
        return [f"{it['name']}: skill-sync registry entry {reg} disagrees with ledger {it['repo']}:{it['path']}"]
    dest = Path(reg["dest"]).expanduser() if reg.get("dest") else skills_root / it["name"]
    if not (dest / "SKILL.md").is_file():
        return [f"{it['name']}: not installed at {dest}; resume: sync_skills.py adopt {it['name']}"]
    got = tree_hash(dest)
    if got != it["tree_sha256"]:
        findings.append(f"{it['name']}: installed tree {got} differs from pinned {it['tree_sha256'][:12]} @ {repo['revision'][:7]}; "
                        f"resume: sync_skills.py check {it['name']}, then adopt or rerun build_sources.py")
    if it.get("model_invocation") == "disabled":
        if not hidden(dest / "SKILL.md"):
            findings.append(f"{it['name']}: SKILL.md lost {HIDE}: true; resume: add it, then sync_skills.py pin {it['name']} {HIDE}")
        if reg.get("frontmatter", {}).get(HIDE) != f"{HIDE}: true":
            findings.append(f"{it['name']}: registry does not pin {HIDE}; resume: sync_skills.py pin {it['name']} {HIDE}")
    known = {(d["from"], d["link"]) for d in it.get("dangling_links", [])}
    for f, link, target in escaping_links(dest):
        if not target.exists() and (f, link) not in known:
            findings.append(f"{it['name']}: {f} links {link}, which does not resolve and is not in dangling_links")
    return findings


def check_ledger(ledger, registry, skills_root, clones):
    findings = []
    repos = {}
    for r in ledger.get("repos") or []:
        need(r, ["id", "url", "revision", "revision_date", "license", "clone", "status"], f"repo {r.get('id')}")
        if not SHA.match(r["revision"]):
            raise SchemaError(f"repo {r['id']}: revision {r['revision']!r} is not a full SHA")
        if r["status"] not in STATUSES:
            raise SchemaError(f"repo {r['id']}: status {r['status']!r} not in {sorted(STATUSES)}")
        need(r["license"], ["spdx"], f"repo {r['id']} license")
        repos[r["id"]] = r
    if not repos:
        raise SchemaError("ledger has no repos")
    items = ledger.get("items") or []
    names = set()
    for it in items:
        need(it, ["name", "repo", "status"], f"item {it.get('name')}")
        if it["status"] not in STATUSES:
            raise SchemaError(f"item {it['name']}: status {it['status']!r} not in {sorted(STATUSES)}")
        if it["repo"] not in repos:
            raise SchemaError(f"item {it['name']}: repo {it['repo']} has no pin")
        if it["name"] in names:
            raise SchemaError(f"item {it['name']}: listed twice")
        names.add(it["name"])
        reg = registry.get(it["name"])
        if it["status"] in INSTALLED:
            need(it, ["path", "tree_sha256"], f"item {it['name']}")
            findings += check_item(it, reg, skills_root, repos[it["repo"]])
        elif reg:
            findings.append(f"{it['name']}: status {it['status']} but skill-sync registers it; adopt and re-status, or `sync_skills.py remove`")
    if clones:
        findings += check_clones(repos, items, registry, skills_root)
    return findings, {it["name"]: it for it in items}


def check_clones(repos, items, registry, skills_root):
    findings = []
    for r in repos.values():
        clone = Path(r["clone"]).expanduser()
        if not (clone / ".git").exists():
            continue
        head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=clone, capture_output=True, text=True).stdout.strip()
        if head != r["revision"]:
            findings.append(f"{r['id']}: clone HEAD {head[:7]} is not the pinned {r['revision'][:7]}; resume: git -C {r['clone']} checkout {r['revision']}")
            continue
        for it in items:
            if it["repo"] != r["id"] or not it.get("tree_sha256") or not it.get("path"):
                continue
            src = clone / it["path"]
            if not src.is_dir():
                findings.append(f"{it['name']}: path {it['path']} missing at pinned {r['revision'][:7]}")
                continue
            entry = registry.get(it["name"], {})
            dest = Path(entry["dest"]).expanduser() if entry.get("dest") else skills_root / it["name"]
            if digest(sync_skills.render(src, entry, dest)) != it["tree_sha256"]:
                findings.append(f"{it['name']}: pinned clone tree, rendered with its registry pins, differs from the ledger hash")
    return findings


def check_matrix(matrix, items, existing_roots, requirement_ids, skills_root, strict):
    findings, planned = [], []
    rows = matrix.get("rows") or []
    if not rows:
        raise SchemaError("matrix has no rows")
    seen = set()
    for c in rows:
        need(c, ["requirement", "fleet", "disposition", "verification"], f"row {c.get('requirement')}")
        rid, d = c["requirement"], c["disposition"]
        if rid in seen:
            raise SchemaError(f"row {rid}: requirement mapped twice")
        seen.add(rid)
        if d not in DISPOSITIONS:
            raise SchemaError(f"row {rid}: disposition {d!r} not in {sorted(DISPOSITIONS)}")
        if d in ("existing-skill", "upstream-skill"):
            need(c, ["skills"], f"row {rid}")
        if d == "upstream-skill":
            need(c, ["adapter"], f"row {rid}")
            for s in c["skills"]:
                it = items.get(s)
                if not it or it["status"] not in INSTALLED:
                    findings.append(f"{rid}: upstream skill {s} is not installed per the ledger")
        if d == "existing-skill":
            for s in c["skills"]:
                if not any((Path(r).expanduser() / s / "SKILL.md").exists() for r in existing_roots):
                    findings.append(f"{rid}: existing skill {s} not found in {existing_roots}")
        if d == "original-local":
            need(c, ["local_skill", "builder"], f"row {rid}")
            if c["builder"] not in BUILDERS:
                raise SchemaError(f"row {rid}: builder {c['builder']!r} not in {sorted(BUILDERS)}")
            if not (skills_root / c["local_skill"] / "SKILL.md").is_file():
                planned.append(rid)
                if strict:
                    findings.append(f"{rid}: original skill {c['local_skill']} has no SKILL.md yet ({c['builder']} builds it)")
        if d == "blocker":
            need(c, ["blocker", "resume"], f"row {rid}")
    missing = sorted(set(requirement_ids) - seen)
    if missing:
        findings.append(f"matrix maps no row for requirement(s) {', '.join(missing)}")
    unknown = sorted(seen - set(requirement_ids))
    if unknown:
        findings.append(f"matrix maps unknown requirement(s) {', '.join(unknown)}")
    return findings, planned


def main(argv=None):
    here = Path(__file__).resolve().parent
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--ledger", default=str(here / "ledger.json"))
    p.add_argument("--matrix", default=str(here / "capability-matrix.json"))
    p.add_argument("--registry", default=str(sync_skills.MANIFEST), help="default: skill-sync's sources.json ($SKILL_SYNC_HOME)")
    p.add_argument("--requirements", default=str(here.parent / "registry/requirements.json"))
    p.add_argument("--skills-root", default=str(SKILLS_ROOT))
    p.add_argument("--existing-root", action="append", default=None,
                   help="skill roots for existing-skill rows, repeatable (default: the skills root that holds company-fleets)")
    p.add_argument("--no-clones", action="store_true", help="skip pinned-clone checks")
    p.add_argument("--strict", action="store_true", help="an original-local row whose skill is not built yet is a finding")
    a = p.parse_args(argv)
    roots = a.existing_root or [str(SKILLS_ROOT)]
    if MISSING:
        print(f"INVALID skill-sync at {SKILLS_ROOT / 'skill-sync'} lacks {', '.join(MISSING)}; install a skill-sync that has them")
        return 2
    try:
        ledger, matrix = load(a.ledger, "ledger"), load(a.matrix, "matrix")
        registry = load(a.registry, "registry")
        reqs = [r["id"] for r in load(a.requirements, "requirements").get("rows", [])]
        if not reqs:
            raise SchemaError(f"requirements {a.requirements}: no rows")
        findings, items = check_ledger(ledger, registry, Path(a.skills_root), not a.no_clones)
        more, planned = check_matrix(matrix, items, roots, reqs, Path(a.skills_root), a.strict)
        findings += more
    except SchemaError as e:
        print(f"INVALID {e}")
        return 2
    for f in findings:
        print(f"FINDING {f}")
    installed = sum(1 for i in items.values() if i["status"] in INSTALLED)
    hidden_n = sum(1 for i in items.values() if i.get("model_invocation") == "disabled")
    print(f"{'OK' if not findings else 'FAIL'}: {len(ledger['repos'])} repos, {len(items)} items ({installed} installed, "
          f"{hidden_n} hidden), {len(matrix['rows'])} of {len(reqs)} requirements mapped, {len(planned)} original skills planned, "
          f"{len(findings)} findings")
    return 1 if findings else 0


if __name__ == "__main__":
    sys.exit(main())
