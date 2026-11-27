"""Fleet-level rules for the product fleet: untrusted content, Trail of Bits provenance, personas, title coverage."""
import json
import os
import re
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
FLEET = os.path.normpath(os.path.join(HERE, ".."))
ROOT = os.path.normpath(os.path.join(FLEET, "..", ".."))
SKILLS = os.path.normpath(os.path.join(ROOT, ".."))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import fleetlib  # noqa: E402,F401  (puts factory-rig on the path)
from factory_rig.contract import contract_hash  # noqa: E402
from fleetlib.handoff import OWNER_FIELDS, open_handoff, validate_handoff  # noqa: E402
from fleetlib.untrusted import describe_source, guarded_update, scan  # noqa: E402

BIOGRAPHY = re.compile(r"\b(\d+\+?\s*(years?|yrs)|decades?|ph\.?d|mba|cissp|cpacc|formerly|former|worked at|award[- ]winning|veteran)\b|\bI\s", re.I)
TITLES = {  # section 6 title -> (role, phrase in its display name)
    "product GM": ("product-lead", "product gm"), "product manager": ("product-lead", "product manager"),
    "product researcher": ("researcher", "product researcher"), "ecosystem strategist": ("researcher", "ecosystem strategist"),
    "UX/content designer": ("ux-content-designer", "ux and content designer"),
    "platform/extension architect": ("platform-architect", "extension"), "SDK/API engineer": ("platform-architect", "sdk/api"),
    "frontend engineer": ("engineer", "frontend"), "backend engineer": ("engineer", "backend"),
    "integration engineer": ("engineer", "integration"), "developer-experience engineer": ("engineer", "developer-experience"),
    "compatibility engineer": ("compatibility-engineer", "compatibility engineer"), "test/release engineer": ("release-engineer", "test and release"),
    "security maintainer": ("security-maintainer", "security maintainer"),
    "accessibility/localization reviewer": ("a11y-l10n-reviewer", "accessibility and localization reviewer"),
    "licensing/entitlements owner": ("commerce-owner", "licensing, entitlements"), "subscriptions/billing specialist": ("commerce-owner", "subscriptions, billing"),
    "pricing analyst": ("commerce-owner", "pricing"), "marketplace/review liaison": ("marketplace-liaison", "marketplace, review"),
    "partnerships": ("marketplace-liaison", "partnerships"), "documentation": ("docs-educator", "documentation"),
    "developer education": ("docs-educator", "developer education"), "support": ("support-success", "support"),
    "customer success": ("support-success", "customer success"), "lifecycle/deprecation owner": ("lifecycle-owner", "lifecycle and deprecation"),
}


