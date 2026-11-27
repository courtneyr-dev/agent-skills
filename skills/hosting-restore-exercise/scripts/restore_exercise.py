#!/usr/bin/env python3
"""restore_exercise: break a disposable local site on purpose, detect it, restore it, measure it.

  monitor        --url URL | --router FILE  [--expect-rows N] [--timeout S]
  run            --targets T.json [--failure crash|corrupt|delete] [--mode restore|failover]
                 [--seed-rows N] [--writes-after-backup K] [--workdir D] [--report-out PATH] [--handoff-dir H]
  review         --handoff-dir H --targets T.json
  evidence-gate  --handoff-dir H --targets T.json [--workdir D]

run seeds a SQLite-backed site process (site_service.py), backs it up, writes K more rows, injects
the failure, polls the monitor until it reports unhealthy, then either restores the backup into a
fresh data folder and starts a new process (restore), or switches a router file to a warm standby
started from the backup and later fails back to a rebuilt primary (failover). Each target in T.json is
reported met, unmet or not-measured from what this run measured; nothing is rounded toward met.

Three commands, three parties. The producer's `run --handoff-dir H` writes report.json and
monitor-log.jsonl. The reviewer named in the owner's handoff record runs `review`, which re-derives
every target status from the measured values and writes review-check.txt bound to the bytes it saw.
`evidence-gate` then checks the targets file is the spec the contract names (spec.sha256), opens the
company-fleets handoff.v1 from the owner record, shows the fresh evidence passes, and shows an edited
report, an edited monitor log, an edited review and an edited contract each fail as stale.

The contract and the handoff owner record are owner files at fixed paths in the fleet's fixtures
(restore-exercise/contract.json and handoff-owner.json). --contract and --owner are refused by name
unless they name those same files; nothing a caller passes replaces the contract or its hash.

Stdout is JSON. Exit 0 every target met (run) or every stale case rejected (evidence-gate); 1 a target
unmet or not measured, a restore that failed, a monitor that saw a fault, or a gate that accepted stale
evidence; 2 invalid input; 3 blocked (the local service could not start). Python 3.9+ standard library.
"""
from __future__ import annotations

import argparse
import copy
import datetime
import json
import os
import shutil
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL_DIR = os.path.dirname(HERE)
OWNER_FILES = os.path.normpath(os.path.join(SKILL_DIR, "..", "company-fleets", "fleets", "hosting", "fixtures", "restore-exercise"))
CONTRACT = os.path.join(OWNER_FILES, "contract.json")
OWNER_RECORD = os.path.join(OWNER_FILES, "handoff-owner.json")
sys.path.insert(0, HERE)

from site_service import open_existing, rows_digest  # noqa: E402

TARGETS = {"detection_seconds": "max", "rto_seconds": "max", "rpo_lost_writes": "max",
           "restore_success": "required", "failback_success": "required"}
FAILURES = ("crash", "corrupt", "delete")
POLL = 0.05
LIMITS = [
    "One lab run on one idle machine. It is a measured test result, not an availability percentage or a service commitment.",
    "A SQLite file and a local HTTP process stand in for a database server and a hosting node; network, storage and region failures are not exercised.",
    "Writes after the last backup are lost by design here (no log shipping), so rpo_lost_writes equals the writes made after the backup.",
    "The lab monitor polls every 0.05 s on the same machine; a production monitor's polling interval and alert delay set the real detection floor.",
]


class InputError(Exception):
    pass


class Blocked(Exception):
    pass


class Refused(Exception):
    def __init__(self, refusal: str, detail: str) -> None:
        super().__init__(detail)
        self.payload = {"verdict": "refused", "refusal": refusal, "detail": detail}


def owner_file(named: Optional[str], fixed: str, refusal: str, what: str) -> str:
    """An owner file is read from its fixed path; a different path the caller names is refused by name."""
    if named and os.path.realpath(named) != os.path.realpath(fixed):
        raise Refused(refusal, "the %s comes only from the owner's %s; the caller-named %s is refused" % (what, fixed, named))
    return fixed


# ---------------------------------------------------------------- monitor

def local_url(url: str) -> str:
    """The monitor only talks to the disposable local service: http on the loopback interface."""
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != "http" or parts.hostname not in ("127.0.0.1", "localhost", "::1"):
        raise InputError("monitor URL must be http on 127.0.0.1, localhost or ::1, got %r" % url)
    return url


