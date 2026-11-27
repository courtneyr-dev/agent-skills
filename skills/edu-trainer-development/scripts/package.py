#!/usr/bin/env python3
"""package: check that a trainer-development package or teacher-education module is complete and honest.

  check MANIFEST.json

The manifest names its files relative to its own folder. The check confirms each file exists, the guide
carries every required section, rubric anchors are labeled generated practice anchors, the calibration
ratings claim no agreement they can't support (agreement.py), the evidence plan passes
(evidence_plan.py), a synthetic package carries no observations, and a teacher-education module keeps its
four evidence lines separate.

Python 3.9+ standard library only. Prints JSON. Exit 0 complete, 1 findings, 2 invalid input or usage.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import agreement  # noqa: E402
import evidence_plan  # noqa: E402

KINDS: Dict[str, Dict[str, List[str]]] = {
    "trainer-package": {
        "files": ["guide", "rubric", "calibration_exercise", "calibration_ratings", "evidence_plan"],
        "sections": ["design rationale", "modeled example", "decision points", "observation and feedback",
                     "rubric calibration", "fading support", "coaching another trainer", "transfer evaluation"],
    },
    "teacher-education-module": {
        "files": ["guide", "rubric", "calibration_exercise", "calibration_ratings", "evidence_plan",
                  "observation_instrument", "answer_key"],
        "sections": ["authentic business task", "computing practice", "pedagogical rationale", "microteaching cycle",
                     "observation", "assessment criteria", "calibration", "evidence lines", "supervisor decisions"],
    },
}
EVIDENCE_LINES = ["business_subject_mastery", "technology_fluency", "pedagogical_competence",
                  "occupational_assessment_readiness"]
ISTE_EDUCATOR_LABELS = {"Learner", "Leader", "Citizen", "Collaborator", "Designer", "Facilitator", "Analyst"}
ANCHOR_ORIGIN = "generated-practice-anchor"


class InputError(ValueError):
    pass


def _load(path: str) -> Any:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _synthetic(doc: Dict[str, Any]) -> bool:
    return doc.get("synthetic") is True or "SYNTHETIC" in str(doc.get("label", "")).upper()


def check(manifest_path: str) -> Dict[str, Any]:
    man = _load(manifest_path)
    if not isinstance(man, dict) or man.get("kind") not in KINDS or not isinstance(man.get("files"), dict):
        raise InputError("the manifest needs kind (%s) and a files object" % " or ".join(sorted(KINDS)))
    spec = KINDS[man["kind"]]
    base = os.path.dirname(os.path.abspath(manifest_path))
    findings: List[str] = []
    report: Dict[str, Any] = {"kind": man["kind"]}
    paths: Dict[str, str] = {}
    for key in spec["files"]:
        rel = man["files"].get(key)
        if not isinstance(rel, str) or not os.path.isfile(os.path.join(base, rel)):
            findings.append("files.%s is missing or does not exist (%r)" % (key, rel))
        else:
            paths[key] = os.path.join(base, rel)

    if "guide" in paths:
        with open(paths["guide"], encoding="utf-8") as fh:
            headings = [ln.lstrip("#").strip().lower() for ln in fh if ln.startswith("#")]
        missing = [s for s in spec["sections"] if not any(s in h for h in headings)]
        findings += ["the guide has no section on %s" % s for s in missing]

    if "rubric" in paths:
        rubric = _load(paths["rubric"])
        criteria = rubric.get("criteria") if isinstance(rubric, dict) else None
        if not isinstance(criteria, list) or not criteria:
            findings.append("the rubric has no criteria")
        else:
            for c in criteria:
                levels = [lv.get("score") for lv in c.get("levels", []) if isinstance(lv, dict)]
                if len(levels) < 2:
                    findings.append("criterion %s has fewer than two levels" % c.get("id"))
            anchors = rubric.get("anchors", [])
            if not anchors:
                findings.append("the rubric has no anchor examples for calibration")
            for a in anchors:
                if a.get("origin") != ANCHOR_ORIGIN:
                    findings.append("anchor %s is not labeled %s" % (a.get("id"), ANCHOR_ORIGIN))

    if "calibration_ratings" in paths:
        try:
            agr = agreement.stats(_load(paths["calibration_ratings"]))
            report["calibration"] = {"status": agr["status"], "discussion_items": len(agr["discussion"])}
            if agr["status"] == "computed" and _synthetic(man):
                findings.append("a synthetic package reports computed agreement; real agreement needs real reviewer ratings")
        except ValueError as exc:
            findings.append("calibration ratings are invalid: %s" % exc)

    if "evidence_plan" in paths:
        try:
            plan = evidence_plan.check(_load(paths["evidence_plan"]))
            report["evidence_plan"] = plan["status"]
            findings += ["evidence plan: %s" % f for f in plan["findings"]]
        except ValueError as exc:
            findings.append("evidence plan is invalid: %s" % exc)

    if "observation_instrument" in paths:
        inst = _load(paths["observation_instrument"])
        items = inst.get("items") if isinstance(inst, dict) else None
        if not isinstance(items, list) or not items or not all(isinstance(i, dict) and i.get("look_fors") for i in items):
            findings.append("the observation instrument needs items, each with look_fors")
        obs = inst.get("observations", []) if isinstance(inst, dict) else []
        if obs and _synthetic(man):
            findings.append("a synthetic package carries %d observation records; observations come from a human observer" % len(obs))
        for o in obs:
            if not str(o.get("observer", "")).startswith("human:"):
                findings.append("observation %s has no human observer" % o.get("id"))

    if man["kind"] == "teacher-education-module":
        lines = man.get("evidence_lines")
        if not isinstance(lines, dict):
            findings.append("the module has no evidence_lines object")
        else:
            for name in EVIDENCE_LINES:
                line = lines.get(name)
                if not isinstance(line, dict) or not line.get("status"):
                    findings.append("evidence line %s is missing or has no status" % name)
                    continue
                for other in line.get("inferred_from", []):
                    findings.append("evidence line %s is inferred from %s; evidence for one line does not establish another"
                                    % (name, other))
            report["evidence_lines"] = {k: v.get("status") for k, v in lines.items() if isinstance(v, dict)}
        labels = man.get("iste_educator_labels", [])
        bad = sorted(set(labels) - ISTE_EDUCATOR_LABELS)
        if bad:
            findings.append("unknown ISTE Educator labels %s" % ", ".join(bad))
        if not labels:
            findings.append("the module tags no ISTE Educator labels")

    report.update({"status": "complete" if not findings else "incomplete", "findings": findings})
    return report


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="package")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check", help="check a trainer package or teacher-education module manifest")
    c.add_argument("manifest")
    try:
        args = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    try:
        result = check(args.manifest)
    except (OSError, ValueError, AttributeError) as exc:
        sys.stdout.write(json.dumps({"status": "invalid-input", "error": str(exc)}, indent=2) + "\n")
        return 2
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0 if result["status"] == "complete" else 1


if __name__ == "__main__":
    sys.exit(main())
