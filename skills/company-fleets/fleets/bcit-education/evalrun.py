#!/usr/bin/env python3
"""evalrun: run script-check evaluation cases for the education fleets and keep raw evidence.

  expect  --exit N [--contains S]... [--absent S]... -- CMD...
          Run CMD, echo its output, exit 0 only when CMD exits N, every S appears and no absent S appears.
  run     --file EVALS_OR_RECORDS.json [--only ID]... [--write]
          Run every case whose check.method is "script" with cwd = the company-fleets root. Without --write
          the raw output goes to a fresh scratch folder (printed in the results), so retained evidence stays
          comparable. With --write it replaces outcome.evidence (default fleets/<fleet>/evidence/evals/<slug>.txt)
          and sets outcome.status to pass or fail and outcome.run_on to today.

Python 3.9+ standard library only. Exit 0 ok, 1 a case failed or the expectation was not met, 2 usage.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import subprocess
import sys
import tempfile
from typing import List, Optional

CF = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
TIMEOUT = 120


def _expect(args: argparse.Namespace) -> int:
    if not args.cmd:
        print("expect: no command after --", file=sys.stderr)
        return 2
    proc = subprocess.run(args.cmd, capture_output=True, text=True, timeout=TIMEOUT)
    out = proc.stdout + proc.stderr
    sys.stdout.write(out)
    problems = []
    if proc.returncode != args.exit:
        problems.append("exit %d, expected %d" % (proc.returncode, args.exit))
    problems += ["missing %r" % s for s in args.contains if s not in out]
    problems += ["unexpected %r" % s for s in args.absent if s in out]
    print("# expect: %s" % ("met" if not problems else "NOT MET: " + "; ".join(problems)))
    return 0 if not problems else 1


def _cases(doc):
    return doc["evals"] if isinstance(doc, dict) and "evals" in doc else []


def _run(args: argparse.Namespace) -> int:
    path = os.path.abspath(args.file)
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    today = datetime.date.today().isoformat()
    scratch = None if args.write else tempfile.mkdtemp(prefix="evalrun-")
    results, failed = [], 0
    for case in _cases(doc):
        if case.get("check", {}).get("method") != "script" or (args.only and case["id"] not in args.only):
            continue
        fleet, _, slug = case["id"].partition(".eval.")
        rel = case.get("outcome", {}).get("evidence") or "fleets/%s/evidence/evals/%s.txt" % (fleet, slug)
        argv = case["check"]["argv"]
        try:
            proc = subprocess.run(argv, cwd=CF, capture_output=True, text=True, timeout=TIMEOUT)
            code, out = proc.returncode, proc.stdout + proc.stderr
        except (OSError, subprocess.TimeoutExpired) as exc:
            code, out = 127, "runner error: %s\n" % exc
        status = "pass" if code == 0 else "fail"
        failed += status == "fail"
        dest = os.path.join(CF, rel) if args.write else os.path.join(scratch, rel.replace("/", "__"))
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        with open(dest, "w", encoding="utf-8") as fh:
            fh.write("$ %s\n# run %s (cwd: company-fleets) case %s\n%s# exit %d\n"
                     % (" ".join(argv), today, case["id"], out if out.endswith("\n") or not out else out + "\n", code))
        if args.write:
            case["outcome"] = {"status": status, "evidence": rel, "run_on": today}
        results.append({"id": case["id"], "status": status, "evidence": rel if args.write else dest})
    if args.write:
        tmp = path + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
        os.replace(tmp, path)
    print(json.dumps({"ran": len(results), "failed": failed, "written": bool(args.write), "scratch": scratch,
                      "results": results}, indent=2))
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
    e.add_argument("--exit", type=int, required=True)
    e.add_argument("--contains", action="append", default=[])
    e.add_argument("--absent", action="append", default=[])
    r = sub.add_parser("run")
    r.add_argument("--file", required=True)
    r.add_argument("--only", action="append", default=[])
    r.add_argument("--write", action="store_true")
    try:
        args = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    if args.mode == "expect":
        args.cmd = cmd
        return _expect(args)
    return _run(args)


if __name__ == "__main__":
    sys.exit(main())
