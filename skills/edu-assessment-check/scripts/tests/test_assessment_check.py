import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import assessment_check as ac  # noqa: E402

LEVELS = [{"score": 1, "descriptor": "beginning"}, {"score": 2, "descriptor": "proficient"}]


def run(doc):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(doc, fh)
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            code = ac.main(["check", fh.name])
    finally:
        os.unlink(fh.name)
    return code, json.loads(buf.getvalue())


def doc(level="apply", task_level="apply", evidence=("product", "explanation"), prompt="Build the sheet.", demands=None, work=None):
    return {"context": {"reading_grade_target": 9},
            "objectives": [{"id": "O1", "level": level, "text": "Build a profit model.", "construct": "profit modeling"}],
            "tasks": [{"id": "T1", "objective_ids": ["O1"], "cognitive_level": task_level, "evidence": list(evidence),
                       "prompt": prompt, "demands": demands or {}}],
            "rubric": [{"id": "R1", "task_id": "T1", "objective_id": "O1", "criterion": "Model", "levels": LEVELS,
                        "scoring_rationale": "Scores the model, not arithmetic."}],
            "student_work": work or []}


def codes(out, key="errors"):
    return {e["code"] for e in out[key]}


class AlignmentTests(unittest.TestCase):
    def test_aligned_package_passes(self):
        code, out = run(doc())
        self.assertEqual(code, 0)
        self.assertTrue(out["ok"])

    def test_recall_quiz_rejected_for_application_objective(self):
        code, out = run(doc(task_level="remember", evidence=("recall",)))
        self.assertEqual(code, 1)
        self.assertIn("recall-only-evidence", codes(out))

    def test_passing_tests_and_ai_output_are_not_understanding(self):
        code, out = run(doc(level="understand", task_level="apply", evidence=("passing-tests", "ai-output")))
        self.assertIn("output-only-evidence", codes(out))

    def test_rubric_must_name_assessed_objective_and_rationale(self):
        d = doc()
        d["objectives"].append({"id": "O2", "level": "remember", "text": "Define margin."})
        d["rubric"][0].update(objective_id="O2", scoring_rationale="")
        code, out = run(d)
        self.assertIn("no-scoring-rationale", codes(out))
        self.assertIn("objective-unscored", codes(out))
        self.assertIn("objective-unassessed", codes(out))


class FairnessTests(unittest.TestCase):
    def test_construct_irrelevant_barriers_are_flagged(self):
        prompt = ("Utilizing the proprietary enterprise spreadsheet application, operationalize comprehensive "
                  "profitability calculations incorporating differentiated methodologies and organizational conventions.")
        demands = {"paid_software": True, "internet_required": True, "color_only_cues": True, "timed_minutes": 5,
                   "brand_specific_tool": "BrandSheet"}
        code, out = run(doc(prompt=prompt, demands=demands))
        self.assertEqual(code, 1)
        self.assertEqual(codes(out, "flags"), {"irrelevant-reading-demand", "paid-software", "no-offline-route",
                                               "color-only", "speed-not-in-construct", "tool-specific"})

    def test_speed_allowed_when_construct_is_speed(self):
        code, out = run(doc(demands={"timed_minutes": 5, "construct_is_speed": True}))
        self.assertEqual(code, 0)

    def test_reading_demand_not_flagged_when_reading_is_the_construct(self):
        d = doc(prompt="Utilizing the proprietary enterprise application, operationalize comprehensive profitability "
                       "calculations incorporating differentiated methodologies and organizational conventions.")
        d["objectives"][0]["construct"] = "reading business documents"
        self.assertEqual(run(d)[0], 0)

    def test_unlabeled_student_work_rejected(self):
        code, out = run(doc(work=[{"id": "W1", "content": "x"}]))
        self.assertIn("unlabeled-student-work", codes(out))
        code, out = run(doc(work=[{"id": "W1", "synthetic": True, "label": "SYNTHETIC practice work"}]))
        self.assertEqual(code, 0)


