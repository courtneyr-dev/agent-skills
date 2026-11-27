import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import package  # noqa: E402

GUIDE = "\n".join("## " + s.title() for s in package.KINDS["trainer-package"]["sections"]) + "\n"
RUBRIC = {"criteria": [{"id": "C1", "levels": [{"score": 0}, {"score": 1}]}],
          "anchors": [{"id": "A1", "origin": "generated-practice-anchor", "intended_score": 0}]}
RATINGS = {"label": "SYNTHETIC test", "scale": [0, 1], "ratings": [
    {"item": "A1", "rater": "generated:a", "score": 0, "source": "generated"},
    {"item": "A1", "rater": "generated:b", "score": 1, "source": "generated"}]}
PLAN = {"intervention": "x", "intended_performance": "y", "human_data_boundary": "Lead collects; agent records nothing.",
        "measures": [{"id": "M1", "kind": "observation", "level": "behavior", "description": "d",
                      "owner": "human:lead", "timing": "t", "baseline": "b"}]}


class PackageTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.write("guide.md", GUIDE)
        self.write("rubric.json", RUBRIC)
        self.write("ratings.json", RATINGS)
        self.write("plan.json", PLAN)
        self.write("exercise.md", "# Calibration\n")
        self.manifest = {"label": "SYNTHETIC test", "kind": "trainer-package", "files": {
            "guide": "guide.md", "rubric": "rubric.json", "calibration_exercise": "exercise.md",
            "calibration_ratings": "ratings.json", "evidence_plan": "plan.json"}}

    def tearDown(self):
        shutil.rmtree(self.dir)

    def write(self, name, obj):
        with open(os.path.join(self.dir, name), "w") as fh:
            fh.write(obj if isinstance(obj, str) else json.dumps(obj))

    def run_check(self, manifest=None):
        self.write("manifest.json", self.manifest if manifest is None else manifest)
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = package.main(["check", os.path.join(self.dir, "manifest.json")])
        return code, json.loads(buf.getvalue())

    def test_complete_package_passes(self):
        code, out = self.run_check()
        self.assertEqual(code, 0, out)
        self.assertEqual(out["calibration"]["status"], "practice-only")

    def test_missing_section_and_file_are_findings(self):
        self.write("guide.md", "## Design rationale\n")
        self.manifest["files"]["evidence_plan"] = "nope.json"
        code, out = self.run_check()
        self.assertEqual(code, 1)
        text = " ".join(out["findings"])
        self.assertIn("transfer evaluation", text)
        self.assertIn("evidence_plan", text)

    def test_unlabeled_anchor_is_a_finding(self):
        self.write("rubric.json", {"criteria": RUBRIC["criteria"], "anchors": [{"id": "A1", "origin": "real"}]})
        code, out = self.run_check()
        self.assertIn("anchor A1", out["findings"][0])

    def test_synthetic_package_cannot_report_computed_agreement(self):
        self.write("ratings.json", {"label": "real ratings", "scale": [0, 1], "ratings": [
            {"item": i, "rater": r, "score": s, "source": "human-rated"}
            for i, r, s in (("a", "human:x", 0), ("a", "human:y", 0), ("b", "human:x", 1), ("b", "human:y", 1))]})
        code, out = self.run_check()
        self.assertTrue(any("synthetic package reports computed agreement" in f for f in out["findings"]))

    def test_teacher_module_rejects_merged_evidence_lines_and_student_labels(self):
        sections = package.KINDS["teacher-education-module"]["sections"]
        self.write("guide.md", "\n".join("## " + s for s in sections))
        self.write("inst.json", {"items": [{"id": "O1", "look_fors": ["x"]}], "observations": [{"id": "z", "observer": "human:s"}]})
        self.write("key.json", {"items": []})
        m = dict(self.manifest, kind="teacher-education-module")
        m["files"] = dict(m["files"], observation_instrument="inst.json", answer_key="key.json")
        m["iste_educator_labels"] = ["Designer", "Empowered Learner"]
        m["evidence_lines"] = {n: {"status": "planned", "inferred_from": []} for n in package.EVIDENCE_LINES}
        m["evidence_lines"]["occupational_assessment_readiness"]["inferred_from"] = ["pedagogical_competence"]
        code, out = self.run_check(m)
        text = " ".join(out["findings"])
        self.assertEqual(code, 1)
        self.assertIn("does not establish another", text)
        self.assertIn("Empowered Learner", text)
        self.assertIn("observation records", text)

    def test_invalid_manifest(self):
        code, out = self.run_check({"kind": "brochure", "files": {}})
        self.assertEqual(code, 2)
        self.write("bad.json", "{")
        buf = io.StringIO()
        with redirect_stdout(buf):
            self.assertEqual(package.main(["check", os.path.join(self.dir, "bad.json")]), 2)
        self.assertEqual(package.main([]), 2)


if __name__ == "__main__":
    unittest.main()
