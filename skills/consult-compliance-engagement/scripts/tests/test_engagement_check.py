"""Behavior tests for engagement_check.py through its CLI."""
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.normpath(os.path.join(HERE, "..", ".."))
SCRIPT = os.path.join(SKILL, "scripts", "engagement_check.py")
FX = os.path.join(SKILL, "fixtures")
SELECTOR = os.path.join(FX, "selector-output.json")
STORE = os.path.join(FX, "evidence-store")


def fixture(name):
    with open(os.path.join(FX, name)) as fh:
        return json.load(fh)


class EngagementCheckTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def run_doc(self, doc, selector=SELECTOR, store=STORE):
        path = os.path.join(self.tmp.name, "engagement.json")
        with open(path, "w") as fh:
            json.dump(doc, fh) if isinstance(doc, dict) else fh.write(doc)
        args = [sys.executable, SCRIPT, "--engagement", path] + (["--selector", selector] if selector else []) \
            + (["--evidence-root", store] if store else [])
        p = subprocess.run(args, capture_output=True, text=True)
        return p.returncode, json.loads(p.stdout)

    def codes(self, out, stage):
        return sorted(e["code"] for s in out["stages"] if s["stage"] == stage for e in s["errors"])

    def test_complete_engagement_may_issue_its_authorized_report(self):
        code, out = self.run_doc(fixture("engagement-ok.json"))
        self.assertEqual(code, 0)
        self.assertEqual(out["decision"], "report-may-issue")
        self.assertEqual([s["stage"] for s in out["stages"]],
                         ["applicability", "control-owners", "evidence-collection", "gap-remediation",
                          "independent-review", "authorized-report"])

    def test_every_planted_gap_is_caught_in_its_stage(self):
        code, out = self.run_doc(fixture("engagement-gaps.json"))
        self.assertEqual(code, 1)
        self.assertEqual(out["decision"], "not-ready")
        self.assertEqual(self.codes(out, "applicability"), ["applicability-undetermined", "licensed-text-not-obtained", "owner-not-human"])
        self.assertIn("control-owner-not-human", self.codes(out, "control-owners"))
        self.assertIn("evidence-stale", self.codes(out, "evidence-collection"))
        self.assertIn("control-without-evidence", self.codes(out, "evidence-collection"))
        self.assertEqual(self.codes(out, "gap-remediation"), ["exception-open"])
        self.assertIn("reviewer-not-independent", self.codes(out, "independent-review"))
        self.assertEqual(self.codes(out, "authorized-report"),
                         ["certification-claim-without-attestation", "claim-category-overreach", "conformance-claim-exceeds-evidence",
                          "report-authorized-with-open-errors",
                          "report-not-authorized-by-human", "report-self-authorized"])

    def test_evidence_at_the_age_limit_passes_and_one_day_over_fails(self):
        code, out = self.run_doc(fixture("engagement-boundary.json"))
        self.assertEqual(code, 0)
        self.assertEqual(out["decision"], "ready-for-human-authorization")
        doc = fixture("engagement-boundary.json")
        doc["evidence"][3]["collected_on"] = "2026-10-25"
        code, out = self.run_doc(doc)
        self.assertEqual(code, 1)
        self.assertEqual(self.codes(out, "evidence-collection"), ["evidence-stale"])

    def test_framework_the_selector_picked_must_be_resolved(self):
        doc = fixture("engagement-ok.json")
        doc["applicability"] = [a for a in doc["applicability"] if a["framework"] != "iso_27001"]
        code, out = self.run_doc(doc)
        self.assertEqual(code, 1)
        self.assertEqual(self.codes(out, "applicability"), ["selector-framework-unresolved"])
        code, out = self.run_doc(doc, selector=None)
        self.assertEqual(code, 0)

    def test_legal_conclusion_needs_counsel_and_unlisted_frameworks_are_refused(self):
        doc = fixture("engagement-ok.json")
        doc["report"]["claims"].append({"id": "C9", "kind": "legal-conclusion", "framework": "gdpr", "text": "Fixture Co meets its GDPR obligations."})
        doc["applicability"].append({"framework": "hipaa", "decision": "not-applicable", "rationale": "No health data."})
        code, out = self.run_doc(doc)
        self.assertEqual(code, 1)
        self.assertIn("legal-conclusion-without-counsel", self.codes(out, "authorized-report"))
        self.assertEqual(self.codes(out, "applicability"), ["framework-unregistered"])

    def test_cross_tenant_evidence_is_refused(self):
        doc = fixture("engagement-ok.json")
        doc["evidence"][0]["tenant_id"] = "tenant-other"
        code, out = self.run_doc(doc)
        self.assertEqual(code, 1)
        self.assertEqual(self.codes(out, "evidence-collection"), ["evidence-cross-tenant"])

    # ---- review 2026-11-26, defect 10: the text decides the claim's category, not its label ----
    def with_claim(self, kind, text, framework="gdpr"):
        doc = fixture("engagement-ok.json")
        doc["report"]["claims"].append({"id": "CX", "kind": kind, "framework": framework, "text": text})
        return doc

    def test_labels_cannot_soften_legal_or_certification_claims(self):
        code, out = self.run_doc(self.with_claim("regulatory-applicability", "Fixture Co complies with GDPR and faces no legal exposure."))
        self.assertEqual(code, 1)
        self.assertIn("legal-conclusion-without-counsel", self.codes(out, "authorized-report"))
        code, out = self.run_doc(self.with_claim("technical-conformance", "Fixture Co is SOC 2 compliant.", framework="soc_2"))
        self.assertEqual(code, 1)
        self.assertIn("certification-claim-without-attestation", self.codes(out, "authorized-report"))

    def test_level_conformance_claim_needs_a_full_evaluation(self):
        code, out = self.run_doc(self.with_claim("technical-conformance", "The site conforms to WCAG 2.2 Level AA.", framework="wcag_2_2"))
        self.assertEqual(code, 1)
        self.assertIn("conformance-claim-exceeds-evidence", self.codes(out, "authorized-report"))

    # ---- review 2026-11-26, defect 11: hashes and tenancy come from the artifact, not the record ----
    def test_evidence_hash_is_recomputed_from_the_artifact(self):
        doc = fixture("engagement-ok.json")
        doc["evidence"][0]["sha256"] = "0" * 64
        code, out = self.run_doc(doc)
        self.assertEqual(code, 1)
        self.assertEqual(self.codes(out, "evidence-collection"), ["evidence-hash-mismatch"])

    def test_evidence_path_in_another_tenant_is_refused(self):
        doc = fixture("engagement-ok.json")
        doc["evidence"][0]["ref"] = "tenants/tenant-other-co/evidence/access-review.csv"
        code, out = self.run_doc(doc)
        self.assertEqual(code, 1)
        self.assertIn("evidence-ref-names-other-tenant", self.codes(out, "evidence-collection"))

    def test_without_artifacts_the_report_cannot_issue(self):
        code, out = self.run_doc(fixture("engagement-ok.json"), store=None)
        self.assertEqual(code, 1)
        self.assertEqual(sorted(set(self.codes(out, "evidence-collection"))), ["evidence-hash-unverified"])

    def test_invalid_inputs_exit_2(self):
        bad_date = fixture("engagement-ok.json")
        bad_date["evidence"][0]["collected_on"] = "11/10/2026"
        wrong = copy.deepcopy(bad_date)
        wrong["schema"] = "compliance-engagement.v0"
        for doc in ("{not json", wrong, bad_date, fixture("engagement-invalid.json")):
            code, out = self.run_doc(doc)
            self.assertEqual(code, 2)
            self.assertIn("error", out)
        code, out = self.run_doc(fixture("engagement-ok.json"), selector=os.path.join(FX, "engagement-ok.json"))
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
