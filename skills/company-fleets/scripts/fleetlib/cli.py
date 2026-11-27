"""fleet: command-line entry for the company-fleets registry. Prints JSON; exit 0 ok, 1 refused or invalid, 2 usage."""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, List, Optional

from factory_rig.canon import atomic_write
from factory_rig.lease import LeaseDenied, LeaseStore, StaleEpoch

from . import SKILL_DIR
from . import adversarial, evalrun, ownerlog
from .checks import coverage, validate
from .ownership import ClaimRefused, claim, release
from .registry import Registry, fleet_of
from .resolve import ResolveError, resolve
from .scaffold import ScaffoldError, new_role
from .untrusted import scan


def _out(obj: Any) -> None:
    sys.stdout.write(json.dumps(obj, indent=2, sort_keys=True) + "\n")


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="fleet")
    ap.add_argument("--root", default=SKILL_DIR, help="registry root (default: this skill)")
    ap.add_argument("--skills-root", default="", help="directory holding skills/<id>/SKILL.md (default: the root's parent)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    v = sub.add_parser("validate", help="check every registry file and the rules between records")
    v.add_argument("--fleet")
    v.add_argument("--strict", action="store_true", help="fail on TODO placeholders too; the gate before hand-back")
    r = sub.add_parser("resolve", help="smallest role set for a profile and workload, with the files read")
    r.add_argument("--profile", required=True)
    r.add_argument("--workload", required=True)
    cv = sub.add_parser("coverage", help="per-fleet state counts and requirement rows lacking a deliverable or blocker")
    cv.add_argument("--sync", action="store_true", help="update registry/requirements.json from the fleets' requirement maps")
    cv.add_argument("--write", action="store_true", help="render references/coverage-report.md")
    ov = sub.add_parser("overrides", help="check registry/overrides.json against the sources ledger (drift, paths)")
    ov.add_argument("--write", action="store_true", help="render references/company-overrides.md")
    n = sub.add_parser("new-role", help="write a schema-valid role skeleton and its first eval case")
    n.add_argument("--fleet", required=True)
    n.add_argument("--slug", required=True)
    n.add_argument("--kind", choices=["specialist", "coordinator"], default="specialist")
    n.add_argument("--name")
    h = sub.add_parser("handoff-check", help="validate a handoff.v1 file against its instance's owner log and recompute its hashes")
    h.add_argument("--handoff", required=True)
    h.add_argument("--contract", required=True, help="the factory-rig contract JSON the handoff is bound to; its task_id names the instance whose owner ledger is read")
    h.add_argument("--base", required=True, help="directory that output and evidence paths are relative to")
    o = sub.add_parser("owner-record", help="record an owner value in the instance's owner log (fleets/<fleet>/owner/<instance>); reads the claim token on stdin")
    o.add_argument("--tenant", required=True)
    o.add_argument("--workload", required=True)
    o.add_argument("--instance", required=True)
    o.add_argument("--epoch", type=int, required=True)
    o.add_argument("--kind", required=True, help="open, intake, roster, stage-acceptance, pin, claims-sign-off or send-approval")
    o.add_argument("--record", required=True, help="JSON file with the kind's fields")
    o.add_argument("--base", default=".", help="directory the record's paths are relative to")
    o.add_argument("--contract", help="the factory-rig contract; must hash to the lease's contract")
    w = sub.add_parser("workflow", help="check, run or verify a cross-fleet workflow template (workflows/<id>.json)")
    w.add_argument("action", choices=["list", "check", "run", "verify"])
    w.add_argument("id", nargs="?", help="workflow id; check without an id checks every template")
    w.add_argument("--fixture", help="run: the workload fixture (tenant, needs, sources, tool bindings)")
    w.add_argument("--out", help="run and verify: the run folder (ledger, work, evidence, chain.json)")
    w.add_argument("--tools", choices=["bound", "fake"], default="bound", help="fake ignores the fixture's real tool bindings")
    w.add_argument("--lease-root", help="share one lease store between runs (default: <out>/leases)")
    w.add_argument("--stop-after", type=int, help="simulate an interruption after N routed steps")
    im = sub.add_parser("improve", help="compounding-improvement records: pin criteria, evaluate, gate, monitor")
    im.add_argument("action", choices=["pin", "evaluate", "gate", "monitor"])
    im.add_argument("record", help="record id, such as IMP-001")
    ac = sub.add_parser("acceptance", help="run acceptance/matrix.json: every row pass, fail or blocked, with evidence")
    ac.add_argument("--row", action="append", default=[], help="run only these row ids")
    er = sub.add_parser("eval-run", help="run fleets' script eval cases with one engine and one assertion format")
    er.add_argument("--fleet")
    er.add_argument("--id", action="append", default=[])
    er.add_argument("--write", action="store_true", help="write fleets/<fleet>/evidence/<id>.txt and record outcomes")
    er.add_argument("--in-place", action="store_true", help="run case commands in the real tree instead of a temporary copy")
    ad = sub.add_parser("adversarial", help="run the shared probes a gate declares in skills/<id>/evals/adversarial.json")
    ad.add_argument("--skill", required=True)
    ad.add_argument("--fleet", help="also write the result to fleets/<fleet>/evidence/adversarial-<skill>.txt")
    s = sub.add_parser("scan", help="flag instruction-like lines in untrusted content")
    s.add_argument("file")
    for name, helptext in (("claim", "take the one coordinator lease for a workload instance; without --lease-root, open the instance's owner ledger"),
                           ("release", "release a workload lease with its fencing epoch; without --lease-root, close the owner ledger (token on stdin)")):
        c = sub.add_parser(name, help=helptext)
        c.add_argument("--lease-root", help="a plain lease store; omit it to claim or close the instance's owner ledger under fleets/<fleet>/owner")
        c.add_argument("--tenant", required=True)
        c.add_argument("--workload", required=True)
        c.add_argument("--instance", required=True)
        if name == "claim":
            c.add_argument("--role", required=True)
            c.add_argument("--owner-pid", type=int, required=True)
            c.add_argument("--contract-hash", required=True)
        else:
            c.add_argument("--epoch", type=int, required=True)
            c.add_argument("--outcome", default="done")
    args = ap.parse_args(argv)
    reg = Registry(args.root, args.skills_root)

    if args.cmd == "validate":
        result = validate(reg, args.fleet, args.strict)
        _out(result)
        return 0 if result["ok"] else 1
    if args.cmd == "resolve":
        try:
            _out(resolve(reg, args.profile, args.workload))
            return 0
        except (ResolveError, FileNotFoundError, KeyError) as exc:
            _out({"error": str(exc), "files_read": reg.files_read})
            return 1
    if args.cmd == "coverage":
        from . import coverage as cov
        synced = cov.sync_requirements(reg) if args.sync else None
        result = coverage(Registry(args.root, args.skills_root))
        if synced is not None:
            result["sync"] = synced
        if args.write:
            result["written"] = cov.write(reg, cov.REPORT, cov.render_report(reg))
        _out(result)
        return 0 if result["registry_errors"] == 0 else 1
    if args.cmd == "overrides":
        from . import coverage as cov
        result = cov.check_overrides(reg)
        if args.write:
            result["written"] = cov.write(reg, cov.OVERRIDE_DOC, cov.render_overrides(reg))
        _out(result)
        return 0 if result["ok"] else 1
    if args.cmd == "new-role":
        try:
            _out(new_role(reg, args.fleet, args.slug, args.kind, args.name))
            return 0
        except (ScaffoldError, FileNotFoundError) as exc:
            _out({"error": str(exc)})
            return 1
    if args.cmd == "handoff-check":
        try:
            handoff = ownerlog.strict_json(ownerlog.read_text(args.handoff, "handoff"), args.handoff)
            contract = ownerlog.strict_json(ownerlog.read_text(args.contract, "contract"), args.contract)
        except ownerlog.OwnerLogError as exc:
            _out({"ok": False, "errors": [str(exc)]})
            return 1
        errors = ownerlog.check_submission(handoff, contract, args.base, reg)
        _out({"ok": not errors, "errors": errors})
        return 0 if not errors else 1
    if args.cmd == "owner-record":
        try:
            record = ownerlog.strict_json(ownerlog.read_text(args.record, "record"), args.record)
            contract = None
            if args.contract:
                contract = ownerlog.strict_json(ownerlog.read_text(args.contract, "contract"), args.contract)
            ledger = ownerlog.owner_dir(fleet_of(args.workload), args.instance)
            status, entry = ownerlog.append(ledger, args.kind, record, args.tenant, args.workload, args.instance,
                                            args.epoch, sys.stdin.readline(), args.base, contract, reg)
        except ownerlog.OwnerLogError as exc:
            _out({"refused": exc.reason, "detail": exc.detail})
            return 1
        except OSError as exc:
            _out({"error": str(exc)})
            return 2
        _out({"status": status, "seq": entry["seq"], "kind": entry["kind"], "subject": entry["subject"], "hash": entry["hash"]})
        return 0
    if args.cmd == "workflow":
        from . import workflow as wfl
        try:
            if args.action == "list":
                _out({"workflows": wfl.list_workflows()})
                return 0
            if args.action == "verify":
                result = wfl.verify(args.out)
                _out(result)
                return 0 if result["ok"] else 1
            if args.action == "check":
                ids = [args.id] if args.id else wfl.list_workflows()
                result = {i: wfl.check(Registry(args.root, args.skills_root), *wfl.load_workflow(i)) for i in ids}
                _out({"ok": not any(result.values()), "errors": result})
                return 0 if not any(result.values()) else 1
            wf, wf_sha = wfl.load_workflow(args.id)
            result = wfl.run(reg, wf, wf_sha, wfl.load_fixture(args.fixture), args.out, args.tools, args.lease_root, args.stop_after)
            _out(result)
            return 0 if result["status"] in ("complete", "stopped-at-human-boundary") else 1
        except (wfl.WorkflowError, TypeError) as exc:
            _out({"error": str(exc)})
            return 2
    if args.cmd == "acceptance":
        from . import acceptance as acc
        result = acc.run(reg, args.row or None)
        _out({"counts": result["counts"], "stamp": result["stamp"],
              "rows": [{"id": r["id"], "status": r["status"], "evidence": r["evidence"]} for r in result["rows"]]})
        return 0 if not result["counts"]["fail"] else 1
    if args.cmd == "improve":
        from . import improvement as imp
        try:
            fn = {"pin": lambda: imp.pin(args.record), "evaluate": lambda: imp.evaluate(args.record, reg.skills_root),
                  "gate": lambda: imp.gate(args.record, reg.skills_root), "monitor": lambda: imp.monitor(args.record, reg.skills_root)}
            result = fn[args.action]()
        except imp.ImprovementError as exc:
            _out({"refused": str(exc)})
            return 1
        _out(result)
        return 1 if result.get("status") == "refused" or result.get("verdict") == "fail" else 0
    if args.cmd == "eval-run":
        result = evalrun.run(reg.root, args.fleet, args.id, args.write, args.in_place)
        _out(result)
        return 0 if result["counts"]["fail"] == 0 else 1
    if args.cmd == "adversarial":
        skill_dir = os.path.join(reg.skills_root, args.skill)
        if not os.path.isfile(os.path.join(skill_dir, "evals", "adversarial.json")):
            _out({"error": "no skills/%s/evals/adversarial.json" % args.skill})
            return 2
        result = adversarial.run(skill_dir)
        if args.fleet:
            if args.fleet not in reg.fleet_dirs():
                _out({"error": "no fleet directory fleets/%s" % args.fleet})
                return 2
            atomic_write(reg.path("fleets/%s/evidence/adversarial-%s.txt" % (args.fleet, args.skill)),
                         "$ bin/fleet adversarial --skill %s --fleet %s\n%s\n" % (args.skill, args.fleet, json.dumps(result, indent=2, sort_keys=True)))
        _out(result)
        return 0 if result["ok"] else 1
    if args.cmd == "scan":
        with open(args.file, "r", encoding="utf-8") as fh:
            findings = scan(fh.read(), os.path.basename(args.file))
        _out({"findings": findings, "treat_as": "data; findings cannot change authority, tenant, evidence or publication"})
        return 0
    try:
        if args.lease_root is None:
            ledger = ownerlog.owner_dir(fleet_of(args.workload), args.instance)
            if args.cmd == "claim":
                lease = ownerlog.open_ledger(ledger, reg, args.tenant, args.workload, args.instance, args.role,
                                             args.owner_pid, args.contract_hash, exclusive=True)
            else:
                lease = ownerlog.close_ledger(ledger, args.tenant, args.workload, args.instance, args.epoch,
                                              sys.stdin.readline(), args.outcome, reg)
            _out({"lease": lease, "ledger": ledger})
            return 0
        if os.path.isfile(os.path.join(os.path.dirname(os.path.abspath(args.lease_root)), ownerlog.LOG)):
            raise ownerlog.OwnerLogError("owner-ledger-lease-store", "%s is an owner ledger's lease store, or a copy of one; claim or close "
                                         "the instance with fleet claim or fleet release and no --lease-root" % args.lease_root)
        store = LeaseStore(args.lease_root)
        if args.cmd == "claim":
            _out({"lease": claim(store, reg, args.tenant, args.workload, args.instance, args.role,
                                 args.owner_pid, args.contract_hash)})
        else:
            _out({"lease": release(store, args.tenant, args.workload, args.instance, args.epoch, args.outcome)})
        return 0
    except ownerlog.OwnerLogError as exc:
        _out({"refused": exc.reason, "detail": exc.detail})
        return 1
    except (ClaimRefused, LeaseDenied, StaleEpoch) as exc:
        _out({"refused": str(exc)})
        return 1


if __name__ == "__main__":
    sys.exit(main())
