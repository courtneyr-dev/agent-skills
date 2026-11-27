#!/usr/bin/env python3
"""Resolve a client project's platform and version to the installed adapter skills, or refuse.

  resolve_adapter.py --project PROJECT.json [--register adapters.json] [--home DIR]

PROJECT.json: {"platform": "wordpress", "version": "6.8", "php_version": "8.2"} (php_version optional).
Exit 0 = supported or range-unstated (with a warning), 1 = legacy route, blocked, unknown platform
or an adapter skill missing from its mount, 2 = invalid input.
"""
import argparse
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_REGISTER = os.path.normpath(os.path.join(HERE, "..", "references", "adapters.json"))
VERSION = re.compile(r"^\d+(?:\.\d+){0,3}$")
LIMITS = [
    "Resolves the adapter from the platform and version the project reports; run wp-project-triage or the project's own tooling to confirm those facts first.",
    "A skill counts as present when its SKILL.md exists in the named mount; presence does not prove the skill's guidance is correct for this project.",
    "Supported ranges are the upstream's own statements at the pinned revision; a null range means the upstream states none, not that every version works.",
]


class InputError(Exception):
    pass


def vtuple(v):
    return tuple(int(x) for x in v.split("."))


def below(v, floor):
    a, b = vtuple(v), vtuple(floor)
    n = max(len(a), len(b))
    return a + (0,) * (n - len(a)) < b + (0,) * (n - len(b))


def skill_paths(skills, mounts, home):
    out = []
    for s in skills:
        root = mounts[s["mount"]].replace("~", home, 1)
        path = os.path.join(root, s["id"], "SKILL.md")
        out.append({"id": s["id"], "mount": s["mount"], "path": path, "present": os.path.isfile(path)})
    return out


def resolve(project, register, home):
    """Pure apart from file-existence checks on the skill mounts."""
    mounts = register["mounts"]
    plat = next((p for p in register["platforms"] if p["id"] == project["platform"]), None)
    base = {"platform": project["platform"], "version": project.get("version"), "warnings": [], "limits": LIMITS}
    if plat is None:
        known = ", ".join(p["id"] for p in register["platforms"])
        return dict(base, ok=False, decision="unknown",
                    reason="no adapter is registered for %s; known platforms: %s. Route to a human specialist." % (project["platform"], known),
                    skills=[])
    if plat["status"] == "blocked":
        return dict(base, ok=False, decision="blocked", reason=plat["blocked_reason"], skills=[])
    sup = plat["supported"]
    host = None
    if plat.get("host"):
        host = next(p for p in register["platforms"] if p["id"] == plat["host"]["platform"])
        hsup, field = host["supported"], plat["host"]["version_field"]
        hold = []
        if hsup.get("min_version") and below(project[field], hsup["min_version"]):
            hold.append("%s %s is below %s" % (field, project[field], hsup["min_version"]))
        if hsup.get("php_min") and below(project["php_version"], hsup["php_min"]):
            hold.append("PHP %s is below %s" % (project["php_version"], hsup["php_min"]))
        if hold:
            return dict(base, ok=False, decision="legacy", skills=skill_paths(host["legacy"]["skills"], mounts, home), source=hsup["source"],
                        reason="%s runs on %s: %s. %s" % (plat["id"], host["id"], "; ".join(hold), host["legacy"]["route"]))
    old = []
    if sup.get("min_version") and project.get("version") and below(project["version"], sup["min_version"]):
        old.append("%s %s is below %s" % (plat["id"], project["version"], sup["min_version"]))
    if sup.get("php_min") and project.get("php_version") and below(project["php_version"], sup["php_min"]):
        old.append("PHP %s is below %s" % (project["php_version"], sup["php_min"]))
    if old:
        skills = skill_paths(plat["legacy"]["skills"], mounts, home)
        return dict(base, ok=False, decision="legacy", reason="; ".join(old) + ". " + plat["legacy"]["route"],
                    skills=skills, source=sup["source"])
    skills = skill_paths(plat["skills"], mounts, home)
    missing = [s["id"] for s in skills if not s["present"]]
    if missing:
        return dict(base, ok=False, decision="adapter-missing", skills=skills, source=sup["source"],
                    reason="installed adapter skills are missing from their mounts: %s. Restore them through skill-sync before relying on this adapter." % ", ".join(missing))
    decision = "supported"
    if not sup.get("min_version"):
        decision = "range-unstated"
        base["warnings"].append("The upstream states no supported version range (%s); confirm %s %s against the project's own requirements."
                                % (sup["source"], plat["id"], project.get("version") or "(no version given)"))
    return dict(base, ok=True, decision=decision, skills=skills, standards=plat["standards"], source=sup["source"])