def probe(url: str, timeout: float = 1.0) -> Dict[str, Any]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return {"healthy": bool(body.get("ok")), "status": resp.status, "rows": body.get("rows"),
                    "content_sha256": body.get("content_sha256")}
    except urllib.error.HTTPError as exc:
        try:
            detail = json.loads(exc.read().decode("utf-8")).get("error", "")
        except ValueError:
            detail = ""
        return {"healthy": False, "status": exc.code, "reason": ("HTTP %d %s" % (exc.code, detail)).strip()}
    except (urllib.error.URLError, OSError) as exc:
        reason = getattr(exc, "reason", exc)
        return {"healthy": False, "status": None, "reason": "unreachable: %s" % reason}


def router_url(router: str) -> str:
    with open(router, encoding="utf-8") as fh:
        return local_url(json.load(fh)["active"] + "/health")


def check(url: str, expect_rows: Optional[int], timeout: float) -> Dict[str, Any]:
    res = probe(url, timeout)
    if res["healthy"] and expect_rows is not None and res["rows"] != expect_rows:
        res = dict(res, healthy=False, reason="rows %s, expected %s" % (res["rows"], expect_rows))
    return res


# ---------------------------------------------------------------- the lab

class Lab:
    """Owns every process and file of one exercise, so cleanup is one call."""

    def __init__(self, workdir: str, tenant: str):
        self.workdir, self.tenant = workdir, tenant
        self.procs: List[subprocess.Popen] = []
        self.t0 = time.monotonic()
        self.timeline: List[Dict[str, Any]] = []
        self.monitor_log: List[str] = []

    def at(self) -> float:
        return round(time.monotonic() - self.t0, 3)

    def event(self, name: str, **extra: Any) -> float:
        t = self.at()
        self.timeline.append(dict(extra, t=t, event=name))
        return t

    def seed(self, db: str, rows: int) -> None:
        conn = sqlite3.connect(db)
        try:
            with conn:
                conn.execute("CREATE TABLE posts (id INTEGER PRIMARY KEY, title TEXT NOT NULL)")
                conn.executemany("INSERT INTO posts (title) VALUES (?)",
                                 [("synthetic post %d" % i,) for i in range(1, rows + 1)])
        finally:
            conn.close()

    def start(self, db: str, name: str) -> Tuple[subprocess.Popen, str]:
        port_file = os.path.join(self.workdir, name + ".port")
        proc = subprocess.Popen([sys.executable, os.path.join(HERE, "site_service.py"), "--db", db,
                                 "--port-file", port_file, "--tenant", self.tenant],
                                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        self.procs.append(proc)
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if os.path.exists(port_file):
                with open(port_file, encoding="utf-8") as fh:
                    url = "http://127.0.0.1:%d" % json.load(fh)["port"]
                if probe(url + "/health")["status"] is not None:
                    return proc, url
            if proc.poll() is not None:
                break
            time.sleep(POLL)
        raise Blocked("the local site service %s did not start within 10 s" % name)

    def write(self, url: str, count: int) -> None:
        for _ in range(count):
            req = urllib.request.Request(url + "/write", data=b"", method="POST")
            with urllib.request.urlopen(req, timeout=2) as resp:
                resp.read()

    def backup(self, db: str, name: str) -> Dict[str, Any]:
        dest = os.path.join(self.workdir, "backups", name + ".sqlite")
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        src, dst = open_existing(db), sqlite3.connect(dest)
        try:
            src.backup(dst)
            rows = dst.execute("SELECT count(*) FROM posts").fetchone()[0]
            digest = rows_digest(dst)
        finally:
            dst.close()
            src.close()
        return {"name": name, "path": dest, "rows": rows, "content_sha256": digest}

    def restore(self, backup: Dict[str, Any], db: str) -> Dict[str, Any]:
        os.makedirs(os.path.dirname(db), exist_ok=True)
        src, dst = sqlite3.connect(backup["path"]), sqlite3.connect(db)
        try:
            src.backup(dst)
            rows = dst.execute("SELECT count(*) FROM posts").fetchone()[0]
            digest = rows_digest(dst)
        finally:
            dst.close()
            src.close()
        return {"rows": rows, "content_sha256": digest, "matches_backup": digest == backup["content_sha256"]}

    def inject(self, kind: str, proc: subprocess.Popen, db: str) -> None:
        if kind == "crash":
            proc.send_signal(signal.SIGKILL)
            proc.wait(timeout=5)
        elif kind == "corrupt":
            with open(db, "r+b") as fh:
                fh.write(b"SYNTHETIC CORRUPTION " * 5)
        else:
            for suffix in ("", "-journal", "-wal", "-shm"):
                if os.path.exists(db + suffix):
                    os.remove(db + suffix)

    def wait_for(self, url_fn: Callable[[], str], healthy: bool, expect_rows: Optional[int],
                 limit: float = 30.0) -> Optional[Dict[str, Any]]:
        deadline = time.monotonic() + limit
        while time.monotonic() < deadline:
            res = check(url_fn(), expect_rows if healthy else None, 1.0)
            self.monitor_log.append(json.dumps(dict(res, t=self.at()), sort_keys=True))
            if res["healthy"] == healthy:
                return res
            time.sleep(POLL)
        return None

    def close(self) -> None:
        for proc in self.procs:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)


