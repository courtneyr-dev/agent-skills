"""Compounding improvement (prompt 2, section 13): a gate between an observed failure and a changed skill.

A record (improvement/records/<id>.json) carries the loop: observation, hypothesis, proposed patch,
pinned criteria, evaluation, review, promotion, monitor and rollback. The rules the gate enforces:

- Criteria are pinned before any evaluation: pin() writes improvement/pins/<id>.json once, with the hash
  of the case file and the thresholds. evaluate() refuses when the cases changed since, so a worker can't
  rewrite its own acceptance criteria to pass.
- Regression cases are computed, not chosen: the foundation tests plus every fleet eval whose command
  exercises the changed capability.
- One unverified observation can't change a skill: the original failure must reproduce on the unpatched
  copy before anything else counts.
- Nothing here edits the rig. Evaluation runs in a throwaway copy; promotion is the owner's `git apply`
  and commit (the rig's update mechanism); rollback is the reverse patch, checked during evaluation.
"""
from __future__ import annotations

import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Optional, Tuple

from factory_rig.canon import atomic_write, sha, sha_file

from . import SKILL_DIR

IMP_DIR = os.path.join(SKILL_DIR, "improvement")
EVIDENCE_DIR = os.path.join(SKILL_DIR, "evidence", "integration", "improvement")
FOUNDATION_TESTS = ["test_guards", "test_handoff", "test_registry", "test_workflow"]
STAGES = ("observed", "reproduced", "evaluated", "reviewed", "promoted")


class ImprovementError(Exception):
    pass