class InvalidInputTests(unittest.TestCase):
    def test_rejects_missing_lists_bad_levels_and_duplicates(self):
        self.assertEqual(run({"objectives": []})[1]["status"], "invalid")
        d = doc(level="memorize")
        d["tasks"][0]["evidence"] = ["vibes"]
        d["rubric"].append(dict(d["rubric"][0]))
        code, out = run(d)
        self.assertEqual(code, 1)
        text = " ".join(out["errors"])
        self.assertIn("memorize", text)
        self.assertIn("evidence must be", text)
        self.assertIn("duplicate ids", text)

    def test_usage(self):
        self.assertEqual(ac.main([]), 2)


UNIT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "company-fleets",
                                     "fleets", "bcit-education", "fixtures", "bcit-unit-store"))


def run_fixture(name):
    with open(os.path.join(UNIT, name), encoding="utf-8") as fh:
        return run(json.load(fh))


class PromptTextOverridesLabels(unittest.TestCase):
    """The verdict follows what the prompt asks for, not only the labels its author declared."""

    def test_recall_quiz_labeled_apply_is_rejected(self):
        code, out = run(doc(prompt="Ten multiple-choice questions: define fixed cost, define variable cost, define break-even."))
        self.assertEqual(code, 1)
        self.assertIn("label-text-mismatch", codes(out))
        self.assertIn("recall-only-evidence", codes(out))

    def test_chatbot_output_labeled_explanation_is_rejected(self):
        code, out = run(doc(level="understand", task_level="understand", evidence=("explanation",),
                            prompt="Paste the chatbot's explanation of break-even; full marks if it is correct."))
        self.assertEqual(code, 1)
        self.assertIn("output-only-evidence", codes(out))

    def test_autograder_only_prompt_labeled_explanation_is_rejected(self):
        code, out = run(doc(level="understand", task_level="apply", evidence=("explanation", "product"),
                            prompt="Submit code that passes the three autograder tests. Full credit when all tests pass."))
        self.assertIn("output-only-evidence", codes(out))

    def test_paid_tool_and_online_step_in_prompt_are_flagged(self):
        code, out = run(doc(prompt="Build the sheet in Microsoft Excel 365 with a paid license, then look up current "
                                   "lemonade prices online. Explain each formula.",
                            demands={"paid_software": False, "internet_required": False, "offline_alternative": True}))
        self.assertEqual(code, 1)
        self.assertTrue({"paid-software", "no-offline-route"} <= codes(out, "flags"))

    def test_free_tool_and_explanation_prompts_still_pass(self):
        for prompt in ("Build the sheet in the school spreadsheet program and explain each formula.",
                       "Write a query for revenue by item, then explain which item drives profit."):
            self.assertEqual(run(doc(prompt=prompt))[0], 0, prompt)

    def test_reviewer_probes_retained_as_fixtures(self):
        for name, code_name in (("assessment-mislabeled-recall.json", "recall-only-evidence"),
                                ("assessment-mislabeled-ai-output.json", "output-only-evidence")):
            code, out = run_fixture(name)
            self.assertEqual(code, 1, name)
            self.assertIn(code_name, codes(out), name)
        code, out = run_fixture("assessment-prompt-paid-online.json")
        self.assertEqual(code, 1)
        self.assertIn("no-offline-route", codes(out, "flags"))

    def test_store_unit_fixtures_unchanged(self):
        self.assertEqual(run_fixture("assessment.json")[0], 0)
        self.assertEqual(run_fixture("assessment-speed-construct.json")[0], 0)

    def test_honest_weak_labels_are_not_called_mismatched(self):
        code, out = run_fixture("assessment-output-only.json")
        self.assertIn("output-only-evidence", codes(out))
        self.assertNotIn("label-text-mismatch", codes(out))


if __name__ == "__main__":
    unittest.main()