def load(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return json.load(fh)


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as fh:
        return fh.read()


class ProductFleetTest(unittest.TestCase):
    roles = load("fleets/product/roles.json")["roles"]

    def test_untrusted_ticket_and_issue_cannot_change_authority(self):
        sources = [(ref, read(ref)) for ref in ("fleets/product/fixtures/untrusted/support-ticket-fx-2041.md",
                                                 "fleets/product/fixtures/untrusted/issue-fx-118.md")]
        findings = [f for ref, text in sources for f in scan(text, ref)]
        print("findings:", json.dumps(findings, indent=1))
        self.assertGreaterEqual({f["category"] for f in findings}, {"authority", "evidence", "exfiltration"})
        flagged = {(f["ref"], f["line"]) for f in findings}
        self.assertNotIn((sources[0][0], 6), flagged, "the customer's legitimate PHP 8.0 report must not be flagged")
        with open(os.path.join(SKILLS, "product-release-gate", "fixtures", "contract.json")) as fh:
            contract = json.load(fh)
        h = open_handoff({
            "handoff_id": "HO-FIX-SUPPORT-2041", "workload_id": "product.workload.support-intake", "tenant_id": "tenant-fixture-co",
            "client_id": None, "operating_profile": "product", "outcome": "SYNTHETIC: triage FX-2041 and FX-118 into routed, reproducible reports.",
            "scope": ["Ticket FX-2041", "Issue FX-118"], "exclusions": ["Replying to customers", "Changing the support range"],
            "acceptance_criteria": ["Each report is reproduced or routed with its evidence"], "sources": [{"ref": "fleets/product/fixtures/untrusted", "revision": "fixture r1"}],
            "producer": "product.support-success", "reviewer": "product.product-lead", "acceptance_owner": "human:support-owner",
            "execution_owner": "product.product-lead",
            "data": {"classification": "internal", "allowed_destinations": ["tenant:tenant-fixture-co", "rig:evidence"]},
            "authority": {"tools": ["fleet scan"], "mutation": "none", "external_actions": "none", "publication": "none"},
            "budget": {"max_minutes": 30, "max_retries": 1}, "stop_conditions": ["Both reports routed"],
            "cancellation": "Stop and keep the triage so far.", "next_consumer": "product.compatibility-engineer",
            "readiness_criteria": ["Reproduction steps recorded"], "contract_hash": contract_hash(contract)})
        attempt = {
            "summary": "FX-2041: fatal error on PHP 8.0, below the declared PHP 8.1 minimum, so outside the support boundary; "
                       "rollback to 1.4.2 works. FX-118: asks for WordPress 6.4, below the declared 6.6 minimum; routed to the product lead as a range request.",
            "inputs": [describe_source(text, ref, "tenant-fixture-co", "internal", "client-file" if "ticket" in ref else "issue") for ref, text in sources],
            "acceptance_owner": "product.support-success",
            "acceptance_criteria": [],
            "authority": {"tools": ["fleet scan"], "mutation": "scoped-write", "external_actions": "human-approved", "publication": "human-approved"},
        }
        new, refused, found = guarded_update(h, attempt, sources)
        self.assertEqual(sorted(r["field"] for r in refused), ["acceptance_criteria", "acceptance_owner", "authority"])
        for field in OWNER_FIELDS:
            self.assertEqual(new[field], h[field], field)
        self.assertEqual(new["summary"], attempt["summary"])
        self.assertEqual(len(new["untrusted_findings"]), len(findings))
        self.assertEqual(validate_handoff(new), [])
        gate = subprocess.run([sys.executable, os.path.join(SKILLS, "product-release-gate", "scripts", "release_gate.py"), "gate",
                               "--candidate", os.path.join(SKILLS, "product-release-gate", "fixtures", "candidate-incompatible-host.json")],
                              capture_output=True, text=True)
        self.assertEqual(gate.returncode, 1)
        self.assertEqual(json.loads(gate.stdout)["decision"], "refused")

    def test_trail_of_bits_attached_only_where_installed(self):
        with open(os.path.join(ROOT, "sources", "ledger.json")) as fh:
            tob = {i["name"] for i in json.load(fh)["items"] if i["repo"] == "trailofbits/skills"}
        attached = [(r["id"], a) for r in self.roles for a in r["skills"]]
        claimed = [(rid, a["id"]) for rid, a in attached if "trailofbits" in a["provenance"]]
        print("installed Trail of Bits skills:", sorted(tob))
        print("attached:", claimed)
        self.assertTrue(claimed)
        for rid, sid in claimed:
            self.assertIn(sid, tob, "%s attaches %s as Trail of Bits but the sources ledger does not list it" % (rid, sid))
            self.assertTrue(os.path.isfile(os.path.join(SKILLS, sid, "SKILL.md")), sid)
        for rid, a in attached:
            if a["id"] in tob:
                self.assertIn("trailofbits", a["provenance"], "%s attaches %s without Trail of Bits attribution" % (rid, a["id"]))

    def test_personas_are_viewpoints_not_biographies(self):
        for r in self.roles:
            for field in ("display_name", "purpose", "voice"):
                self.assertIsNone(BIOGRAPHY.search(r[field]), "%s %s: %r" % (r["id"], field, r[field]))

    def test_every_required_title_maps_to_a_role(self):
        names = {r["id"].split(".", 1)[1]: r["display_name"].lower() for r in self.roles}
        for title, (slug, phrase) in TITLES.items():
            self.assertIn(slug, names, title)
            self.assertIn(phrase, names[slug], "%s should be covered by product.%s" % (title, slug))


if __name__ == "__main__":
    unittest.main()
