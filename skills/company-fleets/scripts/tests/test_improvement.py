"""Compounding-improvement gate: pinned criteria, reproduction, regression, review."""
import difflib
import json
import os
import shutil
import tempfile
import unittest

from support import SKILL

from fleetlib import improvement as imp

SKILLS = os.path.dirname(SKILL)
TARGET = "company-fleets/scripts/fleetlib/untrusted.py"


class Sandbox(unittest.TestCase):
    """Points the module at a temp copy of improvement/ so records, pins and evidence stay out of the rig."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.saved = (imp.SKILL_DIR, imp.IMP_DIR, imp.EVIDENCE_DIR)
        shutil.copytree(os.path.join(SKILL, "improvement"), os.path.join(self.tmp, "improvement"),
                        ignore=shutil.ignore_patterns("pins"))
        imp.SKILL_DIR, imp.IMP_DIR, imp.EVIDENCE_DIR = self.tmp, os.path.join(self.tmp, "improvement"), os.path.join(self.tmp, "evidence")

    def tearDown(self):
        imp.SKILL_DIR, imp.IMP_DIR, imp.EVIDENCE_DIR = self.saved  # the temp copy stays; nothing is deleted

    def record(self, rid, edit=None, patch_text=None, cases=None):
        with open(os.path.join(SKILL, "improvement", "records", "IMP-001.json")) as fh:
            rec = json.load(fh)
        rec["id"] = rid
        rec["change"]["exercised_by"] = ["no-fleet-eval-matches-this"]
        if cases is not None:
            rec["criteria"]["cases"] = "improvement/cases/%s.json" % rid
            self.write("improvement/cases/%s.json" % rid, cases)
        if patch_text is not None:
            rec["change"]["patch"] = "improvement/patches/%s.patch" % rid
            with open(os.path.join(self.tmp, rec["change"]["patch"]), "w") as fh:
                fh.write(patch_text)
        if edit:
            edit(rec)
        self.write("improvement/records/%s.json" % rid, rec)
        return rec

    def write(self, rel, obj):
        with open(os.path.join(self.tmp, rel), "w") as fh:
            json.dump(obj, fh, indent=2)


def cases_of(rid="IMP-001"):
    with open(os.path.join(SKILL, "improvement", "cases", rid + ".json")) as fh:
        return json.load(fh)


class Criteria(Sandbox):
    def test_criteria_edited_after_pin_refuse_evaluation(self):
        c = cases_of()
        self.record("IMP-T1", cases=c)
        self.assertEqual(imp.pin("IMP-T1")["status"], "pinned")
        c["fresh"] = c["fresh"][:1]
        self.write("improvement/cases/IMP-T1.json", c)
        self.assertEqual(imp.pin("IMP-T1")["status"], "refused")
        with self.assertRaisesRegex(imp.ImprovementError, "criteria changed after pinning"):
            imp.evaluate("IMP-T1", SKILLS)

    def test_narrowing_the_regression_selector_breaks_the_pin(self):
        self.record("IMP-T2", cases=cases_of())
        imp.pin("IMP-T2")
        self.record("IMP-T2", cases=cases_of(), edit=lambda r: r["change"].update(exercised_by=["something-else"]))
        with self.assertRaisesRegex(imp.ImprovementError, "criteria changed after pinning"):
            imp.evaluate("IMP-T2", SKILLS)

    def test_evaluation_needs_a_pin(self):
        self.record("IMP-T3", cases=cases_of())
        with self.assertRaisesRegex(imp.ImprovementError, "no pinned criteria"):
            imp.evaluate("IMP-T3", SKILLS)


class Evaluation(Sandbox):
    def test_unreproduced_observation_cannot_change_a_skill(self):
        c = cases_of()
        c["original"] = [dict(c["fresh"][-1], id="already-clean")]  # the base scanner already passes this
        self.record("IMP-T4", cases=c)
        imp.pin("IMP-T4")
        out = imp.evaluate("IMP-T4", SKILLS)
        self.assertEqual(out["verdict"], "fail")
        self.assertFalse(out["checks"]["observation reproduced on the unpatched copy"])
        g = imp.gate("IMP-T4", SKILLS)
        self.assertEqual(g["stage"], "observed")
        self.assertIn("unverified observation", " ".join(g["reasons"]))

    def test_a_patch_that_breaks_a_rule_fails(self):
        path = os.path.join(SKILLS, TARGET)
        with open(path) as fh:
            before = fh.readlines()
        after = [l for l in before if not l.lstrip().startswith('("evidence", r"\\b(skip')]
        self.assertEqual(len(before) - len(after), 1)
        bad = "".join(difflib.unified_diff(before, after, "a/" + TARGET, "b/" + TARGET))
        self.record("IMP-T5", patch_text=bad, cases=cases_of())
        imp.pin("IMP-T5")
        out = imp.evaluate("IMP-T5", SKILLS)
        self.assertEqual(out["verdict"], "fail")
        self.assertFalse(out["checks"]["original failure passes after the patch"])
        self.assertTrue(out["checks"]["reverse patch restores the base file"])


class Gate(Sandbox):
    def test_proposer_cannot_review_its_own_change(self):
        self.record("IMP-T6", cases=cases_of(), edit=lambda r: r.update(
            review={"reviewer": r["change"]["proposed_by"], "verdict": "approve"}))
        g = imp.gate("IMP-T6", SKILLS)
        self.assertIn("the proposer cannot review its own change", g["reasons"])
        self.assertFalse(g["promotable"])


class RealRecord(unittest.TestCase):
    def test_imp_001_waits_for_review_and_promotion(self):
        g = imp.gate("IMP-001", SKILLS)
        self.assertEqual(g["stage"], "evaluated", g["reasons"])
        self.assertFalse(g["promotable"])
        self.assertTrue(any("no review" in r for r in g["reasons"]))


if __name__ == "__main__":
    unittest.main()
