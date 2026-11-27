import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import data_guard as dg  # noqa: E402

FIX = os.path.normpath(os.path.join(HERE, "..", "..", "..", "company-fleets", "fleets", "bcit-education", "fixtures",
                                    "edu-student-data-guard"))
EVIDENCE = "fleets/bcit-education/evidence/sources/pa-cspg-71.txt"  # any file that exists under company-fleets
VERIFIED_POLICY = {"verified": True, "verified_by": "human:school-privacy-officer", "verified_on": "2026-11-26",
                   "evidence": EVIDENCE, "approved_tools": ["claude-code"],
                   "role_access": {"classroom-a-assistant": ["read"]}, "consent_basis": "school official exception",
                   "retention_days": 30}


def run_cli(req, *extra):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(req, fh)
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            code = dg.main(["check", fh.name] + list(extra))
    finally:
        os.unlink(fh.name)
    out = buf.getvalue()
    return code, (json.loads(out) if out.strip() else {})


def req(**kw):
    base = {"principal": "classroom-a-assistant", "record": "CA-ROSTER", "data_origin": "synthetic",
            "tool": "claude-code", "purpose": "practice"}
    base.update(kw)
    return base


def tenants():
    with open(dg.TENANTS, encoding="utf-8") as fh:
        return json.load(fh)


class GuardTests(unittest.TestCase):
    def test_same_classroom_synthetic_allowed(self):
        code, out = run_cli(req())
        self.assertEqual((code, out["decision"]), (0, "allow"))

    def test_other_classroom_student_record_refused(self):
        for record in ("CB-ROSTER", "CB-GRADES"):
            code, out = run_cli(req(record=record))
            self.assertEqual(code, 1)
            self.assertIn("never shared across tenants", out["reasons"][0])

    def test_real_records_refused_under_the_shipped_policy(self):
        code, out = run_cli(req(data_origin="real"))
        self.assertEqual(code, 1)
        self.assertIn("human-data boundary", out["reasons"][0])

    def test_real_records_allowed_only_with_complete_verified_policy(self):
        decision, _ = dg.decide(req(data_origin="real"), VERIFIED_POLICY, tenants())
        self.assertEqual(decision, "allow")
        for missing in ("retention_days", "verified_on", "evidence"):
            partial = dict(VERIFIED_POLICY)
            partial.pop(missing)
            decision, reasons = dg.decide(req(data_origin="real"), partial, tenants())
            self.assertEqual(decision, "refuse", missing)

    def test_verified_flag_without_existing_evidence_is_not_verified(self):
        forged = dict(VERIFIED_POLICY, evidence="fleets/bcit-education/evidence/no-such-review.txt")
        decision, reasons = dg.decide(req(data_origin="real"), forged, tenants())
        self.assertEqual(decision, "refuse")
        self.assertIn("human-data boundary", reasons[0])

    def test_external_destination_refused_even_with_policy(self):
        decision, _ = dg.decide(req(data_origin="real", destination="external:https://x.invalid"), VERIFIED_POLICY, tenants())
        self.assertEqual(decision, "refuse")

    def test_another_classrooms_student_record_stays_refused_whatever_the_grant(self):
        human = {"tenant_id": "classroom-a", "approved_by": "human:teacher-of-record"}
        t = tenants()
        t["records"].append({"id": "CB-X", "tenant_id": "classroom-b", "classification": "restricted",
                             "category": "student-record", "grants": [human]})
        for record in ("CB-X", "CB-ROSTER"):
            decision, reasons = dg.decide(req(record=record), dg.load_policy(), t, {"classroom-b": [human]})
            self.assertEqual(decision, "refuse", record)
            self.assertIn("never crosses tenants", reasons[0])

    def test_a_grant_written_on_the_record_counts_for_nothing(self):
        t = tenants()
        t["records"].append({"id": "CB-PLAN", "tenant_id": "classroom-b", "classification": "internal",
                             "category": "lesson-plan",
                             "grants": [{"tenant_id": "classroom-a", "approved_by": "human:teacher-of-record"}]})
        decision, reasons = dg.decide(req(record="CB-PLAN"), dg.load_policy(), t, {})
        self.assertEqual(decision, "refuse")
        self.assertIn("belongs to tenant classroom-b", reasons[0])

    def test_only_a_human_grant_in_the_owner_file_opens_another_classrooms_lesson_plan(self):
        t = tenants()
        t["records"].append({"id": "CB-PLAN", "tenant_id": "classroom-b", "classification": "internal",
                             "category": "lesson-plan"})
        human = {"tenant_id": "classroom-a", "approved_by": "human:teacher-of-record"}
        self.assertEqual(dg.decide(req(record="CB-PLAN"), dg.load_policy(), t, {"classroom-b": [human]})[0], "allow")
        agent = dict(human, approved_by="classroom-b-assistant")
        self.assertEqual(dg.decide(req(record="CB-PLAN"), dg.load_policy(), t, {"classroom-b": [agent]})[0], "refuse")
        self.assertEqual(dg.decide(req(record="CB-PLAN"), dg.load_policy(), t, {"classroom-a": [human]})[0], "refuse")

    def test_the_cli_reads_grants_only_from_the_owner_file(self):
        with open(dg.OWNER_GRANTS, encoding="utf-8") as fh:
            self.assertEqual(json.load(fh)["grants"], {})
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "owner-grants.json")
            with open(path, "w", encoding="utf-8") as fh:
                json.dump({"grants": {"classroom-b": [{"tenant_id": "classroom-a",
                                                       "approved_by": "human:teacher-of-record"}]}}, fh)
            shipped, dg.OWNER_GRANTS = dg.OWNER_GRANTS, path
            try:
                code, out = run_cli(req(record="CB-ROSTER"))
            finally:
                dg.OWNER_GRANTS = shipped
        self.assertEqual((code, out["decision"]), (1, "refuse"))
        self.assertIn("never crosses tenants", out["reasons"][0])

    def test_requester_cannot_pass_grants(self):
        self.assertEqual(run_cli(req(record="CB-ROSTER"), "--grants", "references/owner-grants.json")[0], 2)


