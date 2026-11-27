#!/usr/bin/env python3
"""evalrun: run the hosting fleet's script evaluation cases and keep raw evidence.

  expect --exit N [--exit M]... [--json PATH=VALUE]... [--contains S]... [--absent S]... -- CMD...
      Run CMD and echo its output. Exit 0 when CMD's exit code is one of N, M, ..., every JSON
      PATH in CMD's stdout equals VALUE, every S appears and no absent S appears. Exit 1 when an
      expectation is not met. Exit 3 when CMD itself exits 3 (blocked: a missing capability) and 3
      was not expected. Every "{tmp}" in CMD becomes one fresh temp folder, deleted afterward.
  run [--only ID]... [--write] [--in-place]
      Run every case in fleets/hosting/evals.json whose check.method is "script", with cwd set to
      the company-fleets root of a temporary copy of the skills root (fleetlib's eval sandbox), so a
      case's writes, owner ledgers included, land in the copy. Print each result. Only with --write:
      save raw output to fleets/hosting/evidence/evals/<slug>.txt and set outcome.status (exit 0
      pass, exit 3 blocked, anything else fail), evidence and run_on. Failures stay on record.
      Without --write nothing on disk changes. --in-place runs the cases in the real tree instead:
      use it only with --only for read-only cases that need a folder Docker shares.
  skills [--write]
      For each hosting-* skill in skills.json: run skill-creator's quick_validate (through uv,
      offline) and the skill's unit tests under this Python and under /usr/bin/python3 when that system interpreter exists.
      With --write, save the raw log to fleets/hosting/evidence/skill-tests.txt.
  roles
      Refuse a role whose behavioral state is verified, or a model-judgment case whose outcome is pass
      or fail, unless its evidence file names a grader (a "# Grader:" line) other than the fleet's
      builder. The builder can't grade its own fleet.

Python 3.9+ standard library only. Exit 0 ok, 1 a case failed, 2 usage.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import shlex
import shutil
import subprocess
import sys
import tempfile
from typing import Any, List, Optional

FLEET = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
CF = os.path.normpath(os.path.join(FLEET, "..", ".."))
SKILLS_ROOT = os.path.dirname(CF)
EVALS = os.path.join(FLEET, "evals.json")
SKILLS = os.path.join(FLEET, "skills.json")
TIMEOUT = 300
BLOCKED = 3
ROLES = os.path.join(FLEET, "roles.json")
FLEET_BUILDER = "the coordinating hosting-workstream agent"
QUICK_VALIDATE = os.environ.get("FLEET_QUICK_VALIDATE", "")  # skill-creator's quick_validate.py; unset skips that step


def _lookup(doc: Any, path: str) -> Any:
    node = doc
    for part in path.split("."):
        if isinstance(node, list):
            node = node[int(part)]
        else:
            node = node[part]
    return node


def _parse_value(text: str) -> Any:
    try:
        return json.loads(text)
    except ValueError:
        return text


def _expect(args: argparse.Namespace) -> int:
    if not args.cmd:
        print("expect: no command after --", file=sys.stderr)
        return 2
    scratch = tempfile.mkdtemp(prefix="hosting-eval-") if any("{tmp}" in a for a in args.cmd) else None
    try:
        cmd = [a.replace("{tmp}", scratch) for a in args.cmd] if scratch else args.cmd
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=TIMEOUT)
    finally:
        if scratch:
            shutil.rmtree(scratch, ignore_errors=True)
    out = proc.stdout + proc.stderr
    sys.stdout.write(out if out.endswith("\n") or not out else out + "\n")
    if proc.returncode == BLOCKED and BLOCKED not in args.exit:
        print("# expect: BLOCKED (command exited 3: missing capability)")
        return BLOCKED
    problems = []
    if proc.returncode not in args.exit:
        problems.append("exit %d, expected %s" % (proc.returncode, " or ".join(map(str, args.exit))))
    if args.json:
        try:
            doc = json.loads(proc.stdout)
        except ValueError:
            doc = None
            problems.append("stdout is not JSON")
        if doc is not None:
            for spec in args.json:
                path, _, raw = spec.partition("=")
                try:
                    got = _lookup(doc, path)
                except (KeyError, IndexError, ValueError, TypeError):
                    problems.append("JSON path %s is missing" % path)
                    continue
                if got != _parse_value(raw):
                    problems.append("JSON %s is %s, expected %s" % (path, json.dumps(got), raw))
    problems += ["missing %r" % s for s in args.contains if s not in out]
    problems += ["unexpected %r" % s for s in args.absent if s in out]
    print("# expect: %s" % ("met" if not problems else "NOT MET: " + "; ".join(problems)))
    return 0 if not problems else 1


def _write_json(path: str, doc: Any) -> None:
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=2, ensure_ascii=False)
        fh.write("\n")
    os.replace(tmp, path)


def _sandbox() -> Any:
    sys.path.insert(0, os.path.join(CF, "scripts"))
    from fleetlib.evalrun import Sandbox
    return Sandbox(CF)


def _run(args: argparse.Namespace) -> int:
    with open(EVALS, encoding="utf-8") as fh:
        doc = json.load(fh)
    today = datetime.date.today().isoformat()
    results, counts = [], {"pass": 0, "fail": 0, "blocked": 0}
    box = None if args.in_place else _sandbox()
    try:
        for case in doc["evals"]:
            if case.get("check", {}).get("method") != "script" or (args.only and case["id"] not in args.only):
                continue
            status, code, rel = _one(case, box.root if box else CF, today, args.write, args.in_place)
            counts[status] += 1
            results.append({"id": case["id"], "status": status, "exit": code, "evidence": rel})
    finally:
        if box:
            box.close()
    if args.write:
        _write_json(EVALS, doc)
    print(json.dumps({"ran": len(results), "counts": counts, "in_place": args.in_place, "results": results}, indent=2))
    return 0 if counts["fail"] == 0 else 1


def _one(case: Any, cwd: str, today: str, write: bool, in_place: bool) -> Any:
    slug = case["id"].split(".eval.", 1)[1]
    rel = "fleets/hosting/evidence/evals/%s.txt" % slug
    argv = case["check"]["argv"]
    try:
        proc = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=TIMEOUT)
        code, out = proc.returncode, proc.stdout + proc.stderr
    except (OSError, subprocess.TimeoutExpired) as exc:
        code, out = 127, "runner error: %s\n" % exc
    status = "pass" if code == 0 else "blocked" if code == BLOCKED else "fail"
    if write:
        dest = os.path.join(CF, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        where = "company-fleets root, in place" if in_place else "company-fleets root of a temporary copy"
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write("$ %s\n# run %s (cwd: %s) case %s kind %s synthetic %s\n%s# exit %d\n" % (
                shlex.join(argv), today, where, case["id"], case["kind"], str(case.get("synthetic", False)).lower(),
                out if out.endswith("\n") or not out else out + "\n", code))
        outcome = {"status": status, "evidence": rel, "run_on": today}
        if status == "blocked":
            outcome["note"] = "Script exited 3 (missing capability); raw output in %s" % rel
        case["outcome"] = outcome
    return status, code, rel


def _grader(rel: str) -> Optional[str]:
    try:
        with open(os.path.join(CF, rel), encoding="utf-8") as fh:
            for line in fh:
                if line.startswith("# Grader:"):
                    return line.split(":", 1)[1].strip().rstrip(".").lower()
    except OSError:
        return None
    return None


def _roles(args: argparse.Namespace) -> int:
    with open(ROLES, encoding="utf-8") as fh:
        roles = json.load(fh)["roles"]
    with open(EVALS, encoding="utf-8") as fh:
        cases = json.load(fh)["evals"]
    claims = [(r["id"], r["verification"]["behavioral"].get("evidence")) for r in roles
              if r["verification"]["behavioral"]["state"] == "verified"]
    claims += [(c["id"], c["outcome"].get("evidence")) for c in cases
               if c["check"]["method"] == "model-judgment" and c["outcome"]["status"] in ("pass", "fail")]
    problems = []
    for ident, rel in claims:
        grader = _grader(rel) if rel else None
        if not grader:
            problems.append({"id": ident, "evidence": rel, "problem": "no '# Grader:' line in the evidence"})
        elif FLEET_BUILDER in grader:
            problems.append({"id": ident, "evidence": rel, "problem": "graded by the fleet's builder (%s)" % FLEET_BUILDER})
    print(json.dumps({"checked": len(claims), "verdict": "fail" if problems else "ok", "problems": problems}, indent=2))
    return 1 if problems else 0


def _skills(args: argparse.Namespace) -> int:
    with open(SKILLS, encoding="utf-8") as fh:
        records = json.load(fh)["skills"]
    lines = ["# hosting skill checks, run %s" % datetime.datetime.now().isoformat(timespec="seconds"),
             "# quick_validate: %s" % (QUICK_VALIDATE or "skipped, FLEET_QUICK_VALIDATE is not set")]
    failed = 0
    for rec in records:
        sid = rec["id"]
        if not sid.startswith("hosting-"):
            continue
        sdir = os.path.join(SKILLS_ROOT, sid)
        steps = [
            ("quick_validate", ["uv", "run", "--offline", "--no-project", "--with", "pyyaml", "python",
                                QUICK_VALIDATE, sdir], "/tmp"),
        ] if QUICK_VALIDATE else []
        steps += [
            ("unittest " + sys.version.split()[0], [sys.executable, "-W", "ignore", "-m", "unittest", "discover",
                                                    "-s", "tests"], os.path.join(sdir, "scripts")),
        ]
        if os.path.exists("/usr/bin/python3"):
            steps.append(("unittest /usr/bin/python3", ["/usr/bin/python3", "-W", "ignore", "-m", "unittest", "discover",
                                                        "-s", "tests"], os.path.join(sdir, "scripts")))
        for name, argv, cwd in steps:
            try:
                proc = subprocess.run(argv, cwd=cwd, capture_output=True, text=True, timeout=TIMEOUT)
                code, out = proc.returncode, (proc.stdout + proc.stderr).strip()
            except (OSError, subprocess.TimeoutExpired) as exc:
                code, out = 127, "runner error: %s" % exc
            failed += code != 0
            tail = "\n".join(out.splitlines()[-3:])
            lines.append("== %s :: %s :: exit %d\n$ %s\n%s" % (sid, name, code, shlex.join(argv), tail))
    lines.append("# failed steps: %d" % failed)
    text = "\n".join(lines) + "\n"
    sys.stdout.write(text)
    if args.write:
        with open(os.path.join(FLEET, "evidence", "skill-tests.txt"), "w", encoding="utf-8") as fh:
            fh.write(text)
    return 0 if failed == 0 else 1


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    cmd: List[str] = []
    if "--" in argv:
        i = argv.index("--")
        argv, cmd = argv[:i], argv[i + 1:]
    ap = argparse.ArgumentParser(prog="evalrun")
    sub = ap.add_subparsers(dest="mode", required=True)
    e = sub.add_parser("expect")
    e.add_argument("--exit", type=int, action="append", required=True)
    e.add_argument("--json", action="append", default=[])
    e.add_argument("--contains", action="append", default=[])
    e.add_argument("--absent", action="append", default=[])
    r = sub.add_parser("run")
    r.add_argument("--only", action="append", default=[])
    r.add_argument("--write", action="store_true")
    r.add_argument("--in-place", dest="in_place", action="store_true")
    s = sub.add_parser("skills")
    s.add_argument("--write", action="store_true")
    sub.add_parser("roles")
    try:
        args = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    if args.mode == "expect":
        args.cmd = cmd
        return _expect(args)
    if args.mode == "run":
        return _run(args)
    if args.mode == "roles":
        return _roles(args)
    return _skills(args)


if __name__ == "__main__":
    sys.exit(main())
