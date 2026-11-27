"""Registry verification and upstream drift detection.

registry/components.json pins each upstream at a revision and lists `watch` files whose change
means a local override or adapter may no longer be valid, each with the checks to rerun.
`drift` compares the pinned revision with the upstream clone's HEAD and reports which watched files
changed in between; it never updates anything.
"""
from __future__ import annotations

import json
import os
import subprocess
from typing import Any, Dict, List

STATUSES = {"installed-and-verified", "installed-inactive", "source-only", "blocked-authentication",
            "blocked-platform", "verification-failed"}
REQUIRED = {"id", "name", "upstream", "revision", "license", "status", "responsibility", "paths", "verify", "update", "rollback"}


def load(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def verify_registry(reg: Dict[str, Any]) -> List[str]:
    errs: List[str] = []
    ids = set()
    for c in reg.get("components", []):
        missing = REQUIRED - set(c)
        if missing:
            errs.append("%s: missing %s" % (c.get("id", "?"), ", ".join(sorted(missing))))
            continue
        if c["id"] in ids:
            errs.append("duplicate component id %s" % c["id"])
        ids.add(c["id"])
        if c["status"] not in STATUSES:
            errs.append("%s: status %r is not one of %s" % (c["id"], c["status"], sorted(STATUSES)))
        if c["status"].startswith("blocked") and not c.get("blocker"):
            errs.append("%s: blocked status needs a blocker with resume steps" % c["id"])
        if c["status"] == "installed-and-verified" and not c.get("evidence"):
            errs.append("%s: installed-and-verified needs evidence links" % c["id"])
    ovr_ids = {o["id"] for o in reg.get("overrides", [])}
    for o in reg.get("overrides", []):
        for k in ("id", "owner", "upstream", "conflict", "behavior", "implementation", "precedence", "verification", "retire_when"):
            if k not in o:
                errs.append("override %s: missing %s" % (o.get("id", "?"), k))
    for c in reg.get("components", []):
        for oid in c.get("overrides", []):
            if oid not in ovr_ids:
                errs.append("%s references unknown override %s" % (c["id"], oid))
    return errs


def drift(reg: Dict[str, Any], upstream_root: str) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    for c in reg.get("components", []):
        clone = c.get("clone")
        if not clone:
            continue
        path = os.path.join(upstream_root, clone)
        if not os.path.isdir(os.path.join(path, ".git")):
            out.append({"id": c["id"], "state": "missing-clone", "path": path})
            continue
        head = subprocess.run(["git", "-C", path, "rev-parse", "HEAD"], capture_output=True, text=True).stdout.strip()
        if head == c["revision"]:
            out.append({"id": c["id"], "state": "pinned", "revision": head[:12]})
            continue
        # Pinned revision may be absent in a shallow clone; report that instead of guessing.
        has = subprocess.run(["git", "-C", path, "cat-file", "-e", c["revision"] + "^{commit}"], capture_output=True).returncode == 0
        if not has:
            out.append({"id": c["id"], "state": "pin-unreachable", "pinned": c["revision"][:12], "head": head[:12]})
            continue
        changed = subprocess.run(["git", "-C", path, "diff", "--name-only", c["revision"], head], capture_output=True, text=True).stdout.split()
        watch = c.get("watch", [])
        hit = [w["path"] for w in watch if w["path"] in changed]
        out.append({"id": c["id"], "state": "drifted" if hit else "moved-unwatched", "pinned": c["revision"][:12], "head": head[:12],
                    "watched_changed": hit, "rerun": sorted({t for w in watch if w["path"] in hit for t in w.get("rerun", [])}),
                    "changed_files": len(changed)})
    return out


def render_overrides(reg_path: str, out_path: str) -> int:
    ov = load(reg_path).get("overrides", [])
    out = ["# Local override register", "",
           "Generated from `registry/overrides.json` by `frig render-overrides`; edit the JSON, not this file. Each entry names the upstream file and "
           "revision, the conflict observed, the local behavior, where it lives, how it is tested, and when to retire it.", ""]
    for o in ov:
        out += ["## %s" % o["id"], "", "- **Owner:** %s" % o["owner"], "- **Upstream:** %s" % o["upstream"],
                "- **Observed conflict:** %s" % o["conflict"], "- **Local behavior:** %s" % o["behavior"],
                "- **Implementation:** %s" % o["implementation"], "- **Precedence and scope:** %s" % o["precedence"],
                "- **Verification:** %s" % o["verification"], "- **Retire when:** %s" % o["retire_when"], ""]
    with open(out_path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(out))
    return len(ov)
