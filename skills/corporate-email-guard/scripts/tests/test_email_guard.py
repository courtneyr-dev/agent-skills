"""Behavior tests for email_guard.py: assert exit codes, JSON and outbox contents.

The suppression list and the approval are owner values in the campaign's owner ledger. Each test repoints the
company-fleets owner root to a temp folder, records them through the owner path, and runs the guard's main()
in this process so it reads the same root. One test runs the installed command against the checked-in fixture
ledger (company-fleets fleets/corporate/owner/fixture-news-2026-11).
"""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.normpath(os.path.join(HERE, "..", "email_guard.py"))
FIX = os.path.normpath(os.path.join(HERE, "..", "..", "fixtures"))
sys.path.insert(0, os.path.dirname(SCRIPT))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..", "..", "..", "company-fleets", "scripts")))
import email_guard  # noqa: E402
from fleetlib import ownerlog  # noqa: E402
from fleetlib.registry import Registry  # noqa: E402

SUPPRESSED = {"carol@example.com", "dave@example.org", "erin@example.net"}
IDENT = ("fixture-co", "corporate.workload.campaign-staging", "fixture-news-2026-11")


def fx(name):
    return os.path.join(FIX, name)


def run(*args):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        code = email_guard.main(list(args))
    return code, json.loads(out.getvalue())


class GuardCase(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="email-guard-")
        self.addCleanup(shutil.rmtree, self.tmp)
        root = tempfile.mkdtemp(prefix="owner-root-")
        old, ownerlog.FLEETS_ROOT = ownerlog.FLEETS_ROOT, root
        self.addCleanup(shutil.rmtree, root, True)
        self.addCleanup(setattr, ownerlog, "FLEETS_ROOT", old)
        self.staged = os.path.join(self.tmp, "staged.json")
        self.outbox = os.path.join(self.tmp, "outbox")
        self.ledger = ownerlog.owner_dir("corporate", IDENT[2])
        self.lease = ownerlog.open_ledger(self.ledger, Registry(), *IDENT, "corporate.chief-of-staff", os.getpid(), "none", exclusive=True)

    def owner(self, kind, rec, base=FIX):
        if isinstance(rec, str):
            with open(fx(rec), encoding="utf-8") as fh:
                rec = json.load(fh)
        return ownerlog.append(self.ledger, kind, rec, *IDENT, self.lease["epoch"], self.lease["token"], base=base)

    def pin(self, path, base=FIX):
        return self.owner("pin", {"name": "suppression-list", "path": path}, base)

    def stage(self, contacts="contacts.csv"):
        return run("stage", "--campaign", fx("campaign.json"), "--contacts", contacts if os.path.isabs(contacts) else fx(contacts), "--out", self.staged)

    def send(self):
        return run("send", "--staged", self.staged, "--outbox", self.outbox)

    def write(self, name, text):
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(text)
        return path

    def outbox_recipients(self):
        if not os.path.isdir(self.outbox):
            return []
        out = []
        for name in os.listdir(self.outbox):
            with open(os.path.join(self.outbox, name), encoding="utf-8") as fh:
                out.append(json.load(fh)["to"])
        return sorted(out)


