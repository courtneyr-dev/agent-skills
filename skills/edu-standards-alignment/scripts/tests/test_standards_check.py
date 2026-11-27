import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import standards_check as sc  # noqa: E402

EVIDENCE = "fleets/bcit-education/evidence/sources/csta-k12-2026.txt"


def rec(rid, **kw):
    base = {"id": rid, "family": "fam", "kind": "student-standard", "audience": "students", "grade_band": "9-12",
            "authority": "A", "title": "T", "edition": "2026", "edition_status": "current", "superseded_by": None,
            "id_scheme": {"pattern": "^HS-[A-Z]{3}-[0-9]{2}$", "example": "HS-ALG-01"}, "labels": ["One", "Two"],
            "source_url": "https://example.invalid", "access": "public", "license": "CC BY-NC-SA",
            "permitted_use": "cite ids", "bundle_text": False, "status": "unverified", "verified_on": None,
            "evidence": None, "notes": "test"}
    base.update(kw)
    return base


REG = {"records": [
    rec("stu-2026"),
    rec("stu-2017", edition="2017", edition_status="superseded", superseded_by="stu-2026",
        id_scheme={"pattern": "^3A-[A-Z]{2}-[0-9]{2}$", "example": "3A-AP-13"}),
    rec("teach-2020", kind="teacher-standard", audience="cs-teachers", id_scheme=None),
    rec("uni", family="uni", kind="university-curriculum", audience="university", id_scheme=None),
    rec("exam", family="exam", kind="occupational-assessment", audience="all", id_scheme=None, access="restricted"),
    rec("wcag", family="w3c", kind="accessibility-standard", audience="all", id_scheme=None),
]}


def run(argv, files):
    paths = []
    for obj in files:
        fh = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False)
        json.dump(obj, fh)
        fh.close()
        paths.append(fh.name)
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            code = sc.main([a.format(*paths) for a in argv])
    finally:
        for p in paths:
            os.unlink(p)
    return code, json.loads(buf.getvalue())


def align(rows, ctx=None):
    return run(["align", "{1}", "--registry", "{0}"], [REG, {"context": ctx or {"learner_audience": "students"}, "alignments": rows}])


def row(**kw):
    base = {"objective_id": "O1", "criterion_id": "R1", "status": "unverified"}
    base.update(kw)
    return base


def codes(out):
    return {f["code"] for r in out["rows"] for f in r["findings"]}


class AlignTests(unittest.TestCase):
    def test_honest_unverified_row_passes(self):
        code, out = align([row(record_id="stu-2026", standard_id="HS-ALG-01")])
        self.assertEqual(code, 0)
        self.assertEqual(out["coverage"], "partial")

    def test_missing_source_is_a_gap_and_overclaim_fails(self):
        code, out = align([row(record_id="state-9999", standard_id="X.1", status="verified", reviewer="human:t", evidence="e")])
        self.assertEqual(code, 1)
        self.assertEqual(out["rows"][0]["supported"], "gap")
        self.assertIn("overclaimed", codes(out))

    def test_verified_needs_registry_verification_and_human_review(self):
        code, out = align([row(record_id="stu-2026", standard_id="HS-ALG-01", status="verified")])
        self.assertIn("overclaimed", codes(out))
        self.assertEqual(out["rows"][0]["supported"], "unverified")

    def test_teacher_standard_for_student_objective(self):
        code, out = align([row(record_id="teach-2020", standard_id="4g")])
        self.assertEqual(code, 1)
        self.assertIn("teacher-standard-for-students", codes(out))

    def test_student_standard_for_teacher_objective(self):
        code, out = align([row(record_id="stu-2026", standard_id="HS-ALG-01", audience="teachers")])
        self.assertIn("student-standard-for-teachers", codes(out))

    def test_wrong_edition_identifier(self):
        code, out = align([row(record_id="stu-2026", standard_id="3A-AP-13")])
        self.assertIn("id-not-in-scheme", codes(out))

    def test_superseded_without_adoption_fails_and_adoption_is_preserved(self):
        code, out = align([row(record_id="stu-2017", standard_id="3A-AP-13")])
        self.assertIn("superseded-edition", codes(out))
        code, out = align([row(record_id="stu-2017", standard_id="3A-AP-13")],
                          {"learner_audience": "students", "district_adoptions": ["stu-2017"]})
        self.assertEqual(code, 0)
        self.assertIn("adopted-older-edition", codes(out))
        code, out = align([row(record_id="stu-2026", standard_id="HS-ALG-01")],
                          {"learner_audience": "students", "district_adoptions": ["stu-2017"]})
        self.assertIn("not-district-adoption", codes(out))

    def test_university_curriculum_needs_bridge(self):
        code, out = align([row(record_id="uni", standard_id="SDF")])
        self.assertIn("university-to-school", codes(out))
        code, out = align([row(record_id="uni", standard_id="SDF", progression_bridge="SDF ideas reduced to tracing loops")])
        self.assertNotIn("university-to-school", codes(out))

    def test_restricted_assessment_and_bundled_text(self):
        code, out = align([row(record_id="exam", standard_id="ACC-1", status="gap"),
                           row(record_id="stu-2026", standard_id="HS-ALG-01", standard_text="copied")])
        self.assertEqual(code, 1)
        self.assertTrue({"restricted-assessment-content", "text-bundled"} <= codes(out))

    def test_accessibility_standard_is_not_an_alignment(self):
        code, out = align([row(record_id="wcag", status="gap")])
        self.assertIn("not-a-learning-standard", codes(out))


