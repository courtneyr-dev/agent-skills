#!/usr/bin/env python3
"""Run this fleet's script evaluation cases and retain their raw output.

Each case with check.method "script" runs its argv from the company-fleets directory. A case passes
when its command exits 0; negative cases wrap the tool so that the expected refusal exits 0. Output
goes to evidence/<case-slug>.txt, headed by the command, the date and the exit code, and the case's
outcome in evals.json is set to pass or fail with that evidence path. Failures are kept, never
deleted. Model-judgment and human cases are left as they are.

--install-check writes evidence/installed-skills.txt: each skill in skills.json resolves under
the skills root that holds company-fleets, its SKILL.md front matter names it, and its listed scripts compile.

Usage: python3 fleets/<fleet>/run_evals.py [--only CASE_ID ...] [--install-check]
Exit 0: no case failed. Exit 1: at least one case failed.
"""
import argparse
import datetime
import json
import os
import re
import shlex
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FLEET = os.path.basename(HERE)
CF = os.path.dirname(os.path.dirname(HERE))
SKILLS_ROOT = os.path.dirname(CF)
EVIDENCE = os.path.join(HERE, "evidence")


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def run_case(case):
    argv = case["check"]["argv"]
    slug = case["id"].split(".eval.", 1)[1]
    started = now()
    try:
        p = subprocess.run(argv, cwd=CF, capture_output=True, text=True, timeout=600)
        code, out, err = p.returncode, p.stdout, p.stderr
    except subprocess.TimeoutExpired as exc:
        code, out, err = None, exc.stdout or "", "timed out after 600s"
    status = "pass" if code == 0 else "fail"
    rel = "fleets/%s/evidence/%s.txt" % (FLEET, slug)
    with open(os.path.join(CF, rel), "w", encoding="utf-8") as fh:
        fh.write("$ %s\n# cwd: skills/company-fleets\n# run: %s\n# case: %s (%s, target %s, synthetic=%s)\n# expected: %s\n# exit: %s -> %s\n"
                 % (shlex.join(argv), started, case["id"], case["kind"], case["target"], case.get("synthetic", False),
                    case["expected"], code, status))
        fh.write("--- stdout ---\n%s\n--- stderr ---\n%s\n" % (out.rstrip(), (err or "").rstrip()))
    case["outcome"] = {"status": status, "evidence": rel, "run_on": started[:10]}
    return status


def install_check():
    with open(os.path.join(HERE, "skills.json"), encoding="utf-8") as fh:
        skills = json.load(fh)["skills"]
    lines, ok = ["# run: %s\n# check: each skill resolves under the skills root, names itself, and its scripts compile" % now()], True
    for s in skills:
        path = os.path.join(SKILLS_ROOT, s["id"], "SKILL.md")
        if not os.path.isfile(path):
            lines.append("FAIL %s: %s missing" % (s["id"], path))
            ok = False
            continue
        head = open(path, encoding="utf-8").read().split("---")[1]
        name = re.search(r"^name:\s*(\S+)", head, re.M)
        compiled = []
        for sp in s["scripts"]:
            src = os.path.join(os.path.dirname(path), sp)
            try:
                compile(open(src, encoding="utf-8").read(), src, "exec")
                compiled.append("%s compiles" % sp)
            except (OSError, SyntaxError) as exc:
                compiled.append("%s FAILS: %s" % (sp, exc))
                ok = False
        named = bool(name and name.group(1) == s["id"])
        ok = ok and named
        lines.append("%s %s -> %s; front matter name %s; %s" % ("ok  " if named else "FAIL", s["id"], os.path.realpath(path),
                                                               name.group(1) if name else "missing", "; ".join(compiled) or "no scripts"))
    with open(os.path.join(EVIDENCE, "installed-skills.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")
    return ok


def main():
    ap = argparse.ArgumentParser(description="Run %s script evaluation cases." % FLEET)
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--install-check", action="store_true")
    args = ap.parse_args()
    os.makedirs(EVIDENCE, exist_ok=True)
    if args.install_check and not install_check():
        print(json.dumps({"install_check": "fail"}))
        return 1
    path = os.path.join(HERE, "evals.json")
    with open(path, encoding="utf-8") as fh:
        doc = json.load(fh)
    counts = {}
    for case in doc["evals"]:
        if case["check"]["method"] == "script" and (not args.only or case["id"] in args.only):
            st = run_case(case)
        else:
            st = case["outcome"]["status"]
        counts[st] = counts.get(st, 0) + 1
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(json.dumps(doc, indent=2) + "\n")
    print(json.dumps({"fleet": FLEET, "outcomes": counts}))
    return 1 if counts.get("fail") else 0


if __name__ == "__main__":
    sys.exit(main())