def _read(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def load(rid: str) -> Dict[str, Any]:
    path = os.path.join(IMP_DIR, "records", rid + ".json")
    if not os.path.isfile(path):
        raise ImprovementError("no improvement record %s" % rid)
    return _read(path)


def criteria(rec: Dict[str, Any]) -> Dict[str, Any]:
    """What the pin covers: the case file's bytes, the pass thresholds, and the selector that computes the
    regression set, so narrowing it to dodge a failing case also breaks the pin."""
    return {"cases_sha256": sha_file(os.path.join(SKILL_DIR, rec["criteria"]["cases"])),
            "thresholds": rec["criteria"]["thresholds"], "regression_selector": rec["change"]["exercised_by"]}


def pin(rid: str) -> Dict[str, Any]:
    rec = load(rid)
    path = os.path.join(IMP_DIR, "pins", rid + ".json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    body = {"record": rid, "criteria": criteria(rec), "criteria_sha256": sha(criteria(rec))}
    try:
        with open(path, "x", encoding="utf-8") as fh:
            fh.write(json.dumps(body, indent=2, sort_keys=True) + "\n")
        return dict(body, status="pinned")
    except FileExistsError:
        old = _read(path)
        same = old["criteria_sha256"] == body["criteria_sha256"]
        return dict(old, status="already-pinned" if same else "refused",
                    **({} if same else {"error": "criteria changed after pinning; open a new record instead"}))


def pinned(rid: str) -> Optional[Dict[str, Any]]:
    path = os.path.join(IMP_DIR, "pins", rid + ".json")
    return _read(path) if os.path.isfile(path) else None


# ---- sandbox and cases -------------------------------------------------------------------------------

def _sandbox(skills_root: str, target_skill: str) -> str:
    """A skills root in a temp dir: every skill symlinked except the target, which is copied."""
    tmp = tempfile.mkdtemp(prefix="fleet-improve-")
    root = os.path.join(tmp, "skills")
    os.makedirs(root)
    for name in os.listdir(skills_root):
        src = os.path.join(skills_root, name)
        if name == target_skill:
            shutil.copytree(src, os.path.join(root, name), symlinks=True,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        elif not name.startswith("."):
            os.symlink(src, os.path.join(root, name))
    return root


def _scan_case(case: Dict[str, Any], skill: str) -> Dict[str, Any]:
    proc = subprocess.run([os.path.join(skill, "bin", "fleet"), "scan", os.path.join(skill, case["file"])],
                          capture_output=True, text=True, cwd=skill, timeout=120)
    got = sorted([f["line"], f["category"]] for f in json.loads(proc.stdout)["findings"]) if proc.returncode == 0 else None
    want = sorted(case["expect"])
    return {"id": case["id"], "pass": got == want, "expected": want, "got": got, "exit": proc.returncode}


def _argv_case(case: Dict[str, Any], skill: str) -> Dict[str, Any]:
    proc = subprocess.run(case["argv"], capture_output=True, text=True, cwd=os.path.join(skill, case.get("cwd", ".")), timeout=900)
    return {"id": case["id"], "pass": proc.returncode == 0, "exit": proc.returncode,
            "tail": (proc.stdout + proc.stderr)[-1500:]}


def _run_case(case: Dict[str, Any], skill: str) -> Dict[str, Any]:
    return _scan_case(case, skill) if case["kind"] == "scan" else _argv_case(case, skill)


def regression_cases(rec: Dict[str, Any], fleets: str) -> List[Dict[str, Any]]:
    """The foundation tests plus every fleet script eval (under `fleets`) whose command uses the changed capability."""
    cases = [{"id": "foundation:" + m, "kind": "argv", "cwd": "scripts/tests",
              "argv": [sys.executable, "-W", "ignore", "-m", "unittest", m]} for m in FOUNDATION_TESTS]
    needle = rec["change"]["exercised_by"]
    for f in sorted(os.listdir(fleets)):
        path = os.path.join(fleets, f, "evals.json")
        if not os.path.isfile(path):
            continue
        for e in _read(path)["evals"]:
            argv = e["check"].get("argv")
            if e["check"]["method"] == "script" and argv and any(n in " ".join(argv) for n in needle):
                cases.append({"id": e["id"], "kind": "argv", "argv": argv})
    return cases


def _patch(root: str, patch: str, reverse: bool = False) -> subprocess.CompletedProcess:
    return subprocess.run(["patch", "-p1", "--forward" if not reverse else "-R", "-d", root, "-i", patch],
                          capture_output=True, text=True, timeout=60)


def evaluate(rid: str, skills_root: str) -> Dict[str, Any]:
    rec = load(rid)
    pin_rec = pinned(rid)
    if pin_rec is None:
        raise ImprovementError("%s has no pinned criteria; run `fleet improve pin %s` before evaluating" % (rid, rid))
    if pin_rec["criteria_sha256"] != sha(criteria(rec)):
        raise ImprovementError("%s criteria changed after pinning (pinned %s, now %s); a worker cannot rewrite its own criteria"
                               % (rid, pin_rec["criteria_sha256"][:12], sha(criteria(rec))[:12]))
    target = os.path.join(skills_root, rec["change"]["target"])
    if sha_file(target) != rec["change"]["target_sha256"]:
        raise ImprovementError("%s target %s moved since the proposal; re-propose against the current file" % (rid, rec["change"]["target"]))
    cases = _read(os.path.join(SKILL_DIR, rec["criteria"]["cases"]))
    skill_name = rec["change"]["target"].split("/", 1)[0]
    root = _sandbox(skills_root, skill_name)
    skill = os.path.join(root, skill_name)
    regression = regression_cases(rec, os.path.join(skill, "fleets"))
    patch = os.path.join(SKILL_DIR, rec["change"]["patch"])
    base = {k: [_run_case(c, skill) for c in cases[k]] for k in ("original", "fresh")}
    base["regression"] = [_run_case(c, skill) for c in regression]
    applied = _patch(root, patch)
    patched_sha = sha_file(os.path.join(root, rec["change"]["target"]))
    after = {k: [_run_case(c, skill) for c in cases[k]] for k in ("original", "fresh")} if applied.returncode == 0 else {}
    if applied.returncode == 0:
        after["regression"] = [_run_case(c, skill) for c in regression]
    reverted = _patch(root, patch, reverse=True)
    rollback_ok = reverted.returncode == 0 and sha_file(os.path.join(root, rec["change"]["target"])) == rec["change"]["target_sha256"]
    th = rec["criteria"]["thresholds"]
    reproduced = all(not r["pass"] for r in base["original"])
    base_ok = {r["id"] for r in base["regression"] if r["pass"]}
    regressions = [r["id"] for r in after.get("regression", []) if r["id"] in base_ok and not r["pass"]]
    fresh_pass = sum(r["pass"] for r in after.get("fresh", []))
    checks = {
        "observation reproduced on the unpatched copy": reproduced,
        "patch applies": applied.returncode == 0,
        "original failure passes after the patch": bool(after) and all(r["pass"] for r in after["original"]),
        "fresh cases pass (%d of %d, need %d)" % (fresh_pass, len(cases["fresh"]), th["min_fresh_pass"]): fresh_pass >= th["min_fresh_pass"],
        "no regression among %d cases that passed before" % len(base_ok): bool(after) and not regressions,
        "reverse patch restores the base file": rollback_ok,
    }
    result = {"record": rid, "run_on": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
              "criteria_sha256": pin_rec["criteria_sha256"], "target": rec["change"]["target"],
              "target_sha256": rec["change"]["target_sha256"], "patched_sha256": patched_sha,
              "patch_sha256": sha_file(patch), "checks": checks, "verdict": "pass" if all(checks.values()) else "fail",
              "regressions": regressions, "pre_existing_failures": [r["id"] for r in base["regression"] if not r["pass"]],
              "base": base, "patched": after, "sandbox": root,
              "label": "Cases are synthetic Fixture Co text; the fresh cases were written by the proposing agent before the patch."}
    out = os.path.join(EVIDENCE_DIR, rid, "evaluation.json")
    atomic_write(out, json.dumps(result, indent=2, sort_keys=True) + "\n")
    return result


def monitor(rid: str, skills_root: str) -> Dict[str, Any]:
    """Run the original failure against the installed skill. Recurring until the change is promoted."""
    rec = load(rid)
    cases = _read(os.path.join(SKILL_DIR, rec["criteria"]["cases"]))
    skill = os.path.join(skills_root, rec["change"]["target"].split("/", 1)[0])
    runs = [_run_case(c, skill) for c in cases["original"]]
    target_sha = sha_file(os.path.join(skills_root, rec["change"]["target"]))
    entry = {"run_on": datetime.datetime.now().astimezone().isoformat(timespec="seconds"), "recurred": not all(r["pass"] for r in runs),
             "installed_target_sha256": target_sha, "cases": runs}
    path = os.path.join(EVIDENCE_DIR, rid, "monitor.jsonl")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry, sort_keys=True) + "\n")
    return entry


def gate(rid: str, skills_root: str) -> Dict[str, Any]:
    """The furthest stage the record has earned, and every reason it can't go further."""
    rec = load(rid)
    reasons: List[str] = []
    pin_rec = pinned(rid)
    ev_path = os.path.join(EVIDENCE_DIR, rid, "evaluation.json")
    ev = _read(ev_path) if os.path.isfile(ev_path) else None
    stage = "observed"
    if pin_rec is None:
        reasons.append("criteria are not pinned")
    elif pin_rec["criteria_sha256"] != sha(criteria(rec)):
        reasons.append("criteria changed after pinning")
    if ev is None:
        reasons.append("no evaluation on record: one unverified observation cannot change a skill")
    else:
        if not ev["checks"].get("observation reproduced on the unpatched copy"):
            reasons.append("the original failure did not reproduce: unverified observation")
        else:
            stage = "reproduced"
        if pin_rec and ev["criteria_sha256"] != pin_rec["criteria_sha256"]:
            reasons.append("evaluation ran against different criteria than the pin")
        if ev["patch_sha256"] != sha_file(os.path.join(SKILL_DIR, rec["change"]["patch"])):
            reasons.append("the patch changed after evaluation")
        if ev["verdict"] != "pass":
            reasons.append("evaluation verdict is %s: %s" % (ev["verdict"], [k for k, v in ev["checks"].items() if not v]))
        elif stage == "reproduced" and not reasons:
            stage = "evaluated"
    review = rec.get("review") or {}
    if not review.get("reviewer"):
        reasons.append("no review: a principal other than %s must review the patch and evaluation" % rec["change"]["proposed_by"])
    elif review["reviewer"] == rec["change"]["proposed_by"]:
        reasons.append("the proposer cannot review its own change")
    elif review.get("verdict") != "approve":
        reasons.append("review verdict is %s" % review.get("verdict"))
    elif stage == "evaluated":
        stage = "reviewed"
    installed = sha_file(os.path.join(skills_root, rec["change"]["target"]))
    promoted = ev is not None and installed == ev["patched_sha256"]
    commit = (rec.get("promotion") or {}).get("commit")
    if stage == "reviewed" and promoted and commit:
        stage = "promoted"
    elif stage == "reviewed":
        reasons.append("not promoted: the owner applies the patch and commits it (%s)" % rec["promotion"]["command"])
    return {"record": rid, "stage": stage, "promotable": stage == "reviewed", "reasons": reasons,
            "installed_target_sha256": installed, "installed_is_patched": promoted}
