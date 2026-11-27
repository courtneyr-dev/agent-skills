#!/usr/bin/env python3
"""Prove bin/fleet eval-run judges every fleet's script cases the way the existing runners do.

For each script case in fleets/*/evals.json: run its argv unchanged (the existing runner path) and map
the exit code with that fleet's own run-mode rule, run the same case through fleetlib.evalrun, and
compare both with the retained outcome.status. Writes the table and counts to
evidence/eval-run-equivalence.txt. Nothing in any fleet's files changes.
"""
import datetime
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.realpath(__file__))
sys.path.insert(0, HERE)

from fleetlib import SKILL_DIR, evalrun  # noqa: E402

BLOCKED_FLEETS = {"corporate", "agency", "hosting"}  # their run modes record exit 3 as blocked


def old_status(fleet, argv):
    try:
        code = subprocess.run(argv, cwd=SKILL_DIR, capture_output=True, text=True, timeout=900).returncode
    except (OSError, subprocess.TimeoutExpired):
        code = 127
    return "pass" if code == 0 else "blocked" if code == 3 and fleet in BLOCKED_FLEETS else "fail"


def main():
    rows, started = [], datetime.datetime.now().isoformat(timespec="seconds")
    for fleet, _, _, case in evalrun.script_cases(SKILL_DIR, sys.argv[1] if len(sys.argv) > 1 else None):
        old = old_status(fleet, case["check"]["argv"])
        try:
            p = evalrun.plan(case)
            new = evalrun.execute(p, SKILL_DIR)["status"]
            runner = p.runner
        except evalrun.PlanError as exc:
            new, runner = "unparsed: %s" % exc, "-"
        rows.append((case["id"], case["outcome"]["status"], old, new, runner))
        print("%-70s retained=%-8s old=%-8s new=%s" % rows[-1][:4], flush=True)
    same = sum(1 for r in rows if r[2] == r[3])
    lines = ["# eval-run equivalence, started %s, finished %s" % (started, datetime.datetime.now().isoformat(timespec="seconds")),
             "# old = the case's argv run unchanged, exit mapped by its fleet's run mode; new = bin/fleet eval-run's engine",
             "# cases %d; old == new %d; old != new %d; new != retained %d; old != retained %d"
             % (len(rows), same, len(rows) - same, sum(r[3] != r[1] for r in rows), sum(r[2] != r[1] for r in rows)),
             "id\tretained\told\tnew\trunner"]
    lines += ["\t".join(r) for r in rows]
    out = os.path.join(SKILL_DIR, "evidence", "eval-run-equivalence.txt")
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    print(lines[2])
    return 0 if same == len(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
