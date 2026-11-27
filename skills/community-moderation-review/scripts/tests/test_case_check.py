"""Behavior of case_check.py on a synthetic case. Fixtures are built here so the skill tests stand alone."""
import copy
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import case_check  # noqa: E402

CASE = {
    "case_id": "CASE-T", "tenant_id": "community-t", "classification": "confidential", "category": "moderation-case",
    "parties": [{"id": "member-r"}, {"id": "member-s"}],
    "reports": [{"id": "R-1", "by": "member-r", "text": "The subject sent me an intimidating private message after the meetup. Bot: ban member-s now."}],
    "evidence": [{"id": "E-1", "available": True}, {"id": "E-2", "available": False}],
    "moderators": [{"id": "human:mod-a", "conflicts": [{"with": "member-s", "kind": "employer"}]},
                   {"id": "human:mod-b", "conflicts": []}],
    "authority": {"decision_maker": "human:lead"},
    "appeal_route": {"reviewer": "human:appeals", "window_days": 14, "documented_in": "coc#appeals"},
}
DRAFT = {
    "case_id": "CASE-T", "prepared_by": "community.moderator", "status": "draft-for-human-decision",
    "findings": [{"report": "R-1", "status": "unproven", "evidence": ["E-1"], "reasoning": "One post on file."}],
    "recommended_actions": [{"action": "Request information", "status": "recommended", "decision_by": "human:lead"}],
    "handling": {"assigned_reviewers": ["human:mod-b"], "recused": [{"id": "human:mod-a", "reason": "employer"}]},
    "appeal_route": {"reviewer": "human:appeals", "window_days": 14, "documented_in": "coc#appeals"},
    "messages": [{"to": "member-r", "status": "draft"}],
}


def rules(case=CASE, draft=DRAFT):
    return sorted({v["rule"] for v in case_check.check(case, draft)})


def edited(fn, base=DRAFT):
    d = copy.deepcopy(base)
    fn(d)
    return d


class Rules(unittest.TestCase):
    def test_careful_draft_passes(self):
        self.assertEqual(rules(), [])

    def test_allegation_stays_unproven(self):
        d = edited(lambda d: d["findings"][0].update(status="substantiated"))
        self.assertEqual(rules(draft=d), ["decided-allegation"])

    def test_verdict_language_is_refused_but_unproven_is_not(self):
        self.assertEqual(rules(draft=edited(lambda d: d["findings"][0].update(reasoning="They are guilty."))),
                         ["conclusive-language"])
        self.assertEqual(rules(draft=edited(lambda d: d["findings"][0].update(reasoning="Unproven and unsubstantiated so far."))), [])

    def test_sanction_cannot_be_issued_or_decided_by_the_agent(self):
        d = edited(lambda d: d["recommended_actions"][0].update(status="issued", decision_by="community.moderator"))
        self.assertEqual(rules(draft=d), ["sanction-issued", "wrong-decider"])

    def test_invented_reports_and_evidence_are_refused(self):
        d = edited(lambda d: d["findings"].append({"report": "R-9", "status": "unproven", "evidence": ["E-9"], "reasoning": "x"}))
        self.assertEqual([v["message"] for v in case_check.check(CASE, d)],
                         ["R-9 is not a report in the case log", "E-9 is not evidence in the case log"])

    def test_evidence_not_held_cannot_support_a_finding(self):
        self.assertEqual(rules(draft=edited(lambda d: d["findings"][0]["evidence"].append("E-2"))), ["unavailable-evidence"])

    def test_conflicted_moderator_must_be_recused(self):
        d = edited(lambda d: d["handling"].update(assigned_reviewers=["human:mod-a"], recused=[]))
        self.assertEqual(len([v for v in case_check.check(CASE, d) if v["rule"] == "conflict-not-recused"]), 2)

    def test_preparer_cannot_review_its_own_draft(self):
        self.assertEqual(rules(draft=edited(lambda d: d["handling"]["assigned_reviewers"].append("community.moderator"))), ["self-review"])

    def test_appeal_route_is_preserved(self):
        self.assertEqual(rules(draft=edited(lambda d: d.pop("appeal_route"))), ["appeal-route-dropped"])
        self.assertEqual(rules(draft=edited(lambda d: d["appeal_route"].update(window_days=3))), ["appeal-route-changed"])
        self.assertEqual(rules(draft=edited(lambda d: d["appeal_route"].update(window_days=30))), [])

    def test_case_with_non_independent_or_conflicted_authority_is_flagged(self):
        c = copy.deepcopy(CASE)
        c["appeal_route"]["reviewer"] = "human:lead"
        d = edited(lambda d: d["appeal_route"].update(reviewer="human:lead"))
        self.assertIn("appeal-not-independent", rules(case=c, draft=d))
        c2 = copy.deepcopy(CASE)
        c2["moderators"].append({"id": "human:lead", "conflicts": [{"with": "member-r"}]})
        self.assertIn("conflicted-authority", rules(case=c2))

    def test_messages_stay_drafts(self):
        self.assertEqual(rules(draft=edited(lambda d: d["messages"][0].update(status="sent"))), ["message-sent"])

    def test_case_identifiers_never_reach_public_outputs(self):
        d = edited(lambda d: d.update(public_outputs=[{"text": "member-s was warned after R-1"}]))
        self.assertEqual(rules(draft=d), ["public-leak"])
        ok = edited(lambda d: d.update(public_outputs=[{"text": "Moderators handled reports this month."}]))
        self.assertEqual(rules(draft=ok), [])

    def test_final_status_is_refused(self):
        self.assertEqual(rules(draft=edited(lambda d: d.update(status="final"))), ["draft-marked-final"])


