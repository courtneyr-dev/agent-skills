"""Task contracts, dependency graph validation and the executable frontier.

The authoritative delivery state (a tracker or yysun `.projects`) supplies task status and
dependencies. A rig contract adds what execution needs and the tracker does not hold: the
accepted specification revision, required decisions, eligible backends, and a verify command.
A task is on the frontier for a backend only when every check passes; each rejection carries
its reasons so the router can explain why work did not start.
"""
from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from .canon import sha, sha_file

CONTRACT_KEYS = {
    "schema_version", "task_id", "repo", "title", "spec", "depends_on", "required_decisions",
    "backends", "base_branch", "verify", "acceptance",
}
ID_RE = re.compile(r"^[A-Z](?:[A-Z0-9-]{0,62}[A-Z0-9])$")
KNOWN_BACKENDS = {"noodle", "pmo", "curia", "implement-spec", "t3"}


def contract_hash(contract: Dict[str, Any]) -> str:
    return sha(contract)


def validate_contract(c: Any) -> List[str]:
    errs: List[str] = []
    if not isinstance(c, dict):
        return ["contract must be an object"]
    missing = CONTRACT_KEYS - set(c)
    extra = set(c) - CONTRACT_KEYS
    if missing:
        errs.append("missing keys: " + ", ".join(sorted(missing)))
    if extra:
        errs.append("unknown keys: " + ", ".join(sorted(extra)))
    if errs:
        return errs
    if c["schema_version"] != 1:
        errs.append("schema_version must be 1")
    if not (isinstance(c["task_id"], str) and ID_RE.match(c["task_id"])):
        errs.append("task_id malformed")
    for key in ("repo", "title", "base_branch"):
        if not (isinstance(c[key], str) and c[key].strip()):
            errs.append(key + " must be a non-empty string")
    spec = c["spec"]
    if not (isinstance(spec, dict) and set(spec) == {"id", "revision", "sha256"}
            and all(isinstance(spec[k], str) and spec[k] for k in spec)):
        errs.append("spec must be exactly {id, revision, sha256} non-empty strings")
    for key in ("depends_on", "required_decisions", "backends", "acceptance"):
        if not (isinstance(c[key], list) and all(isinstance(x, str) and x for x in c[key])):
            errs.append(key + " must be a list of non-empty strings")
    if isinstance(c.get("backends"), list):
        if not c["backends"]:
            errs.append("backends must not be empty")
        bad = [b for b in c["backends"] if b not in KNOWN_BACKENDS]
        if bad:
            errs.append("unknown backends: " + ", ".join(bad))
    if isinstance(c.get("acceptance"), list) and not c["acceptance"]:
        errs.append("acceptance must not be empty")
    if isinstance(c.get("acceptance"), list) and len(set(c["acceptance"])) != len(c["acceptance"]):
        errs.append("acceptance strings must be unique")
    v = c["verify"]
    if not (isinstance(v, dict) and set(v) == {"argv"} and isinstance(v["argv"], list)
            and v["argv"] and all(isinstance(x, str) for x in v["argv"])):
        errs.append("verify must be {argv: [non-empty list of strings]} (never a shell string)")
    return errs


def find_cycles(deps: Dict[str, List[str]]) -> List[List[str]]:
    """Return a list of cycles (each a list of ids) in a dependency map; ids outside the map are ignored."""
    WHITE, GREY, BLACK = 0, 1, 2
    color = {k: WHITE for k in deps}
    cycles: List[List[str]] = []
    stack: List[str] = []

    def visit(n: str) -> None:
        color[n] = GREY
        stack.append(n)
        for m in deps.get(n, []):
            if m not in deps:
                continue
            if color[m] == GREY:
                cycles.append(stack[stack.index(m):] + [m])
            elif color[m] == WHITE:
                visit(m)
        stack.pop()
        color[n] = BLACK

    for node in list(deps):
        if color[node] == WHITE:
            visit(node)
    return cycles


# ---------------------------------------------------------------- workspace loading

def parse_frontmatter(text: str) -> Dict[str, Any]:
    """Frontmatter where each value is single-line JSON (the yysun grammar) or a bare scalar."""
    out: Dict[str, Any] = {}
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return out
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        v = v.strip()
        try:
            out[k.strip()] = json.loads(v)
        except ValueError:
            out[k.strip()] = v
    return out


