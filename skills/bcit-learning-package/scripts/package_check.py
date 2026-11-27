#!/usr/bin/env python3
"""package_check: check that a BCIT learning package is complete and that its parts hold up when executed.

  python3 package_check.py check PACKAGE.json [--skills-root DIR]

Checks the manifest (context, files, section pointers to Markdown headings), refuses claimed learning
gains that lack human-sourced evidence, then runs the sibling skills on the package's own files:
edu-assessment-check, edu-answer-key-check and edu-standards-alignment. A sibling that is not installed
is a missing-capability error, never a pass. Prints JSON. Exit 0 ok, 1 findings or invalid, 2 usage.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from typing import Any, Dict, List, Optional

SKILLS_ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
CONTEXT_FIELDS = ("course", "grade_band", "prerequisites", "duration", "resources", "technology_constraints")
FILES = ("teacher_guide", "student_materials", "worked_example", "assessment", "answer_key", "alignment")
SECTIONS = ("guided_practice", "independent_application", "checks_for_understanding", "misconceptions",
            "answer_rationale", "accessibility_differentiation", "offline_alternative",
            "evidence_feedback_reteaching", "extension", "teacher_review_points")
SIBLINGS = {
    "assessment": ("edu-assessment-check", "scripts/assessment_check.py", ["check"]),
    "answer_key": ("edu-answer-key-check", "scripts/answer_key.py", ["check"]),
    "alignment": ("edu-standards-alignment", "scripts/standards_check.py", ["align"]),
}


def headings(path: str) -> List[str]:
    with open(path, encoding="utf-8") as fh:
        return [m.group(1).strip().lower() for m in re.finditer(r"^#{1,6}\s+(.+?)\s*#*\s*$", fh.read(), re.M)]


def run_sibling(kind: str, target: str, skills_root: str) -> Dict[str, Any]:
    skill, rel, verb = SIBLINGS[kind]
    script = os.path.join(skills_root, skill, rel)
    if not os.path.isfile(script):
        return {"skill": skill, "status": "missing-capability", "ok": False,
                "message": "%s is not installed at %s; this part of the package is unchecked" % (skill, script)}
    proc = subprocess.run([sys.executable, script] + verb + [target], capture_output=True, text=True, timeout=120)
    try:
        out = json.loads(proc.stdout)
    except ValueError:
        out = {"raw": proc.stdout[-400:] + proc.stderr[-400:]}
    keep = {k: out.get(k) for k in ("ok", "summary", "flagged", "errors", "flags", "coverage", "supported_counts") if k in out}
    return dict({"skill": skill, "status": "ran", "exit": proc.returncode, "ok": proc.returncode == 0}, **keep)


def check(pkg: Any, base: str, skills_root: str) -> Dict[str, Any]:
    errors: List[Dict[str, str]] = []
    notes: List[str] = []

    def err(code: str, msg: str) -> None:
        errors.append({"code": code, "message": msg})

    if not isinstance(pkg, dict):
        return {"ok": False, "status": "invalid", "errors": [{"code": "invalid", "message": "package must be an object"}]}
    ctx = pkg.get("context") if isinstance(pkg.get("context"), dict) else {}
    for f in CONTEXT_FIELDS:
        if not ctx.get(f):
            err("context-missing", "context.%s is missing or empty" % f)
    files = pkg.get("files") if isinstance(pkg.get("files"), dict) else {}
    paths: Dict[str, List[str]] = {}
    for f in FILES:
        val = files.get(f)
        vals = val if isinstance(val, list) else [val] if val else []
        if not vals:
            err("file-missing", "files.%s is not named" % f)
        for v in vals:
            p = os.path.join(base, v)
            if not os.path.isfile(p):
                err("file-missing", "files.%s %s does not exist" % (f, v))
            else:
                paths.setdefault(f, []).append(p)
    sections = pkg.get("sections") if isinstance(pkg.get("sections"), dict) else {}
    for s in SECTIONS:
        ptr = sections.get(s)
        if not ptr or "#" not in str(ptr):
            err("section-missing", "sections.%s needs a file#Heading pointer" % s)
            continue
        fname, head = str(ptr).split("#", 1)
        p = os.path.join(base, fname)
        if not os.path.isfile(p):
            err("section-missing", "sections.%s points to %s, which does not exist" % (s, fname))
        elif head.strip().lower() not in headings(p):
            err("section-missing", "sections.%s: %s has no heading %r" % (s, fname, head))
    if pkg.get("differentiation_preserves_demand") is not True:
        err("demand-lowered", "differentiation must keep the intended learning demand; say how supports change access, not the target")
    ev = pkg.get("learning_evidence") if isinstance(pkg.get("learning_evidence"), dict) else {}
    status = ev.get("status")
    if status not in ("not-collected", "collected"):
        err("learning-evidence", "learning_evidence.status must be not-collected or collected")
    elif status == "collected" and not (str(ev.get("source", "")).startswith("human:") and ev.get("evidence")):
        err("invented-learning-evidence", "collected learning evidence needs a human source and an evidence reference; "
                                          "generated packages do not show learning")
    if ev.get("claims") and status != "collected":
        err("invented-learning-evidence", "learning claims %r appear with no collected evidence" % ev["claims"])
    checks = {}
    for kind in SIBLINGS:
        if kind in paths:
            res = run_sibling(kind, paths[kind][0], skills_root)
            checks[kind] = res
            if res["status"] == "missing-capability":
                err("missing-capability", res["message"])
            elif not res["ok"]:
                err("%s-failed" % kind.replace("_", "-"), "%s reported findings; see checks.%s" % (res["skill"], kind))
    if checks.get("alignment", {}).get("coverage") in ("partial", "gap"):
        notes.append("standards coverage is %s; the package is labeled a draft until a teacher verifies the mappings"
                     % checks["alignment"]["coverage"])
    return {"ok": not errors, "errors": errors, "notes": notes, "checks": checks, "label": pkg.get("label", "")}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="package_check")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("package")
    c.add_argument("--skills-root", default=SKILLS_ROOT)
    try:
        args = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    try:
        with open(args.package, encoding="utf-8") as fh:
            pkg = json.load(fh)
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "status": "invalid", "errors": [{"code": "invalid", "message": str(exc)}]}, indent=2))
        return 1
    result = check(pkg, os.path.dirname(os.path.abspath(args.package)), os.path.abspath(args.skills_root))
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
