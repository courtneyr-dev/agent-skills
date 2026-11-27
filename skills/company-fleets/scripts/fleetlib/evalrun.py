"""eval-run: one runner and one assertion format for every fleet's script eval cases.

A case either carries check.expect {exit, contains, absent, json} beside a raw argv, or wraps its argv
in one of the per-fleet runners (corporate run_evals.py, product expect.py, bcit-education evalrun.py,
hosting evalrun.py). A wrapped argv is parsed into the same expect shape, honoring that runner's
options ({tmp}, --env, --json, the python3 rewrite and its timeout), so every case is judged by one
engine without editing any evals.json. A raw argv with no expect passes on exit 0. Exit 3, when the
case did not expect it, means a capability is missing and the case is blocked.
"""
from __future__ import annotations

import datetime
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, NamedTuple, Optional

from factory_rig.canon import atomic_write

BLOCKED = 3
DEFAULT_TIMEOUT = 600
# Per-fleet runners this engine reads. sub: the runner's subcommand; tmp: substitutes {tmp}; py: rewrites a
# leading python3 to this interpreter; multi_exit: accepts several --exit; json/env: supports that option.
DIALECTS = {
    "fleets/corporate/run_evals.py": dict(sub="expect", timeout=600, tmp=False, py=False, multi_exit=False, json=False, env=True),
    "fleets/product/tests/expect.py": dict(sub=None, timeout=900, tmp=True, py=True, multi_exit=False, json=False, env=False),
    "fleets/bcit-education/evalrun.py": dict(sub="expect", timeout=120, tmp=False, py=False, multi_exit=False, json=False, env=False),
    "fleets/hosting/tools/evalrun.py": dict(sub="expect", timeout=300, tmp=True, py=False, multi_exit=True, json=True, env=False),
}


class PlanError(Exception):
    pass


class Plan(NamedTuple):
    cmd: List[str]
    expect: Dict[str, Any]
    timeout: int
    tmp: bool
    env: Dict[str, str]
    runner: str


def _expect(exit_codes=None, contains=None, absent=None, json_paths=None) -> Dict[str, Any]:
    return {"exit": list(exit_codes) if exit_codes else [0], "contains": list(contains or []),
            "absent": list(absent or []), "json": dict(json_paths or {})}


def _value(raw: str) -> Any:
    try:
        return json.loads(raw)
    except ValueError:
        return raw


def plan(case: Dict[str, Any]) -> Plan:
    check = case["check"]
    argv = list(check["argv"])
    if "expect" in check:
        e = check["expect"]
        return Plan(argv, _expect(e.get("exit"), e.get("contains"), e.get("absent"), e.get("json")),
                    DEFAULT_TIMEOUT, True, {}, "check.expect")
    if len(argv) >= 2 and os.path.basename(argv[0]).startswith("python") and argv[1] in DIALECTS:
        d = DIALECTS[argv[1]]
        rest = argv[2:]
        if d["sub"]:
            if not rest or rest[0] != d["sub"]:
                raise PlanError("%s: only the %s mode is a per-case wrapper" % (argv[1], d["sub"]))
            rest = rest[1:]
        if "--" not in rest:
            raise PlanError("%s: no -- before the command" % argv[1])
        i = rest.index("--")
        opts, cmd = rest[:i], rest[i + 1:]
        codes: List[int] = []
        contains: List[str] = []
        absent: List[str] = []
        paths: Dict[str, Any] = {}
        env: Dict[str, str] = {}
        k = 0
        while k < len(opts):
            flag = opts[k]
            if k + 1 >= len(opts):
                raise PlanError("%s: %s has no value" % (argv[1], flag))
            val = opts[k + 1]
            if flag == "--exit":
                codes = codes + [int(val)] if d["multi_exit"] else [int(val)]
            elif flag == "--contains":
                contains.append(val)
            elif flag == "--absent":
                absent.append(val)
            elif flag == "--json" and d["json"]:
                path, _, raw = val.partition("=")
                paths[path] = _value(raw)
            elif flag == "--env" and d["env"]:
                key, _, value = val.partition("=")
                env[key] = os.path.expanduser(value)
            else:
                raise PlanError("%s: unsupported option %s" % (argv[1], flag))
            k += 2
        if not codes:
            raise PlanError("%s: --exit is required" % argv[1])
        if d["py"] and cmd and cmd[0] == "python3":
            cmd = [sys.executable] + cmd[1:]
        return Plan(cmd, _expect(codes, contains, absent, paths), d["timeout"], d["tmp"], env, argv[1])
    return Plan(argv, _expect(), DEFAULT_TIMEOUT, False, {}, "raw")


