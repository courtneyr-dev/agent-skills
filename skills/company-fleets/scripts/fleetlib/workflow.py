"""Cross-fleet workflow templates (prompt 2, section 12): check a template, route it, run its handoff chain.

A template (workflows/<id>.json) lists steps. Each routed step becomes one handoff.v1 from its producer
to the next routed step's producer. run() claims the template's home workload with the one coordinator
lease (factory-rig, through ownerlog.open_ledger, which records the claim in the run's owner log), then for
each step: records the handoff's owner fields in that log (`open`, which also writes opened/), lets a tool
write outputs and evidence, applies only worker fields (guarded_update scans untrusted sources and refuses
protected fields), submits, and reconciles through the foundation gate. The chain stops at the first step
that is not accepted. Resume and verify compare each handoff with the owner log, not with opened/.

Routing: a step with `when` runs only when the fixture's `needs` lists that tag, and a fleet is read only
when a routed step or the home workload names it. A step with `boundary: human-data` never runs here:
the chain stops there and says what a person must supply.

Tools: a fixture binds a step to real commands (`tools.<step>`); an unbound step gets the fake tool,
which writes a labeled synthetic artifact and a fake check. The CLI's `--tools fake` ignores bindings.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from typing import Any, Dict, List, Optional, Tuple

from factory_rig.canon import atomic_write, sha, sha_file
from factory_rig.contract import contract_hash, validate_contract
from factory_rig.lease import LeaseDenied, LeaseStore, StaleEpoch

from . import SKILL_DIR, ownerlog
from .handoff import Ledger, gate_errors, open_handoff, validate_handoff
from .ownership import ClaimRefused, release
from .registry import FLEETS, PROFILES, Registry, fleet_file, fleet_of
from .untrusted import describe_source, guarded_update

WORKFLOW_DIR = os.path.join(SKILL_DIR, "workflows")
STEP_KEYS = {"id", "stage", "producer", "reviewer", "acceptance_owner", "outcome", "acceptance_criteria",
             "readiness_criteria", "artifact", "skills", "when", "boundary", "authority", "scope"}
WORKFLOW_KEYS = {"schema_version", "id", "code", "name", "source", "profile", "coordinator", "home_workload",
                 "outcome", "final_consumer", "stop_conditions", "cancellation", "steps"}
DEFAULT_AUTHORITY = {"mutation": "staged", "external_actions": "none", "publication": "none"}
PLACEHOLDER_FIXTURE = {"instance": "CHECK", "tenant_id": "fixture-co", "client_id": None, "exclusions": [],
                       "sources": [{"ref": "workflow check", "revision": "static"}],
                       "data": {"classification": "internal", "allowed_destinations": ["tenant:fixture-co", "rig:evidence"]},
                       "budget": {"max_minutes": 30, "max_retries": 1}}


class WorkflowError(Exception):
    pass


def workflow_path(wid: str) -> str:
    return os.path.join(WORKFLOW_DIR, wid + ".json")


def list_workflows() -> List[str]:
    return sorted(f[:-5] for f in os.listdir(WORKFLOW_DIR) if f.endswith(".json"))


def load_workflow(wid_or_path: str) -> Tuple[Dict[str, Any], str]:
    path = wid_or_path if wid_or_path.endswith(".json") else workflow_path(wid_or_path)
    if not os.path.isfile(path):
        raise WorkflowError("no workflow template %s (known: %s)" % (wid_or_path, ", ".join(list_workflows())))
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh), sha_file(path)


def route(wf: Dict[str, Any], needs: List[str]) -> Tuple[List[Dict[str, Any]], List[str]]:
    """The steps this outcome needs, in order, and the ids of the steps left out."""
    routed = [s for s in wf["steps"] if not s.get("when") or s["when"] in needs]
    return routed, [s["id"] for s in wf["steps"] if s not in routed]


def principals(wf: Dict[str, Any], steps: List[Dict[str, Any]]) -> List[str]:
    out = [wf["coordinator"], wf["final_consumer"]]
    for s in steps:
        out += [s["producer"], s["reviewer"], s["acceptance_owner"]]
    return out


def fleets_needed(wf: Dict[str, Any], steps: List[Dict[str, Any]]) -> List[str]:
    return sorted({fleet_of(p) for p in principals(wf, steps) if not p.startswith("human:")} | {fleet_of(wf["home_workload"])})


def run_contract(wf: Dict[str, Any], wf_sha: str, fixture: Dict[str, Any]) -> Dict[str, Any]:
    """The factory-rig contract one run is bound to. Editing the template or the fixture changes its hash,
    which makes every earlier handoff and evidence record stale."""
    fx = {k: v for k, v in fixture.items() if k != "_dir"}
    return {
        "schema_version": 1, "task_id": "WF-%s-%s" % (wf["code"], fixture["instance"]),
        "repo": "fixture-co/" + fixture["tenant_id"], "title": "%s for %s" % (wf["name"], fixture["tenant_id"]),
        "spec": {"id": "WORKFLOW-" + wf["code"], "revision": "1", "sha256": sha({"workflow": wf_sha, "fixture": fx})},
        "depends_on": [], "required_decisions": [], "backends": ["implement-spec"], "base_branch": "main",
        "verify": {"argv": ["bin/fleet", "workflow", "verify", "--workflow", wf["id"]]},
        "acceptance": sorted({c for s in wf["steps"] for c in s["acceptance_criteria"]}),
    }


def handoff_id(wf: Dict[str, Any], index: int, instance: str) -> str:
    return "HO-%s-%02d-%s" % (wf["code"], index + 1, instance)


def owner_record(wf: Dict[str, Any], wf_sha: str, steps: List[Dict[str, Any]], i: int, fixture: Dict[str, Any],
                 chash: str) -> Dict[str, Any]:
    """The contract owner's fields for routed step i. Nothing here comes from a worker or a source document."""
    s = steps[i]
    nxt = steps[i + 1]["producer"] if i + 1 < len(steps) else wf["final_consumer"]
    authority = dict(DEFAULT_AUTHORITY, tools=list(s.get("skills", [])))
    authority.update(s.get("authority", {}))
    return {
        "handoff_id": handoff_id(wf, wf["steps"].index(s), fixture["instance"]),
        "workload_id": wf["home_workload"], "tenant_id": fixture["tenant_id"], "client_id": fixture.get("client_id"),
        "operating_profile": fixture.get("profile", wf["profile"]), "outcome": s["outcome"],
        "scope": s.get("scope") or ["%s stage of the %s workflow" % (s["stage"], wf["name"])],
        "exclusions": list(fixture.get("exclusions", [])), "acceptance_criteria": s["acceptance_criteria"],
        "sources": list(fixture["sources"]) + [{"ref": "company-fleets/workflows/%s.json" % wf["id"], "revision": wf_sha[:12]}],
        "producer": s["producer"], "reviewer": s["reviewer"], "acceptance_owner": s["acceptance_owner"],
        "execution_owner": wf["coordinator"], "data": fixture["data"], "authority": authority,
        "budget": fixture["budget"], "stop_conditions": wf["stop_conditions"], "cancellation": wf["cancellation"],
        "next_consumer": nxt, "readiness_criteria": s["readiness_criteria"], "contract_hash": chash,
    }


