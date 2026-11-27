"""Adapter over yysun/project-manager's agent-execution scripts (state authority in yysun-led mode).

These scripts are deterministic state transitions, not a scheduler. They accept evidence in the
right shape but do not check it is true (a probe accepted a fabricated hash), so every evidence
record built here comes from something this process actually computed or read.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
from typing import Any, Dict, List, Optional

from .canon import sha_file


class YysunError(Exception):
    def __init__(self, message: str, envelope: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.envelope = envelope


def _run(skill_dir: str, script: str, args: List[str], stdin: Optional[str] = None) -> Dict[str, Any]:
    cmd = ["node", os.path.join(skill_dir, "scripts", script)] + args + ["--json"]
    proc = subprocess.run(cmd, input=stdin, capture_output=True, text=True, timeout=120)
    raw = proc.stdout.strip() or proc.stderr.strip()
    try:
        env = json.loads(raw)
    except ValueError:
        raise YysunError("%s produced non-JSON output (exit %d): %s" % (script, proc.returncode, raw[:300]))
    if proc.returncode != 0 or not env.get("ok"):
        raise YysunError("%s failed: %s" % (script, json.dumps(env.get("errors"))[:400]), env)
    return env


def validate(skill_dir: str, project: str) -> Dict[str, Any]:
    return _run(skill_dir, "project-validate.js", [project])


def start_agent(skill_dir: str, project: str, task_id: str) -> Dict[str, Any]:
    return _run(skill_dir, "project-start-agent.js", [project, task_id])["data"]


def ingest(skill_dir: str, project: str, task_id: str, manifest: Dict[str, Any]) -> Dict[str, Any]:
    return _run(skill_dir, "project-ingest-agent-manifest.js", [project, task_id], stdin=json.dumps(manifest))["data"]


def contract_payload(contract_path: str) -> Dict[str, Any]:
    with open(contract_path, "r", encoding="utf-8") as fh:
        text = fh.read()
    for line in text.split("\n"):
        if line.startswith('{"created_at"') or line.startswith('{"project"'):
            return json.loads(line)
    raise YysunError("no payload line in %s" % contract_path)


def active_contract(project: str, task_id: str) -> Dict[str, Any]:
    """Return {contract_id, spec_sha256, path} for the task's active Task Contract."""
    base = os.path.join(project, "handoffs", task_id)
    if not os.path.isdir(base):
        raise YysunError("no handoffs for %s" % task_id)
    # newest contract directory by the created_at inside the payload
    best = None
    for name in os.listdir(base):
        path = os.path.join(base, name, "TASK-CONTRACT.md")
        if os.path.isfile(path):
            payload = contract_payload(path)
            if best is None or payload["created_at"] > best[0]["created_at"]:
                best = (payload, name, path)
    if best is None:
        raise YysunError("no TASK-CONTRACT.md under %s" % base)
    return {"contract_id": best[1], "spec_sha256": best[0]["task"]["spec_sha256"], "path": best[2],
            "acceptance": best[0]["task"]["acceptance"]}


def build_manifest(project_id: str, task_id: str, ac: Dict[str, Any], sequence: int, observed_at: str,
                   commit_sha: str, verify_ref: str, verify_result: str, verify_log: str,
                   review_ref: str, review_result: str, review_file: str, status: str = "verified",
                   blocker: Optional[str] = None) -> Dict[str, Any]:
    """Evidence Manifest from computed facts: file hashes are read from disk, never supplied."""
    evidence = [
        {"kind": "commit", "ref": commit_sha, "result": "candidate tree is the integrated tree", "sha256": None},
        {"kind": "command", "ref": verify_ref, "result": verify_result, "sha256": None},
        {"kind": "artifact", "ref": verify_log, "result": "verify output captured", "sha256": sha_file(verify_log)},
        {"kind": "review", "ref": review_ref, "result": review_result, "sha256": None},
        {"kind": "artifact", "ref": review_file, "result": "review record bound to candidate", "sha256": sha_file(review_file)},
    ]
    return {
        "schema_version": 1, "sequence": sequence, "contract_id": ac["contract_id"],
        "project": {"id": project_id}, "task": {"id": task_id, "spec_sha256": ac["spec_sha256"]},
        "status": status, "blocker": blocker, "evidence": evidence,
        "acceptance_evidence": {a: list(evidence) for a in ac["acceptance"]},
        "sources": [], "observed_at": observed_at, "notes": [],
    }


def task_status(project: str, task_id: str) -> Optional[str]:
    from .contract import load_tasks
    t = load_tasks(project).get(task_id)
    return t.get("status") if t else None


def project_id(project: str) -> str:
    with open(os.path.join(project, "PROJECT.md"), "r", encoding="utf-8") as fh:
        m = re.search(r'^id: "([^"]+)"', fh.read(), re.M)
    if not m:
        raise YysunError("PROJECT.md has no id")
    return m.group(1)