class StageTests(GuardCase):
    def setUp(self):
        super().setUp()
        self.pin("suppression.csv")

    def test_suppressed_contacts_never_staged_even_with_case_variant_or_note(self):
        code, out = self.stage()
        self.assertEqual(code, 0)
        self.assertEqual(out["send_authority"], "none")
        self.assertFalse(SUPPRESSED & set(out["recipients"]))
        self.assertEqual(out["recipients"], ["alice@example.com", "bob@example.org", "frank@example.com", "heidi@example.org"])
        self.assertEqual(out["excluded"], {"suppressed": 2, "invalid": 1, "duplicate": 1, "other-list": 1})
        with open(self.staged, encoding="utf-8") as fh:
            self.assertFalse(SUPPRESSED & set(json.load(fh)["recipients"]))

    def test_plus_tags_and_gmail_dots_stay_suppressed(self):
        """The reviewer's major 6: carol+news@example.com and v.ictim@gmail.com staged with suppressed: 0."""
        self.pin(self.write("s.csv", "email,reason,recorded_on\ncarol@example.com,unsubscribed,2026-09-02\nvictim@gmail.com,unsubscribed,2026-09-02\n"), self.tmp)
        con = self.write("c.csv", "email,name,list,notes\ncarol+news@example.com,C,newsletter,\nv.ictim@gmail.com,V,newsletter,\n"
                                  "V.I.C.T.I.M+x@googlemail.com,V,newsletter,\nreader+news@example.com,R,newsletter,\n")
        code, out = self.stage(con)
        self.assertEqual(code, 0)
        self.assertEqual((out["recipients"], out["excluded"]["suppressed"]), (["reader+news@example.com"], 3))

    def test_the_caller_cannot_hand_the_guard_a_suppression_list(self):
        empty = self.write("empty.csv", "email,reason,recorded_on\n")
        code, out = run("stage", "--campaign", fx("campaign.json"), "--contacts", fx("contacts.csv"), "--suppression", empty, "--out", self.staged)
        self.assertEqual(code, 2)
        self.assertIn("usage", out["error"])
        self.assertFalse(os.path.exists(self.staged))

    def test_fixture_approval_hashes_match_a_fresh_stage(self):
        _, out = self.stage()
        with open(fx("approval-valid.json"), encoding="utf-8") as fh:
            approval = json.load(fh)
        self.assertEqual(approval["campaign_sha256"], out["campaign_sha256"])
        self.assertEqual(approval["recipient_sha256"], out["recipient_sha256"])

    def test_bad_contacts_header_is_invalid_input(self):
        bad = self.write("contacts.csv", "address,name\nx@example.com,X\n")
        code, out = self.stage(bad)
        self.assertEqual(code, 2)
        self.assertIn("header", out["error"])
        self.assertFalse(os.path.exists(self.staged))

    def test_a_campaign_without_a_pinned_list_is_refused(self):
        with open(fx("campaign.json"), encoding="utf-8") as fh:
            other = dict(json.load(fh), campaign_id="no-ledger-campaign")
        path = self.write("campaign.json", json.dumps(other))
        code, out = run("stage", "--campaign", path, "--contacts", fx("contacts.csv"), "--out", self.staged)
        self.assertEqual(code, 1)
        self.assertIn("owner-log-missing", out["refused"])
        self.assertFalse(os.path.exists(self.staged))


class SuppressionRowTests(GuardCase):
    """Review defect 11: malformed suppression rows must not load silently and suppress nothing, even in the owner's pin."""

    def test_trailing_dot_and_zero_width_entries_still_suppress(self):
        self.pin(self.write("s.csv", "email,reason,recorded_on\ndotted@example.com.,unsubscribed,2026-09-01\n"
                                     "uni@example.com​,unsubscribed,2026-09-01\n"), self.tmp)
        con = self.write("c.csv", "email,name,list,notes\ndotted@example.com,D,newsletter,\nuni@example.com,U,newsletter,\n"
                                  "dotted@example.com.,D,newsletter,trailing dot on the contact\nok@example.com,O,newsletter,\n")
        code, out = self.stage(con)
        self.assertEqual(code, 0)
        self.assertEqual(out["recipients"], ["ok@example.com"])
        self.assertEqual(out["excluded"]["suppressed"], 3)  # the trailing-dot contact is suppressed before it can count as a duplicate

    def test_unparseable_suppression_row_fails_loudly(self):
        self.pin(self.write("s.csv", "email,reason,recorded_on\nvictim@example.com,unsubscribed,2026-09-01\nnot-an-address,unsubscribed,2026-09-01\n"), self.tmp)
        code, out = self.stage()
        self.assertEqual(code, 2)
        self.assertIn("row 3", out["error"])
        self.assertFalse(os.path.exists(self.staged))

    def test_unknown_suppression_reason_is_invalid_input(self):
        self.pin(self.write("s.csv", "email,reason,recorded_on\nx@example.com,asked-nicely,2026-11-01\n"), self.tmp)
        code, out = self.stage()
        self.assertEqual(code, 2)
        self.assertIn("reason", out["error"])

    def test_send_refuses_a_malformed_suppression_list(self):
        self.pin("suppression.csv")
        self.stage()
        self.owner("send-approval", "approval-valid.json")
        self.pin(self.write("s.csv", "email,reason,recorded_on\nheidi@@example.org,unsubscribed,2026-11-25\n"), self.tmp)
        code, out = self.send()
        self.assertEqual(code, 2)
        self.assertFalse(os.path.exists(self.outbox))