def _roles(reg: Registry, fleets: List[str]) -> Dict[str, Dict[str, Any]]:
    out = {}
    for f in fleets:
        for r in reg.load(fleet_file(f, "roles"))["roles"]:
            out[r["id"]] = r
    return out


def structure_errors(wf: Dict[str, Any]) -> List[str]:
    """Key-level errors that make a template unreadable; no registry reads."""
    errors = ["missing key %s" % k for k in sorted(WORKFLOW_KEYS - set(wf))]
    errors += ["unknown key %s" % k for k in sorted(set(wf) - WORKFLOW_KEYS)]
    seen = set()
    for s in wf.get("steps", []):
        errors += ["step %s: unknown key %s" % (s.get("id"), k) for k in sorted(set(s) - STEP_KEYS)]
        if s.get("id") in seen:
            errors.append("duplicate step id %s" % s.get("id"))
        seen.add(s.get("id"))
    return errors


def check(reg: Registry, wf: Dict[str, Any], wf_sha: str = "0" * 64) -> List[str]:
    """Every template rule: structure, separation of duties, profile, registered roles, the home workload's
    coordinator, and every step's handoff built and validated through the foundation's handoff schema."""
    errors = structure_errors(wf)
    if errors:
        return errors
    for s in wf["steps"]:
        if s["producer"] == s["acceptance_owner"]:
            errors.append("step %s: producer %s is also its acceptance owner" % (s["id"], s["producer"]))
        if s["producer"] == s["reviewer"]:
            errors.append("step %s: producer %s reviews its own output" % (s["id"], s["producer"]))
    profile = next((p for p in reg.load(PROFILES)["profiles"] if p["id"] == wf["profile"]), None)
    if profile is None:
        return errors + ["unknown profile %s" % wf["profile"]]
    registered = [f["id"] for f in reg.load(FLEETS)["fleets"]]
    fleets = fleets_needed(wf, wf["steps"])
    errors += ["fleet %s is not registered" % f for f in fleets if f not in registered]
    errors += ["profile %s does not activate fleet %s" % (wf["profile"], f) for f in fleets if f in registered and f not in profile["fleets"]]
    roles = _roles(reg, [f for f in fleets if f in registered])
    for p in sorted(set(principals(wf, wf["steps"]))):
        if not p.startswith("human:") and p not in roles:
            errors.append("%s is not a role in fleets/%s/roles.json" % (p, fleet_of(p)))
    if wf["coordinator"] in roles and roles[wf["coordinator"]]["kind"] != "coordinator":
        errors.append("%s is not a coordinator" % wf["coordinator"])
    home = next((w for w in reg.load(fleet_file(fleet_of(wf["home_workload"]), "roles"))["workloads"]
                 if w["id"] == wf["home_workload"]), None)
    if home is None:
        errors.append("home workload %s does not exist" % wf["home_workload"])
    elif wf["coordinator"] not in home["roles"]:
        errors.append("coordinator %s is not in home workload %s" % (wf["coordinator"], wf["home_workload"]))
    for i, s in enumerate(wf["steps"]):
        h = open_handoff(owner_record(wf, wf_sha, wf["steps"], i, PLACEHOLDER_FIXTURE, "0" * 64))
        errors += ["step %s handoff: %s" % (s["id"], e) for e in validate_handoff(h)]
    return errors