def load_json(path, what):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError) as exc:
        raise InputError("cannot read %s %s: %s" % (what, path, exc))


def parse_project(obj):
    if not isinstance(obj, dict) or not isinstance(obj.get("platform"), str) or not obj["platform"].strip():
        raise InputError("project needs a non-empty 'platform'")
    for key in ("version", "php_version", "wordpress_version"):
        if key in obj and (not isinstance(obj[key], str) or not VERSION.match(obj[key])):
            raise InputError("project %s must look like 7.0 or 8.2.1" % key)
    return obj


def host_requirements(project, register):
    """Every minimum the register states must be checkable, so the project must report the matching fact: a platform
    with min_version needs version, one with php_min needs php_version, and a platform that runs on a host
    (WooCommerce on WordPress) needs the host's version and PHP. A missing fact is invalid input, never a pass."""
    plat = next((p for p in register["platforms"] if p["id"] == project["platform"]), None)
    if plat and plat.get("host"):
        for key in (plat["host"]["version_field"], "php_version"):
            if key not in project:
                raise InputError("project on %s needs %s, because %s's minimums apply first" % (plat["id"], key, plat["host"]["platform"]))
    if plat and plat.get("status") != "blocked":
        sup = plat.get("supported", {})
        for limit, key in (("min_version", "version"), ("php_min", "php_version")):
            if sup.get(limit) and key not in project:
                raise InputError("project on %s needs %s, because the register's minimum %s %s can't be checked without it" % (plat["id"], key, limit, sup[limit]))
    return project


def parse_register(obj):
    if not isinstance(obj, dict) or not isinstance(obj.get("platforms"), list) or not isinstance(obj.get("mounts"), dict):
        raise InputError("register needs 'mounts' and 'platforms'")
    for p in obj["platforms"]:
        if p.get("status") == "blocked":
            if not p.get("blocked_reason"):
                raise InputError("blocked platform %s needs a blocked_reason" % p.get("id"))
            continue
        if not p.get("skills") or "supported" not in p:
            raise InputError("platform %s needs skills and supported" % p.get("id"))
        for s in p["skills"] + p.get("legacy", {}).get("skills", []):
            if s.get("mount") not in obj["mounts"]:
                raise InputError("platform %s skill %s names unknown mount %s" % (p["id"], s.get("id"), s.get("mount")))
        if p["supported"].get("min_version") and "legacy" not in p:
            raise InputError("platform %s has a min_version but no legacy route" % p["id"])
        if p.get("host"):
            h = next((x for x in obj["platforms"] if x["id"] == p["host"].get("platform")), None)
            if h is None or "legacy" not in h or not p["host"].get("version_field"):
                raise InputError("platform %s names host %s, which needs a legacy route and a version_field" % (p["id"], p["host"].get("platform")))
    return obj


def main(argv=None):
    ap = argparse.ArgumentParser(description="Resolve a project's platform to installed adapter skills.")
    ap.add_argument("--project", required=True)
    ap.add_argument("--register", default=DEFAULT_REGISTER)
    ap.add_argument("--home", default=os.path.expanduser("~"), help="home directory the mounts resolve against")
    try:
        args = ap.parse_args(argv)
    except SystemExit as exc:
        if exc.code not in (0, None):
            print(json.dumps({"error": "usage: --project PROJECT.json [--register FILE] [--home DIR]"}, indent=2))
            return 2
        raise
    try:
        project = parse_project(load_json(args.project, "project"))
        register = parse_register(load_json(args.register, "register"))
        host_requirements(project, register)
    except InputError as exc:
        print(json.dumps({"error": str(exc)}, indent=2, sort_keys=True))
        return 2
    result = resolve(project, register, args.home)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
