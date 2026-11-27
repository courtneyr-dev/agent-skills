#!/usr/bin/env python3
"""needs: decide whether instruction addresses a performance problem before anyone designs a course.

  route CASE.json    print the route, the remedies with reason codes, and the questions still open

Missing knowledge or practice is diagnosed apart from information, tools, process, access and
incentives (Mager and Pipe's performance analysis; Gilbert's Behavior Engineering Model). An evidence
value counts only when it names its source; a missing or unsourced value becomes a question, never a
guessed route.

Python 3.9+ standard library only. Prints JSON. Exit 0 a route was decided, 1 evidence is missing so
the output is a list of questions instead of a route, 2 invalid input or usage.
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Dict, List, Optional

# (key, factor, question, remedy code when the value is false, remedy)
ENVIRONMENT = [
    ("expectations_clear", "information",
     "Do performers know what good performance looks like and when it is expected?",
     "ENV-INFO-EXPECTATIONS", "State the expectation and the standard; put a job aid or checklist at the point of work."),
    ("feedback_given", "information",
     "Do performers get timely, specific feedback on how they performed?",
     "ENV-INFO-FEEDBACK", "Add feedback: show performers their results soon after the task."),
    ("tools_adequate", "resources",
     "Do the tools, systems and materials let a skilled person do the task?",
     "ENV-RESOURCE-TOOL", "Fix or replace the tool; route the defect to the tool owner."),
    ("process_clear", "resources",
     "Does the process let the task be done as intended, without conflicting steps or approvals?",
     "ENV-RESOURCE-PROCESS", "Fix the process; route the change to the process owner."),
    ("access_ok", "resources",
     "Do performers have the access, permissions, time and accommodations the task needs?",
     "ENV-RESOURCE-ACCESS", "Grant the access, time or accommodation; route to its owner."),
    ("consequences_aligned", "incentives",
     "Is doing the task well rewarded, and is skipping it free of hidden rewards?",
     "ENV-INCENTIVE", "Realign consequences; route to the manager who owns them."),
]
SKILL_QUESTIONS = {
    "can_do_when_required": "Could the performer do the task correctly now if it were required and everything else "
                            "were in place? Observe a real attempt; a self-report is not enough.",
    "did_it_before": "Has the performer ever done the task correctly?",
    "performed_often": "Is the task done often enough to stay fluent?",
}
KEYS = {k for k, *_ in ENVIRONMENT} | set(SKILL_QUESTIONS)
COURSE_WORDS = {"course", "training", "workshop", "elearning", "e-learning", "module", "class"}


class InputError(ValueError):
    pass


def _text(obj: Dict[str, Any], key: str, where: str) -> str:
    val = obj.get(key)
    if not isinstance(val, str) or not val.strip():
        raise InputError("%s.%s must be non-empty text" % (where, key))
    return val


def validate(case: Any) -> None:
    if not isinstance(case, dict):
        raise InputError("the case must be a JSON object")
    _text(case, "problem", "case")
    aud, task, ev = case.get("audience"), case.get("task"), case.get("evidence")
    if not isinstance(aud, dict):
        raise InputError("case.audience must be an object")
    _text(aud, "who", "audience")
    if not isinstance(task, dict):
        raise InputError("case.task must be an object")
    _text(task, "name", "task")
    steps = task.get("steps")
    if not isinstance(steps, list) or not steps or not all(isinstance(s, str) and s.strip() for s in steps):
        raise InputError("task.steps must be a non-empty list of text steps")
    if not isinstance(ev, dict):
        raise InputError("case.evidence must be an object")
    for key, item in ev.items():
        if key not in KEYS:
            raise InputError("evidence.%s is not a known diagnostic question (known: %s)" % (key, ", ".join(sorted(KEYS))))
        if not isinstance(item, dict) or "value" not in item:
            raise InputError("evidence.%s must be an object with value and source" % key)
        if item["value"] not in (True, False, None) or isinstance(item["value"], int) and not isinstance(item["value"], bool):
            raise InputError("evidence.%s.value must be true, false or null" % key)
        if not isinstance(item.get("source", ""), str):
            raise InputError("evidence.%s.source must be text" % key)
    req = case.get("requested_solution")
    if req is not None and not isinstance(req, str):
        raise InputError("case.requested_solution must be text when present")


def route(case: Dict[str, Any]) -> Dict[str, Any]:
    validate(case)
    ev = case["evidence"]
    warnings: List[str] = []
    known: Dict[str, Optional[bool]] = {}
    for key, item in ev.items():
        if item["value"] is not None and not item.get("source", "").strip():
            warnings.append("evidence.%s has a value but no source; treated as missing" % key)
            continue
        known[key] = item["value"]

    remedies: List[Dict[str, str]] = []
    questions: List[Dict[str, str]] = []
    for key, factor, question, code, remedy in ENVIRONMENT:
        val = known.get(key)
        if val is False:
            remedies.append({"code": code, "factor": factor, "remedy": remedy, "because": ev[key]["source"]})
        elif val is None:
            questions.append({"key": key, "question": question})

    course: Optional[bool] = None
    can = known.get("can_do_when_required")
    if can is None:
        questions.insert(0, {"key": "can_do_when_required", "question": SKILL_QUESTIONS["can_do_when_required"]})
    elif can is True:
        course = False
    else:
        before = known.get("did_it_before")
        if before is None:
            questions.append({"key": "did_it_before", "question": SKILL_QUESTIONS["did_it_before"]})
        elif before is False:
            course = True
            remedies.append({"code": "SKILL-TRAINING", "factor": "knowledge-and-skill",
                             "remedy": "Teach the skill with practice and feedback on the real task; try a job aid first "
                                       "when the task is rare or short.",
                             "because": ev["did_it_before"]["source"]})
        else:
            often = known.get("performed_often")
            if often is None:
                questions.append({"key": "performed_often", "question": SKILL_QUESTIONS["performed_often"]})
            elif often is False:
                course = False
                remedies.append({"code": "SKILL-PRACTICE", "factor": "knowledge-and-skill",
                                 "remedy": "Schedule practice or a refresher job aid; the skill existed and faded from disuse.",
                                 "because": ev["performed_often"]["source"]})
            else:
                course = False
                remedies.append({"code": "SKILL-FEEDBACK", "factor": "knowledge-and-skill",
                                 "remedy": "Give feedback on each attempt; frequent practice without feedback is not fixing the gap.",
                                 "because": ev["performed_often"]["source"]})

    env_codes = [r["code"] for r in remedies if r["code"].startswith("ENV-")]
    notes: List[str] = []
    if course is True and env_codes:
        notes.append("Fix %s before or alongside training; skills taught into a blocking environment do not transfer."
                     % ", ".join(env_codes))
    not_recommended: List[str] = []
    requested = (case.get("requested_solution") or "").strip()
    wants_course = any(w in requested.lower().split() or requested.lower() == w for w in COURSE_WORDS)
    if wants_course and course is False:
        not_recommended.append("%s: the evidence shows performers can do the task, so instruction would not remove "
                               "the cause; act on the remedies instead." % requested)
    elif wants_course and course is None:
        not_recommended.append("%s: deferred until the open questions are answered." % requested)

    if questions:
        status = "collect-evidence"
    elif not remedies:
        status = "no-gap-found"
        notes.append("No skill or environment gap appears in the evidence; re-check the performance discrepancy "
                     "and whether it is worth solving.")
    else:
        status = "route"

    aud, task = case["audience"], case["task"]
    analysis_gaps = (["audience.%s" % k for k in ("size", "context", "access_needs") if k not in aud]
                     + ["task.%s" % k for k in ("frequency", "criticality", "conditions") if k not in task])
    return {
        "status": status,
        "course_indicated": course,
        "remedies": remedies,
        "questions": questions,
        "not_recommended": not_recommended,
        "notes": notes,
        "warnings": warnings,
        "audience_task_analysis": {"audience": aud, "task": task, "analysis_gaps": analysis_gaps},
    }


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="needs")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("route", help="route one performance problem")
    r.add_argument("case")
    try:
        args = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    try:
        with open(args.case, encoding="utf-8") as fh:
            case = json.load(fh)
        result = route(case)
    except (OSError, ValueError) as exc:
        sys.stdout.write(json.dumps({"status": "invalid-input", "error": str(exc)}, indent=2) + "\n")
        return 2
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0 if result["status"] in ("route", "no-gap-found") else 1


if __name__ == "__main__":
    sys.exit(main())