# ---- tools -----------------------------------------------------------------------------------------

def _expand(value: str, ctx: Dict[str, str]) -> str:
    for k, v in ctx.items():
        value = value.replace("{%s}" % k, v)
    return value


def _run(cmd: Dict[str, Any], ctx: Dict[str, str], env_extra: Dict[str, str]) -> subprocess.CompletedProcess:
    env = dict(os.environ)
    env.update({k: os.path.expanduser(_expand(v, ctx)) for k, v in env_extra.items()})
    argv = [os.path.expanduser(_expand(a, ctx)) for a in cmd["argv"]]
    return subprocess.run(argv, cwd=_expand(cmd.get("cwd", "{skill}"), ctx), capture_output=True, text=True, timeout=600, env=env)


def fake_tool(step: Dict[str, Any], work: str, inputs: List[Dict[str, Any]]) -> Dict[str, Any]:
    name = "%s.md" % step["id"]
    body = ["# SYNTHETIC fake-tool output: %s" % step["stage"], "",
            "Artifact: %s" % step.get("artifact", step["stage"]),
            "Producer: %s" % step["producer"], "Inputs:"] + ["- %s %s" % (i["ref"], i.get("sha256", "")) for i in inputs]
    os.makedirs(work, exist_ok=True)
    with open(os.path.join(work, name), "w", encoding="utf-8") as fh:
        fh.write("\n".join(body) + "\n")
    out_sha = sha_file(os.path.join(work, name))
    return {"outputs": [name], "check_text": "fake check: %s sha256 %s present and labeled synthetic\n" % (name, out_sha),
            "exit": 0, "ok": True, "summary": "Fake tool produced the %s artifact for the %s stage." % (step.get("artifact", "stage"), step["stage"]),
            "assumptions": ["Fake tool: the artifact is a labeled placeholder, not real work."]}