# ---------------------------------------------------------------- targets

def load_targets(path: str) -> Dict[str, Any]:
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError) as exc:
        raise InputError("cannot read targets %s: %s" % (path, exc))
    targets = doc.get("targets") if isinstance(doc, dict) else None
    if not isinstance(targets, dict) or not targets:
        raise InputError("targets file needs a non-empty 'targets' object")
    for name, spec in targets.items():
        kind = TARGETS.get(name)
        if kind is None:
            raise InputError("unknown target %s; known: %s" % (name, ", ".join(sorted(TARGETS))))
        if not isinstance(spec, dict) or kind not in spec:
            raise InputError("target %s needs a %r field" % (name, kind))
        if kind == "max" and (isinstance(spec["max"], bool) or not isinstance(spec["max"], (int, float)) or spec["max"] < 0):
            raise InputError("target %s max must be a number at or above 0" % name)
        if kind == "required" and spec["required"] is not True:
            raise InputError("target %s required must be true" % name)
    return doc


def judge(targets: Dict[str, Any], measured: Dict[str, Any]) -> Dict[str, Any]:
    out = {}
    for name, spec in sorted(targets.items()):
        value = measured.get(name)
        if value is None:
            status = "not-measured"
        elif TARGETS[name] == "max":
            status = "met" if value <= spec["max"] else "unmet"
        else:
            status = "met" if value is True else "unmet"
        out[name] = {"target": spec, "measured": value, "status": status}
    return out


# ---------------------------------------------------------------- exercise