def _lookup(doc: Any, path: str) -> Any:
    node = doc
    for part in path.split("."):
        node = node[int(part)] if isinstance(node, list) else node[part]
    return node


def judge(expect: Dict[str, Any], code: int, stdout: str, out: str) -> List[str]:
    """Every expectation that does not hold, as a readable line. Empty means pass."""
    problems = []
    if code not in expect["exit"]:
        problems.append("exit %d, expected %s" % (code, " or ".join(map(str, expect["exit"]))))
    if expect["json"]:
        try:
            doc = json.loads(stdout)
        except ValueError:
            doc = None
            problems.append("stdout is not JSON")
        if doc is not None:
            for path, want in expect["json"].items():
                try:
                    got = _lookup(doc, path)
                except (KeyError, IndexError, ValueError, TypeError):
                    problems.append("JSON path %s is missing" % path)
                    continue
                if got != want:
                    problems.append("JSON %s is %s, expected %s" % (path, json.dumps(got), json.dumps(want)))
    problems += ["missing %r" % s for s in expect["contains"] if s not in out]
    problems += ["unexpected %r" % s for s in expect["absent"] if s in out]
    return problems


def execute(p: Plan, cwd: str) -> Dict[str, Any]:
    scratch = tempfile.mkdtemp(prefix="fleet-eval-") if p.tmp and any("{tmp}" in a for a in p.cmd) else None
    cmd = [a.replace("{tmp}", scratch) for a in p.cmd] if scratch else list(p.cmd)
    try:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=p.timeout,
                              env=dict(os.environ, **p.env))
        code, stdout, out = proc.returncode, proc.stdout, proc.stdout + proc.stderr
    except (OSError, subprocess.TimeoutExpired) as exc:
        code, stdout, out = 127, "", "runner error: %s\n" % exc
    finally:
        if scratch:
            shutil.rmtree(scratch, ignore_errors=True)
    problems = judge(p.expect, code, stdout, out)
    status = "pass" if not problems else "blocked" if code == BLOCKED and BLOCKED not in p.expect["exit"] else "fail"
    return {"status": status, "exit": code, "problems": problems, "output": out}


def script_cases(root: str, fleet: Optional[str] = None, ids: Optional[List[str]] = None):
    """Yield (fleet, evals.json path, document, case) for every script case in scope."""
    base = os.path.join(root, "fleets")
    for f in sorted(os.listdir(base)) if os.path.isdir(base) else []:
        path = os.path.join(base, f, "evals.json")
        if (fleet and f != fleet) or not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
        for case in doc.get("evals", []):
            if case.get("check", {}).get("method") == "script" and (not ids or case["id"] in ids):
                yield f, path, doc, case


def _clone(src: str, dst: str) -> None:
    """Copy a tree once: APFS clones (cp -c) when available, then a plain copy. Symlinks stay symlinks."""
    for argv in (["cp", "-cR", src, dst], ["cp", "-R", src, dst]):
        if subprocess.run(argv, capture_output=True).returncode == 0:
            return
        if os.path.exists(dst):
            raise OSError("partial copy at %s from %s" % (dst, " ".join(argv)))
    shutil.copytree(src, dst, symlinks=True)


def _remove_own_temp(path: str) -> None:
    def force(fn, p, _exc):
        os.chmod(os.path.dirname(p), 0o700)
        os.chmod(p, 0o700)
        fn(p)
    shutil.rmtree(path, onerror=force)