def real_tool(step: Dict[str, Any], binding: Dict[str, Any], ctx: Dict[str, str]) -> Dict[str, Any]:
    work = ctx["work"]
    os.makedirs(work, exist_ok=True)
    log = []
    env_extra = binding.get("env", {})
    for c in binding.get("collect", []):
        src = os.path.expanduser(_expand(c["from"], ctx))
        dst = os.path.join(work, c["as"])
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        (shutil.copytree(src, dst, dirs_exist_ok=True) if os.path.isdir(src) else shutil.copyfile(src, dst))
    for p in binding.get("produce", []):
        proc = _run(p, ctx, env_extra)
        log.append("$ %s\nexit %d\n%s%s" % (" ".join(p["argv"]), proc.returncode, proc.stdout, proc.stderr))
        if "stdout" in p:
            with open(os.path.join(work, p["stdout"]), "w", encoding="utf-8") as fh:
                fh.write(proc.stdout)
        if proc.returncode not in p.get("expect_exit", [0]):
            return {"outputs": [], "check_text": "\n".join(log), "exit": proc.returncode, "ok": False,
                    "summary": "produce command exited %d" % proc.returncode, "assumptions": []}
    chk = binding["check"]
    proc = _run(chk, ctx, env_extra)
    log.append("$ %s\nexit %d\n%s%s" % (" ".join(chk["argv"]), proc.returncode, proc.stdout, proc.stderr))
    ok = proc.returncode in chk.get("expect_exit", [0]) and all(s in proc.stdout for s in chk.get("contains", []))
    return {"outputs": list(binding["outputs"]), "check_text": "\n".join(log), "exit": proc.returncode, "ok": ok,
            "summary": binding.get("summary", "Ran the bound tools for %s." % step["stage"]),
            "assumptions": list(binding.get("assumptions", []))}


# ---- run -------------------------------------------------------------------------------------------

def _records_for(ledger: Ledger, hid: str) -> List[Dict[str, Any]]:
    out = []
    for name in sorted(os.listdir(ledger.submitted)):
        if name.endswith(".json"):
            rec = ledger.get(name[:-5])
            if rec and rec["handoff_id"] == hid:
                out.append(rec)
    return out


def _log_call(base: str, step_id: str, kind: str) -> None:
    with open(os.path.join(base, "tool-calls.jsonl"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"step": step_id, "tool": kind}) + "\n")