class RegistryTests(unittest.TestCase):
    def test_live_registries_are_valid(self):
        self.assertEqual(run(["registry"], [])[0], 0)
        self.assertEqual(run(["orgs"], [])[0], 0)

    def test_registry_rejects_bad_records(self):
        bad = {"records": [rec("a", status="verified"), rec("a"), rec("b", kind="poster", superseded_by="zzz",
                                                                       id_scheme={"pattern": "^X$", "example": "Y"})]}
        code, out = run(["registry", "--registry", "{0}"], [bad])
        self.assertEqual(code, 1)
        text = " ".join(out["errors"])
        for part in ("a is verified without", "duplicate record id a", "kind 'poster'", "example 'Y'", "zzz"):
            self.assertIn(part, text)

    def test_orgs_rejects_membership_and_installable(self):
        org = {"id": "x", "name": "X", "acronym": "X", "former_names": [], "audience": "a", "resources": [],
               "professional_learning": [], "url": "u", "terms": "t", "priority": "secondary", "kind": "package",
               "installable": True, "membership": "member", "status": "verified", "verified_on": None,
               "evidence": None, "notes": ""}
        code, out = run(["orgs", "--orgs", "{0}"], [{"records": [org]}])
        self.assertEqual(code, 1)
        self.assertEqual(len(out["errors"]), 4)


class CoverageAndOrgRefTests(unittest.TestCase):
    def test_coverage_reports_missing_and_unknown(self):
        code, out = run(["coverage", "{1}", "--record", "stu-2026", "--field", "areas", "--registry", "{0}"],
                        [REG, {"courses": [{"id": "C1", "areas": ["One", "Three"]}]}])
        self.assertEqual(code, 1)
        self.assertEqual(out["missing"], ["Two"])
        self.assertEqual(out["unknown_labels"][0]["label"], "Three")

    def test_org_refs_against_live_registry(self):
        code, out = run(["org-refs", "{0}"], [{"references": [{"name": "SIGITE", "relation": "cites"},
                                                               {"name": "CSTA", "relation": "member"}]}])
        self.assertEqual(code, 1)
        found = [f["code"] for r in out["references"] for f in r["findings"]]
        self.assertIn("former-name", found)
        self.assertIn("credential-claim", found)


