import copy
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import needs  # noqa: E402


def ev(value, source="fixture source"):
    return {"value": value, "source": source}


BASE = {
    "problem": "Editors publish late.",
    "audience": {"who": "Editors"},
    "task": {"name": "Publish", "steps": ["Draft", "Publish"]},
    "evidence": {
        "can_do_when_required": ev(True),
        "expectations_clear": ev(True),
        "feedback_given": ev(True),
        "tools_adequate": ev(True),
        "process_clear": ev(True),
        "access_ok": ev(True),
        "consequences_aligned": ev(True),
    },
}


def case(**evidence):
    c = copy.deepcopy(BASE)
    c["evidence"].update(evidence)
    return c


def run_cli(obj):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        fh.write(obj if isinstance(obj, str) else json.dumps(obj))
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            code = needs.main(["route", fh.name])
    finally:
        os.unlink(fh.name)
    return code, json.loads(buf.getvalue())


class RouteTests(unittest.TestCase):
    def test_tool_obstacle_routes_away_from_a_course(self):
        c = case(tools_adequate=ev(False, "upload times out"))
        c["requested_solution"] = "course"
        out = needs.route(c)
        self.assertEqual(out["status"], "route")
        self.assertIs(out["course_indicated"], False)
        self.assertEqual([r["code"] for r in out["remedies"]], ["ENV-RESOURCE-TOOL"])
        self.assertTrue(out["not_recommended"][0].startswith("course:"))

    def test_never_done_before_routes_to_training(self):
        out = needs.route(case(can_do_when_required=ev(False), did_it_before=ev(False)))
        self.assertIs(out["course_indicated"], True)
        self.assertEqual([r["code"] for r in out["remedies"]], ["SKILL-TRAINING"])

    def test_faded_skill_routes_to_practice_not_a_course(self):
        out = needs.route(case(can_do_when_required=ev(False), did_it_before=ev(True), performed_often=ev(False)))
        self.assertIs(out["course_indicated"], False)
        self.assertEqual(out["remedies"][0]["code"], "SKILL-PRACTICE")

    def test_training_with_environment_obstacle_warns_about_transfer(self):
        out = needs.route(case(can_do_when_required=ev(False), did_it_before=ev(False), access_ok=ev(False)))
        self.assertIn("ENV-RESOURCE-ACCESS", out["notes"][0])

    def test_unknown_skill_question_collects_evidence(self):
        code, out = run_cli(case(can_do_when_required=ev(None, "")))
        self.assertEqual(code, 1)
        self.assertEqual(out["status"], "collect-evidence")
        self.assertIsNone(out["course_indicated"])
        self.assertEqual(out["questions"][0]["key"], "can_do_when_required")

    def test_unsourced_value_is_treated_as_missing(self):
        out = needs.route(case(tools_adequate=ev(False, "")))
        self.assertEqual(out["status"], "collect-evidence")
        self.assertEqual(out["remedies"], [])
        self.assertIn("no source", out["warnings"][0])

    def test_no_gap_found_is_reported_not_invented(self):
        code, out = run_cli(case())
        self.assertEqual(code, 0)
        self.assertEqual(out["status"], "no-gap-found")
        self.assertEqual(out["remedies"], [])

    def test_analysis_gaps_list_missing_audience_and_task_fields(self):
        out = needs.route(case())
        self.assertIn("audience.size", out["audience_task_analysis"]["analysis_gaps"])
        self.assertIn("task.frequency", out["audience_task_analysis"]["analysis_gaps"])


class InvalidInputTests(unittest.TestCase):
    def assertInvalid(self, obj):
        code, out = run_cli(obj)
        self.assertEqual(code, 2)
        self.assertEqual(out["status"], "invalid-input")

    def test_not_json(self):
        self.assertInvalid("{not json")

    def test_not_an_object(self):
        self.assertInvalid([1, 2])

    def test_missing_task_steps(self):
        c = case()
        c["task"]["steps"] = []
        self.assertInvalid(c)

    def test_value_must_be_boolean_or_null(self):
        self.assertInvalid(case(tools_adequate={"value": "no", "source": "x"}))
        self.assertInvalid(case(tools_adequate={"value": 0, "source": "x"}))

    def test_unknown_evidence_key(self):
        self.assertInvalid(case(learning_style={"value": True, "source": "x"}))

    def test_missing_problem(self):
        c = case()
        del c["problem"]
        self.assertInvalid(c)

    def test_usage_error(self):
        self.assertEqual(needs.main([]), 2)


if __name__ == "__main__":
    unittest.main()
