#!/usr/bin/env python3
"""Run every script-method eval case of one fleet and keep its raw output as evidence.

usage: run_evals.py --fleet product|consultancies [--write]

Runs each case's argv from the company-fleets root, writes the raw output to the case's
outcome.evidence path (fleets/<fleet>/evidence/<slug>.txt by default) with a header naming the
command and time, and prints a JSON summary. With --write it records status (pass when the argv
exits 0, fail otherwise) and run_on in fleets/<fleet>/evals.json. Failures stay on record.
Model-judgment and human cases are listed, never run.
"""
import argparse
import datetime
import json
import os
import subprocess
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", ".."))


def main(argv):
    ap = argparse.ArgumentParser(prog="run_evals")
    ap.add_argument("--fleet", required=True, choices=["product", "consultancies"])
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    rel = "fleets/%s/evals.json" % args.fleet
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        doc = json.load(fh)
    now = datetime.datetime.now(datetime.timezone.utc)
    summary = {"fleet": args.fleet, "run_at": now.strftime("%Y-%m-%dT%H:%MZ"), "pass": [], "fail": [], "not_run": []}
    for case in doc["evals"]:
        if case["check"]["method"] != "script":
            summary["not_run"].append(case["id"])
            continue
        slug = case["id"].split(".eval.", 1)[1]
        evidence = case["outcome"].get("evidence") or "fleets/%s/evidence/%s.txt" % (args.fleet, slug)
        if not evidence.startswith("fleets/%s/evidence/" % args.fleet):
            raise SystemExit("%s evidence must live under fleets/%s/evidence/" % (case["id"], args.fleet))
        argv_ = [sys.executable if a == "python3" else a for a in case["check"]["argv"]]
        p = subprocess.run(argv_, cwd=ROOT, capture_output=True, text=True)
        header = ("# SYNTHETIC Fixture Co data. Raw output of eval %s (%s, target %s).\n"
                  "# $ %s\n# cwd: skills/company-fleets  run: %s  exit: %d\n\n"
                  % (case["id"], case["kind"], case["target"], " ".join(case["check"]["argv"]), summary["run_at"], p.returncode))
        with open(os.path.join(ROOT, evidence), "w", encoding="utf-8") as fh:
            fh.write(header + p.stdout + (("\nstderr:\n" + p.stderr) if p.stderr.strip() else ""))
        status = "pass" if p.returncode == 0 else "fail"
        summary[status].append(case["id"])
        if args.write:
            case["outcome"] = {"status": status, "evidence": evidence, "run_on": now.strftime("%Y-%m-%d")}
    if args.write:
        with open(os.path.join(ROOT, rel), "w", encoding="utf-8") as fh:
            fh.write(json.dumps(doc, indent=2) + "\n")
    summary["counts"] = {k: len(summary[k]) for k in ("pass", "fail", "not_run")}
    print(json.dumps(summary, indent=2))
    return 1 if summary["fail"] else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
