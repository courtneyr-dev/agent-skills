#!/usr/bin/env python3
"""lesson: check a CS classroom lesson package and respond to supplied learner work.

  check   <lesson.json>                     run every example and reference solution, check completeness
  respond <lesson.json> [<learner-work.json>] feedback grounded in the learner's actual output

Prints JSON. Exit 0 ok (respond always returns 0 when it produced a response), 1 check findings,
2 usage error or invalid input. Python 3.9+ standard library only.

Learner code runs with `python3 -I` in a fresh temporary directory, a minimal environment and a
timeout. That is process isolation, not a security sandbox: run real learner code inside the
school's own sandboxed environment.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from typing import Any, Dict, List, Optional, Tuple

TIMEOUT_S = 5
MAX_OUTPUT = 4000
GRADE_BAND = re.compile(r"^(PK|K|[1-9]|1[0-2])(-([1-9]|1[0-2]))?$")
TASK_KINDS = {"predict", "trace", "modify", "explain", "construct", "transfer"}
UNDERSTANDING_EVIDENCE = {"explanation", "trace", "prediction", "oral-explanation", "annotated-code"}
STANDARD_AUDIENCE = {
    "csta-k12-2026": "students",
    "csta-k12-2017": "students",
    "csta-teacher-2020": "teachers",
    "cs2023": "university",
}
REQUIRED = ["label", "context", "objective", "language_rationale", "teacher_guide", "examples", "tasks",
            "misconception_probes", "rubric", "accessibility", "reteaching", "extension"]


class Invalid(Exception):
    """Input the tool cannot interpret at all (exit 2)."""


def _load(path: str) -> Dict[str, Any]:
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError) as exc:
        raise Invalid("cannot read %s: %s" % (path, exc))
    if not isinstance(doc, dict):
        raise Invalid("%s must hold a JSON object" % path)
    return doc


def normalize(text: str) -> str:
    return "\n".join(line.rstrip() for line in str(text).strip().splitlines())


def run_python(code: str, stdin: str = "") -> Dict[str, Any]:
    """Run code with python3 -I in a fresh temp dir; return stdout, stderr, exit code, timeout flag."""
    with tempfile.TemporaryDirectory(prefix="cs-lesson-") as tmp:
        path = os.path.join(tmp, "main.py")
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(code)
        env = {"PATH": "/usr/bin:/bin", "PYTHONIOENCODING": "utf-8", "HOME": tmp}
        try:
            proc = subprocess.run([sys.executable, "-I", path], input=stdin, capture_output=True, text=True,
                                  cwd=tmp, env=env, timeout=TIMEOUT_S)
        except subprocess.TimeoutExpired:
            return {"stdout": "", "stderr": "timed out after %ds" % TIMEOUT_S, "exit": None, "timeout": True}
    return {"stdout": proc.stdout[:MAX_OUTPUT], "stderr": proc.stderr[-MAX_OUTPUT:], "exit": proc.returncode,
            "timeout": False}


def _text(value: Any) -> bool:
    return isinstance(value, str) and len(value.strip()) >= 3


def _nonempty(value: Any) -> bool:
    if isinstance(value, str):
        return _text(value)
    if isinstance(value, (list, dict)):
        return len(value) > 0
    return value is not None


def _completeness(doc: Dict[str, Any]) -> List[str]:
    errors = ["missing or empty section: %s" % key for key in REQUIRED if not _nonempty(doc.get(key))]
    ctx = doc.get("context") or {}
    if not isinstance(ctx, dict):
        return errors + ["context must be an object"]
    band = ctx.get("grade_band")
    if not (isinstance(band, str) and GRADE_BAND.match(band)):
        errors.append("context.grade_band must name the actual grade band, e.g. 9-10 (got %r)" % band)
    status = ctx.get("assignment_status") or {}
    for field in ("teaching_assignment", "certification"):
        if status.get(field) not in ("verified", "unverified"):
            errors.append("context.assignment_status.%s must be verified or unverified" % field)
        elif status.get(field) == "verified" and not str(status.get("verified_by", "")).startswith("human:"):
            errors.append("assignment_status.%s says verified without a human:<role> verified_by" % field)
    acc = doc.get("accessibility") or {}
    if isinstance(acc, dict):
        if not _nonempty(acc.get("checks")):
            errors.append("accessibility.checks is empty")
        if not (_text(acc.get("low_bandwidth_alternative")) or _text(acc.get("unplugged_alternative"))):
            errors.append("accessibility needs a low-bandwidth or unplugged alternative")
    guide = doc.get("teacher_guide") or {}
    if isinstance(guide, dict) and not _nonempty(guide.get("wait_points")):
        errors.append("teacher_guide.wait_points is empty: say where the teacher stops for actual learner responses")
    return errors


def _standards(doc: Dict[str, Any]) -> List[str]:
    errors = []
    band = str((doc.get("context") or {}).get("grade_band", ""))
    for i, s in enumerate(doc.get("standards", []) or []):
        where = "standards[%d]" % i
        if not isinstance(s, dict):
            errors.append("%s must be an object" % where)
            continue
        if "text" in s:
            errors.append("%s bundles standard text; cite the label and link only (CSTA is noncommercial share-alike)" % where)
        audience = STANDARD_AUDIENCE.get(s.get("record_id"))
        if audience is None:
            errors.append("%s record_id %r is not a known registry record" % (where, s.get("record_id")))
        elif audience == "teachers":
            errors.append("%s cites a teacher-practice standard (%s) for a student objective" % (where, s["record_id"]))
        elif audience == "university" and GRADE_BAND.match(band) and not _text(s.get("bridge")):
            errors.append("%s applies a university curriculum (%s) to grade band %s without a bridge" % (where, s["record_id"], band))
        if s.get("status") == "verified" and not str(s.get("reviewer", "")).startswith("human:"):
            errors.append("%s says verified without a human:<role> reviewer" % where)
    return errors


def _run_examples(doc: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    results, errors = [], []
    for ex in doc.get("examples", []) or []:
        if not isinstance(ex, dict) or not _text(ex.get("code")) or "expected_output" not in ex:
            errors.append("example %r needs code and expected_output" % (ex.get("id") if isinstance(ex, dict) else ex))
            continue
        r = run_python(ex["code"], ex.get("stdin", ""))
        ok = r["exit"] == 0 and normalize(r["stdout"]) == normalize(ex["expected_output"])
        results.append({"example": ex.get("id"), "match": ok, "expected": ex["expected_output"], "actual": r["stdout"],
                        "stderr": r["stderr"][-300:]})
        if not ok:
            errors.append("example %s: stated expected output %r but the code printed %r"
                          % (ex.get("id"), normalize(ex["expected_output"]), normalize(r["stdout"]) or r["stderr"][-200:]))
    return results, errors


def _run_tasks(doc: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], List[str]]:
    results, errors = [], []
    for t in doc.get("tasks", []) or []:
        tid = t.get("id") if isinstance(t, dict) else t
        if not isinstance(t, dict) or t.get("kind") not in TASK_KINDS:
            errors.append("task %r needs a kind in %s" % (tid, sorted(TASK_KINDS)))
            continue
        if not _text(t.get("prompt")) or not _text(t.get("answer_rationale")):
            errors.append("task %s needs a student prompt and an answer_rationale" % tid)
        if t["kind"] == "predict":
            if not _text(t.get("given_code")) or "expected_output" not in t:
                errors.append("predict task %s needs given_code and expected_output" % tid)
                continue
            r = run_python(t["given_code"])
            ok = normalize(r["stdout"]) == normalize(t["expected_output"])
            results.append({"task": tid, "test": "given_code", "match": ok, "actual": r["stdout"]})
            if not ok:
                errors.append("task %s: stated expected output %r but given_code printed %r"
                              % (tid, normalize(t["expected_output"]), normalize(r["stdout"])))
            continue
        tests = t.get("tests") or []
        if not tests or not _text(t.get("reference_solution")):
            errors.append("task %s needs tests with expected outputs and a reference_solution" % tid)
            continue
        for test in tests:
            r = run_python(t["reference_solution"], test.get("stdin", ""))
            ok = r["exit"] == 0 and normalize(r["stdout"]) == normalize(test.get("expected_output", ""))
            results.append({"task": tid, "test": test.get("id"), "match": ok, "expected": test.get("expected_output"),
                            "actual": r["stdout"]})
            if not ok:
                errors.append("task %s test %s: expected %r but the reference solution printed %r; the answer key or the solution is wrong"
                              % (tid, test.get("id"), normalize(test.get("expected_output", "")), normalize(r["stdout"]) or r["stderr"][-200:]))
    return results, errors


def _rubric(doc: Dict[str, Any]) -> List[str]:
    rubric = doc.get("rubric") or []
    if not isinstance(rubric, list):
        return ["rubric must be a list of criteria"]
    errors = ["rubric criterion %r needs criterion text and an evidence list" % (c.get("id") if isinstance(c, dict) else c)
              for c in rubric if not (isinstance(c, dict) and _text(c.get("criterion")) and c.get("evidence"))]
    kinds = {e for c in rubric if isinstance(c, dict) for e in (c.get("evidence") or [])}
    if rubric and not kinds & UNDERSTANDING_EVIDENCE:
        errors.append("rubric accepts passing code or produced output as sufficient evidence of understanding; "
                      "add a criterion that needs an explanation, trace or prediction")
    if rubric and not any(isinstance(t, dict) and t.get("kind") == "transfer" for t in doc.get("tasks", []) or []):
        errors.append("no transfer task: assess the pattern on a new problem")
    return errors


def check(doc: Dict[str, Any]) -> Dict[str, Any]:
    errors = _completeness(doc) + _standards(doc)
    ex_results, ex_errors = _run_examples(doc)
    task_results, task_errors = _run_tasks(doc)
    errors += ex_errors + task_errors + _rubric(doc)
    return {"ok": not errors, "errors": errors, "examples": ex_results, "task_runs": task_results,
            "note": "Executed results check the package's answers; they say nothing about learning. Teacher review decides use."}


def _probe_matches(probe: Dict[str, Any], code: str, prediction: str, outputs: Dict[str, str]) -> bool:
    sig = probe.get("signals") or {}
    checks = []
    if "output_equals" in sig:
        test_id, want = sig["output_equals"].get("test"), sig["output_equals"].get("value")
        checks.append(normalize(outputs.get(test_id, "\0")) == normalize(want))
    if "code_regex" in sig:
        checks.append(re.search(sig["code_regex"], code or "") is not None)
    if "prediction_equals" in sig:
        checks.append(normalize(prediction) == normalize(sig["prediction_equals"]))
    return bool(checks) and all(checks)


def respond(doc: Dict[str, Any], work: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    base = {"progress_claim": None,
            "note": "The script never records mastery or progress. The teacher of record reviews the work and decides."}
    if work is None:
        return dict(base, status="awaiting-learner-response", feedback=None, next_action=None,
                    reason="No learner work was supplied. Wait for the learner's actual response.")
    task = next((t for t in doc.get("tasks", []) or [] if isinstance(t, dict) and t.get("id") == work.get("task_id")), None)
    if task is None:
        raise Invalid("learner work names task %r, which the lesson does not define" % work.get("task_id"))
    code = str(work.get("code") or "")
    prediction = str(work.get("prediction") or "")
    explanation = (str(work.get("explanation") or "") + "\n" + str(work.get("trace") or "")).strip()
    base.update({"task_id": task["id"], "learner_ref": work.get("learner_ref")})
    if not code.strip() and not prediction.strip() and not explanation:
        return dict(base, status="awaiting-learner-response", feedback=None, next_action=None,
                    reason="The supplied work is empty. Nothing was attempted, so there is nothing to give feedback on.")
    probes = [p for p in doc.get("misconception_probes", []) or [] if isinstance(p, dict) and p.get("task_id") == task["id"]]

    if task.get("kind") == "predict":
        actual = run_python(task.get("given_code", ""))["stdout"]
        matched = [p for p in probes if _probe_matches(p, "", prediction, {})]
        if normalize(prediction) == normalize(actual):
            status = "ready-for-teacher-review" if explanation else "not-yet-evidence-of-understanding"
            return dict(base, status=status, misconceptions=[], feedback="Your prediction %r matches what the program printed." % normalize(actual),
                        next_action=None if explanation else task.get("follow_up_prompt", "Explain how you got your prediction, line by line."))
        first = matched[0] if matched else {}
        return dict(base, status="prediction-differs", misconceptions=[{"id": p.get("id"), "name": p.get("name")} for p in matched],
                    feedback=("You predicted %r; the program printed %r. %s" % (normalize(prediction), normalize(actual), first.get("feedback", ""))).strip(),
                    next_action=first.get("next_action", "Run the program and compare each line with your prediction."))

    tests, outputs = [], {}
    for test in task.get("tests") or []:
        r = run_python(code, test.get("stdin", ""))
        outputs[test.get("id")] = r["stdout"]
        passed = r["exit"] == 0 and normalize(r["stdout"]) == normalize(test.get("expected_output", ""))
        tests.append({"id": test.get("id"), "input": test.get("stdin", ""), "expected": test.get("expected_output"),
                      "actual": r["stdout"], "error": r["stderr"][-300:] if r["exit"] != 0 else "", "passed": passed})
    matched = [p for p in probes if _probe_matches(p, code, prediction, outputs)]
    failing = [t for t in tests if not t["passed"]]
    if failing:
        f, first = failing[0], (matched[0] if matched else {})
        shown = normalize(f["actual"]) or ("an error: " + f["error"].strip().splitlines()[-1] if f["error"].strip() else "nothing")
        return dict(base, status="tests-failing", tests=tests, misconceptions=[{"id": p.get("id"), "name": p.get("name")} for p in matched],
                    feedback=("For input %r your program printed %s; the task expects %r. %s"
                              % (f["input"].strip(), shown, normalize(f["expected"]), first.get("feedback", ""))).strip(),
                    next_action=first.get("next_action", "Trace your program by hand on input %r and write each variable's value on every pass." % f["input"].strip()))
    follow_up = task.get("follow_up_prompt", "Explain how your program works and trace it on the first test input.")
    if work.get("ai_generated") is True:
        return dict(base, status="not-yet-evidence-of-understanding", tests=tests, misconceptions=[],
                    feedback="The tests pass, but the work is marked AI-generated. Passing output is not evidence of your understanding.",
                    next_action=follow_up)
    if task.get("requires_explanation") and not explanation:
        return dict(base, status="not-yet-evidence-of-understanding", tests=tests, misconceptions=[],
                    feedback="All %d tests pass. Passing tests show the program works, not how you reasoned about it." % len(tests),
                    next_action=follow_up)
    missing = [str(v) for v in task.get("trace_values", []) if not re.search(r"(?<![\d.])%s(?![\d.])" % re.escape(str(v)), explanation)]
    if missing:
        return dict(base, status="not-yet-evidence-of-understanding", tests=tests, misconceptions=[],
                    feedback="All tests pass. Your trace leaves out the running values %s." % ", ".join(missing),
                    next_action=follow_up)
    return dict(base, status="ready-for-teacher-review", tests=tests, misconceptions=[],
                feedback="All %d tests pass and your trace names each running value. Your teacher will review the explanation." % len(tests),
                next_action=task.get("transfer_prompt"))


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    usage = "usage: lesson.py check <lesson.json> | respond <lesson.json> [<learner-work.json>]"
    if not argv or argv[0] not in ("check", "respond") or not (2 <= len(argv) <= (3 if argv[0] == "respond" else 2)):
        print(json.dumps({"error": usage}))
        return 2
    try:
        doc = _load(argv[1])
        if argv[0] == "check":
            result = check(doc)
            print(json.dumps(result, indent=2))
            return 0 if result["ok"] else 1
        work = _load(argv[2]) if len(argv) == 3 else None
        if work is not None and not isinstance(work.get("task_id"), str):
            raise Invalid("learner work needs a task_id")
        print(json.dumps(respond(doc, work), indent=2))
        return 0
    except Invalid as exc:
        print(json.dumps({"error": "invalid input", "detail": str(exc)}))
        return 2


if __name__ == "__main__":
    sys.exit(main())
