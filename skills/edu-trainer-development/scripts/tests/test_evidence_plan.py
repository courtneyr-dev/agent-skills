import copy
import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import evidence_plan  # noqa: E402

GOOD = {
    "intervention": "Coaching cycle for new facilitators",
    "intended_performance": "Facilitators give criterion-specific feedback during practice",
    "human_data_boundary": "The program lead collects observations with participant consent; the agent drafts instruments only.",
    "revisit_if": "Fewer than half of observed sessions show criterion-specific feedback after two cycles",
    "measures": [
        {"id": "M1", "kind": "observation", "level": "behavior", "description": "Observed session", "owner": "human:program-lead",
         "timing": "Week 4", "baseline": "Week 0 observation", "result": None},
        {"id": "M2", "kind": "satisfaction-survey", "level": "reaction", "description": "Session survey",
         "owner": "human:program-lead", "timing": "End of session", "baseline": "None: first offering"},
    ],
}


def plan(**changes):
    p = copy.deepcopy(GOOD)
    p.update(changes)
    return p


def run_cli(obj):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        fh.write(obj if isinstance(obj, str) else json.dumps(obj))
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            code = evidence_plan.main(["check", fh.name])
    finally:
        os.unlink(fh.name)
    return code, json.loads(buf.getvalue())


class CheckTests(unittest.TestCase):
    def test_observation_plan_is_accepted(self):
        code, out = run_cli(GOOD)
        self.assertEqual(code, 0)
        self.assertEqual(out["evidence_measures"], ["M1"])
        self.assertEqual(out["transfer_measures"], ["M1"])
        self.assertEqual(out["warnings"], [])

    def test_survey_and_attendance_only_is_rejected(self):
        p = plan(measures=[GOOD["measures"][1],
                           {"id": "M3", "kind": "attendance", "level": "reaction", "description": "Sign-in",
                            "owner": "human:program-lead", "timing": "Each session", "baseline": "n/a"}])
        code, out = run_cli(p)
        self.assertEqual(code, 1)
        self.assertTrue(any("no evidence of learning" in f for f in out["findings"]))

    def test_generated_artifact_is_not_evidence(self):
        p = plan(measures=[{"id": "M1", "kind": "generated-artifact", "level": "learning", "description": "AI lesson",
                            "owner": "human:x", "timing": "t", "baseline": "b"}])
        self.assertEqual(evidence_plan.check(p)["status"], "rejected")

    def test_prefilled_result_is_rejected(self):
        p = plan()
        p["measures"][0]["result"] = "82% gave specific feedback"
        out = evidence_plan.check(p)
        self.assertTrue(any("pre-filled" in f for f in out["findings"]))

    def test_prefilled_top_level_outcomes_rejected(self):
        self.assertEqual(evidence_plan.check(plan(results={"gain": 0.3}))["status"], "rejected")

    def test_missing_owner_timing_baseline_and_boundary(self):
        p = plan(human_data_boundary="")
        p["measures"][0].update({"owner": "agent", "timing": "", "baseline": None})
        out = evidence_plan.check(p)
        text = " ".join(out["findings"])
        for word in ("human owner", "timing", "baseline", "human_data_boundary"):
            self.assertIn(word, text)

    def test_learning_without_transfer_warns(self):
        p = plan()
        p["measures"][0]["level"] = "learning"
        out = evidence_plan.check(p)
        self.assertEqual(out["status"], "accepted")
        self.assertIn("transfer", out["warnings"][0])


class InvalidInputTests(unittest.TestCase):
    def assertInvalid(self, obj):
        code, out = run_cli(obj)
        self.assertEqual(code, 2, out)

    def test_not_json(self):
        self.assertInvalid("nope")

    def test_unknown_kind(self):
        p = plan()
        p["measures"][0]["kind"] = "vibes"
        self.assertInvalid(p)

    def test_unknown_level(self):
        p = plan()
        p["measures"][0]["level"] = "delight"
        self.assertInvalid(p)

    def test_empty_measures(self):
        self.assertInvalid(plan(measures=[]))

    def test_duplicate_ids(self):
        p = plan()
        p["measures"][1]["id"] = "M1"
        self.assertInvalid(p)

    def test_missing_intervention(self):
        p = plan()
        del p["intervention"]
        self.assertInvalid(p)


if __name__ == "__main__":
    unittest.main()
