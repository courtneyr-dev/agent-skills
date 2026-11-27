"""Disposable fixture workspace: a git repo, an accepted spec, a yysun project and rig contracts.

Used by the tests and by `python3 -m factory_rig.fixture <dir>` for the pilot. The feature is small and
real: add `multiply` to a tiny calculator with tests.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from typing import Any, Dict, List, Optional

from .canon import sha_file

SPEC = """---
schema_version: 1
id: "SPEC-MUL"
revision: "1"
status: "accepted"
decisions: {"DEC-INTEGER-ONLY": "accepted"}
---

# SPEC-MUL: multiply

`calc.multiply(a, b)` returns the product of two integers. It raises `TypeError` for non-integer input
(DEC-INTEGER-ONLY: floats and strings are rejected; bool is rejected too).
"""

CALC = '''"""Tiny calculator."""


def add(a, b):
    return a + b
'''

TEST_CALC = '''import unittest

import calc


class AddTests(unittest.TestCase):
    def test_add(self):
        self.assertEqual(calc.add(2, 3), 5)


if __name__ == "__main__":
    unittest.main()
'''


def sh(cwd: str, *args: str) -> str:
    return subprocess.run(list(args), cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


def build(root: str, skill_dir: str, extra_tasks: Optional[List[Dict[str, Any]]] = None) -> str:
    os.makedirs(root, exist_ok=True)
    root = os.path.realpath(root)  # yysun refuses symlinked workspace roots (macOS /var -> /private/var)
    repo = os.path.join(root, "repo")
    os.makedirs(repo)
    sh(repo, "git", "init", "-q", "-b", "main")
    sh(repo, "git", "config", "user.email", "fixture@example.invalid")
    sh(repo, "git", "config", "user.name", "Fixture")
    with open(os.path.join(repo, "calc.py"), "w") as fh:
        fh.write(CALC)
    with open(os.path.join(repo, "test_calc.py"), "w") as fh:
        fh.write(TEST_CALC)
    with open(os.path.join(repo, ".gitignore"), "w") as fh:
        fh.write("__pycache__/\n")
    with open(os.path.join(repo, ".noodle.toml"), "w") as fh:
        fh.write('mode = "supervised"\n\n[skills]\npaths = [".agents/skills"]\n')
    from . import noodle_setup
    noodle_setup.install(repo)
    sh(repo, "git", "add", "-A")
    sh(repo, "git", "commit", "-q", "-m", "Initial calculator")
    os.makedirs(os.path.join(root, "specs"))
    spec_path = os.path.join(root, "specs", "SPEC-MUL.md")
    with open(spec_path, "w") as fh:
        fh.write(SPEC)

    tasks = [
        {"id": "TASK-MUL", "title": "Add multiply to calc", "status": "ready",
         "outcome": "calc.multiply exists and is tested.", "acceptance": ["multiply returns the product of two integers",
                                                                           "multiply rejects non-integer input with TypeError"],
         "depends_on": []},
        {"id": "TASK-DOC", "title": "Document multiply", "status": "planned",
         "outcome": "README documents multiply.", "acceptance": ["README mentions multiply"], "depends_on": ["TASK-MUL"]},
    ] + (extra_tasks or [])
    tmd = ["---", "schema_version: 1", "---", ""]
    for t in tasks:
        rec = {"outcome": t["outcome"], "acceptance": t["acceptance"], "status": t["status"],
               "executor": {"provider": "agent", "scope": "absolute", "root": repo}}
        if t["depends_on"]:
            rec["depends_on"] = t["depends_on"]
        blocks = [o["id"] for o in tasks if t["id"] in o["depends_on"]]  # yysun requires the reverse link
        if blocks:
            rec["blocks"] = blocks
        if t.get("blocked_by"):
            rec["blocked_by"] = t["blocked_by"]
        tmd += ["## %s - %s" % (t["id"], t["title"]), "", "```json", json.dumps(rec), "```", ""]
    proj = '''---
schema_version: 1
id: "RIGPILOT"
name: "Rig pilot"
status: "active"
owner: null
start_date: null
target_date: null
current_milestone: null
profile: "standard"
adapters: ["human", "agent"]
created: "2026-11-25"
updated: "2026-11-25"
---

## Objective

Prove the factory rig end to end on a disposable repository.

## Success Criteria

- [SC-MUL] calc.multiply is merged with verified evidence.
'''
    payload = json.dumps({"project_md": proj, "tasks_md": "\n".join(tmd)})
    p = subprocess.run(["node", os.path.join(skill_dir, "scripts", "project-init-workspace.js"), root, "pilot", "--json"],
                       input=payload, capture_output=True, text=True)
    if p.returncode != 0:
        raise RuntimeError("yysun init failed: " + (p.stdout + p.stderr)[:500])

    rig = os.path.join(root, ".factory-rig")
    os.makedirs(os.path.join(rig, "contracts"))
    cfg = {"repo_name": "rig-pilot", "repo_dir": "repo", "project": ".projects/pilot", "specs_dir": "specs",
           "integration_branch": "main", "yysun_skill_dir": skill_dir, "state_root": ".factory-rig/state",
           "noodle_runtime": ".noodle"}
    with open(os.path.join(rig, "config.json"), "w") as fh:
        json.dump(cfg, fh, indent=2)
    spec_sha = sha_file(spec_path)
    for t in tasks:
        contract = {
            "schema_version": 1, "task_id": t["id"], "repo": "rig-pilot", "title": t["title"],
            "spec": {"id": "SPEC-MUL", "revision": "1", "sha256": spec_sha}, "depends_on": t["depends_on"],
            "required_decisions": ["DEC-INTEGER-ONLY"], "backends": ["noodle", "pmo"], "base_branch": "main",
            "verify": {"argv": ["python3", "-m", "unittest", "-v"]}, "acceptance": t["acceptance"],
        }
        with open(os.path.join(rig, "contracts", t["id"] + ".json"), "w") as fh:
            json.dump(contract, fh, indent=2, sort_keys=True)
    return root


if __name__ == "__main__":
    default = os.environ.get("FRIG_YYSUN_SKILL") or os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "project-manager")
    skill = os.path.abspath(os.path.expanduser(sys.argv[2] if len(sys.argv) > 2 else default))
    print(build(sys.argv[1], skill))