class SendTests(GuardCase):
    def setUp(self):
        super().setUp()
        self.pin("suppression.csv")
        code, _ = self.stage()
        self.assertEqual(code, 0)

    def assert_refused(self, needle):
        code, out = self.send()
        self.assertEqual(code, 1)
        self.assertFalse(out["ok"])
        self.assertIn(needle, out["refused"])
        self.assertEqual(out["sent"], 0)
        self.assertFalse(os.path.exists(self.outbox), "a refused send must not create or touch the outbox")

    def test_send_without_approval_is_refused(self):
        self.assert_refused("no approval")

    def test_caller_written_approval_file_counts_for_nothing(self):
        """The reviewer's major 6: a caller-written approval for the staged hashes sent 6 messages."""
        with open(self.staged, encoding="utf-8") as fh:
            staged = json.load(fh)
        appr = self.write("appr2.json", json.dumps({"approved_by": "human:me", "campaign_sha256": staged["campaign_sha256"],
                                                    "recipient_sha256": staged["recipient_sha256"], "approved_on": "2026-11-26", "channel": "fake-outbox"}))
        code, out = run("send", "--staged", self.staged, "--approval", appr, "--outbox", self.outbox)
        self.assertEqual(code, 2)
        self.assertFalse(os.path.exists(self.outbox))
        self.assert_refused("no approval")

    def test_wrong_campaign_hash_is_refused(self):
        self.owner("send-approval", "approval-wrong-hash.json")
        self.assert_refused("no approval")

    def test_agent_approver_is_refused(self):
        with self.assertRaises(ownerlog.OwnerLogError) as cm:
            self.owner("send-approval", "approval-not-human.json")
        self.assertEqual(cm.exception.reason, "record-invalid")
        self.assert_refused("no approval")

    def test_real_transport_is_refused(self):
        self.owner("send-approval", "approval-smtp.json")
        self.assert_refused("no real transport")

    def test_edited_staged_file_is_refused(self):
        self.owner("send-approval", "approval-valid.json")
        with open(self.staged, encoding="utf-8") as fh:
            staged = json.load(fh)
        staged["recipients"].append("carol@example.com")
        with open(self.staged, "w", encoding="utf-8") as fh:
            json.dump(staged, fh)
        self.assert_refused("does not match its own hashes")

    def test_approved_send_reaches_only_the_fake_outbox(self):
        self.owner("send-approval", "approval-valid.json")
        code, out = self.send()
        self.assertEqual(code, 0)
        self.assertEqual((out["sent"], out["already_sent"], out["transport"]), (4, 0, "fake-outbox"))
        self.assertEqual(self.outbox_recipients(), ["alice@example.com", "bob@example.org", "frank@example.com", "heidi@example.org"])

    def test_contact_suppressed_after_staging_is_not_sent(self):
        self.owner("send-approval", "approval-valid.json")
        self.pin("suppression-grown.csv")
        code, out = self.send()
        self.assertEqual(code, 0)
        self.assertEqual(out["suppressed_at_send"], ["frank@example.com"])
        self.assertNotIn("frank@example.com", self.outbox_recipients())
        self.assertFalse(SUPPRESSED & set(self.outbox_recipients()))

    def test_second_send_is_a_no_op(self):
        self.owner("send-approval", "approval-valid.json")
        self.send()
        before = sorted(os.listdir(self.outbox))
        code, out = self.send()
        self.assertEqual(code, 0)
        self.assertEqual((out["sent"], out["already_sent"]), (0, 4))
        self.assertEqual(sorted(os.listdir(self.outbox)), before)

    def test_limits_name_what_the_guard_does_not_establish(self):
        self.owner("send-approval", "approval-valid.json")
        _, out = self.send()
        self.assertTrue(any("legal compliance" in s for s in out["limits"]))
        self.assertTrue(any("same-user process" in s for s in out["limits"]))


class InstalledCommand(unittest.TestCase):
    def test_checked_in_fixture_ledger_stages_and_sends_to_the_fake_outbox(self):
        with tempfile.TemporaryDirectory() as tmp:
            staged, outbox = os.path.join(tmp, "staged.json"), os.path.join(tmp, "outbox")
            p = subprocess.run([sys.executable, SCRIPT, "stage", "--campaign", fx("campaign.json"), "--contacts", fx("contacts.csv"), "--out", staged],
                               capture_output=True, text=True)
            self.assertEqual(p.returncode, 0, p.stdout)
            p = subprocess.run([sys.executable, SCRIPT, "send", "--staged", staged, "--outbox", outbox], capture_output=True, text=True)
            self.assertEqual((p.returncode, json.loads(p.stdout)["sent"]), (0, 4))


class UsageTests(unittest.TestCase):
    def test_missing_subcommand_is_usage_error(self):
        code, out = run()
        self.assertEqual(code, 2)
        self.assertIn("usage", out["error"])


if __name__ == "__main__":
    unittest.main()