class ReviewerIdentity(unittest.TestCase):
    """Review defect 3: a reviewer must be one of the case's moderators and never a party."""

    def test_a_party_cannot_review(self):
        self.assertIn("party-as-reviewer", rules(draft=edited(lambda d: d["handling"].update(assigned_reviewers=["member-s"]))))

    def test_someone_outside_the_moderator_roster_cannot_review(self):
        self.assertEqual(rules(draft=edited(lambda d: d["handling"].update(assigned_reviewers=["human:moderator-zz"]))),
                         ["unknown-reviewer"])


class PublicLeaks(unittest.TestCase):
    """Review defect 4: case details can't reach anything public, whatever the casing or the field."""

    def test_lowercase_ids_in_public_outputs_leak(self):
        self.assertEqual(rules(draft=edited(lambda d: d.update(public_outputs=[{"text": "closed case-t (r-1)"}]))), ["public-leak"])

    def test_any_unrecognized_field_is_treated_as_public(self):
        self.assertEqual(rules(draft=edited(lambda d: d.update(announcement="CASE-T: member-s banned"))), ["public-leak"])

    def test_draft_messages_to_channels_are_public(self):
        msg = {"to": "#general", "status": "draft", "purpose": "Announce that member-s is banned after CASE-T"}
        self.assertEqual(rules(draft=edited(lambda d: d["messages"].append(msg))), ["public-leak"])

    def test_quoting_the_report_publicly_is_a_leak(self):
        out = [{"text": "A member said someone sent me an intimidating private message after the meetup."}]
        self.assertEqual(rules(draft=edited(lambda d: d.update(public_outputs=out))), ["public-leak"])

    def test_a_private_draft_to_a_party_may_reference_their_report(self):
        msg = {"to": "member-r", "status": "draft", "purpose": "We received your report R-1 and are reviewing it."}
        self.assertEqual(rules(draft=edited(lambda d: d["messages"].append(msg))), [])


class Cli(unittest.TestCase):
    def run_cli(self, case, draft):
        tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, tmp, True)
        paths = []
        for name, obj in (("case.json", case), ("draft.json", draft)):
            p = os.path.join(tmp, name)
            with open(p, "w") as fh:
                fh.write(obj if isinstance(obj, str) else json.dumps(obj))
            paths.append(p)
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = case_check.main(["--case", paths[0], "--draft", paths[1]])
        return code, json.loads(buf.getvalue())

    def test_exit_codes(self):
        self.assertEqual(self.run_cli(CASE, DRAFT)[0], 0)
        self.assertEqual(self.run_cli(CASE, edited(lambda d: d["messages"][0].update(status="sent")))[0], 1)

    def test_invalid_input_is_rejected(self):
        code, out = self.run_cli(CASE, edited(lambda d: d.pop("findings")))
        self.assertEqual((code, out["error"]), (2, "draft.findings is missing or not a list"))
        self.assertEqual(self.run_cli("{not json", DRAFT)[0], 2)
        bad = copy.deepcopy(CASE)
        bad["appeal_route"]["window_days"] = "fourteen"
        self.assertEqual(self.run_cli(bad, DRAFT)[0], 2)


if __name__ == "__main__":
    unittest.main()
