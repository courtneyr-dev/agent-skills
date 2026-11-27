"""Noodle backlog adapter (sync/done/add/edit) with the rig's stricter validation.

Design choice: Noodle's scheduler is an LLM session that turns a non-empty backlog into orders. The
rig's router already chose and validated the work, so `sync` prints nothing by default; that keeps
Noodle's scheduler idle and Noodle an execution backend. Work arrives through `frig dispatch`
(Noodle's own `enqueue` control command), after contract, dependency, decision and lease checks.

`project()` is the strict projection used if a scheduler-mode pilot is ever enabled: it refuses any
item that Noodle's own weaker validation (id + title only) would accept. `done` never mutates tracker
state; it appends the callback to .factory-rig/callbacks.jsonl so a duplicate or interrupted call is
visible and idempotent, and completion stays with the gate and its receipts.
"""
from __future__ import annotations

import json
import os
import sys
import time
from typing import Any, Dict, Iterable, List

REQUIRED = ("id", "title", "status", "contract_hash", "spec_revision", "lease_epoch")


def project(items: Iterable[Dict[str, Any]]) -> List[str]:
    lines: List[str] = []
    seen = set()
    for it in items:
        missing = [k for k in REQUIRED if it.get(k) in (None, "")]
        if missing:
            raise ValueError("item %r missing %s" % (it.get("id"), ", ".join(missing)))
        if it["id"] in seen:
            raise ValueError("duplicate item id %s" % it["id"])
        seen.add(it["id"])
        lines.append(json.dumps(it, sort_keys=True))
    return lines


def record_done(callbacks_path: str, item_id: str) -> bool:
    """Append a done callback once per item id; return False for a duplicate."""
    os.makedirs(os.path.dirname(callbacks_path), exist_ok=True)
    if os.path.exists(callbacks_path):
        with open(callbacks_path, "r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    if json.loads(line).get("id") == item_id:
                        return False
                except ValueError:
                    pass
    with open(callbacks_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"id": item_id, "at": time.time(), "event": "noodle-done-callback"}) + "\n")
    return True


def main(argv: List[str]) -> int:
    if not argv:
        return 2
    op = argv[0]
    if op == "sync":
        return 0  # empty backlog by design: no LLM scheduler session
    if op == "done" and len(argv) == 2:
        record_done(os.path.join(os.environ.get("FRIG_WS", "."), ".factory-rig", "callbacks.jsonl"), argv[1])
        return 0
    if op in ("add", "edit"):
        sys.stderr.write("frig backlog adapter: %s is not supported; use `frig dispatch`\n" % op)
        return 2
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
