"""Acceptance runner: every row of acceptance/matrix.json as pass, fail or blocked, with its commands and evidence.

Check kinds:
- eval: a fleet's own eval case, by id. Its check.argv runs from the skill directory; exit 0 means the
  eval's expectation held, exit 3 that a capability is missing (blocked), as eval-run reads it. A
  model-judgment or human eval has no command, so it reports blocked.
- expect-blocked: the required behavior is an honest "not measured"; passes when the eval record is
  blocked with a note.
- unittest: a module, class or test under scripts/tests.
- command: an argv with {python}, {skill}, {skills} and {repo} placeholders.
- demo: reruns that demonstration through demos/run_demos.py into a fresh stamped folder.
- internal: checks implemented here (coverage, imp-001).

A row fails if any check fails, is blocked if any check is blocked, and passes otherwise. Each run writes
evidence/integration/acceptance/runs/<stamp>/<row>.txt and refreshes evidence/integration/acceptance/<row>.txt
and results.json. Nothing is deleted.
"""
from __future__ import annotations

import datetime
import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional

from factory_rig.canon import atomic_write

from . import SKILL_DIR
from .checks import coverage as fleet_coverage
from .registry import PROFILES, Registry

MATRIX = os.path.join(SKILL_DIR, "acceptance", "matrix.json")
OUT = os.path.join(SKILL_DIR, "evidence", "integration", "acceptance")
REPO = os.path.normpath(os.path.join(SKILL_DIR, "..", ".."))
TAIL = 4000


def _evals(reg: Registry) -> Dict[str, Dict[str, Any]]:
    out = {}
    for f in reg.fleet_dirs():
        path = reg.path("fleets/%s/evals.json" % f)
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as fh:
                for e in json.load(fh)["evals"]:
                    out[e["id"]] = e
    return out


def _run(argv: List[str], cwd: str) -> Dict[str, Any]:
    try:
        p = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=900)
        return {"exit": p.returncode, "output": (p.stdout + p.stderr)}
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {"exit": None, "output": "could not run: %s" % exc}


def _internal(name: str, reg: Registry) -> Dict[str, Any]:
    if name == "coverage":
        cov = fleet_coverage(Registry(reg.root, reg.skills_root))
        with open(reg.path(PROFILES), encoding="utf-8") as fh:
            profiles = [p["id"] for p in json.load(fh)["profiles"]]
        workloads = set()
        for f in reg.fleet_dirs():
            with open(reg.path("fleets/%s/roles.json" % f), encoding="utf-8") as fh:
                for w in json.load(fh)["workloads"]:
                    workloads.update(w["profiles"])
        empty = [f["fleet"] for f in cov["fleets"] if not f["roles"]]
        bare = [p for p in profiles if p not in workloads]
        lines = ["registry errors: %d" % cov["registry_errors"], "fleets without roles: %s" % (empty or "none"),
                 "profiles without a workload: %s" % (bare or "none"),
                 "requirement rows: %d, without a deliverable or blocker: %d %s" % (
                     cov["requirements"]["rows"], cov["requirements"]["uncovered"], cov["requirements"]["uncovered_ids"][:20])]
        ok = not cov["registry_errors"] and not empty and not bare and cov["requirements"]["uncovered"] == 0
        return {"status": "pass" if ok else "fail", "command": "fleetlib.acceptance internal coverage (bin/fleet coverage)", "exit": 0 if ok else 1,
                "output": "\n".join(lines)}
    if name == "imp-001":
        from .improvement import EVIDENCE_DIR, gate
        g = gate("IMP-001", reg.skills_root)
        with open(os.path.join(EVIDENCE_DIR, "IMP-001", "evaluation.json"), encoding="utf-8") as fh:
            ev = json.load(fh)
        ok = ev["verdict"] == "pass" and g["stage"] in ("evaluated", "reviewed", "promoted")
        return {"status": "pass" if ok else "fail", "command": "bin/fleet improve gate IMP-001 (and evaluation.json)", "exit": 0 if ok else 1,
                "output": json.dumps({"evaluation_run_on": ev["run_on"], "checks": ev["checks"], "regressions": ev["regressions"], "gate": g}, indent=2)}
    return {"status": "fail", "command": "internal " + name, "exit": None, "output": "unknown internal check"}


