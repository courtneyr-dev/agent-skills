"""Behavior of kit_check.py. The kit and plan are built here so the skill tests stand alone."""
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import kit_check  # noqa: E402

KIT = """# Kit
## Charter
Purpose: help. Membership model: open. Non-goals: no sales.
## Onboarding path
Purpose, onboarding, first meaningful participation, ongoing contribution, leadership development.
## Governance map
| Decision | Owner | Record | Review or appeal |
|---|---|---|---|
| Funding | `human:board` | Funding register | Quarterly board review |
| Sponsor acceptance | human:board | Sponsor register | Board review |
## Moderation and escalation
Conflict of interest recusal; appeal to a separate person; the decision maker is human:lead; evidence held; records stay confidential.
## Event playbook
Accessibility requests, volunteer shifts, contingency room, post-event survey, code of conduct posted.
## Contributor journey
Good first tasks, environment setup in one command, review within 3 days, recognition by opt-in, succession plan, maintainer support.
## Measurement plan
Consent-based aggregate measures: [plan](plan.json).
## Improvement loop
Evidence, review, contribution path change, onboarding update, follow-up.
"""
PLAN = {"community": "c", "metrics": [{
    "id": "first-response", "question": "How long do newcomers wait?", "definition": "Median hours to the first reply by someone else.",
    "source": {"kind": "chaoss", "url": "https://chaoss.community/kb/metric-time-to-first-response/"},
    "level": "community", "min_group_size": 5, "consent_basis": "Public posts, aggregated.", "publish": "public"}]}


class KitCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        json.dump(PLAN, open(os.path.join(self.tmp, "plan.json"), "w"))

    def rules(self, text):
        return sorted({v["rule"] for v in kit_check.check(text, self.tmp)[0]})

    def test_complete_kit_passes(self):
        self.assertEqual(self.rules(KIT), [])

    def test_each_section_is_required(self):
        self.assertEqual(self.rules(KIT.replace("## Event playbook", "## Events")), ["missing-section"])

    def test_load_bearing_parts_are_required(self):
        self.assertEqual(self.rules(KIT.replace("appeal to a separate person; ", "")), ["missing-part"])

    def test_governance_decisions_need_human_owners_records_and_review(self):
        self.assertEqual(self.rules(KIT.replace("`human:board` | Funding register", "community.strategy-lead | Funding register")), ["non-human-owner"])
        self.assertEqual(self.rules(KIT.replace("| Quarterly board review |", "| |")), ["governance-table"])

    def test_ranking_and_sales_language_is_refused_unless_negated(self):
        self.assertEqual(self.rules(KIT + "\nPublish a leaderboard each month.\n"), ["ranking-or-sales"])
        self.assertEqual(self.rules(KIT + "\nWe never publish a leaderboard.\n"), [])
        self.assertEqual(self.rules(KIT + "\nPass attendees to the account team as sales leads.\n"), ["ranking-or-sales"])

    def test_linked_plan_is_linted(self):
        bad = dict(PLAN, metrics=[dict(PLAN["metrics"][0], level="person")])
        json.dump(bad, open(os.path.join(self.tmp, "plan.json"), "w"))
        self.assertEqual(self.rules(KIT), ["plan-individual-level"])
        self.assertEqual(self.rules(KIT.replace("(plan.json)", "(missing.json)")), ["no-plan"])

    def test_missing_measures_skill_is_noted_not_hidden(self):
        saved = kit_check.MEASURES
        kit_check.MEASURES = os.path.join(self.tmp, "absent.py")
        try:
            violations, notes = kit_check.check(KIT, self.tmp)
        finally:
            kit_check.MEASURES = saved
        self.assertEqual(violations, [])
        self.assertIn("wasn't linted", notes[0])

    def test_invalid_input_is_rejected(self):
        for content in (None, "just prose, no sections"):
            path = os.path.join(self.tmp, "kit.md")
            if content is not None:
                open(path, "w").write(content)
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = kit_check.main([path if content is not None else os.path.join(self.tmp, "none.md")])
            self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