class Sandbox:
    """A temporary copy that case commands run in, so their writes land in the copy. When the registry root is a
    skill (it has a SKILL.md), the copy is its parent skills root, so sibling skills a case calls come along; any
    other root is copied alone. Paths in argv and env that name the copied tree are rewritten to the copy. A
    command that finds the real tree by other means (HOME, a symlink, a hardcoded path) can still reach it."""

    def __init__(self, root: str):
        root = os.path.abspath(root)
        src = os.path.dirname(root) if os.path.isfile(os.path.join(root, "SKILL.md")) else root
        self.tmp = tempfile.mkdtemp(prefix="fleet-eval-sandbox-")
        try:
            real_src, real_tmp = os.path.realpath(src), os.path.realpath(self.tmp)
            if os.path.commonpath([real_src, real_tmp]) == real_src:
                raise OSError("refusing to copy %s into a folder inside itself (%s)" % (src, self.tmp))
            self.copy = os.path.join(self.tmp, os.path.basename(src))
            _clone(src, self.copy)
        except BaseException:
            _remove_own_temp(self.tmp)
            raise
        self.root = self.copy if src == root else os.path.join(self.copy, os.path.basename(root))
        names = {src, real_src}
        home = os.path.expanduser("~")
        names |= {"~" + n[len(home):] for n in (src, real_src) if n.startswith(home + os.sep)}  # tilde forms
        self.pattern = re.compile("|".join(re.escape(n) + r"(?=/|$)" for n in sorted(names, key=len, reverse=True)))

    def rewrite(self, p: Plan) -> Plan:
        fix = lambda a: self.pattern.sub(lambda _m: self.copy, a)
        return p._replace(cmd=[fix(a) for a in p.cmd], env={k: fix(v) for k, v in p.env.items()})

    def close(self) -> None:
        _remove_own_temp(self.tmp)


def run(root: str, fleet: Optional[str] = None, ids: Optional[List[str]] = None, write: bool = False,
        in_place: bool = False) -> Dict[str, Any]:
    """Run every script case in scope inside a temporary copy of the skills root, made once per call.

    The real tree changes only as follows. Without write: nothing. With write: fleets/<fleet>/evidence/<id>.txt
    for each case run, and the outcome of those cases in fleets/<fleet>/evals.json. With in_place: case commands
    run in the real tree, so whatever they write lands there too. "wrote" lists the evidence and evals.json paths."""
    today = datetime.date.today().isoformat()
    cases = list(script_cases(root, fleet, ids))
    results, touched, wrote = [], {}, []
    box = Sandbox(root) if cases and not in_place else None
    try:
        for f, path, doc, case in cases:
            try:
                p = plan(case)
            except (PlanError, ValueError) as exc:
                results.append({"id": case["id"], "fleet": f, "status": "fail", "runner": "unparsed", "problems": [str(exc)]})
                continue
            r = execute(box.rewrite(p), box.root) if box else execute(p, root)
            results.append({"id": case["id"], "fleet": f, "status": r["status"], "exit": r["exit"], "runner": p.runner,
                            "problems": r["problems"]})
            if write:
                rel = "fleets/%s/evidence/%s.txt" % (f, case["id"])
                lines = ["$ %s" % " ".join(case["check"]["argv"]), "# eval-run %s, cwd company-fleets%s, case %s, runner %s"
                         % (today, "" if in_place else " (temporary copy)", case["id"], p.runner),
                         r["output"].rstrip("\n"), "# exit %d" % r["exit"]]
                lines += ["# CHECK %s" % x for x in r["problems"]] + ["# status %s" % r["status"]]
                atomic_write(os.path.join(root, rel), "\n".join(lines) + "\n")
                wrote.append(rel)
                case["outcome"] = {"status": r["status"], "evidence": rel, "run_on": today}
                if r["status"] == "blocked":
                    case["outcome"]["note"] = "The command exited 3 (missing capability); raw output in %s" % rel
                touched[path] = doc
    finally:
        if box:
            box.close()
    for path, doc in touched.items():
        atomic_write(path, json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
        wrote.append(os.path.relpath(path, root))
    counts = {s: sum(1 for r in results if r["status"] == s) for s in ("pass", "fail", "blocked")}
    return {"ran": len(results), "counts": counts, "written": write, "in_place": in_place, "wrote": wrote, "results": results}