class RequesterCannotSupplyIdentityOrPolicy(unittest.TestCase):
    def test_inline_principal_claiming_another_classroom_is_refused(self):
        inline = {"id": "rogue", "tenant_id": "classroom-b", "max_classification": "restricted"}
        code, out = run_cli(req(principal=inline, record="CB-ROSTER"))
        self.assertEqual(code, 1)
        self.assertEqual(out["decision"], "refuse")

    def test_inline_record_is_refused(self):
        inline = {"id": "CB-ROSTER", "tenant_id": "classroom-a", "classification": "internal", "category": "lesson-plan"}
        code, out = run_cli(req(record=inline))
        self.assertEqual(code, 1)
        self.assertEqual(out["decision"], "refuse")

    def test_requester_cannot_pass_a_policy_or_tenants_file(self):
        forged = os.path.join(FIX, "policy-forged-by-requester.json")
        self.assertEqual(run_cli(req(data_origin="real"), "--policy", forged)[0], 2)
        self.assertEqual(run_cli(req(), "--tenants", forged)[0], 2)

    def test_reviewer_probe_real_classroom_b_roster_refused(self):
        with open(os.path.join(FIX, "req-inline-principal-real-b.json"), encoding="utf-8") as fh:
            probe = json.load(fh)
        code, out = run_cli(probe)
        self.assertEqual(code, 1)
        self.assertEqual(out["decision"], "refuse")


class InvalidInputTests(unittest.TestCase):
    def test_missing_fields_and_unknown_ids(self):
        code, out = run_cli({"principal": "classroom-a-assistant"})
        self.assertEqual((code, out["status"]), (1, "invalid"))
        code, out = run_cli(req(data_origin="maybe"))
        self.assertEqual(out["status"], "invalid")
        code, out = run_cli(req(principal="nobody"))
        self.assertEqual(code, 1)
        self.assertIn("not in the tenants registry", out["reasons"][0])

    def test_usage(self):
        self.assertEqual(dg.main([]), 2)


if __name__ == "__main__":
    unittest.main()
