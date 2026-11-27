"""Dispatch, completion and reconciliation: the trusted integration path.

Order of side effects in dispatch (each step is recoverable from the previous):
  lease -> tracker contract (yysun start-agent) -> Noodle enqueue -> attempt record
If enqueue fails after the tracker started the task, a blocked manifest records that through the
tracker's own supported transition and the lease is released; nothing is left half-owned.
"""
from __future__ import annotations

import datetime
import json
import os
import subprocess
import uuid
from typing import Any, Dict, List, Optional

from . import gate, noodle_control, yysun
from .canon import read_json
from .contract import contract_hash, frontier, load_contracts, load_tasks
from .lease import LeaseStore, StaleEpoch
from .receipts import ReceiptStore, idempotency_key

PENDING_ONLY = ("no independent review record",)
REQUIRED_NOODLE_SKILLS = ("factory-execute",)


def utcnow() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


class Workspace:
    def __init__(self, root: str):
        self.root = os.path.abspath(root)
        self.rig_dir = os.path.join(self.root, ".factory-rig")
        cfg = read_json(os.path.join(self.rig_dir, "config.json"))
        if cfg is None:
            raise FileNotFoundError("no .factory-rig/config.json under %s" % self.root)
        self.cfg = cfg
        self.repo = os.path.join(self.root, cfg["repo_dir"])
        self.project = os.path.join(self.root, cfg["project"])
        self.specs_dir = os.path.join(self.root, cfg.get("specs_dir", "specs"))
        self.integration = cfg.get("integration_branch", "main")
        self.skill_dir = os.path.expanduser(cfg["yysun_skill_dir"])
        self.state_root = os.path.join(self.root, cfg.get("state_root", ".factory-rig/state"))
        self.noodle_runtime = os.path.join(self.repo, cfg.get("noodle_runtime", ".noodle"))
        self.leases = LeaseStore(os.path.join(self.state_root, "leases"))
        self.receipts = ReceiptStore(os.path.join(self.state_root, "receipts"))
        self.attempts_path = os.path.join(self.rig_dir, "attempts.jsonl")

    def attempts(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.attempts_path):
            return []
        with open(self.attempts_path, "r", encoding="utf-8") as fh:
            return [json.loads(l) for l in fh if l.strip()]

    def record_attempt(self, rec: Dict[str, Any]) -> None:
        with open(self.attempts_path, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")

    def attempt(self, attempt_id: str) -> Dict[str, Any]:
        found = [a for a in self.attempts() if a["attempt_id"] == attempt_id and a.get("event") == "dispatched"]
        if not found:
            raise KeyError("unknown attempt %s" % attempt_id)
        return found[-1]


def noodle_skill_paths(ws: Workspace) -> List[str]:
    """skills.paths from .noodle.toml (default ['.agents/skills']), expanded like Noodle does."""
    import re
    try:
        with open(os.path.join(ws.repo, ".noodle.toml"), "r", encoding="utf-8") as fh:
            text = fh.read()
    except FileNotFoundError:
        return [os.path.join(ws.repo, ".agents/skills")]
    sec = re.search(r"^\[skills\]\s*\n(.*?)(?=^\[|\Z)", text, re.S | re.M)
    m = re.search(r"paths\s*=\s*\[(.*?)\]", sec.group(1), re.S) if sec else None
    raw = re.findall(r'"([^"]+)"', m.group(1)) if m else [".agents/skills"]
    return [os.path.expanduser(p) if p.startswith("~") else os.path.join(ws.repo, p) for p in raw]


def noodle_has_skills(ws: Workspace, noodle_bin: Optional[str] = None, required=REQUIRED_NOODLE_SKILLS) -> List[str]:
    """Required skills Noodle's Resolve() cannot find (override NOODLE-SKILL-RESOLUTION).

    `noodle skills list` skips symlinked skill directories (DirEntry.IsDir is false for symlinks)
    while Resolve() follows them, so listing output cannot be trusted for rig mount links. This mirrors
    Resolve(): first search path holding <name>/SKILL.md wins, symlinks followed.
    """
    from . import noodle_setup
    missing = list(noodle_setup.drift(ws.repo))
    for name in required:
        if not any(os.path.isfile(os.path.join(p, name, "SKILL.md")) for p in noodle_skill_paths(ws)):
            missing.append(name)
    missing = [m for m in dict.fromkeys(missing)]
    return missing


def codex_model_problem(model: str, cache_path: Optional[str] = None) -> Optional[str]:
    """Reason a Codex model slug is unusable for this account, from Codex's own models cache (no provider call)."""
    path = cache_path or os.path.join(os.environ.get("CODEX_HOME") or os.path.expanduser("~/.codex"), "models_cache.json")
    data = read_json(path)
    if data is None:
        return None  # no cache: cannot judge, let the provider answer
    models = data.get("models", data) if isinstance(data, dict) else data
    listed = {m.get("slug"): m.get("visibility") for m in models if isinstance(m, dict)}
    if model not in listed:
        return "model %r is not in Codex's accessible catalog (available: %s)" % (model, ", ".join(sorted(k for k, v in listed.items() if v == "list")))
    return None


def build_prompt(contract: Dict[str, Any], chash: str, attempt_id: str, contract_id: str, base_sha: str) -> str:
    return "\n".join([
        "Use the factory-execute skill. You are the implementation worker for ONE bounded contract.",
        "",
        "task_id: %s" % contract["task_id"],
        "attempt_id: %s" % attempt_id,
        "tracker_contract_id: %s" % contract_id,
        "rig_contract_hash: %s" % chash,
        "base_sha: %s" % base_sha,
        "title: %s" % contract["title"],
        "spec: %s revision %s (sha256 %s)" % (contract["spec"]["id"], contract["spec"]["revision"], contract["spec"]["sha256"]),
        "",
        "Acceptance criteria (exact strings):",
    ] + ["- %s" % a for a in contract["acceptance"]] + [
        "",
        "Verify command (argv, run it before you finish): %s" % json.dumps(contract["verify"]["argv"]),
        "",
        "Commit your work on the current branch in this worktree. Do not merge, push, close tasks,",
        "claim other work, or start another orchestration loop. Reply with the candidate commit sha and",
        "the proof line from the factory-execute skill.",
    ])


def dispatch(ws: Workspace, task_id: str, backend: str, owner_pid: int, noodle_bin: Optional[str] = None,
             provider: str = "codex", model: str = "", ttl: float = 900.0) -> Dict[str, Any]:
    tasks = load_tasks(ws.project)
    contracts = load_contracts(ws.rig_dir)
    eligible, rejected = frontier(tasks, contracts, ws.specs_dir, backend)
    if task_id not in eligible:
        return {"ok": False, "stage": "frontier", "reasons": rejected.get(task_id, ["unknown task"])}
    c = contracts[task_id]
    chash = contract_hash(c)
    if backend == "noodle":
        missing = noodle_has_skills(ws)
        if missing:
            return {"ok": False, "stage": "preflight", "reasons": ["Noodle skill preflight failed: " + "; ".join(missing)]}
        if owner_pid <= 0:
            return {"ok": False, "stage": "preflight", "reasons": ["owner pid is required so lease liveness tracks the real backend"]}
    from .lease import process_fingerprint
    if process_fingerprint(owner_pid) is None:
        return {"ok": False, "stage": "preflight", "reasons": ["owner pid %d is not running" % owner_pid]}
    if provider == "codex" and model:
        problem = codex_model_problem(model)
        if problem:
            return {"ok": False, "stage": "preflight", "reasons": [problem]}
    attempt_id = "A" + uuid.uuid4().hex[:8]
    base_sha = gate.git(ws.repo, "rev-parse", ws.integration)
    from .lease import LeaseDenied
    try:
        lease = ws.leases.acquire(c["repo"], task_id, chash, backend, attempt_id, ws.repo, owner_pid, ttl=ttl)
    except LeaseDenied as exc:
        return {"ok": False, "stage": "lease", "reasons": [exc.reason], "holder": exc.holder}
    try:
        started = yysun.start_agent(ws.skill_dir, ws.project, task_id)
    except yysun.YysunError as exc:
        ws.leases.release(c["repo"], task_id, lease["epoch"], "tracker-start-failed")
        return {"ok": False, "stage": "tracker", "reasons": [str(exc)]}
    order_id = "%s-%s" % (task_id.lower(), attempt_id.lower())
    try:
        cmd_id = noodle_control.send(ws.noodle_runtime, {
            "action": "enqueue", "order_id": order_id, "task_key": "factory-execute", "skill": "factory-execute",
            "provider": provider, "model": model,
            "prompt": build_prompt(c, chash, attempt_id, started["contract_id"], base_sha),
        })
    except Exception as exc:
        block_task(ws, task_id, c, "dispatch failed before enqueue: %s" % exc)
        ws.leases.release(c["repo"], task_id, lease["epoch"], "enqueue-failed")
        return {"ok": False, "stage": "enqueue", "reasons": [str(exc)]}
    rec = {"event": "dispatched", "attempt_id": attempt_id, "task_id": task_id, "backend": backend,
           "contract_hash": chash, "tracker_contract_id": started["contract_id"], "base_sha": base_sha,
           "epoch": lease["epoch"], "order_id": order_id, "control_id": cmd_id, "provider": provider, "at": utcnow()}
    ws.record_attempt(rec)
    return {"ok": True, "attempt": rec}


def block_task(ws: Workspace, task_id: str, c: Dict[str, Any], blocker: str) -> None:
    ac = yysun.active_contract(ws.project, task_id)
    pid = yysun.project_id(ws.project)
    manifest = {
        "schema_version": 1, "sequence": 1, "contract_id": ac["contract_id"], "project": {"id": pid},
        "task": {"id": task_id, "spec_sha256": ac["spec_sha256"]}, "status": "blocked", "blocker": blocker,
        "evidence": [], "acceptance_evidence": {a: [] for a in ac["acceptance"]}, "sources": [],
        "observed_at": utcnow(), "notes": [],
    }
    yysun.ingest(ws.skill_dir, ws.project, task_id, manifest)


def worktree_for(ws: Workspace, attempt: Dict[str, Any], override: Optional[str] = None) -> str:
    if override:
        return override
    for item in noodle_control.pending_review(ws.noodle_runtime):
        if item.get("order_id") == attempt["order_id"]:
            return item["worktree_path"]
    raise gate.GateError("no pending-review worktree for order %s" % attempt["order_id"])


def context(ws: Workspace, attempt: Dict[str, Any], worktree: str) -> Dict[str, Any]:
    c = load_contracts(ws.rig_dir)[attempt["task_id"]]
    return {"contract": c, "epoch": attempt["epoch"], "attempt_id": attempt["attempt_id"], "specs_dir": ws.specs_dir,
            "repo": ws.repo, "worktree": worktree, "integration_branch": ws.integration, "base_sha": attempt["base_sha"],
            "rig_dir": ws.rig_dir}


def complete(ws: Workspace, attempt_id: str, worktree: Optional[str] = None, close_noodle: bool = True) -> Dict[str, Any]:
    attempt = ws.attempt(attempt_id)
    prior = ws.receipts.find_attempt(attempt_id)
    if prior is not None and prior["step"] == "complete":
        return {"ok": True, "state": "already-complete", "receipt": prior["key"]}
    if prior is not None and prior["step"] == "intent":
        landed = subprocess.run(["git", "-C", ws.repo, "merge-base", "--is-ancestor", prior["data"]["candidate_sha"], ws.integration],
                                capture_output=True).returncode == 0
        if landed:
            ws.receipts.advance(prior["key"], "integrated", {"observed": "candidate already on integration branch"})
            prior = ws.receipts.get(prior["key"])
        else:
            prior = None  # crashed before integration: re-run the gate; begin() keeps the same receipt
    if prior is not None:
        return _finish(ws, attempt, prior["key"], prior["data"], close_noodle)  # resume: approval already spent
    wt = worktree_for(ws, attempt, worktree)
    ctx = context(ws, attempt, wt)
    c = ctx["contract"]
    verdict = gate.check(ctx, ws.leases)
    if not verdict["ok"]:
        pending = all(r in PENDING_ONLY for r in verdict["reasons"])
        if pending:
            return {"ok": False, "state": "awaiting-review", "reasons": verdict["reasons"]}
        # Failed acceptance: record it through the tracker's own transition, leave the candidate unmerged.
        try:
            block_task(ws, c["task_id"], c, "gate rejected candidate: " + "; ".join(verdict["reasons"])[:600])
        except Exception as exc:
            verdict["reasons"].append("could not record blocked state: %s" % exc)
        try:
            ws.leases.release(c["repo"], c["task_id"], attempt["epoch"], "gate-rejected")
        except StaleEpoch:
            pass
        return {"ok": False, "state": "rejected", "reasons": verdict["reasons"]}
    facts = verdict["facts"]
    key = idempotency_key(c["task_id"], attempt_id, facts["contract_hash"], facts["candidate_sha"])
    data = {"task_id": c["task_id"], "attempt_id": attempt_id, "candidate_sha": facts["candidate_sha"],
            "candidate_tree": facts["candidate_tree"], "base_sha": facts["base_sha"],
            "contract_hash": facts["contract_hash"], "repo": c["repo"], "epoch": attempt["epoch"],
            "order_id": attempt["order_id"], "verify_log": facts["verify"]["log"],
            "review_file": facts["review_file"], "reviewer": (facts.get("reviewer") or {}).get("provider"),
            "verify_argv": c["verify"]["argv"]}
    ws.receipts.begin(key, data)  # intent is durable before the first side effect
    out = gate.integrate(ctx, facts)
    ws.receipts.advance(key, "integrated", out)
    return _finish(ws, attempt, key, data, close_noodle)


def _finish(ws: Workspace, attempt: Dict[str, Any], key: str, data: Dict[str, Any], close_noodle: bool) -> Dict[str, Any]:
    """Steps after integration; safe to re-enter from any receipt state."""
    rec = ws.receipts.get(key)
    c = load_contracts(ws.rig_dir)[data["task_id"]]
    if rec["step"] == "intent":
        # Intent recorded but integration unconfirmed: only reconcile may advance it (it checks git).
        return {"ok": False, "state": "intent-unconfirmed", "receipt": key,
                "reasons": ["receipt at intent; run reconcile to learn whether the merge happened"]}
    if rec["step"] == "integrated":
        ac = yysun.active_contract(ws.project, c["task_id"])
        m = yysun.build_manifest(
            yysun.project_id(ws.project), c["task_id"], ac, 1, utcnow(), data["candidate_sha"],
            " ".join(data["verify_argv"]), "exit 0 in a fresh checkout of the candidate", data["verify_log"],
            "independent review by %s" % data.get("reviewer"), "approve", data["review_file"])
        out = yysun.ingest(ws.skill_dir, ws.project, c["task_id"], m)
        ws.receipts.advance(key, "state_recorded", {"manifest_id": out["manifest_id"], "tracker_status": out["status"]})
        rec = ws.receipts.get(key)
    noodle_ack = None
    if close_noodle and rec["step"] == "state_recorded":
        try:
            cid = noodle_control.send(ws.noodle_runtime, {"action": "merge", "order_id": attempt["order_id"]})
            noodle_ack = noodle_control.wait_ack(ws.noodle_runtime, cid, timeout=30)
        except Exception as exc:
            noodle_ack = {"status": "unsent", "message": str(exc)}
    if rec["step"] == "state_recorded":
        try:
            ws.leases.release(c["repo"], c["task_id"], attempt["epoch"], "complete")
        except StaleEpoch:
            pass
        ws.receipts.advance(key, "complete", {"noodle_ack": noodle_ack})
    return {"ok": True, "state": "complete", "receipt": key, "candidate_sha": data["candidate_sha"], "noodle_ack": noodle_ack}


def abandon(ws: Workspace, attempt_id: str, why: str) -> Dict[str, Any]:
    """Router-side recovery for an attempt whose worker failed or was stopped.

    Records the failure through the tracker's own blocked transition (task stays incomplete, retryable with
    the tracker's --retry-blocker), releases the lease, and leaves any worktree and branch untouched so
    side effects stay visible. It does not merge and does not delete anything.
    """
    attempt = ws.attempt(attempt_id)
    c = load_contracts(ws.rig_dir)[attempt["task_id"]]
    block_task(ws, attempt["task_id"], c, "attempt %s abandoned: %s" % (attempt_id, why))
    try:
        ws.leases.release(c["repo"], attempt["task_id"], attempt["epoch"], "abandoned")
    except StaleEpoch:
        pass
    ws.record_attempt({"event": "abandoned", "attempt_id": attempt_id, "task_id": attempt["task_id"], "why": why, "at": utcnow()})
    return {"ok": True, "state": "abandoned", "attempt": attempt_id}


def reconcile(ws: Workspace) -> Dict[str, Any]:
    def integrated(data: Dict[str, Any]) -> bool:
        r = subprocess.run(["git", "-C", ws.repo, "merge-base", "--is-ancestor", data["candidate_sha"], ws.integration], capture_output=True)
        return r.returncode == 0

    def state_done(data: Dict[str, Any]) -> bool:
        return yysun.task_status(ws.project, data["task_id"]) == "done"

    def finish(data: Dict[str, Any]) -> None:
        try:
            ws.leases.release(data["repo"], data["task_id"], data["epoch"], "complete")
        except StaleEpoch:
            pass

    report = ws.receipts.reconcile(integrated, state_done, finish)
    unresolved = [r for r in report if r["step"] != "complete"]
    return {"receipts": report, "unresolved": unresolved}
