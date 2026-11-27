"""Write a schema-valid role skeleton and its first evaluation case into a fleet's own files.

The eval is written before the role, so an interrupted run leaves at most an unused eval case,
which the next run reuses; it never leaves a role pointing at a missing case.
"""
from __future__ import annotations

import json
from typing import Any, Dict, Optional

from factory_rig.canon import atomic_write

from .registry import Registry, fleet_file
from .schema import Schemas


class ScaffoldError(Exception):
    pass


def skeleton(fleet: str, slug: str, kind: str, name: str, eval_id: str) -> Dict[str, Any]:
    todo = "TODO: replace before claiming coverage"
    return {
        "id": "%s.%s" % (fleet, slug),
        "display_name": name,
        "fleet": fleet,
        "kind": kind,
        "dispatch": False,
        "purpose": "TODO: one sentence on the outcome this role owns",
        "responsibilities": ["TODO: a responsibility you can check"],
        "exclusions": ["TODO: work this role must hand to someone else"],
        "activation_triggers": ["TODO: the request or event that activates this role"],
        "authority_boundary": {"may": ["Draft and analyze within the assigned workload"],
                               "may_not": ["Accept its own output", "Send, publish, purchase or deploy outside the rig"]},
        "required_context": [todo],
        "tools": [],
        "skills": [{"id": slug, "provenance": "local:company-fleets (planned)",
                    "blocked_reason": "TODO: skill not built yet; attach a real skill id or state the real blocker"}],
        "inputs": [todo],
        "outputs": [todo],
        "acceptance_criteria": [todo],
        "relations": {"reviewers": ["human:accountable-owner"], "acceptor": "human:accountable-owner",
                      "escalation": ["human:accountable-owner"]},
        "data_access": {"max_classification": "internal", "tenant_scoped": True},
        "external_actions": {"mode": "none", "limits": ["No external sends, posts, purchases or deployments"]},
        "budget": {"max_minutes": 30, "max_retries": 2},
        "cancellation": "Stop, label partial artifacts as partial, release any lease, and report what remains.",
        "handoff": {"schema": "handoff.v1", "next_consumers": [], "readiness": [todo]},
        "voice": "TODO: the professional communication style this work calls for",
        "limitations": ["A persona is a viewpoint, not a credential or an authority"],
        "verification": {"coverage": {"state": "gap", "note": "Skeleton only"},
                         "installed": {"state": "not-installed"},
                         "activated": {"state": "not-activated"},
                         "behavioral": {"state": "unverified"}},
        "evals": [eval_id],
    }


def new_role(reg: Registry, fleet: str, slug: str, kind: str = "specialist", name: Optional[str] = None) -> Dict[str, Any]:
    if fleet not in reg.fleet_dirs():
        raise ScaffoldError("no fleet directory fleets/%s" % fleet)
    roles_rel, evals_rel = fleet_file(fleet, "roles"), fleet_file(fleet, "evals")
    roles_doc, evals_doc = reg.load(roles_rel), reg.load(evals_rel)
    rid = "%s.%s" % (fleet, slug)
    if any(r.get("id") == rid for r in roles_doc["roles"]):
        raise ScaffoldError("role %s already exists" % rid)
    if kind == "coordinator":
        have = [r["id"] for r in roles_doc["roles"] if r.get("kind") == "coordinator"]
        if have:
            raise ScaffoldError("fleet %s already has coordinator %s" % (fleet, have[0]))
    eval_id = "%s.eval.%s-smoke" % (fleet, slug)
    role = skeleton(fleet, slug, kind, name or slug.replace("-", " ").capitalize(), eval_id)
    errors = Schemas().validate(role, "role.schema.json")
    if errors:
        raise ScaffoldError("skeleton fails the role schema: " + "; ".join(errors))
    if not any(e.get("id") == eval_id for e in evals_doc["evals"]):
        evals_doc["evals"].append({
            "id": eval_id, "kind": "positive", "target": rid,
            "input": "TODO: a realistic request this role should handle",
            "expected": "TODO: the observable result that counts as a pass",
            "check": {"method": "model-judgment"}, "synthetic": True, "outcome": {"status": "not-run"},
        })
        atomic_write(reg.path(evals_rel), json.dumps(evals_doc, indent=2) + "\n")
    roles_doc["roles"].append(role)
    atomic_write(reg.path(roles_rel), json.dumps(roles_doc, indent=2) + "\n")
    return {"role": rid, "eval": eval_id, "files": [roles_rel, evals_rel]}
