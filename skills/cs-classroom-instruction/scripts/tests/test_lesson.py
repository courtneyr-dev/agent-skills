import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "lesson.py")
sys.path.insert(0, os.path.join(HERE, ".."))
import lesson  # noqa: E402

SUM = "nums = [int(x) for x in input().split()]\ntotal = 0\nfor n in nums:\n    total = total + n\nprint(total)\n"
LESSON = {
    "label": "SYNTHETIC test lesson",
    "context": {"grade_band": "9-10", "assignment_status": {"teaching_assignment": "unverified", "certification": "unverified"}},
    "objective": {"id": "O1", "text": "Total a list with an accumulator and explain it", "level": "apply"},
    "language_rationale": "Python runs offline here",
    "standards": [{"record_id": "csta-k12-2026", "label": "Algorithms and Programming", "status": "unverified"}],
    "teacher_guide": {"sequence": ["model", "predict", "construct"], "wait_points": ["after predict"]},
    "examples": [{"id": "E1", "code": "print(2 + 3)\n", "expected_output": "5"}],
    "tasks": [
        {"id": "T1", "kind": "predict", "prompt": "What prints?", "given_code": "t = 0\nfor p in [2, 3]:\n    t = t + p\nprint(t)\n",
         "expected_output": "5", "answer_rationale": "0, 2, 5"},
        {"id": "T2", "kind": "construct", "prompt": "Total the numbers", "answer_rationale": "start at 0, add each",
         "tests": [{"id": "three", "stdin": "1 2 3\n", "expected_output": "6"}, {"id": "empty", "stdin": "\n", "expected_output": "0"}],
         "reference_solution": SUM, "requires_explanation": True, "trace_values": [1, 3, 6]},
        {"id": "T3", "kind": "transfer", "prompt": "Largest number", "answer_rationale": "best so far",
         "tests": [{"id": "three", "stdin": "1 5 3\n", "expected_output": "5"}],
         "reference_solution": "nums = [int(x) for x in input().split()]\nprint(max(nums))\n"}],
    "misconception_probes": [
        {"id": "M1", "task_id": "T2", "name": "skips first", "signals": {"output_equals": {"test": "three", "value": "5"}},
         "feedback": "The first number was never added.", "next_action": "Trace with input 4."},
        {"id": "M2", "task_id": "T1", "name": "last item", "signals": {"prediction_equals": "3"}, "feedback": "3 is the last item.",
         "next_action": "Print t inside the loop."}],
    "rubric": [{"id": "R1", "criterion": "Explains the running total", "evidence": ["trace"]},
               {"id": "R2", "criterion": "Program passes tests", "evidence": ["tests"]}],
    "accessibility": {"checks": ["keyboard only"], "unplugged_alternative": "index cards"},
    "reteaching": "trace again with cards",
    "extension": "compute the average",
}


def run_cli(*args):
    proc = subprocess.run([sys.executable, SCRIPT] + list(args), capture_output=True, text=True, timeout=60)
    return proc.returncode, proc.stdout


def write(tmp, name, doc):
    path = os.path.join(tmp, name)
    with open(path, "w") as fh:
        fh.write(doc if isinstance(doc, str) else json.dumps(doc))
    return path


class CheckTests(unittest.TestCase):
    def test_complete_lesson_passes(self):
        result = lesson.check(copy.deepcopy(LESSON))
        self.assertEqual(result["errors"], [])
        self.assertTrue(all(r["match"] for r in result["examples"] + result["task_runs"]))

    def test_wrong_expected_output_is_caught(self):
        doc = copy.deepcopy(LESSON)
        doc["examples"][0]["expected_output"] = "6"
        doc["tasks"][1]["tests"][0]["expected_output"] = "7"
        errors = lesson.check(doc)["errors"]
        self.assertTrue(any("example E1" in e and "'6'" in e for e in errors))
        self.assertTrue(any("task T2 test three" in e and "answer key or the solution is wrong" in e for e in errors))

    def test_passing_code_rubric_is_rejected(self):
        doc = copy.deepcopy(LESSON)
        doc["rubric"] = [{"id": "R1", "criterion": "Tests pass", "evidence": ["tests", "ai-output"]}]
        self.assertTrue(any("passing code" in e for e in lesson.check(doc)["errors"]))

    def test_missing_sections_and_alternative_are_reported(self):
        doc = copy.deepcopy(LESSON)
        del doc["reteaching"]
        doc["accessibility"] = {"checks": ["zoom"]}
        errors = lesson.check(doc)["errors"]
        self.assertIn("missing or empty section: reteaching", errors)
        self.assertTrue(any("low-bandwidth or unplugged" in e for e in errors))

    def test_grade_band_and_assignment_status_required(self):
        doc = copy.deepcopy(LESSON)
        doc["context"] = {"grade_band": "high school", "assignment_status": {"teaching_assignment": "verified", "certification": "yes"}}
        errors = lesson.check(doc)["errors"]
        self.assertTrue(any("grade_band" in e for e in errors))
        self.assertTrue(any("teaching_assignment says verified" in e for e in errors))
        self.assertTrue(any("certification must be" in e for e in errors))

    def test_standards_mixups_and_bundled_text(self):
        doc = copy.deepcopy(LESSON)
        doc["standards"] = [{"record_id": "csta-teacher-2020", "label": "x"},
                            {"record_id": "cs2023", "label": "y"},
                            {"record_id": "csta-k12-2026", "label": "z", "text": "copied standard text"},
                            {"record_id": "made-up", "label": "w"}]
        errors = " | ".join(lesson.check(doc)["errors"])
        self.assertIn("teacher-practice standard", errors)
        self.assertIn("without a bridge", errors)
        self.assertIn("bundles standard text", errors)
        self.assertIn("not a known registry record", errors)

    def test_no_transfer_task_is_reported(self):
        doc = copy.deepcopy(LESSON)
        doc["tasks"] = doc["tasks"][:2]
        self.assertTrue(any("no transfer task" in e for e in lesson.check(doc)["errors"]))


