"""Client for Noodle's supported control interface (runtime-dir control.ndjson + control-ack.ndjson).

Protocol (read from loop/control.go at the pinned revision): take an flock on control.lock, append
one JSON command per line to control.ndjson; the loop reads and truncates the file under the same
lock and appends an ack line per command id to control-ack.ndjson. Actions seen in
dispatchControlCommand: pause resume drain skip kill steer merge reject request-changes mode enqueue
stop-all requeue edit-item reorder stop set-max-concurrency advance add-stage park-review.
This module only sends commands the rig needs: enqueue, merge, kill, stop-all, drain.
"""
from __future__ import annotations

import fcntl
import json
import os
import time
import uuid
from typing import Any, Dict, List, Optional

ALLOWED = {"enqueue", "merge", "kill", "stop-all", "drain", "pause", "resume", "mode"}


def send(runtime_dir: str, command: Dict[str, Any]) -> str:
    if command.get("action") not in ALLOWED:
        raise ValueError("control action %r is not in the rig's allowed set" % command.get("action"))
    cmd = dict(command)
    cmd.setdefault("id", "frig-" + uuid.uuid4().hex[:16])
    os.makedirs(runtime_dir, exist_ok=True)
    lock = os.path.join(runtime_dir, "control.lock")
    fd = os.open(lock, os.O_CREAT | os.O_RDWR, 0o644)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        with open(os.path.join(runtime_dir, "control.ndjson"), "a", encoding="utf-8") as fh:
            fh.write(json.dumps(cmd, sort_keys=True) + "\n")
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)
    return cmd["id"]


def acks(runtime_dir: str) -> List[Dict[str, Any]]:
    p = os.path.join(runtime_dir, "control-ack.ndjson")
    if not os.path.exists(p):
        return []
    out = []
    with open(p, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    pass
    return out


def wait_ack(runtime_dir: str, cmd_id: str, timeout: float = 60.0, poll: float = 0.5) -> Optional[Dict[str, Any]]:
    deadline = time.time() + timeout
    while time.time() < deadline:
        for a in acks(runtime_dir):
            if a.get("id") == cmd_id:
                return a
        time.sleep(poll)
    return None


def pending_review(runtime_dir: str) -> List[Dict[str, Any]]:
    p = os.path.join(runtime_dir, "pending-review.json")
    if not os.path.exists(p):
        return []
    with open(p, "r", encoding="utf-8") as fh:
        return json.load(fh).get("items", [])
