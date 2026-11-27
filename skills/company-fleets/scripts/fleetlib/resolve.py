"""Select the smallest role set for one profile and workload, reading only the files that set needs.

Reads registry/profiles.json, the workload's own fleets/<fleet>/roles.json, and the roles.json of
any other fleet the workload names and the profile activates. Skill bodies are listed as paths to
load on demand, never read here. Registry.files_read is the proof.
"""
from __future__ import annotations

from typing import Any, Dict, List

from .registry import PROFILES, Registry, fleet_file, fleet_of


class ResolveError(Exception):
    pass


def resolve(reg: Registry, profile_id: str, workload_id: str) -> Dict[str, Any]:
    profile = next((p for p in reg.load(PROFILES)["profiles"] if p["id"] == profile_id), None)
    if profile is None:
        raise ResolveError("unknown profile %s" % profile_id)
    home = fleet_of(workload_id)
    if home not in profile["fleets"]:
        raise ResolveError("profile %s does not activate fleet %s" % (profile_id, home))
    docs = {home: reg.load(fleet_file(home, "roles"))}
    workload = next((w for w in docs[home]["workloads"] if w["id"] == workload_id), None)
    if workload is None:
        raise ResolveError("fleet %s has no workload %s" % (home, workload_id))
    if profile_id not in workload["profiles"]:
        raise ResolveError("workload %s does not apply to profile %s" % (workload_id, profile_id))

    wanted: List[str] = []
    for rid in workload["roles"] + workload.get("by_profile", {}).get(profile_id, []):
        if rid not in wanted:
            wanted.append(rid)
    roles, excluded = [], []
    for rid in wanted:
        fleet = fleet_of(rid)
        if fleet not in profile["fleets"]:
            excluded.append({"id": rid, "reason": "profile %s does not activate fleet %s" % (profile_id, fleet)})
            continue
        if fleet not in docs:
            docs[fleet] = reg.load(fleet_file(fleet, "roles"))
        role = next((r for r in docs[fleet]["roles"] if r["id"] == rid), None)
        if role is None:
            raise ResolveError("workload %s names unknown role %s" % (workload_id, rid))
        roles.append({
            "id": rid,
            "fleet": fleet,
            "kind": role["kind"],
            "display_name": role["display_name"],
            "skills": [{"id": s["id"], "path": "skills/%s/SKILL.md" % s["id"],
                        "installed": reg.skill_installed(s["id"]),
                        **({"blocked_reason": s["blocked_reason"]} if "blocked_reason" in s else {})}
                       for s in role["skills"]],
        })
    return {
        "profile": profile_id,
        "workload": workload_id,
        "coordinator": next((r["id"] for r in roles if r["kind"] == "coordinator"), None),
        "roles": roles,
        "excluded": excluded,
        "files_read": list(reg.files_read),
    }