def parse_tasks_md(text: str) -> Dict[str, Dict[str, Any]]:
    """Parse yysun TASKS.md: `## ID - title` followed by one fenced json object."""
    tasks: Dict[str, Dict[str, Any]] = {}
    pattern = re.compile(r"^## ([A-Z][A-Z0-9-]*[A-Z0-9]) - (.*?)\n+```json\n(.*?)\n```", re.S | re.M)
    for m in pattern.finditer(text):
        rec = json.loads(m.group(3))
        rec["_title"] = m.group(2).strip()
        tasks[m.group(1)] = rec
    return tasks


def load_tasks(project_dir: str) -> Dict[str, Dict[str, Any]]:
    with open(os.path.join(project_dir, "TASKS.md"), "r", encoding="utf-8") as fh:
        return parse_tasks_md(fh.read())


def load_contracts(rig_dir: str) -> Dict[str, Dict[str, Any]]:
    out: Dict[str, Dict[str, Any]] = {}
    cdir = os.path.join(rig_dir, "contracts")
    if not os.path.isdir(cdir):
        return out
    for name in sorted(os.listdir(cdir)):
        if name.endswith(".json"):
            with open(os.path.join(cdir, name), "r", encoding="utf-8") as fh:
                out[name[:-5]] = json.load(fh)
    return out


def load_spec(specs_dir: str, spec_id: str) -> Optional[Dict[str, Any]]:
    path = os.path.join(specs_dir, spec_id + ".md")
    if not os.path.isfile(path):
        return None
    with open(path, "r", encoding="utf-8") as fh:
        fm = parse_frontmatter(fh.read())
    fm["_sha256"] = sha_file(path)
    return fm


def frontier(tasks: Dict[str, Dict[str, Any]], contracts: Dict[str, Dict[str, Any]],
             specs_dir: str, backend: str) -> Tuple[List[str], Dict[str, List[str]]]:
    """Return (eligible task ids, {task id: [reasons]}) for one backend."""
    eligible: List[str] = []
    rejected: Dict[str, List[str]] = {}
    deps_map = {tid: list(t.get("depends_on", [])) for tid, t in tasks.items()}
    cyclic = {n for cyc in find_cycles(deps_map) for n in cyc}
    for tid, task in sorted(tasks.items()):
        why: List[str] = []
        if task.get("status") != "ready":
            why.append("status is %s, not ready" % task.get("status"))
        if task.get("blocked_by"):
            why.append("explicit blockers: %s" % "; ".join(task["blocked_by"]))
        if tid in cyclic:
            why.append("task is in a dependency cycle")
        for d in task.get("depends_on", []):
            if d not in tasks:
                why.append("dependency %s does not exist" % d)
            elif tasks[d].get("status") != "done":
                why.append("dependency %s is %s, not done" % (d, tasks[d].get("status")))
        c = contracts.get(tid)
        if c is None:
            why.append("no rig contract")
        else:
            cerrs = validate_contract(c)
            if cerrs:
                why.extend("contract: " + e for e in cerrs)
            else:
                if c["task_id"] != tid:
                    why.append("contract task_id %s does not match" % c["task_id"])
                if sorted(c["depends_on"]) != sorted(task.get("depends_on", [])):
                    why.append("contract depends_on differs from tracker")
                if backend not in c["backends"]:
                    why.append("backend %s not eligible (contract allows %s)" % (backend, ",".join(c["backends"])))
                spec = load_spec(specs_dir, c["spec"]["id"])
                if spec is None:
                    why.append("specification %s not found" % c["spec"]["id"])
                else:
                    if spec.get("status") != "accepted":
                        why.append("specification %s is %s, not accepted" % (c["spec"]["id"], spec.get("status")))
                    if str(spec.get("revision")) != c["spec"]["revision"]:
                        why.append("specification revision %s differs from contract %s" % (spec.get("revision"), c["spec"]["revision"]))
                    if spec["_sha256"] != c["spec"]["sha256"]:
                        why.append("specification bytes changed since the contract was written")
                    decisions = spec.get("decisions", {})
                    for dec in c["required_decisions"]:
                        if decisions.get(dec) != "accepted":
                            why.append("decision %s is %s, not accepted" % (dec, decisions.get(dec, "missing")))
        if why:
            rejected[tid] = why
        else:
            eligible.append(tid)
    return eligible, rejected