class RespondTests(unittest.TestCase):
    def respond(self, **work):
        return lesson.respond(copy.deepcopy(LESSON), dict({"task_id": "T2"}, **work))

    def test_no_work_waits(self):
        r = lesson.respond(LESSON, None)
        self.assertEqual(r["status"], "awaiting-learner-response")
        self.assertIsNone(r["feedback"])
        self.assertIsNone(r["progress_claim"])

    def test_empty_work_waits(self):
        r = self.respond(code="", explanation="")
        self.assertEqual(r["status"], "awaiting-learner-response")
        self.assertIsNone(r["progress_claim"])

    def test_failing_work_quotes_actual_output_and_probe(self):
        code = "nums = [int(x) for x in input().split()]\nt = 0\nfor i in range(1, len(nums)):\n    t += nums[i]\nprint(t)\n"
        r = self.respond(code=code, explanation="adds them")
        self.assertEqual(r["status"], "tests-failing")
        self.assertIn("printed 5", r["feedback"])
        self.assertEqual([m["id"] for m in r["misconceptions"]], ["M1"])
        self.assertEqual(r["next_action"], "Trace with input 4.")

    def test_runtime_error_is_quoted(self):
        r = self.respond(code="print(undefined_name)\n", explanation="x")
        self.assertEqual(r["status"], "tests-failing")
        self.assertIn("NameError", r["feedback"])

    def test_passing_without_explanation_is_not_evidence(self):
        r = self.respond(code=SUM, explanation="")
        self.assertEqual(r["status"], "not-yet-evidence-of-understanding")
        self.assertIsNone(r["progress_claim"])

    def test_ai_generated_passing_work_is_not_evidence(self):
        r = self.respond(code=SUM, explanation="1, 3, 6", ai_generated=True)
        self.assertEqual(r["status"], "not-yet-evidence-of-understanding")

    def test_trace_missing_values_is_not_evidence(self):
        r = self.respond(code=SUM, explanation="it adds 1 and then 3")
        self.assertEqual(r["status"], "not-yet-evidence-of-understanding")
        self.assertIn("6", r["feedback"])

    def test_complete_trace_goes_to_teacher_review_without_progress_claim(self):
        r = self.respond(code=SUM, explanation="starts at 0", trace="1 then 3 then 6")
        self.assertEqual(r["status"], "ready-for-teacher-review")
        self.assertIsNone(r["progress_claim"])

    def test_prediction_misconception(self):
        r = lesson.respond(LESSON, {"task_id": "T1", "prediction": "3"})
        self.assertEqual(r["status"], "prediction-differs")
        self.assertIn("printed '5'", r["feedback"])
        self.assertEqual(r["misconceptions"][0]["id"], "M2")

    def test_timeout_is_reported_not_hung(self):
        r = self.respond(code="while True:\n    pass\n", explanation="x")
        self.assertEqual(r["status"], "tests-failing")
        self.assertIn("timed out", r["feedback"])


class CliTests(unittest.TestCase):
    def test_usage_and_invalid_input_exit_2(self):
        with tempfile.TemporaryDirectory() as tmp:
            good = write(tmp, "lesson.json", LESSON)
            self.assertEqual(run_cli()[0], 2)
            self.assertEqual(run_cli("grade", good)[0], 2)
            self.assertEqual(run_cli("check", write(tmp, "bad.json", "{not json"))[0], 2)
            self.assertEqual(run_cli("check", write(tmp, "list.json", [1, 2]))[0], 2)
            self.assertEqual(run_cli("respond", good, write(tmp, "w.json", {"task_id": "T9", "code": "x"}))[0], 2)
            self.assertEqual(run_cli("respond", good, write(tmp, "w2.json", {"code": "x"}))[0], 2)

    def test_exit_codes_for_check(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(run_cli("check", write(tmp, "ok.json", LESSON))[0], 0)
            bad = copy.deepcopy(LESSON)
            bad["examples"][0]["expected_output"] = "9"
            code, out = run_cli("check", write(tmp, "bad.json", bad))
            self.assertEqual(code, 1)
            self.assertFalse(json.loads(out)["ok"])

    def test_respond_without_work_exits_0_and_waits(self):
        with tempfile.TemporaryDirectory() as tmp:
            code, out = run_cli("respond", write(tmp, "lesson.json", LESSON))
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["status"], "awaiting-learner-response")


if __name__ == "__main__":
    unittest.main()
