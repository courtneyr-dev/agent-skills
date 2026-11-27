"""Premerge acceptance gate: the only path that lands a candidate on the integration branch.

Inputs are facts the gate recomputes, never claims a worker made:
  - the candidate is the worktree HEAD commit and the worktree is clean
  - the integration branch still sits at the base the attempt started from
  - the verify command (argv list from the contract) passes in a fresh detached checkout of the candidate
  - an independent review record names this task, attempt, contract hash, candidate and base, and
    the reviewer's provider differs from the implementer's
  - the specification is still accepted at the contract's revision and bytes
  - the lease epoch presented is the current active one
Anything that changes after approval (new commit, rebased base, edited contract or spec) fails the
corresponding check because each is compared at merge time, not copied from the approval.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from typing import Any, Dict, List, Optional

from .canon import sha_file
from .contract import contract_hash, load_spec, validate_contract


class GateError(Exception):
    pass


def git(repo: str, *args: str, check: bool = True) -> str:
    p = subprocess.run(["git", "-C", repo] + list(args), capture_output=True, text=True, timeout=120)
    if check and p.returncode != 0:
        raise GateError("git %s failed: %s" % (" ".join(args), p.stderr.strip()[:300]))
    return p.stdout.strip()


def review_path(rig_dir: str, task_id: str, attempt_id: str) -> str:
    return os.path.join(rig_dir, "reviews", task_id, attempt_id + ".json")


def evidence_dir(rig_dir: str, task_id: str, attempt_id: str) -> str:
    return os.path.join(rig_dir, "evidence", task_id, attempt_id)


def write_review(rig_dir: str, record: Dict[str, Any]) -> str:
    required = {"task_id", "attempt_id", "contract_hash", "candidate_sha", "base_sha", "verdict", "reviewer", "implementer", "findings"}
    missing = required - set(record)
    if missing:
        raise GateError("review record missing: " + ", ".join(sorted(missing)))
    path = review_path(rig_dir, record["task_id"], record["attempt_id"])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    rec = dict(record)
    rec.setdefault("at", time.time())
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(rec, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return path


def run_verify(repo: str, candidate_sha: str, argv: List[str], log_path: str, timeout: int = 600) -> Dict[str, Any]:
    """Run the contract's verify argv in a fresh detached worktree of the candidate."""
    tmp = tempfile.mkdtemp(prefix="frig-verify-")
    wt = os.path.join(tmp, "checkout")
    try:
        git(repo, "worktree", "add", "--detach", wt, candidate_sha)
        os.makedirs(os.path.dirname(log_path), exist_ok=True)
        p = subprocess.run(argv, cwd=wt, capture_output=True, text=True, timeout=timeout)
        with open(log_path, "w", encoding="utf-8") as fh:
            fh.write("$ %s\n(exit %d)\n--- stdout\n%s\n--- stderr\n%s\n" % (" ".join(argv), p.returncode, p.stdout, p.stderr))
        return {"exit": p.returncode, "log": log_path, "log_sha256": sha_file(log_path)}
    finally:
        subprocess.run(["git", "-C", repo, "worktree", "remove", "--force", wt], capture_output=True)
        shutil.rmtree(tmp, ignore_errors=True)


