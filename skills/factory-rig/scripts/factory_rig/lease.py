"""Atomic workload ownership across backends and checkouts.

Key = logical repo name + task id (not a path), so two checkouts or two backends contend for
the same lease. The critical section holds an flock, so acquisition is atomic on one host and
the lock vanishes if its holder dies. A lease carries a monotonically increasing epoch (a fencing
token): every later write (heartbeat, release, receipt, merge) must present the current epoch,
so a worker that lost its lease cannot mutate the workload.

Expiry alone never reclaims a lease. A takeover needs proof the previous holder cannot continue:
its process is gone (pid absent, or the pid now belongs to a different process start time), or an
explicit `fence` terminated it and verified the exit. A live holder past expiry marks the lease
`uncertain` and blocks everyone until an operator or `fence` resolves it.
"""
from __future__ import annotations

import fcntl
import hashlib
import json
import os
import signal
import subprocess
import time
from contextlib import contextmanager
from typing import Any, Dict, Iterator, List, Optional

from .canon import atomic_write


class LeaseDenied(Exception):
    def __init__(self, reason: str, holder: Optional[Dict[str, Any]] = None):
        super().__init__(reason)
        self.reason = reason
        self.holder = holder


class StaleEpoch(Exception):
    pass


def process_fingerprint(pid: int) -> Optional[str]:
    """Return the process start time string, or None when the pid is not running."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return None
    except PermissionError:
        pass
    try:
        out = subprocess.run(["ps", "-o", "stat=,lstart=", "-p", str(pid)], capture_output=True, text=True, timeout=5).stdout.strip()
    except Exception:
        return None
    if not out or out.startswith("Z"):  # a zombie has exited and cannot mutate anything
        return None
    return out.split(None, 1)[1] if " " in out else out


def lease_key(repo: str, task_id: str) -> str:
    return hashlib.sha256((repo + "\0" + task_id).encode()).hexdigest()[:24]


class LeaseStore:
    def __init__(self, root: str):
        self.root = root
        os.makedirs(root, exist_ok=True)

    # ------------------------------------------------------------ internals
    def _paths(self, key: str):
        return (os.path.join(self.root, key + ".lock"), os.path.join(self.root, key + ".json"),
                os.path.join(self.root, key + ".history.jsonl"))

    @contextmanager
    def _locked(self, key: str) -> Iterator[None]:
        lockp = self._paths(key)[0]
        fd = os.open(lockp, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def _read(self, key: str) -> Optional[Dict[str, Any]]:
        p = self._paths(key)[1]
        if not os.path.exists(p):
            return None
        with open(p, "r", encoding="utf-8") as fh:
            return json.load(fh)

    def _write(self, key: str, rec: Dict[str, Any]) -> None:
        atomic_write(self._paths(key)[1], json.dumps(rec, indent=2, sort_keys=True) + "\n")

    def _history(self, key: str, event: Dict[str, Any]) -> None:
        with open(self._paths(key)[2], "a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, sort_keys=True) + "\n")

    # ------------------------------------------------------------ public API
    def acquire(self, repo: str, task_id: str, contract_hash: str, backend: str, attempt_id: str,
                worktree: str, owner_pid: int, ttl: float = 600.0, now: Optional[float] = None) -> Dict[str, Any]:
        now = time.time() if now is None else now
        key = lease_key(repo, task_id)
        with self._locked(key):
            cur = self._read(key)
            epoch = 1
            if cur is not None:
                epoch = cur["epoch"] + 1
                if cur["state"] in ("active", "uncertain"):
                    holder = {k: cur[k] for k in ("backend", "attempt_id", "owner_pid", "epoch", "expires_at", "state")}
                    if cur["state"] == "active" and cur["expires_at"] > now:
                        raise LeaseDenied("held by %s (attempt %s) until %.0f" % (cur["backend"], cur["attempt_id"], cur["expires_at"]), holder)
                    fp = process_fingerprint(cur["owner_pid"])
                    if fp is not None and fp == cur.get("owner_fingerprint"):
                        cur["state"] = "uncertain"
                        self._write(key, cur)
                        self._history(key, {"event": "uncertain", "at": now, "epoch": cur["epoch"], "owner_pid": cur["owner_pid"]})
                        raise LeaseDenied("lease expired but holder pid %d is still running; fence it first" % cur["owner_pid"], holder)
                    self._history(key, {"event": "superseded", "at": now, "epoch": cur["epoch"], "attempt_id": cur["attempt_id"],
                                        "reason": "holder process gone"})
            rec = {
                "repo": repo, "task_id": task_id, "contract_hash": contract_hash, "backend": backend,
                "attempt_id": attempt_id, "worktree": worktree, "owner_pid": owner_pid,
                "owner_fingerprint": process_fingerprint(owner_pid), "epoch": epoch, "state": "active",
                "acquired_at": now, "heartbeat_at": now, "expires_at": now + ttl,
            }
            self._write(key, rec)
            self._history(key, {"event": "acquired", "at": now, "epoch": epoch, "backend": backend, "attempt_id": attempt_id})
            return rec

    def _check(self, key: str, epoch: int) -> Dict[str, Any]:
        cur = self._read(key)
        if cur is None or cur["epoch"] != epoch or cur["state"] != "active":
            raise StaleEpoch("epoch %s is not the current active lease" % epoch)
        return cur

    def heartbeat(self, repo: str, task_id: str, epoch: int, ttl: float = 600.0, now: Optional[float] = None) -> Dict[str, Any]:
        now = time.time() if now is None else now
        key = lease_key(repo, task_id)
        with self._locked(key):
            cur = self._check(key, epoch)
            cur["heartbeat_at"] = now
            cur["expires_at"] = now + ttl
            self._write(key, cur)
            return cur

    def assert_current(self, repo: str, task_id: str, epoch: int) -> Dict[str, Any]:
        key = lease_key(repo, task_id)
        with self._locked(key):
            return self._check(key, epoch)

    def release(self, repo: str, task_id: str, epoch: int, outcome: str, now: Optional[float] = None) -> Dict[str, Any]:
        now = time.time() if now is None else now
        key = lease_key(repo, task_id)
        with self._locked(key):
            cur = self._check(key, epoch)
            cur["state"] = "released"
            cur["outcome"] = outcome
            cur["released_at"] = now
            self._write(key, cur)
            self._history(key, {"event": "released", "at": now, "epoch": epoch, "outcome": outcome})
            return cur

    def status(self, repo: str, task_id: str) -> Optional[Dict[str, Any]]:
        key = lease_key(repo, task_id)
        with self._locked(key):
            return self._read(key)

    def history(self, repo: str, task_id: str) -> List[Dict[str, Any]]:
        p = self._paths(lease_key(repo, task_id))[2]
        if not os.path.exists(p):
            return []
        with open(p, "r", encoding="utf-8") as fh:
            return [json.loads(l) for l in fh if l.strip()]

    @staticmethod
    def _signal(pid: int, sig: int) -> None:
        """Signal the holder's process group, unless that group is our own: then signal only the holder.

        A holder that shares the caller's group (started from the same shell, for example) must not take the
        caller down with it.
        """
        try:
            pg = os.getpgid(pid)
        except ProcessLookupError:
            return
        if pg == os.getpgrp():
            os.kill(pid, sig)
        else:
            os.killpg(pg, sig)

    def fence(self, repo: str, task_id: str, grace: float = 5.0, now: Optional[float] = None,
              expected_epoch: Optional[int] = None) -> Dict[str, Any]:
        """Terminate the holder process and verify it exited. Only then is the lease takeover-safe.

        Side effects the holder already made stay visible in the worktree and history; fencing
        stops further mutation, it does not undo anything.
        """
        now = time.time() if now is None else now
        key = lease_key(repo, task_id)
        with self._locked(key):
            cur = self._read(key)
            if cur is None or cur["state"] == "released":
                raise LeaseDenied("nothing to fence")
            if expected_epoch is not None and cur["epoch"] != expected_epoch:
                raise StaleEpoch("lease is at epoch %s, not the expected %s: a newer holder may be live" % (cur["epoch"], expected_epoch))
            pid = cur["owner_pid"]
            fp = process_fingerprint(pid)
            if fp is not None and fp == cur.get("owner_fingerprint"):
                self._signal(pid, signal.SIGTERM)
                deadline = time.time() + grace
                while time.time() < deadline and process_fingerprint(pid) == fp:
                    time.sleep(0.1)
                if process_fingerprint(pid) == fp:
                    self._signal(pid, signal.SIGKILL)
                    time.sleep(0.2)
                if process_fingerprint(pid) == fp:
                    raise LeaseDenied("holder pid %d survived SIGKILL; cannot establish it stopped" % pid)
            cur["state"] = "fenced"
            cur["fenced_at"] = now
            self._write(key, cur)
            self._history(key, {"event": "fenced", "at": now, "epoch": cur["epoch"], "owner_pid": pid,
                                "note": "side effects already made by the holder remain unverified"})
            return cur
