"""Tenant and data-classification boundaries for records and handoffs.

A record stays inside its tenant unless it is public, an approved abstraction, or covered by a grant in
the tenant owner's own record. The caller passes that owner-recorded grant list; a grant written on the
record itself is the requester's claim and counts for nothing. Student records and moderation cases are
refused before any grant is read: no grant moves them across tenants. An approved abstraction is a
separate derived record (derived_from names its source) classified public or internal; the flag on a
confidential or restricted record lifts nothing.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

LEVEL = {"public": 0, "internal": 1, "confidential": 2, "restricted": 3}
NEVER_SHARED_BY_DEFAULT = {"student-record", "moderation-case"}


def can_read(principal: Dict[str, Any], record: Dict[str, Any],
             owner_grants: Optional[Iterable[Dict[str, Any]]] = None) -> Tuple[bool, str]:
    """principal: {tenant_id, max_classification}. record: {id, tenant_id, classification, category, ...}.
    owner_grants: grants from the record tenant's owner record, loaded by the caller; record["grants"] is ignored."""
    if LEVEL[record["classification"]] > LEVEL[principal["max_classification"]]:
        return False, "%s is %s, above the reader's %s clearance" % (record["id"], record["classification"], principal["max_classification"])
    if record["tenant_id"] == principal["tenant_id"]:
        return True, "same tenant"
    if record.get("category") in NEVER_SHARED_BY_DEFAULT:
        return False, "%s is a %s and is never shared across tenants by default; no grant moves it, it never crosses tenants" % (record["id"], record["category"])
    for g in owner_grants or ():
        if g.get("tenant_id") == principal["tenant_id"] and str(g.get("approved_by", "")).startswith("human:"):
            return True, "owner-recorded grant approved by %s" % g["approved_by"]
    if record["classification"] == "public":
        return True, "public"
    if record.get("approved_abstraction") is True:
        if record.get("derived_from") and LEVEL[record["classification"]] <= LEVEL["internal"]:
            return True, "approved abstraction derived from %s" % record["derived_from"]
        return False, ("%s is %s and flagged as an abstraction; only a separate derived record (derived_from set, "
                       "public or internal) crosses tenants" % (record["id"], record["classification"]))
    return False, "%s belongs to tenant %s" % (record["id"], record["tenant_id"])


def destination_errors(h: Dict[str, Any]) -> List[str]:
    errors = []
    level = LEVEL[h["data"]["classification"]]
    for dest in h["data"]["allowed_destinations"]:
        kind, _, target = dest.partition(":")
        if kind == "tenant" and target != h["tenant_id"]:
            errors.append("destination %s is outside tenant %s" % (dest, h["tenant_id"]))
        if kind == "external":
            if h["authority"]["external_actions"] != "human-approved":
                errors.append("external destination %s needs external_actions=human-approved" % dest)
            if level >= LEVEL["confidential"]:
                errors.append("external destination %s cannot receive %s data" % (dest, h["data"]["classification"]))
    return errors


def input_errors(h: Dict[str, Any]) -> List[str]:
    """Each input must be readable by the handoff's own tenant at the handoff's label, through can_read.
    Student records and moderation cases also stay inside the producer's fleet and tenant."""
    errors = []
    reader = {"tenant_id": h["tenant_id"], "max_classification": h["data"]["classification"]}
    sensitive = False
    for i in h["inputs"]:
        ok, why = can_read(reader, {"id": i["ref"], "tenant_id": i["tenant_id"], "classification": i["classification"],
                                    "category": i.get("category")})
        if not ok:
            errors.append("input %s: %s" % (i["ref"], why))
        sensitive = sensitive or i.get("category") in NEVER_SHARED_BY_DEFAULT
    if sensitive:
        fleet = h["producer"].split(".", 1)[0]
        nxt = h["next_consumer"]
        if not nxt.startswith("human:") and nxt.split(".", 1)[0] != fleet:
            errors.append("handoff carries student records or moderation cases; next consumer %s is outside fleet %s" % (nxt, fleet))
        for dest in h["data"]["allowed_destinations"]:
            if dest != "tenant:" + h["tenant_id"]:
                errors.append("handoff carries student records or moderation cases; destination %s is outside tenant %s"
                              % (dest, h["tenant_id"]))
    return errors