def check(ctx: Dict[str, Any], leases, now: Optional[float] = None) -> Dict[str, Any]:
    """Evaluate every acceptance condition. Returns {ok, reasons, facts}. Never mutates the repo."""
    reasons: List[str] = []
    facts: Dict[str, Any] = {}
    c = ctx["contract"]
    errs = validate_contract(c)
    if errs:
        return {"ok": False, "reasons": ["contract invalid: " + "; ".join(errs)], "facts": {}}
    chash = contract_hash(c)
    facts["contract_hash"] = chash
    try:
        lease = leases.assert_current(c["repo"], c["task_id"], ctx["epoch"])
        if lease["contract_hash"] != chash:
            reasons.append("contract changed since dispatch (lease %s, now %s)" % (lease["contract_hash"][:12], chash[:12]))
        if lease["attempt_id"] != ctx["attempt_id"]:
            reasons.append("attempt id does not match the lease")
    except Exception as exc:
        reasons.append("lease: %s" % exc)

    spec = load_spec(ctx["specs_dir"], c["spec"]["id"])
    if spec is None or spec.get("status") != "accepted":
        reasons.append("specification is not accepted")
    elif str(spec.get("revision")) != c["spec"]["revision"] or spec["_sha256"] != c["spec"]["sha256"]:
        reasons.append("specification changed after the contract was written")

    repo, wt = ctx["repo"], ctx["worktree"]
    integ = ctx["integration_branch"]
    try:
        cand = git(wt, "rev-parse", "HEAD")
        facts["candidate_sha"] = cand
        facts["candidate_tree"] = git(wt, "rev-parse", "HEAD^{tree}")
        if git(wt, "status", "--porcelain"):
            reasons.append("candidate worktree has uncommitted changes")
        base = ctx["base_sha"]
        facts["base_sha"] = base
        if git(repo, "rev-parse", integ) != base:
            reasons.append("integration branch moved since the attempt started; approvals are void")
        anc =subprocess.run(["git", "-C", repo, "merge-base", "--is-ancestor", base, cand], capture_output=True)
        if anc.returncode != 0:
            reasons.append("candidate does not descend from the recorded base")
        if cand == base:
            reasons.append("candidate has no commits beyond the base")
    except GateError as exc:
        reasons.append(str(exc))
        return {"ok": False, "reasons": reasons, "facts": facts}

    ev = evidence_dir(ctx["rig_dir"], c["task_id"], ctx["attempt_id"])
    vr = run_verify(repo, cand, c["verify"]["argv"], os.path.join(ev, "verify.log"))
    facts["verify"] = vr
    if vr["exit"] != 0:
        reasons.append("verify command exited %d" % vr["exit"])

    rp = review_path(ctx["rig_dir"], c["task_id"], ctx["attempt_id"])
    if not os.path.isfile(rp):
        reasons.append("no independent review record")
    else:
        with open(rp, "r", encoding="utf-8") as fh:
            rv = json.load(fh)
        facts["review_file"] = rp
        facts["review_sha256"] = sha_file(rp)
        for key, want in (("task_id", c["task_id"]), ("attempt_id", ctx["attempt_id"]), ("contract_hash", chash),
                          ("candidate_sha", facts.get("candidate_sha")), ("base_sha", ctx["base_sha"])):
            if rv.get(key) != want:
                reasons.append("review %s %r does not match %r" % (key, rv.get(key), want))
        if rv.get("verdict") != "approve":
            reasons.append("review verdict is %r" % rv.get("verdict"))
        if rv.get("reviewer", {}).get("provider") == rv.get("implementer", {}).get("provider"):
            reasons.append("reviewer is not independent of the implementer (same provider)")
        facts["reviewer"] = rv.get("reviewer")
    return {"ok": not reasons, "reasons": reasons, "facts": facts}


def integrate(ctx: Dict[str, Any], facts: Dict[str, Any]) -> Dict[str, Any]:
    """Fast-forward the integration branch to exactly the reviewed candidate, then prove tree equality."""
    repo, integ = ctx["repo"], ctx["integration_branch"]
    if git(repo, "rev-parse", integ) != facts["base_sha"]:
        raise GateError("integration branch moved; refusing to integrate")
    if git(repo, "symbolic-ref", "--short", "HEAD") != integ:
        raise GateError("repo checkout is not on %s" % integ)
    if git(repo, "status", "--porcelain"):
        raise GateError("integration checkout is dirty")
    git(repo, "merge", "--ff-only", facts["candidate_sha"])
    head = git(repo, "rev-parse", "HEAD")
    tree = git(repo, "rev-parse", "HEAD^{tree}")
    if head != facts["candidate_sha"] or tree != facts["candidate_tree"]:
        raise GateError("integrated result differs from the reviewed candidate")
    return {"integrated_sha": head, "integrated_tree": tree}
