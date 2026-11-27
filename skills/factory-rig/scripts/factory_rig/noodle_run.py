"""Bounded foreground runner for Noodle (override NOODLE-SCHEDULER-BUDGET).

Observed 2026-11-25 against the pinned revision: when a worker stage fails, Noodle parks the failure
event "for later recovery" and injects a scheduler session; with a no-op `schedule` stub nothing
resolves the event, "mise changed" resets the cooldown, and the loop starts another scheduler session
every ~15 s (8 real provider calls in 3 minutes). Noodle has no setting that bounds this.

This runner owns the Noodle process so the budget is enforced outside it:
  - stop when more than --max-scheduler-sessions scheduler sessions have been observed (default 3: the one
    Noodle injects at start, one after the enqueue changes mise, one spare), so at most max+1 have started
    (a stop is a poll away; real scheduler sessions take seconds, so overshoot is one session);
  - stop immediately when any worker stage fails (recovery is the router's job, via `frig abandon`);
  - stop at --max-wall seconds;
  - with --exit-when-idle, stop once every attempt's lease is no longer active.
Stops are SIGTERM to the Noodle process group, then SIGKILL after a grace period, and the reason is
written to .factory-rig/noodle-run.json. The Noodle pid is the lease owner pid for `frig dispatch`.
"""
from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import time
from typing import Any, Dict, List, Optional


def count_sessions(runtime_dir: str) -> Dict[str, int]:
    sdir = os.path.join(runtime_dir, "sessions")
    out = {"schedule": 0, "other": 0}
    if os.path.isdir(sdir):
        for name in os.listdir(sdir):
            out["schedule" if name.startswith("schedule-") else "other"] += 1
    return out


def worker_failed(log_path: str) -> bool:
    try:
        with open(log_path, "r", encoding="utf-8", errors="replace") as fh:
            return any("cook exited with status failed" in line for line in fh)
    except FileNotFoundError:
        return False


def stop_group(proc: subprocess.Popen, grace: float = 10.0) -> str:
    try:
        os.killpg(proc.pid, signal.SIGTERM)
    except ProcessLookupError:
        return "already-exited"
    deadline = time.time() + grace
    while time.time() < deadline:
        if proc.poll() is not None:
            return "terminated"
        time.sleep(0.2)
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    proc.wait(timeout=5)
    return "killed"


def run(noodle_bin: str, repo: str, rig_dir: str, runtime_dir: str, active_leases, max_scheduler_sessions: int = 3,
        max_wall: float = 1800.0, exit_when_idle: bool = False, env: Optional[Dict[str, str]] = None,
        poll: float = 1.0, idle_grace: float = 4.0) -> Dict[str, Any]:
    """active_leases() -> number of attempts whose lease is still active (injected so tests need no tracker)."""
    os.makedirs(rig_dir, exist_ok=True)
    log_path = os.path.join(rig_dir, "noodle.log")
    pid_path = os.path.join(rig_dir, "noodle.pid")
    e = dict(os.environ)
    e.update(env or {})
    e.setdefault("NOODLE_NO_BROWSER", "1")
    with open(log_path, "ab") as log:
        proc = subprocess.Popen([noodle_bin, "start"], cwd=repo, env=e, stdout=log, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, start_new_session=True)
    with open(pid_path, "w", encoding="utf-8") as fh:
        fh.write(str(proc.pid))
    started = time.time()
    reason = None
    ever_active = False
    quiet_since: Optional[float] = None
    while reason is None:
        time.sleep(poll)
        if proc.poll() is not None:
            reason = "noodle exited on its own (code %s)" % proc.returncode
            break
        n = count_sessions(runtime_dir)
        if worker_failed(log_path):  # root cause first: a failed worker is what makes the scheduler loop
            reason = "a worker stage failed; recovery belongs to the router"
        elif n["schedule"] > max_scheduler_sessions:
            reason = "scheduler session budget exceeded (%d > %d)" % (n["schedule"], max_scheduler_sessions)
        elif time.time() - started > max_wall:
            reason = "wall clock limit %.0fs reached" % max_wall
        elif exit_when_idle:
            active = active_leases()
            ever_active = ever_active or active > 0
            if ever_active and active == 0:
                quiet_since = quiet_since or time.time()
                if time.time() - quiet_since >= idle_grace:
                    reason = "all leases settled"
            else:
                quiet_since = None
    how = stop_group(proc) if proc.poll() is None else "already-exited"
    result = {"reason": reason, "stop": how, "noodle_pid": proc.pid, "seconds": round(time.time() - started, 1),
              "sessions": count_sessions(runtime_dir), "log": log_path}
    with open(os.path.join(rig_dir, "noodle-run.json"), "w", encoding="utf-8") as fh:
        json.dump(result, fh, indent=2, sort_keys=True)
        fh.write("\n")
    return result
