"""handoff.v1: open, update, validate, check evidence freshness, and record idempotently.

Field authority is a table, not a convention. The contract owner sets OWNER_FIELDS when the handoff
opens; a worker may only add WORKER_FIELDS; SYSTEM_FIELDS are computed here. An instruction a worker
picked up from untrusted content therefore cannot move authority, tenant, acceptance criteria or
publication rules: apply_worker_update refuses those fields and reports the attempt, and the gate
compares every owner field with the write-once record the owner opened (owner_errors), so editing
the handoff file afterward fails too.

Hashing, contract validation and the idempotency key come from factory-rig (canon, contract,
receipts), so a handoff is bound to the same contract hash the merge gate checks.
"""
from __future__ import annotations

import copy
import json
import os
import tempfile
from typing import Any, Dict, List, Tuple

from factory_rig.canon import atomic_write, canonical, sha, sha_bytes, sha_file
from factory_rig.contract import contract_hash, validate_contract
from factory_rig.receipts import idempotency_key as receipt_key

from .schema import Schemas
from .tenancy import destination_errors, input_errors

OWNER_FIELDS = (
    "handoff_id", "workload_id", "tenant_id", "client_id", "operating_profile", "outcome", "scope",
    "exclusions", "acceptance_criteria", "sources", "producer", "reviewer", "acceptance_owner",
    "execution_owner", "data", "authority", "budget", "stop_conditions", "cancellation",
    "next_consumer", "readiness_criteria", "contract_hash",
)
WORKER_FIELDS = ("inputs", "outputs", "evidence", "summary", "assumptions", "unresolved_decisions", "untrusted_findings")
SYSTEM_FIELDS = ("schema_version", "idempotency_key", "reconciliation_state")


def key_for(h: Dict[str, Any]) -> str:
    """Same handoff, parties, contract and output bytes give the same key, however often it is retried."""
    outputs = sorted((o["path"], o["sha256"]) for o in h.get("outputs", []))
    attempt = "%s:%s->%s" % (h["handoff_id"], h["producer"], h["next_consumer"])
    return receipt_key(h["workload_id"], attempt, h["contract_hash"], sha(outputs))


def open_handoff(owner: Dict[str, Any]) -> Dict[str, Any]:
    unknown = set(owner) - set(OWNER_FIELDS)
    if unknown:
        raise ValueError("only the contract owner's fields may open a handoff; got " + ", ".join(sorted(unknown)))
    h = dict(copy.deepcopy(owner), schema_version=1, reconciliation_state="submitted",
             inputs=[], outputs=[], evidence=[], summary="Not started.", assumptions=[], unresolved_decisions=[],
             untrusted_findings=[])
    h["idempotency_key"] = key_for(h)
    return h


def apply_worker_update(h: Dict[str, Any], update: Dict[str, Any]) -> Tuple[Dict[str, Any], List[Dict[str, str]]]:
    """Apply only worker-writable fields. Lists are appended, summary is replaced. Returns (new handoff, refused fields)."""
    new = copy.deepcopy(h)
    refused = []
    for field, value in update.items():
        if field not in WORKER_FIELDS:
            refused.append({"field": field, "reason": "protected: only the contract owner sets %s" % field})
        elif field == "summary":
            new["summary"] = value
        else:
            new[field] = new[field] + list(value)
    new["idempotency_key"] = key_for(new)
    return new, refused


def validate_handoff(h: Any) -> List[str]:
    errors = Schemas().validate(h, "handoff.schema.json")
    if errors:
        return errors
    if h["acceptance_owner"] == h["producer"]:
        errors.append("producer %s cannot be its own acceptance owner" % h["producer"])
    if h["reviewer"] == h["producer"]:
        errors.append("producer %s cannot review its own output" % h["producer"])
    if h["idempotency_key"] != key_for(h):
        errors.append("idempotency_key does not match the workload, parties, contract and outputs")
    outputs = {o["path"] for o in h["outputs"]}
    for ev in h["evidence"]:
        if ev["about"] not in outputs:
            errors.append("evidence %s is about %s, which is not an output" % (ev["path"], ev["about"]))
        if ev["path"] in outputs:
            errors.append("evidence %s is itself an output; an output cannot be its own evidence" % ev["path"])
    errors.extend(destination_errors(h))
    errors.extend(input_errors(h))
    return errors


def owner_errors(h: Dict[str, Any], opened: Dict[str, Any]) -> List[str]:
    """Every owner field must equal the record the contract owner opened."""
    return ["protected field %s differs from the record the owner opened" % f
            for f in OWNER_FIELDS if h.get(f) != opened.get(f)]


