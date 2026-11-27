#!/usr/bin/env python3
"""data_guard: decide whether an education workflow may read one student-related record.

  python3 data_guard.py check REQUEST

The request names a principal and a record by id only. Both resolve from the tenants registry
(company-fleets/fixtures/tenants.json), the policy loads from references/school-policy.json and grants
load from the owner file references/owner-grants.json; the requester can supply none of them, so it
cannot declare its own classroom, role, policy or grant. A grant written on the record counts for
nothing. Tenant and classification rules come from company-fleets (fleetlib.tenancy, imported, not
copied): another classroom's student records stay refused whatever the grant. On top of them:
real student records need a school policy a named human verified, with a date and an evidence file that
exists, an approved tool, role access, a consent or authorization basis and a retention period;
external destinations for student records are refused.
Prints JSON. Exit 0 allow, 1 refuse or invalid input, 2 usage.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import sys
from typing import Any, Dict, List, Optional, Tuple

SKILL = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
CF = os.path.normpath(os.path.join(SKILL, "..", "company-fleets"))
sys.path.insert(0, os.path.join(CF, "scripts"))
from fleetlib.tenancy import LEVEL, can_read  # noqa: E402

POLICY = os.path.join(SKILL, "references", "school-policy.json")
OWNER_GRANTS = os.path.join(SKILL, "references", "owner-grants.json")
TENANTS = os.path.join(CF, "fixtures", "tenants.json")
STUDENT_CATEGORIES = {"student-record"}


def _load(path: str) -> Any:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def load_policy() -> Dict[str, Any]:
    return _load(POLICY)


def load_owner_grants() -> Dict[str, List[Dict[str, Any]]]:
    """Grants each tenant's owner recorded, keyed by the tenant that owns the records."""
    grants = _load(OWNER_GRANTS)["grants"]
    if not isinstance(grants, dict) or not all(isinstance(v, list) for v in grants.values()):
        raise ValueError("owner-grants.json grants must map a tenant id to a list of grants")
    return grants


def _resolve(ref: Any, pool: List[Dict[str, Any]], kind: str) -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    if not isinstance(ref, str):
        return None, ("%s must be an id from the tenants registry; inline %s objects are refused because the "
                      "requester could declare its own classroom, role or classification" % (kind, kind))
    hit = next((x for x in pool if x.get("id") == ref), None)
    return (hit, None) if hit else (None, "%s %r is not in the tenants registry" % (kind, ref))


def policy_verified(policy: Dict[str, Any]) -> bool:
    """A named human, a date and an evidence file that exists under company-fleets or this skill."""
    if policy.get("verified") is not True or not str(policy.get("verified_by", "")).startswith("human:"):
        return False
    try:
        datetime.date.fromisoformat(str(policy.get("verified_on")))
    except ValueError:
        return False
    ev = policy.get("evidence")
    if not isinstance(ev, str) or not ev or ev.startswith("/") or ".." in ev.split("/"):
        return False
    return os.path.isfile(os.path.join(CF, ev)) or os.path.isfile(os.path.join(SKILL, ev))


def validate(req: Any) -> List[str]:
    if not isinstance(req, dict):
        return ["the request must be a JSON object"]
    errs = ["request is missing %s" % f for f in ("principal", "record", "data_origin", "tool", "purpose") if not req.get(f)]
    if req.get("data_origin") and req["data_origin"] not in ("synthetic", "real"):
        errs.append("data_origin must be synthetic or real")
    return errs


def decide(req: Dict[str, Any], policy: Dict[str, Any], tenants: Dict[str, Any],
           owner_grants: Optional[Dict[str, List[Dict[str, Any]]]] = None) -> Tuple[str, List[str]]:
    reasons: List[str] = []
    principal, e1 = _resolve(req["principal"], tenants.get("principals", []), "principal")
    record, e2 = _resolve(req["record"], tenants.get("records", []), "record")
    if e1 or e2:
        return "refuse", [e for e in (e1, e2) if e]
    for field in ("tenant_id", "max_classification"):
        if field not in principal:
            return "refuse", ["principal is missing %s" % field]
    for field in ("id", "tenant_id", "classification"):
        if field not in record:
            return "refuse", ["record is missing %s" % field]
    if record["classification"] not in LEVEL or principal["max_classification"] not in LEVEL:
        return "refuse", ["unknown classification level"]
    ok, why = can_read(principal, record, (owner_grants or {}).get(record["tenant_id"], []))
    if not ok:
        reasons.append("tenant boundary: " + why)
    dest = str(req.get("destination", "local"))
    if dest != "local" and record.get("category") in STUDENT_CATEGORIES:
        reasons.append("destination %s refused: student records leave the tenant only through the school's own "
                       "approved process, never from this workflow" % dest)
    if req["data_origin"] == "real":
        missing = []
        if not policy_verified(policy):
            missing.append("a school student-data policy verified by a named human, with a date and an evidence file that exists")
        if req["tool"] not in policy.get("approved_tools", []):
            missing.append("tool %s on the school's approved list" % req["tool"])
        role = principal.get("role") or principal.get("id")
        if role not in policy.get("role_access", {}):
            missing.append("role access for %s" % role)
        if not policy.get("consent_basis"):
            missing.append("a consent or authorization basis")
        if not policy.get("retention_days"):
            missing.append("a retention period")
        if missing:
            reasons.append("human-data boundary: real student records need " + "; ".join(missing))
    return ("refuse" if reasons else "allow"), (reasons or ["same tenant, synthetic or policy-approved, local only"])


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="data_guard")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("request")
    try:
        args = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    try:
        req, policy, tenants = _load(args.request), load_policy(), _load(TENANTS)
        owner_grants = load_owner_grants()
    except (OSError, ValueError, KeyError) as exc:
        print(json.dumps({"decision": "refuse", "status": "invalid", "reasons": [str(exc)]}, indent=2))
        return 1
    problems = validate(req)
    if problems:
        print(json.dumps({"decision": "refuse", "status": "invalid", "reasons": problems}, indent=2))
        return 1
    decision, reasons = decide(req, policy, tenants, owner_grants)
    print(json.dumps({"decision": decision, "reasons": reasons, "policy_verified": policy_verified(policy),
                      "request": {k: req[k] for k in ("principal", "record", "data_origin", "tool")}}, indent=2))
    return 0 if decision == "allow" else 1


if __name__ == "__main__":
    sys.exit(main())
