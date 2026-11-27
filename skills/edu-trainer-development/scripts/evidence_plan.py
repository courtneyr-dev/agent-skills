#!/usr/bin/env python3
"""evidence_plan: check a plan to collect actual learning and transfer evidence before anyone runs it.

  check PLAN.json

A plan is rejected when its only evidence is a satisfaction survey, attendance, completion, a
self-report or a generated artifact; when a measure lacks a human owner, timing or baseline; when it
names no human-data boundary; or when any outcome value is already filled in. Results come from real
collection after the plan runs, never from the plan itself.

Python 3.9+ standard library only. Prints JSON. Exit 0 accepted, 1 rejected, 2 invalid input or usage.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

WEAK = {"satisfaction-survey", "attendance", "completion", "self-report", "generated-artifact"}
STRONG = {"performance-task", "observation", "work-sample", "system-data", "knowledge-check"}
LEVELS = {"reaction", "learning", "behavior", "results"}
TRANSFER = {"behavior", "results"}
OUTCOME_KEYS = ("result", "results", "observed", "observations", "score", "scores", "gain", "outcome", "value", "rating", "ratings")


class InputError(ValueError):
    pass


def _filled(v: Any) -> bool:
    return v not in (None, "", [], {})


def validate(plan: Any) -> None:
    if not isinstance(plan, dict):
        raise InputError("the plan must be a JSON object")
    for key in ("intervention", "intended_performance"):
        if not isinstance(plan.get(key), str) or not plan[key].strip():
            raise InputError("plan.%s must be non-empty text" % key)
    measures = plan.get("measures")
    if not isinstance(measures, list) or not measures:
        raise InputError("plan.measures must be a non-empty list")
    ids = set()
    for n, m in enumerate(measures):
        if not isinstance(m, dict):
            raise InputError("measure %d must be an object" % n)
        if not isinstance(m.get("id"), str) or not m["id"] or m["id"] in ids:
            raise InputError("measure %d needs a unique text id" % n)
        ids.add(m["id"])
        if m.get("kind") not in WEAK | STRONG:
            raise InputError("measure %s kind %r is not one of %s" % (m["id"], m.get("kind"), ", ".join(sorted(WEAK | STRONG))))
        if m.get("level") not in LEVELS:
            raise InputError("measure %s level %r is not one of %s" % (m["id"], m.get("level"), ", ".join(sorted(LEVELS))))


def check(plan: Dict[str, Any]) -> Dict[str, Any]:
    validate(plan)
    findings: List[str] = []
    warnings: List[str] = []
    measures = plan["measures"]
    for m in measures:
        mid = m["id"]
        owner = m.get("owner")
        if not isinstance(owner, str) or not owner.startswith("human:"):
            findings.append("%s has no human owner (owner must be human:<role>)" % mid)
        for key in ("timing", "baseline", "description"):
            if not isinstance(m.get(key), str) or not m[key].strip():
                findings.append("%s has no %s" % (mid, key))
        filled = [k for k in OUTCOME_KEYS if _filled(m.get(k))]
        if filled:
            findings.append("%s has pre-filled outcome values (%s); results come from real collection, not the plan"
                            % (mid, ", ".join(filled)))
    top = [k for k in OUTCOME_KEYS if _filled(plan.get(k))]
    if top:
        findings.append("the plan has pre-filled outcome values (%s); results come from real collection, not the plan"
                        % ", ".join(top))
    evidence = [m["id"] for m in measures if m["kind"] in STRONG and m["level"] != "reaction"]
    transfer = [m["id"] for m in measures if m["kind"] in STRONG and m["level"] in TRANSFER]
    if not evidence:
        findings.append("no evidence of learning or transfer: satisfaction surveys, attendance, completion, "
                        "self-reports and generated artifacts don't show what anyone can now do")
    boundary = plan.get("human_data_boundary")
    if not isinstance(boundary, str) or not boundary.strip():
        findings.append("no human_data_boundary: name who collects real data, under what approval, and that the "
                        "agent stops before inventing results")
    if evidence and not transfer:
        warnings.append("no behavior or results measure, so transfer to the job or classroom stays unmeasured")
    if not isinstance(plan.get("revisit_if"), str) or not plan["revisit_if"].strip():
        warnings.append("no revisit_if rule for deciding the intervention didn't work")
    return {
        "status": "rejected" if findings else "accepted",
        "findings": findings,
        "warnings": warnings,
        "evidence_measures": evidence,
        "transfer_measures": transfer,
        "measures": len(measures),
    }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="evidence_plan")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="check a learning-evidence collection plan")
    c.add_argument("plan")
    try:
        args = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    try:
        with open(args.plan, encoding="utf-8") as fh:
            result = check(json.load(fh))
    except (OSError, ValueError) as exc:
        sys.stdout.write(json.dumps({"status": "invalid-input", "error": str(exc)}, indent=2) + "\n")
        return 2
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0 if result["status"] == "accepted" else 1


if __name__ == "__main__":
    sys.exit(main())