def run(reg: Registry, wf: Dict[str, Any], wf_sha: str, fixture: Dict[str, Any], base: str,
        tools: str = "bound", lease_root: Optional[str] = None, stop_after: Optional[int] = None) -> Dict[str, Any]:
    base = os.path.abspath(base)
    os.makedirs(base, exist_ok=True)
    errors = structure_errors(wf)
    if errors:
        return {"status": "refused", "reason": "template structure", "errors": errors}
    steps, not_routed = route(wf, fixture.get("needs", []))
    profile = fixture.get("profile", wf["profile"])
    active = next((p["fleets"] for p in reg.load(PROFILES)["profiles"] if p["id"] == profile), None)
    if active is None or any(f not in active for f in fleets_needed(wf, steps)):
        return {"status": "refused", "reason": "profile %s does not activate every routed fleet %s" % (profile, fleets_needed(wf, steps)),
                "files_read": list(reg.files_read)}
    contract = run_contract(wf, wf_sha, fixture)
    assert not validate_contract(contract), validate_contract(contract)
    chash = contract_hash(contract)
    atomic_write(os.path.join(base, "contract.json"), json.dumps(contract, indent=2, sort_keys=True) + "\n")
    fleets = fleets_needed(wf, steps)
    roles = _roles(reg, fleets)
    report: Dict[str, Any] = {"workflow": wf["id"], "instance": fixture["instance"], "tenant_id": fixture["tenant_id"],
                              "profile": profile, "contract_hash": chash, "route": [s["id"] for s in steps],
                              "not_routed": not_routed, "steps": []}

    store_root, ledger_root = lease_root or os.path.join(base, "leases"), os.path.join(base, "ledger")
    store = LeaseStore(store_root)
    ident = (fixture["tenant_id"], wf["home_workload"], fixture["instance"])
    try:
        lease = ownerlog.open_ledger(ledger_root, reg, *ident, wf["coordinator"], os.getpid(), chash, exclusive=False, store_root=store_root)
    except (ClaimRefused, LeaseDenied, StaleEpoch, ownerlog.OwnerLogError) as exc:
        report.update(status="refused", reason="ownership: %s" % exc, files_read=list(reg.files_read))
        return report
    report["lease"] = {"holder": wf["coordinator"], "epoch": lease["epoch"], "key": "%s/%s#%s" % ident}

    ledger = Ledger(ledger_root)
    ctx_base = {"skill": SKILL_DIR, "skills": reg.skills_root, "base": base, "python": sys.executable,
                "fixture_dir": fixture.get("_dir", base)}
    prev_outputs: List[Dict[str, Any]] = []
    status, stopped_at = "complete", None
    try:
        for i, s in enumerate(steps):
            entry: Dict[str, Any] = {"step": s["id"], "stage": s["stage"], "fleet": fleet_of(s["producer"]),
                                     "producer": s["producer"], "acceptance_owner": s["acceptance_owner"]}
            report["steps"].append(entry)
            if stop_after is not None and i >= stop_after:
                entry["state"] = "not-run"
                status, stopped_at = "interrupted", stopped_at or s["id"]
                continue
            if status != "complete":
                entry["state"] = "not-run"
                continue
            if s.get("boundary") == "human-data":
                entry.update(state="awaiting-human-data", reason="This step needs data only a person can supply (%s); "
                             "the run stops here instead of inventing it." % s["outcome"])
                status, stopped_at = "stopped-at-human-boundary", s["id"]
                continue
            missing = [p for p in (s["producer"], s["reviewer"], s["acceptance_owner"]) if not p.startswith("human:") and p not in roles]
            if missing:
                entry.update(state="blocked-role", reason="not registered yet: " + ", ".join(missing))
                status, stopped_at = "blocked", s["id"]
                continue
            owner = owner_record(wf, wf_sha, steps, i, fixture, chash)
            entry["handoff_id"], entry["next_consumer"] = owner["handoff_id"], owner["next_consumer"]
            pre = validate_handoff(open_handoff(owner))
            if pre:
                entry.update(state="refused", errors=pre)
                status, stopped_at = "refused", s["id"]
                continue
            try:
                opened = ownerlog.append(ledger_root, "open", {k: v for k, v in owner.items() if k != "contract_hash"}, *ident,
                                         lease["epoch"], lease["token"], base=base, reg=reg, store_root=store_root)[1]["body"]
            except ownerlog.OwnerLogError as exc:
                entry.update(state="refused", errors=[str(exc)])
                status, stopped_at = "refused", s["id"]
                continue
            h = open_handoff(opened)
            done = [r for r in _records_for(ledger, owner["handoff_id"]) if r["reconciliation_state"] == "accepted"]
            if done and not gate_errors(done[-1], opened, contract, base):
                entry.update(state="accepted", resumed=True, idempotency_key=done[-1]["idempotency_key"])
                prev_outputs = done[-1]["outputs"]
                continue
            work = os.path.join(base, "work", s["id"])
            inputs = [{"ref": o["path"], "tenant_id": fixture["tenant_id"], "classification": fixture["data"]["classification"],
                       "trust": "trusted", "source_kind": "rig-record", "sha256": o["sha256"]} for o in prev_outputs]
            sources = []
            for u in fixture.get("untrusted", []):
                if u["step"] == s["id"]:
                    text = open(os.path.join(fixture.get("_dir", base), u["path"]), encoding="utf-8").read()
                    inputs.append(describe_source(text, u["path"], fixture["tenant_id"], u.get("classification", fixture["data"]["classification"]), u["source_kind"]))
                    sources.append((u["path"], text))
            binding = fixture.get("tools", {}).get(s["id"]) if tools == "bound" else None
            _log_call(base, s["id"], "real" if binding else "fake")
            result = real_tool(s, binding, dict(ctx_base, work=work)) if binding else fake_tool(s, work, inputs)
            ev_rel = "evidence/%s.txt" % s["id"]
            entry["tool"] = "real" if binding else "fake"
            entry["check_exit"] = result["exit"]
            if not result["ok"]:
                atomic_write(os.path.join(base, ev_rel), result["check_text"])
                entry.update(state="check-failed", evidence=ev_rel, summary=result["summary"])
                status, stopped_at = "stopped", s["id"]
                continue
            outs = [{"path": os.path.relpath(os.path.join(work, o), base), "sha256": sha_file(os.path.join(work, o)),
                     "artifact_type": s.get("artifact", s["stage"])} for o in result["outputs"]]
            reviewed = "".join("reviewed-sha256: %s %s\n" % (o["sha256"], o["path"]) for o in outs)
            atomic_write(os.path.join(base, ev_rel), reviewed + result["check_text"])
            ev_sha = sha_file(os.path.join(base, ev_rel))
            update = {"inputs": inputs, "outputs": outs, "summary": result["summary"], "assumptions": result["assumptions"],
                      "evidence": [{"path": ev_rel, "sha256": ev_sha, "about": o["path"], "about_sha256": o["sha256"],
                                    "contract_hash": chash} for o in outs]}
            update.update(fixture.get("worker_requests", {}).get(s["id"], {}))
            h2, refused, findings = guarded_update(h, update, sources)
            entry["refused_fields"] = [r["field"] for r in refused]
            entry["untrusted_findings"] = [{"line": f["line"], "category": f["category"]} for f in findings]
            sub = ledger.submit(h2)
            entry["submit"] = sub["status"]
            if sub["status"] not in ("recorded", "duplicate"):
                entry.update(state="refused", errors=sub.get("errors", []))
                status, stopped_at = "refused", s["id"]
                continue
            settled = {r["key"]: r for r in ledger.reconcile(contract, base)}
            rec = ledger.get(sub["key"])
            entry.update(state=rec["reconciliation_state"], idempotency_key=sub["key"],
                         errors=settled.get(sub["key"], {}).get("errors", []), outputs=[o["path"] for o in outs], evidence=ev_rel)
            if rec["reconciliation_state"] != "accepted":
                status, stopped_at = "stopped", s["id"]
                continue
            prev_outputs = outs
    finally:
        release(store, fixture["tenant_id"], wf["home_workload"], fixture["instance"], lease["epoch"], status)
    loaded = sorted({p.split("/")[1] for p in reg.files_read if p.startswith("fleets/")})
    registered = [f["id"] for f in reg.load(FLEETS)["fleets"]]
    report.update(status=status, stopped_at=stopped_at, fleets_loaded=loaded,
                  fleets_not_loaded=[f for f in registered if f not in loaded], files_read=list(reg.files_read))
    atomic_write(os.path.join(base, "chain.json"), json.dumps(report, indent=2, sort_keys=True) + "\n")
    return report