def evidence_errors(h: Dict[str, Any], contract: Dict[str, Any], base: str) -> List[str]:
    """Recompute every hash now. Evidence counts only if it was produced for these exact output bytes
    under this exact contract, and the evidence file itself names the output hash it reviewed, so
    rehashing a changed output without a new review leaves the old review stale."""
    errors = ["contract: " + e for e in validate_contract(contract)]
    current = contract_hash(contract)
    if h["contract_hash"] != current:
        errors.append("handoff is bound to contract %s but the contract is now %s" % (h["contract_hash"][:12], current[:12]))
    if not h["outputs"]:
        errors.append("handoff has no outputs, so there is nothing for evidence to back")
    now: Dict[str, str] = {}
    for o in h["outputs"]:
        p = os.path.join(base, o["path"])
        if not os.path.isfile(p):
            errors.append("output %s is missing" % o["path"])
            continue
        now[o["path"]] = sha_file(p)
        if now[o["path"]] != o["sha256"]:
            errors.append("output %s changed after the handoff recorded it" % o["path"])
    fresh = set()
    for ev in h["evidence"]:
        p = os.path.join(base, ev["path"])
        if not os.path.isfile(p):
            errors.append("evidence %s is missing" % ev["path"])
            continue
        with open(p, "rb") as fh:
            data = fh.read()
        stale = []
        if sha_bytes(data) != ev["sha256"]:
            stale.append("its file was edited after it was recorded")
        if ev["about_sha256"] not in data.decode("utf-8", "replace"):
            stale.append("it does not name the output hash it reviewed (add the line reviewed-sha256: %s)" % ev["about_sha256"])
        if ev["contract_hash"] != current:
            stale.append("it was produced under contract %s, not the current %s" % (ev["contract_hash"][:12], current[:12]))
        if ev["about_sha256"] != now.get(ev["about"]):
            stale.append("it checked a different version of %s" % ev["about"])
        if stale:
            errors.append("stale evidence %s: %s" % (ev["path"], "; ".join(stale)))
        elif ev["path"] not in now:
            fresh.add(ev["about"])
    for path in sorted(set(now) - fresh):
        errors.append("output %s has no fresh evidence" % path)
    return errors


def gate_errors(h: Any, opened: Dict[str, Any], contract: Dict[str, Any], base: str) -> List[str]:
    """Everything the next consumer needs before it may start: shape, owner fields, tenancy, fresh evidence."""
    errors = validate_handoff(h)
    if errors:
        return errors
    return owner_errors(h, opened) + evidence_errors(h, contract, base)


def _publish(path: str, obj: Any) -> bool:
    """Create path with obj's JSON, or return False if it already exists. link() makes the create exclusive."""
    fd, tmp = tempfile.mkstemp(prefix=".tmp-", dir=os.path.dirname(path))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.write(json.dumps(obj, indent=2, sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.link(tmp, path)
        return True
    except FileExistsError:
        return False
    finally:
        os.unlink(tmp)


def _read(path: str) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        return None


class Ledger:
    """opened/<handoff_id>.json is the owner's write-once record; submitted/<key>.json holds one file per
    idempotency key. A retry is a no-op, a different body under the same key is refused, two racing
    submitters cannot both win, and the state a caller sends is ignored: every submission starts
    `submitted` and only reconcile settles it."""

    def __init__(self, root: str):
        self.opened = os.path.join(root, "opened")
        self.submitted = os.path.join(root, "submitted")
        os.makedirs(self.opened, exist_ok=True)
        os.makedirs(self.submitted, exist_ok=True)

    def open(self, owner: Dict[str, Any]) -> Dict[str, Any]:
        h = open_handoff(owner)
        path = os.path.join(self.opened, h["handoff_id"] + ".json")
        if not _publish(path, {f: h[f] for f in OWNER_FIELDS}) and _read(path) != {f: h[f] for f in OWNER_FIELDS}:
            raise ValueError("handoff %s is already open with different owner fields" % h["handoff_id"])
        return h

    def opened_record(self, handoff_id: str) -> Any:
        return _read(os.path.join(self.opened, handoff_id + ".json"))

    def get(self, key: str) -> Any:
        return _read(os.path.join(self.submitted, key + ".json"))

    @staticmethod
    def _body(h: Dict[str, Any]) -> str:
        return canonical({k: v for k, v in h.items() if k != "reconciliation_state"})

    def submit(self, h: Dict[str, Any]) -> Dict[str, Any]:
        errors = validate_handoff(h)
        opened = self.opened_record(h["handoff_id"]) if not errors else None
        if not errors and opened is None:
            errors = ["handoff %s was never opened by its owner" % h["handoff_id"]]
        elif opened is not None:
            errors = owner_errors(h, opened)
        if errors:
            return {"status": "invalid", "errors": errors}
        key = h["idempotency_key"]
        if _publish(os.path.join(self.submitted, key + ".json"), dict(h, reconciliation_state="submitted")):
            return {"status": "recorded", "key": key}
        existing = self.get(key)
        if existing is not None and self._body(existing) == self._body(h):
            return {"status": "duplicate", "key": key, "state": existing["reconciliation_state"]}
        return {"status": "conflict", "key": key, "errors": ["a different handoff body already holds key %s" % key]}

    def reconcile(self, contract: Dict[str, Any], base: str) -> List[Dict[str, Any]]:
        """Move each submitted handoff to accepted or rejected from the gate recomputed now. Settled records are left alone."""
        report = []
        for name in sorted(os.listdir(self.submitted)):
            if not name.endswith(".json"):
                continue
            path = os.path.join(self.submitted, name)
            h = _read(path)
            if h["reconciliation_state"] == "submitted":
                errs = gate_errors(h, self.opened_record(h["handoff_id"]) or {}, contract, base)
                h["reconciliation_state"] = "rejected" if errs else "accepted"
                atomic_write(path, json.dumps(h, indent=2, sort_keys=True) + "\n")
                report.append({"key": name[:-5], "state": h["reconciliation_state"], "errors": errs})
        return report