def run_exercise(targets_path: str, failure: str, mode: str, seed_rows: int, writes_after: int,
                 workdir: str) -> Tuple[Dict[str, Any], List[str]]:
    doc = load_targets(targets_path)
    tenant = doc.get("tenant_id", "tenant-a")
    if failure not in FAILURES or mode not in ("restore", "failover"):
        raise InputError("failure must be one of %s and mode restore or failover" % ", ".join(FAILURES))
    if seed_rows < 1 or writes_after < 0:
        raise InputError("--seed-rows must be at least 1 and --writes-after-backup at least 0")
    if os.path.isdir(workdir) and os.listdir(workdir):
        raise InputError("workdir %s is not empty; every exercise starts from nothing" % workdir)
    lab = Lab(workdir, tenant)
    measured: Dict[str, Any] = {"restore_success": False}
    report: Dict[str, Any] = {}
    try:
        primary_db = os.path.join(workdir, "primary", "site.sqlite")
        os.makedirs(os.path.dirname(primary_db))
        lab.seed(primary_db, seed_rows)
        proc, url = lab.start(primary_db, "primary")
        lab.event("primary-started", url=url)
        backup = lab.backup(primary_db, "backup-1")
        lab.event("backup-taken", rows=backup["rows"])
        router = os.path.join(workdir, "router.json")
        standby_url = None
        if mode == "failover":
            standby = lab.restore(backup, os.path.join(workdir, "standby", "site.sqlite"))
            _, standby_url = lab.start(os.path.join(workdir, "standby", "site.sqlite"), "standby")
            lab.event("standby-started-from-backup", rows=standby["rows"], url=standby_url)
        with open(router, "w", encoding="utf-8") as fh:
            json.dump({"active": url}, fh)
        lab.write(url, writes_after)
        rows_before_failure = probe(url + "/health")["rows"]
        lab.event("writes-after-backup", count=writes_after, rows=rows_before_failure)

        t_fail = lab.event("failure-injected", kind=failure)
        lab.inject(failure, proc, primary_db)
        down =lab.wait_for(lambda: router_url(router), healthy=False, expect_rows=None)
        if down is None:
            raise Blocked("the monitor never saw the injected %s failure within 30 s" % failure)
        t_detect = lab.event("monitor-detected", reason=down.get("reason"))
        measured["detection_seconds"] = round(t_detect - t_fail, 3)
        if failure != "crash":
            proc.terminate()
            proc.wait(timeout=5)

        if mode == "restore":
            restored = lab.restore(backup, os.path.join(workdir, "restored", "site.sqlite"))
            lab.event("backup-restored", **restored)
            _, new_url = lab.start(os.path.join(workdir, "restored", "site.sqlite"), "restored")
            with open(router, "w", encoding="utf-8") as fh:
                json.dump({"active": new_url}, fh)
        else:
            restored = {"rows": backup["rows"], "content_sha256": backup["content_sha256"], "matches_backup": True}
            with open(router, "w", encoding="utf-8") as fh:
                json.dump({"active": standby_url}, fh)
            lab.event("router-switched-to-standby")
        up = lab.wait_for(lambda: router_url(router), healthy=True, expect_rows=backup["rows"])
        t_up = lab.event("monitor-healthy" if up else "monitor-still-unhealthy")
        success = bool(up and restored["matches_backup"] and up.get("content_sha256") == backup["content_sha256"])
        measured["restore_success"] = success
        if success:
            measured["rto_seconds"] = round(t_up - t_fail, 3)
            measured["rpo_lost_writes"] = rows_before_failure - up["rows"]

        if mode == "failover" and success:
            back = lab.backup(os.path.join(workdir, "standby", "site.sqlite"), "backup-2-from-standby")
            rebuilt = lab.restore(back, os.path.join(workdir, "primary-rebuilt", "site.sqlite"))
            _, rebuilt_url = lab.start(os.path.join(workdir, "primary-rebuilt", "site.sqlite"), "primary-rebuilt")
            with open(router, "w", encoding="utf-8") as fh:
                json.dump({"active": rebuilt_url}, fh)
            again = lab.wait_for(lambda: router_url(router), healthy=True, expect_rows=back["rows"])
            measured["failback_success"] = bool(again and rebuilt["matches_backup"]
                                                and again.get("content_sha256") == back["content_sha256"])
            lab.event("failed-back-to-rebuilt-primary", success=measured["failback_success"])

        judged = judge(doc["targets"], measured)
        all_met = all(v["status"] == "met" for v in judged.values())
        verdict = ("restore-failed" if not success else "restored-all-targets-met" if all_met
                   else "restored-targets-not-all-met")
        report = {
            "label": "SYNTHETIC lab exercise for Fixture Co %s; disposable local service, not production." % tenant,
            "exercise": {"tenant_id": tenant, "mode": mode, "failure": failure, "seed_rows": seed_rows,
                         "writes_after_backup": writes_after,
                         "run_at": datetime.datetime.now(datetime.timezone.utc).isoformat(timespec="seconds")},
            "backup": {k: backup[k] for k in ("name", "rows", "content_sha256")},
            "restore": restored, "measured": measured, "targets": judged, "verdict": verdict,
            "unmet": sorted(n for n, v in judged.items() if v["status"] != "met"),
            "timeline": lab.timeline, "monitor_probes": len(lab.monitor_log),
            "assumptions": LIMITS + ["Targets come from %s: %s" % (os.path.basename(targets_path),
                                                                    doc.get("source", "no source stated"))],
        }
    finally:
        lab.close()
    return report, lab.monitor_log


def exit_for(report: Dict[str, Any]) -> int:
    return 0 if report["verdict"] == "restored-all-targets-met" else 1


# ---------------------------------------------------------------- evidence gate

def review_report(report: Dict[str, Any], log: List[str], targets_path: str) -> Dict[str, Any]:
    """The reviewer's own check: re-derive every target status from the measured values and confirm
    the monitor log saw the fault and then the recovery. Nothing here trusts the report's verdict."""
    rederived = judge(load_targets(targets_path)["targets"], report["measured"])
    probes = [json.loads(line) for line in log if line.strip()]
    first_down = next((i for i, p in enumerate(probes) if not p["healthy"]), None)
    recovered = first_down is not None and any(p["healthy"] for p in probes[first_down:])
    return {"statuses_match": all(rederived[n]["status"] == report["targets"][n]["status"] for n in rederived),
            "rederived_statuses": ", ".join("%s=%s" % (n, v["status"]) for n, v in sorted(rederived.items())),
            "monitor_saw_fault_then_recovery": recovered, "monitor_probes": len(probes)}


