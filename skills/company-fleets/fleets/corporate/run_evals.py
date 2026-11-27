#!/usr/bin/env python3
"""Run a fleet's script evaluation cases and keep their raw output as evidence.

  run_evals.py expect --exit N [--contains TEXT]... [--absent TEXT]... [--env KEY=VALUE]... -- CMD ARGS...
  run_evals.py run --fleet FLEET [--only CASE_ID]...

`expect` runs one command from the company-fleets directory, prints its raw output, and exits 0 only when the
exit code and text expectations hold (3 when the command reported blocked). Eval cases wrap their argv in it,
so each case asserts its own result. `run` executes every script case of a fleet, writes
fleets/<fleet>/evidence/<case-slug>.txt (command, date, raw output), and records pass, fail or blocked in
evals.json. Model-judgment and human cases are left as they are. Shared by the corporate and agency fleets.
"""
import argparse
import datetime
import json
import os
import subprocess
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))


def cmd_expect(a):
    env = dict(os.environ)
    for pair in a.env:
        key, _, value = pair.partition("=")
        env[key] = os.path.expanduser(value)
    argv = list(a.cmd[1:] if a.cmd and a.cmd[0] == "--" else a.cmd)
    if not argv:
        print("expect: no command given")
        return 2
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, cwd=ROOT, env=env, timeout=600)
    except OSError as exc:
        print("[expect] could not run %s: %s -> FAIL" % (argv[0], exc))
        return 1
    text = proc.stdout + proc.stderr
    missing = [s for s in a.contains if s not in text]
    present = [s for s in a.absent if s in text]
    ok = proc.returncode == a.exit and not missing and not present
    sys.stdout.write(proc.stdout)
    if proc.stderr.strip():
        sys.stdout.write("[stderr]\n%s\n" % proc.stderr.strip())
    sys.stdout.write("[expect] exit %d (expected %d); missing %s; forbidden present %s -> %s\n"
                     % (proc.returncode, a.exit, missing or "none", present or "none", "PASS" if ok else "FAIL"))
    if not ok and proc.returncode == 3 and a.exit != 3:
        return 3
    return 0 if ok else 1


def cmd_run(a):
    path = os.path.join(ROOT, "fleets", a.fleet, "evals.json")
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    today = datetime.date.today().isoformat()
    summary = {"pass": 0, "fail": 0, "blocked": 0, "skipped": 0}
    for case in doc["evals"]:
        if case["check"]["method"] != "script" or (a.only and case["id"] not in a.only):
            summary["skipped"] += 1
            continue
        slug = case["id"].split(".eval.", 1)[1]
        rel = "fleets/%s/evidence/%s.txt" % (a.fleet, slug)
        proc = subprocess.run(case["check"]["argv"], capture_output=True, text=True, cwd=ROOT, timeout=900)
        with open(os.path.join(ROOT, rel), "w", encoding="utf-8") as fh:
            fh.write("# eval %s (%s, target %s)\n$ (cwd skills/company-fleets) %s\nrun on %s, exit %d\n\n%s%s"
                     % (case["id"], case["kind"], case["target"], " ".join(case["check"]["argv"]), today,
                        proc.returncode, proc.stdout, ("\n[stderr]\n" + proc.stderr) if proc.stderr.strip() else ""))
        status = {0: "pass", 3: "blocked"}.get(proc.returncode, "fail")
        outcome = {"status": status, "evidence": rel, "run_on": today}
        if status == "blocked":
            outcome = {"status": "blocked", "run_on": today,
                       "note": "The check reported a missing adapter; see %s for the reason." % rel}
        case["outcome"] = outcome
        summary[status] += 1
        print("%-60s %s" % (case["id"], status))
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
    print(json.dumps(summary))
    return 0 if summary["fail"] == 0 else 1


def main(argv=None):
    ap = argparse.ArgumentParser(prog="run_evals.py")
    sub = ap.add_subparsers(dest="mode", required=True)
    e = sub.add_parser("expect")
    e.add_argument("--exit", type=int, required=True)
    e.add_argument("--contains", action="append", default=[])
    e.add_argument("--absent", action="append", default=[])
    e.add_argument("--env", action="append", default=[])
    e.add_argument("cmd", nargs=argparse.REMAINDER)
    r = sub.add_parser("run")
    r.add_argument("--fleet", required=True)
    r.add_argument("--only", action="append", default=[])
    a = ap.parse_args(argv)
    return cmd_expect(a) if a.mode == "expect" else cmd_run(a)


if __name__ == "__main__":
    sys.exit(main())