class InvalidInputTests(unittest.TestCase):
    def test_align_rejects_bad_rows(self):
        code, out = run(["align", "{1}", "--registry", "{0}"], [REG, {"alignments": [{"objective_id": "O1", "status": "great"}]}])
        self.assertEqual(code, 1)
        self.assertEqual(out["status"], "invalid")
        code, out = run(["align", "{1}", "--registry", "{0}"], [REG, {"alignments": []}])
        self.assertEqual(out["status"], "invalid")

    def test_usage_error(self):
        self.assertEqual(sc.main(["nope"]), 2)


SRC = "fleets/bcit-education/evidence/sources/csta-k12-2026.txt"  # exists under company-fleets
PUB = {"records": [rec("pub", status="verified", verified_on="2026-11-25", evidence=SRC,
                       ids=["HS-ALG-01", "HS-ALG-02"], ids_source=SRC),
                   rec("scheme-only", status="verified", verified_on="2026-11-25", evidence=SRC)]}


def align_pub(rows):
    return run(["align", "{1}", "--registry", "{0}"], [PUB, {"context": {"learner_audience": "students"}, "alignments": rows}])


def reviewed(**kw):
    return row(status="verified", reviewer="human:teacher-of-record", evidence=SRC, **kw)


class PublishedIdTests(unittest.TestCase):
    """A well-formed identifier is not a real one: ids are checked against the stored published list."""

    def test_invented_wellformed_id_is_not_verified(self):
        code, out = align_pub([reviewed(record_id="pub", standard_id="HS-ALG-99")])
        self.assertEqual(code, 1)
        self.assertEqual(out["rows"][0]["supported"], "gap")
        self.assertIn("id-not-published", codes(out))

    def test_published_id_with_existing_review_evidence_verifies(self):
        code, out = align_pub([reviewed(record_id="pub", standard_id="HS-ALG-01")])
        self.assertEqual(code, 0, out)
        self.assertEqual(out["rows"][0]["supported"], "verified")

    def test_review_evidence_file_must_exist(self):
        code, out = align_pub([row(record_id="pub", standard_id="HS-ALG-01", status="verified",
                                   reviewer="human:teacher-of-record", evidence="evidence/review-notes.txt")])
        self.assertEqual(code, 1)
        self.assertEqual(out["rows"][0]["supported"], "unverified")
        self.assertIn("review-evidence-missing", codes(out))

    def test_scheme_without_stored_ids_caps_at_unverified(self):
        code, out = align_pub([reviewed(record_id="scheme-only", standard_id="HS-ALG-01")])
        self.assertEqual(out["rows"][0]["supported"], "unverified")
        self.assertIn("id-list-not-stored", codes(out))

    def test_registry_rejects_stored_ids_outside_the_scheme(self):
        bad = {"records": [rec("pub", ids=["HS-ALG-01", "XX-1"], ids_source=SRC)]}
        code, out = run(["registry", "--registry", "{0}"], [bad])
        self.assertEqual(code, 1)
        self.assertIn("XX-1", " ".join(out["errors"]))

    def test_reviewer_probes_against_live_registry(self):
        for record_id, sid in (("csta-k12-2026", "HS-ALG-ZZ-99"), ("iste-students", "1.7.z")):
            code, out = run(["align", "{0}"], [{"context": {"learner_audience": "students"}, "alignments": [
                row(record_id=record_id, standard_id=sid, status="verified", reviewer="human:teacher-of-record",
                    evidence="evidence/review-notes.txt")]}])
            self.assertEqual(code, 1, sid)
            self.assertNotEqual(out["rows"][0]["supported"], "verified", sid)
            self.assertIn("id-not-published", codes(out), sid)

    def test_live_registry_stores_published_ids(self):
        with open(sc.DEFAULT_REGISTRY, encoding="utf-8") as fh:
            recs = {r["id"]: r for r in json.load(fh)["records"]}
        self.assertIn("HS-ALG-ML-06", recs["csta-k12-2026"]["ids"])
        self.assertIn("3A-AP-13", recs["csta-k12-2017"]["ids"])
        self.assertIn("1.5", recs["iste-students"]["ids"])
        self.assertNotIn("1.7.z", recs["iste-students"]["ids"])


if __name__ == "__main__":
    unittest.main()