def _read_json(path: str, what: str) -> Dict[str, Any]:
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError) as exc:
        raise InputError("cannot read %s %s: %s" % (what, path, exc))
    if not isinstance(doc, dict):
        raise InputError("%s %s must be a JSON object" % (what, path))
    return doc


def write_handoff(handoff_dir: str, report: Dict[str, Any], log: List[str]) -> None:
    """The producer's outputs, written by run --handoff-dir."""
    if os.path.isdir(handoff_dir) and os.listdir(handoff_dir):
        raise InputError("--handoff-dir %s is not empty" % handoff_dir)
    os.makedirs(handoff_dir, exist_ok=True)
    with open(os.path.join(handoff_dir, "report.json"), "w", encoding="utf-8") as fh:
        json.dump(report, fh, indent=2, sort_keys=True)
    with open(os.path.join(handoff_dir, "monitor-log.jsonl"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(log) + "\n")


def review(handoff_dir: str, targets: str, owner_path: str = OWNER_RECORD) -> Dict[str, Any]:
    """The reviewer's own step, a separate command: re-derive from the producer's files and bind the review to them."""
    sys.path.insert(0, os.path.normpath(os.path.join(SKILL_DIR, "..", "factory-rig", "scripts")))
    from factory_rig.canon import sha_file
    owner = _read_json(owner_path, "owner record")
    if owner.get("reviewer") == owner.get("producer"):
        return {"verdict": "refused", "refusal": "self-review",
                "detail": "the owner record names %s as both producer and reviewer" % owner.get("producer")}
    report = _read_json(os.path.join(handoff_dir, "report.json"), "report")
    try:
        with open(os.path.join(handoff_dir, "monitor-log.jsonl"), encoding="utf-8") as fh:
            log = fh.read().splitlines()
    except UnicodeDecodeError:
        raise InputError("monitor log %s is not UTF-8 text" % os.path.join(handoff_dir, "monitor-log.jsonl"))
    except OSError as exc:
        raise InputError("cannot read monitor log: %s" % exc)
    rep_sha, log_sha = sha_file(os.path.join(handoff_dir, "report.json")), sha_file(os.path.join(handoff_dir, "monitor-log.jsonl"))
    result = review_report(report, log, targets)
    with open(os.path.join(handoff_dir, "review-check.txt"), "w", encoding="utf-8") as fh:
        fh.write("Review of the restore exercise handoff %s by %s, a separate step after both outputs.\n"
                 % (owner.get("handoff_id"), owner.get("reviewer")))
        fh.write("reviewed-sha256: %s (report.json)\nreviewed-sha256: %s (monitor-log.jsonl)\n" % (rep_sha, log_sha))
        fh.write("".join("%s: %s\n" % (k, v) for k, v in result.items()))
    ok = result["statuses_match"] and result["monitor_saw_fault_then_recovery"]
    return dict(result, verdict="reviewed" if ok else "review-failed", reviewer=owner.get("reviewer"),
                review_sha256=sha_file(os.path.join(handoff_dir, "review-check.txt")))


def evidence_gate(handoff_dir: str, targets: str, workdir: str, contract_path: str = CONTRACT,
                  owner_path: str = OWNER_RECORD) -> Dict[str, Any]:
    if os.path.exists(workdir) and (not os.path.isdir(workdir) or os.listdir(workdir)):
        raise InputError("--workdir %s must be absent or empty; the gate copies the handoff into it" % workdir)
    sys.path.insert(0, os.path.normpath(os.path.join(SKILL_DIR, "..", "company-fleets", "scripts")))
    from fleetlib.handoff import apply_worker_update, evidence_errors, open_handoff, validate_handoff
    from factory_rig.canon import sha_file
    from factory_rig.contract import contract_hash

    contract, owner = _read_json(contract_path, "contract"), _read_json(owner_path, "owner record")
    owner.pop("label", None)
    named = (contract.get("spec") or {}).get("sha256")
    if named != sha_file(targets):
        return {"verdict": "refused", "refusal": "targets-not-in-contract",
                "detail": "the contract's spec.sha256 is %s; the targets file %s hashes to %s" % (named, targets, sha_file(targets))}
    owner["contract_hash"] = contract_hash(contract)
    names = ("report.json", "monitor-log.jsonl", "review-check.txt")
    missing = [n for n in names if not os.path.isfile(os.path.join(handoff_dir, n))]
    if missing:
        return {"verdict": "refused", "refusal": "handoff-incomplete",
                "detail": "%s lacks %s; the producer runs run --handoff-dir, the reviewer runs review" % (handoff_dir, ", ".join(missing))}
    base = os.path.join(workdir, "handoff")
    shutil.copytree(handoff_dir, base)
    report = _read_json(os.path.join(base, "report.json"), "report")
    rep_sha, log_sha = sha_file(os.path.join(base, "report.json")), sha_file(os.path.join(base, "monitor-log.jsonl"))
    chk_sha = sha_file(os.path.join(base, "review-check.txt"))
    try:
        opened = open_handoff(owner)
    except ValueError as exc:
        raise InputError("owner record: %s" % exc)
    h, refused = apply_worker_update(opened, {
        "outputs": [{"path": "report.json", "sha256": rep_sha, "artifact_type": "restore-exercise-report"},
                    {"path": "monitor-log.jsonl", "sha256": log_sha, "artifact_type": "monitor-log"}],
        "evidence": [{"path": "review-check.txt", "sha256": chk_sha, "about": about, "about_sha256": about_sha,
                      "contract_hash": owner["contract_hash"]}
                     for about, about_sha in (("report.json", rep_sha), ("monitor-log.jsonl", log_sha))],
        "summary": "Restore exercise %s; unmet targets: %s" % (report.get("verdict"), ", ".join(report.get("unmet", [])) or "none")})

    def gate(h2: Dict[str, Any], c2: Dict[str, Any], b2: str) -> List[str]:
        return validate_handoff(h2) or evidence_errors(h2, c2, b2)

    def mutated(name: str, edit: Callable[[str, Dict[str, Any]], None]) -> Dict[str, Any]:
        b2 = os.path.join(workdir, name)
        shutil.copytree(base, b2)
        c2 = copy.deepcopy(contract)
        edit(b2, c2)
        errs = gate(h, c2, b2)
        return {"accepted": not errs, "errors": errs}

    def edit_report(b2: str, c2: Dict[str, Any]) -> None:
        p = os.path.join(b2, "report.json")
        with open(p, encoding="utf-8") as fh:
            doc = json.load(fh)
        doc["measured"]["rpo_lost_writes"] = (doc["measured"].get("rpo_lost_writes") or 0) + 1
        for v in doc["targets"].values():
            v["status"] = "unmet" if v["status"] == "met" else "met"
        with open(p, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2, sort_keys=True)

    def edit_log(b2: str, c2: Dict[str, Any]) -> None:
        with open(os.path.join(b2, "monitor-log.jsonl"), "a", encoding="utf-8") as fh:
            fh.write('{"healthy": true, "note": "appended after review"}\n')

    def relax_contract(b2: str, c2: Dict[str, Any]) -> None:
        c2["acceptance"] = ["Any restore counts as success"]

    def edit_review(b2: str, c2: Dict[str, Any]) -> None:
        with open(os.path.join(b2, "review-check.txt"), "a", encoding="utf-8") as fh:
            fh.write("all targets met (appended after review)\n")

    fresh = gate(h, contract, base)
    cases = {"report-edited": mutated("report-edited", edit_report),
             "monitor-log-edited": mutated("log-edited", edit_log),
             "review-check-edited": mutated("review-edited", edit_review),
             "contract-relaxed-after-review": mutated("contract-edited", relax_contract)}
    try:
        with open(os.path.join(base, "monitor-log.jsonl"), encoding="utf-8") as fh:
            log_lines = fh.read().splitlines()
    except UnicodeDecodeError:
        raise InputError("monitor log in %s is not UTF-8 text" % handoff_dir)
    rederived = review_report(report, log_lines, targets)
    if fresh or refused or not rederived["statuses_match"]:
        verdict = "refused"
    elif any(c["accepted"] for c in cases.values()):
        verdict = "gate-accepted-stale-evidence"
    else:
        verdict = "stale-evidence-rejected"
    return {"verdict": verdict, "fresh": {"accepted": not fresh and not refused, "errors": fresh + [str(r) for r in refused]},
            "stale_cases": cases, "review": rederived, "exercise_verdict": report.get("verdict"), "unmet": report.get("unmet"),
            "targets_sha256": contract["spec"]["sha256"],
            "handoff": {"handoff_id": h["handoff_id"], "producer": h["producer"], "reviewer": h["reviewer"],
                        "acceptance_owner": h["acceptance_owner"], "idempotency_key": h["idempotency_key"]},
            "assumptions": ["The gate is company-fleets fleetlib.handoff.evidence_errors over factory-rig hashes; this script only drives it.",
                            "The targets file is the contract's spec: it must hash to spec.sha256, so relaxing a target changes the contract.",
                            "The contract and the owner record are read from their fixed owner paths; a caller can't swap either.",
                            "A process running as the same OS user can rewrite those owner files or run all three steps under any "
                            "listed name; the separation is by command and owner record, and only separate OS accounts or signed "
                            "records close it."]}


# ---------------------------------------------------------------- main

def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="restore_exercise")
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("monitor")
    g = m.add_mutually_exclusive_group(required=True)
    g.add_argument("--url")
    g.add_argument("--router")
    m.add_argument("--expect-rows", type=int)
    m.add_argument("--timeout", type=float, default=1.0)
    r = sub.add_parser("run")
    r.add_argument("--targets", required=True)
    r.add_argument("--failure", default="crash", choices=FAILURES)
    r.add_argument("--mode", default="restore", choices=("restore", "failover"))
    r.add_argument("--seed-rows", type=int, default=20)
    r.add_argument("--writes-after-backup", type=int, default=3)
    r.add_argument("--workdir")
    r.add_argument("--report-out")
    r.add_argument("--handoff-dir", help="write report.json and monitor-log.jsonl here for the reviewer")
    v = sub.add_parser("review")
    v.add_argument("--handoff-dir", required=True)
    v.add_argument("--targets", required=True)
    v.add_argument("--owner", help="refused unless it is the owner's handoff-owner.json")
    e = sub.add_parser("evidence-gate")
    e.add_argument("--handoff-dir", required=True)
    e.add_argument("--targets", required=True)
    e.add_argument("--contract", help="refused unless it is the owner's contract.json")
    e.add_argument("--owner", help="refused unless it is the owner's handoff-owner.json")
    e.add_argument("--workdir")
    args = ap.parse_args(argv)

    def emit(obj: Dict[str, Any]) -> None:
        print(json.dumps(obj, indent=2, sort_keys=True))

    if args.cmd == "monitor":
        try:
            url = router_url(args.router) if args.router else local_url(args.url)
        except InputError as exc:
            emit({"error": str(exc)})
            return 2
        except (OSError, ValueError, KeyError) as exc:
            emit({"error": "cannot read router: %s" % exc})
            return 2
        res = check(url, args.expect_rows, args.timeout)
        emit(dict(res, url=url))
        return 0 if res["healthy"] else 1
    own = getattr(args, "workdir", None) is None and args.cmd != "review"
    workdir = getattr(args, "workdir", None) or (tempfile.mkdtemp(prefix="restore-exercise-") if own else "")
    try:
        if args.cmd == "run":
            report, _ = run_exercise(args.targets, args.failure, args.mode, args.seed_rows,
                                     args.writes_after_backup, os.path.join(workdir, "lab"))
            if args.report_out:
                with open(args.report_out, "w", encoding="utf-8") as fh:
                    json.dump(report, fh, indent=2, sort_keys=True)
            if args.handoff_dir:
                write_handoff(args.handoff_dir, report, _)
            emit(report)
            return exit_for(report)
        owner = owner_file(args.owner, OWNER_RECORD, "owner-record-not-owner-file", "handoff owner record")
        if args.cmd == "review":
            result = review(args.handoff_dir, args.targets, owner)
            emit(result)
            return 0 if result["verdict"] == "reviewed" else 1
        contract = owner_file(args.contract, CONTRACT, "contract-not-owner-file", "contract")
        result = evidence_gate(args.handoff_dir, args.targets, workdir, contract, owner)
        emit(result)
        return 0 if result["verdict"] == "stale-evidence-rejected" else 1
    except Refused as exc:
        emit(exc.payload)
        return 1
    except InputError as exc:
        emit({"error": str(exc)})
        return 2
    except Blocked as exc:
        emit({"blocked": str(exc)})
        return 3
    finally:
        if own:
            shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