def verify(base: str) -> Dict[str, Any]:
    """Recompute the gate now for every handoff a run accepted, against the owner fields in the run's owner log.
    An output, evidence file, contract, owner log entry, or opened/ or submitted/ record edited after acceptance
    turns that step stale."""
    base = os.path.abspath(base)
    with open(os.path.join(base, "contract.json"), encoding="utf-8") as fh:
        contract = json.load(fh)
    with open(os.path.join(base, "chain.json"), encoding="utf-8") as fh:
        chain = json.load(fh)
    ledger = Ledger(os.path.join(base, "ledger"))
    try:
        entries = ownerlog.read(os.path.join(base, "ledger"))
        if ownerlog.state(entries)["contract_hash"] != contract_hash(contract):
            raise ownerlog.OwnerLogError("ledger-not-for-this-work", "the run's owner log is bound to another contract than contract.json")
    except ownerlog.OwnerLogError as exc:
        return {"ok": False, "checked": 0, "steps": [], "error": str(exc)}
    results = []
    for e in chain["steps"]:
        if e.get("state") != "accepted":
            continue
        h = ledger.get(e["idempotency_key"])
        opened = ownerlog.effective(entries, "open", h["handoff_id"]) if h else None
        errs = (gate_errors(h, opened["body"], contract, base) if opened else ["handoff-not-opened: no open record in the owner log"]) if h else ["record missing"]
        results.append({"step": e["step"], "handoff_id": e["handoff_id"], "ok": not errs, "errors": errs})
    return {"ok": all(r["ok"] for r in results) and bool(results), "checked": len(results), "steps": results}


def load_fixture(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as fh:
        fx = json.load(fh)
    fx["_dir"] = os.path.dirname(os.path.abspath(path))
    for k in ("instance", "tenant_id", "sources", "data", "budget"):
        if k not in fx:
            raise WorkflowError("fixture %s lacks %s" % (path, k))
    return fx
