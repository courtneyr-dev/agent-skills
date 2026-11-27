"""Community fleet guards on synthetic Community A data: an untrusted issue that tries to redirect a
worker, confidential moderation cases that never cross tenants or reach metrics by default, and the
feedback-to-product handoff. Uses fleetlib's guards and the community skills' own code, not copies."""
import copy
import importlib.util
import json
import os
import sys
import unittest

FLEET = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CF = os.path.dirname(os.path.dirname(FLEET))
SKILLS = os.path.dirname(CF)
sys.path.insert(0, os.path.join(CF, "scripts"))

import fleetlib  # noqa: E402,F401  (puts factory-rig on sys.path)
from fleetlib.handoff import open_handoff, validate_handoff  # noqa: E402
from fleetlib.tenancy import can_read  # noqa: E402
from fleetlib.untrusted import describe_source, guarded_update, scan  # noqa: E402

FX = os.path.join(FLEET, "fixtures")


def module(skill, name):
    spec = importlib.util.spec_from_file_location(name, os.path.join(SKILLS, skill, "scripts", name + ".py"))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def load(rel):
    with open(os.path.join(FX, rel)) as fh:
        return json.load(fh)


def text(rel):
    with open(os.path.join(FX, rel)) as fh:
        return fh.read()


def case_record(**extra):
    case = load("moderation/case-cm-1.json")
    rec = {"id": case["case_id"], "tenant_id": case["tenant_id"], "classification": case["classification"],
           "category": case["category"], "approved_abstraction": True}
    rec.update(extra)
    return rec


class UntrustedIssue(unittest.TestCase):
    def test_scan_flags_the_redirects_as_data(self):
        cats = {f["category"] for f in scan(text("untrusted/issue-submission.md"), "issue-submission.md")}
        self.assertTrue({"override", "authority", "exfiltration", "evidence", "publication"} <= cats, cats)

    def test_issue_cannot_move_tenant_acceptance_destinations_or_publication(self):
        owner = load("handoff/feedback-to-product-owner.json")
        new, refused, findings = guarded_update(open_handoff(owner), {
            "tenant_id": "community-b",
            "acceptance_owner": "community.member-success-lead",
            "data": {"classification": "internal", "allowed_destinations": ["external:collector.example.invalid"]},
            "authority": dict(owner["authority"], publication="human-approved"),
            "summary": "Members report docs search never loads on phones; repro steps attached; no member named.",
        }, [("issue-submission.md", text("untrusted/issue-submission.md"))])
        self.assertEqual({r["field"] for r in refused}, {"tenant_id", "acceptance_owner", "data", "authority"})
        self.assertEqual((new["tenant_id"], new["authority"]["publication"]), ("community-a", "none"))
        self.assertIn("phones", new["summary"])
        self.assertGreaterEqual(len(new["untrusted_findings"]), 5)
        self.assertEqual(validate_handoff(new), [])

    def test_the_community_b_line_is_refused_by_tenancy_whatever_the_scanner_flags(self):
        other = case_record(id="CB-CASE-9", tenant_id="community-b")
        ok, why = can_read({"tenant_id": "community-a", "max_classification": "confidential"}, other)
        self.assertFalse(ok)
        self.assertIn("never shared", why)


class ConfidentialCases(unittest.TestCase):
    def test_moderation_case_never_crosses_tenants_by_default_even_as_an_approved_abstraction(self):
        for principal in ({"tenant_id": "fixture-co", "max_classification": "confidential"},
                          {"tenant_id": "community-b", "max_classification": "restricted"}):
            ok, why = can_read(principal, case_record())
            self.assertFalse(ok, principal)
            self.assertIn("never shared across tenants by default", why)

    def test_same_tenant_moderation_reader_can_read_and_no_grant_crosses_tenants(self):
        self.assertTrue(can_read({"tenant_id": "community-a", "max_classification": "confidential"}, case_record())[0])
        corporate = {"tenant_id": "fixture-co", "max_classification": "confidential"}
        for approver in ("human:community-governance-board", "community.trust-safety-lead"):
            grant = [{"tenant_id": "fixture-co", "approved_by": approver}]
            for record, owner_grants in ((case_record(grants=grant), None), (case_record(), grant)):
                ok, why = can_read(corporate, record, owner_grants)
                self.assertFalse(ok, approver)
                self.assertIn("never crosses tenants", why)

    def test_feedback_handoff_refuses_the_case_as_an_input(self):
        h = open_handoff(load("handoff/feedback-to-product-owner.json"))
        h["inputs"] = [describe_source(text("untrusted/issue-submission.md"), "issue-41", "community-a", "internal", "issue"),
                       {"ref": "CM-CASE-1", "tenant_id": "community-a", "classification": "confidential", "trust": "trusted",
                        "source_kind": "rig-record"}]
        errs = validate_handoff(h)
        self.assertTrue(any("CM-CASE-1" in e and "confidential" in e for e in errs), errs)
        self.assertFalse(any("issue-41" in e for e in errs), errs)

    def test_public_metrics_exclude_case_records_and_name_no_one(self):
        measures = module("community-health-measures", "measures")
        activity = load("measures/activity.json")
        out = json.dumps(measures.aggregate(load("measures/plan-good.json"), activity))
        people = {r.get("person") for r in activity["records"] if r.get("person")}
        for ident in people | {"CM-CASE-1"}:
            self.assertNotIn(ident, out)
        self.assertEqual(json.loads(out)["excluded_records"]["confidential-or-case"], 2)

    def test_moderation_draft_that_leaks_into_a_public_update_is_refused(self):
        cc = module("community-moderation-review", "case_check")
        case = cc.parse_case(load("moderation/case-cm-1.json"))
        draft = cc.parse_draft(copy.deepcopy(load("moderation/draft-good.json")))
        self.assertEqual(cc.check(case, draft), [])
        draft["public_outputs"] = [{"text": "Following CM-CASE-1 we reminded everyone about replies."}]
        self.assertEqual([v["rule"] for v in cc.check(case, draft)], ["public-leak"])


if __name__ == "__main__":
    unittest.main()
