"""Durable completion receipts with idempotent, resumable steps.

Completing a task has ordered side effects that cannot be one transaction:
  1. integrate   (candidate lands on the integration branch)
  2. state       (authoritative tracker records the task verified/done with evidence)
  3. release     (lease released)
A receipt records intent BEFORE step 1 and each step after it succeeds. `reconcile` re-derives
what actually happened from the real systems and completes only the missing steps, so a crash or a
duplicate callback between any two steps neither loses completion nor completes twice. A failed
callback leaves a visible non-complete receipt; nothing is dropped silently.
"""
from __future__ import annotations

import json
import os
import time
from typing import Any, Callable, Dict, List, Optional

from .canon import atomic_write, sha

STEPS = ["intent", "integrated", "state_recorded", "complete"]


def idempotency_key(task_id: str, attempt_id: str, contract_hash: str, candidate_sha: str) -> str:
    return sha({"task": task_id, "attempt": attempt_id, "contract": contract_hash, "candidate": candidate_sha})[:32]


class ReceiptStore:
    def __init__(self, root: str):
        self.root = root
        os.makedirs(root, exist_ok=True)

    def _path(self, key: str) -> str:
        return os.path.join(self.root, key + ".json")

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        p = self._path(key)
        if not os.path.exists(p):
            return None
        with open(p, "r", encoding="utf-8") as fh:
            return json.load(fh)

    def begin(self, key: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create the receipt at `intent`; an existing receipt is returned unchanged (duplicate callback)."""
        cur = self.get(key)
        if cur is not None:
            return cur
        rec = {"key": key, "step": "intent", "created_at": time.time(), "data": data, "log": [
            {"step": "intent", "at": time.time()}]}
        atomic_write(self._path(key), json.dumps(rec, indent=2, sort_keys=True) + "\n")
        return rec

    def advance(self, key: str, step: str, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        rec = self.get(key)
        if rec is None:
            raise KeyError(key)
        if STEPS.index(step) <= STEPS.index(rec["step"]):
            return rec  # idempotent: already at or past this step
        if STEPS.index(step) != STEPS.index(rec["step"]) + 1:
            raise ValueError("cannot move receipt %s from %s to %s" % (key, rec["step"], step))
        rec["step"] = step
        rec["log"].append({"step": step, "at": time.time(), **(extra or {})})
        if extra:
            rec["data"].update(extra)
        atomic_write(self._path(key), json.dumps(rec, indent=2, sort_keys=True) + "\n")
        return rec

    def find_attempt(self, attempt_id: str) -> Optional[Dict[str, Any]]:
        for name in sorted(os.listdir(self.root)):
            if name.endswith(".json"):
                rec = self.get(name[:-5])
                if rec and rec["data"].get("attempt_id") == attempt_id:
                    return rec
        return None

    def open_receipts(self) -> List[Dict[str, Any]]:
        out = []
        for name in sorted(os.listdir(self.root)):
            if name.endswith(".json"):
                rec = self.get(name[:-5])
                if rec and rec["step"] != "complete":
                    out.append(rec)
        return out

    def reconcile(self, inspect_integrated: Callable[[Dict[str, Any]], bool],
                  inspect_state: Callable[[Dict[str, Any]], bool],
                  finish: Callable[[Dict[str, Any]], None]) -> List[Dict[str, Any]]:
        """Advance every open receipt to what the real world already shows; report what stays unresolved.

        inspect_integrated(data): did the candidate tree land? inspect_state(data): does the tracker
        show the task done with this contract's manifest? finish(data): release the lease. Steps the
        world does not show are NOT advanced; the caller decides whether to redo them.
        """
        report: List[Dict[str, Any]] = []
        for rec in self.open_receipts():
            key, data = rec["key"], rec["data"]
            if rec["step"] == "intent" and inspect_integrated(data):
                rec = self.advance(key, "integrated", {"observed": "candidate tree on integration branch"})
            if rec["step"] == "integrated" and inspect_state(data):
                rec = self.advance(key, "state_recorded", {"observed": "tracker shows done with manifest"})
            if rec["step"] == "state_recorded":
                finish(data)
                rec = self.advance(key, "complete")
            report.append({"key": key, "step": rec["step"], "task_id": data.get("task_id")})
        return report