def run_check(c: Dict[str, Any], reg: Registry, evals: Dict[str, Dict[str, Any]], demos: Dict[str, Any]) -> Dict[str, Any]:
    ref = c.get("id") or c.get("target") or c.get("name") or " ".join(c.get("argv", [])[:3])
    res: Dict[str, Any] = {"kind": c["kind"], "ref": ref}
    if c["kind"] == "blocked":
        return dict(res, status="blocked", command="none", output=c["note"])
    if c["kind"] in ("eval", "expect-blocked"):
        e = evals.get(c["id"])
        if e is None:
            return dict(res, status="fail", command="none", output="no fleets/*/evals.json defines %s" % c["id"])
        if c["kind"] == "expect-blocked":
            st = e["outcome"]["status"]
            ok = st == "blocked" and bool(e["outcome"].get("note"))
            return dict(res, status="pass" if ok else "fail", command="read the eval record",
                        output="outcome %s: %s" % (st, e["outcome"].get("note", "")))
        if e["check"]["method"] != "script":
            return dict(res, status="blocked", command="none", output="%s is a %s check with no command" % (c["id"], e["check"]["method"]))
        r = _run(e["check"]["argv"], SKILL_DIR)
        return dict(res, status={0: "pass", 3: "blocked"}.get(r["exit"], "fail"), command=" ".join(e["check"]["argv"]), **r)
    if c["kind"] == "unittest":
        argv = [sys.executable, "-W", "ignore", "-m", "unittest", c["target"]]
        r = _run(argv, os.path.join(SKILL_DIR, "scripts", "tests"))
        return dict(res, status="pass" if r["exit"] == 0 else "fail", command="(cwd scripts/tests) " + " ".join(argv[1:]), **r)
    if c["kind"] == "command":
        ctx = {"python": sys.executable, "skill": SKILL_DIR, "skills": reg.skills_root, "repo": REPO}
        expand = lambda s: s.format(**ctx)
        argv, cwd = [expand(a) for a in c["argv"]], expand(c.get("cwd", "{skill}"))
        r = _run(argv, cwd)
        ok = r["exit"] == c.get("expect_exit", 0)
        return dict(res, status="pass" if ok else ("blocked" if r["exit"] is None else "fail"),
                    command="(cwd %s) %s" % (os.path.relpath(cwd, REPO), " ".join(c["argv"])), **r)
    if c["kind"] == "demo":
        if c["id"] not in demos:
            demos[c["id"]] = _run([sys.executable, os.path.join(SKILL_DIR, "demos", "run_demos.py"), c["id"]], SKILL_DIR)
            with open(os.path.join(OUT, "..", "demos", "results.json"), encoding="utf-8") as fh:
                demos[c["id"]]["result"] = next((d for d in json.load(fh)["demos"] if d["id"] == c["id"]), {})
        d = demos[c["id"]]
        status = d["result"].get("status", "fail")
        return dict(res, status=status if status in ("pass", "blocked") else "fail", command="python3 demos/run_demos.py " + c["id"],
                    exit=d["exit"], output=d["output"] + "\nrun: %s" % d["result"].get("run"))
    if c["kind"] == "internal":
        return dict(res, **_internal(c["name"], reg))
    return dict(res, status="fail", command="none", output="unknown check kind %s" % c["kind"])


def row_status(checks: List[Dict[str, Any]]) -> str:
    states = {c["status"] for c in checks}
    return "fail" if "fail" in states else ("blocked" if "blocked" in states else "pass")


def run(reg: Registry, only: Optional[List[str]] = None) -> Dict[str, Any]:
    with open(MATRIX, encoding="utf-8") as fh:
        matrix = json.load(fh)
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    runs = os.path.join(OUT, "runs", stamp)
    os.makedirs(runs)
    evals, demos = _evals(reg), {}
    rows = []
    for row in matrix["rows"]:
        if only and row["id"] not in only:
            continue
        checks = [run_check(c, reg, evals, demos) for c in row["checks"]]
        status = row_status(checks)
        text = ["# Acceptance row %s: %s" % (row["id"], row["test"]), "Required: " + row["required"], "Owner: " + row["owner"],
                "Run: %s (bin/fleet acceptance --row %s)" % (stamp, row["id"]), "Status: " + status.upper(), ""]
        for c in checks:
            text += ["## %s %s: %s" % (c["kind"], c["ref"], c["status"].upper()), "$ " + c["command"], "exit %s" % c.get("exit"),
                     c.get("output", "")[-TAIL:], ""]
        body = "\n".join(text) + "\n"
        atomic_write(os.path.join(runs, row["id"] + ".txt"), body)
        atomic_write(os.path.join(OUT, row["id"] + ".txt"), body)
        rows.append({"id": row["id"], "test": row["test"], "owner": row["owner"], "status": status,
                     "evidence": "evidence/integration/acceptance/%s.txt" % row["id"],
                     "checks": [{"kind": c["kind"], "ref": c["ref"], "status": c["status"], "command": c["command"]} for c in checks]})
    result = {"run_on": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "stamp": stamp,
              "command": "bin/fleet acceptance" + ("".join(" --row " + r for r in only) if only else ""),
              "counts": {s: sum(1 for r in rows if r["status"] == s) for s in ("pass", "fail", "blocked")}, "rows": rows}
    atomic_write(os.path.join(runs, "results.json"), json.dumps(result, indent=2, sort_keys=True) + "\n")
    if not only:
        atomic_write(os.path.join(OUT, "results.json"), json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result
