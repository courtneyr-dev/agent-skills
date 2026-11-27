"""Behavior tests for abuse_case.py: exit codes, JSON fields and files a caller sees."""
import contextlib
import io
import json
import os
import shutil
import stat
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.normpath(os.path.join(HERE, "..")))

import abuse_case as ac  # noqa: E402

RIG = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
FIX = os.path.join(RIG, "company-fleets", "fleets", "hosting", "fixtures", "abuse-response")
PHISHING = os.path.join(FIX, "phishing-report-tenant-b.txt")
COPYRIGHT = os.path.join(FIX, "copyright-report-tenant-b.txt")
POLICY = os.path.join(FIX, "policies.json")
HUMAN = "human:abuse-policy-owner"


def run(*argv):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            code = ac.main(list(argv))
        except SystemExit as exc:
            code = exc.code
    out = buf.getvalue()
    return code, json.loads(out) if out.strip() else None


class CaseTest(unittest.TestCase):
    """The owner folder is repointed to a temp folder in process, the way a test plays the owner."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)
        self.case = os.path.join(self.tmp, "case")
        old, ac.OWNER_ROOT = ac.OWNER_ROOT, os.path.join(self.tmp, "owner-root")
        self.addCleanup(setattr, ac, "OWNER_ROOT", old)
        self.anchors = ac.anchors_path()

    def r(self, *argv):
        return run(*argv)

    def report(self, name, text):
        path = os.path.join(self.tmp, name)
        with open(path, "w") as fh:
            fh.write("SYNTHETIC FIXTURE: test report.\n" + text)
        return path

    def intake(self, report=PHISHING, category="phishing", case=None, tenant="tenant-b"):
        return self.r("intake", "--report", report, "--case-dir", case or self.case, "--tenant", tenant, "--category", category)

    def propose(self, action, approver=None, policy=POLICY, case=None):
        """Propose; when approver is given and the proposal stands, run the separate approve step as that approver."""
        code, out = self.r("propose", "--case-dir", case or self.case, "--action", action, "--policy", policy)
        if approver is not None and code == 0 and out.get("state") == "proposed":
            return self.r("approve", "--case-dir", case or self.case, "--by", approver)
        return code, out

    def listing(self):
        return sorted(os.path.relpath(os.path.join(d, f), self.case) for d, _, fs in os.walk(self.case) for f in fs)

    def custody(self):
        return open(os.path.join(self.case, "custody.jsonl"), "rb").read()

    def rewrite(self, rel, transform):
        path = os.path.join(self.case, rel)
        os.chmod(path, 0o644)
        data = open(path, "rb").read()
        with open(path, "wb") as fh:
            fh.write(transform(data))


class IntakeTests(CaseTest):
    def test_preserves_a_read_only_copy_with_a_manifest_and_custody_chain(self):
        code, out = self.intake()
        self.assertEqual((code, out["verdict"], out["state"]), (0, "preserved", "preserved"))
        copy = os.path.join(self.case, "evidence", "phishing-report-tenant-b.txt")
        self.assertEqual(open(copy, "rb").read(), open(PHISHING, "rb").read())
        self.assertEqual(stat.S_IMODE(os.stat(copy).st_mode), 0o444)
        manifest = json.load(open(os.path.join(self.case, "manifest.json")))
        import hashlib
        self.assertEqual(manifest["files"][0]["sha256"], hashlib.sha256(open(PHISHING, "rb").read()).hexdigest())
        self.assertEqual(manifest["files"][0]["size"], os.path.getsize(PHISHING))
        self.assertEqual((manifest["tenant_id"], manifest["category"]), ("tenant-b", "phishing"))
        first = json.loads(self.custody().decode().splitlines()[0])
        self.assertEqual((first["seq"], first["action"], first["state"], first["prev_sha256"]), (0, "intake", "preserved", "0" * 64))
        self.assertEqual(self.listing(), ["custody.jsonl", "evidence/phishing-report-tenant-b.txt", "manifest.json"])
        self.assertEqual(self.r("verify", "--case-dir", self.case)[0], 0)

    def test_embedded_instructions_are_flagged_as_data(self):
        _, out = self.intake()
        cats = sorted(f["category"] for f in out["untrusted_findings"])
        self.assertEqual(cats, ["exfiltration", "override", "tenant-access"])
        manifest = json.load(open(os.path.join(self.case, "manifest.json")))
        self.assertEqual(len(manifest["untrusted_findings"]), 3)
        self.assertEqual(self.r("show", "--case-dir", self.case)[1]["state"], "preserved")

    def test_a_report_without_instructions_has_no_findings(self):
        _, out = self.intake(COPYRIGHT, "copyright")
        self.assertEqual(out["untrusted_findings"], [])

    def test_intake_never_overwrites_an_existing_case(self):
        self.intake()
        before = self.custody()
        code, out = self.intake(COPYRIGHT, "copyright")
        self.assertEqual((code, out["verdict"]), (1, "refused"))
        self.assertEqual(self.custody(), before)

    def test_invalid_input_exits_2(self):
        self.assertEqual(run("intake", "--report", os.path.join(self.tmp, "none.txt"), "--case-dir", self.case,
                             "--tenant", "tenant-b", "--category", "phishing")[0], 2)
        self.assertEqual(run("intake", "--report", PHISHING, "--case-dir", self.case, "--tenant", "Tenant B!", "--category", "phishing")[0], 2)
        self.assertEqual(run("intake", "--report", PHISHING, "--case-dir", self.case, "--tenant", "tenant-b", "--category", "fraud")[0], 2)
        blocker = os.path.join(self.tmp, "afile")
        open(blocker, "w").close()
        self.assertEqual(run("intake", "--report", PHISHING, "--case-dir", blocker, "--tenant", "tenant-b", "--category", "spam")[0], 2)
        old = ac.MAX_REPORT_BYTES
        ac.MAX_REPORT_BYTES = 10
        try:
            self.assertEqual(self.intake()[0], 2)
        finally:
            ac.MAX_REPORT_BYTES = old
        self.assertFalse(os.path.exists(self.case))


class VerifyTests(CaseTest):
    def setUp(self):
        super().setUp()
        self.intake()

    def test_untouched_case_is_intact(self):
        code, out = self.r("verify", "--case-dir", self.case)
        self.assertEqual((code, out["verdict"], out["problems"], out["files_checked"]), (0, "intact", [], 1))

    def test_edited_evidence_is_caught(self):
        self.rewrite("evidence/phishing-report-tenant-b.txt", lambda d: d.replace(b"bank", b"shop"))
        code, out = self.r("verify", "--case-dir", self.case)
        self.assertEqual((code, out["verdict"]), (1, "tampered"))
        self.assertIn("hash differs", out["problems"][0])

    def test_deleted_and_added_evidence_are_caught(self):
        os.remove(os.path.join(self.case, "evidence", "phishing-report-tenant-b.txt"))
        self.assertIn("is missing", self.r("verify", "--case-dir", self.case)[1]["problems"][0])
        with open(os.path.join(self.case, "evidence", "extra.txt"), "w") as fh:
            fh.write("planted")
        self.assertTrue(any("not in the manifest" in p for p in self.r("verify", "--case-dir", self.case)[1]["problems"]))

    def test_edited_manifest_is_caught(self):
        self.rewrite("manifest.json", lambda d: d.replace(b'"phishing"', b'"other"'))
        code, out = self.r("verify", "--case-dir", self.case)
        self.assertEqual(code, 1)
        self.assertIn("manifest.json differs from the hash recorded at intake", out["problems"])

    def test_edited_and_truncated_custody_are_caught(self):
        self.propose("escalate")
        lines = self.custody().decode().splitlines()
        self.assertEqual(len(lines), 2)
        self.rewrite("custody.jsonl", lambda d: d.replace(b'"preserved"', b'"released"', 1))
        code, out = self.r("verify", "--case-dir", self.case)
        self.assertEqual(code, 1)
        self.assertTrue(any("custody chain broken at line 1" in p for p in out["problems"]))
        self.rewrite("custody.jsonl", lambda d: ("\n".join(lines[1:]) + "\n").encode())
        self.assertEqual(self.r("verify", "--case-dir", self.case)[0], 1)

    def test_writable_evidence_is_a_warning_not_a_failure(self):
        os.chmod(os.path.join(self.case, "evidence", "phishing-report-tenant-b.txt"), 0o644)
        code, out = self.r("verify", "--case-dir", self.case)
        self.assertEqual((code, len(out["warnings"])), (0, 1))

    def test_invalid_input_exits_2(self):
        self.assertEqual(self.r("verify", "--case-dir", os.path.join(self.tmp, "none"))[0], 2)
        empty = os.path.join(self.tmp, "empty")
        os.makedirs(empty)
        self.assertEqual(self.r("verify", "--case-dir", empty)[0], 2)
        self.assertEqual(run("verify")[0], 2)


class ProposeTests(CaseTest):
    def setUp(self):
        super().setUp()
        self.intake()

    def test_suspend_is_only_proposed_until_an_owner_listed_human_approves(self):
        code, out = self.propose("suspend")
        self.assertEqual((code, out["decision"], out["state"], out["executed"]), (0, "proposed-for-approval", "proposed", False))

    def test_the_proposer_cannot_approve_and_only_owner_listed_humans_can(self):
        code, out = self.r("propose", "--case-dir", self.case, "--action", "suspend", "--approved-by", "human:abuse-response-analyst")
        self.assertEqual((code, out["refusal"], out["recorded"]), (1, "approval-needs-approve-step", False))
        for who in ("role:abuse-lead", "human:", "human:abuse-response-analyst", "human:ai-assistant"):
            code, out = self.propose("suspend", who)
            self.assertEqual((code, out["refusal"]), (1, "approver-not-authorized"), who)
            self.r("propose", "--case-dir", self.case, "--action", "escalate")

    def test_an_analyst_written_policy_is_refused(self):
        mine = os.path.join(self.tmp, "my-policy.json")
        json.dump({"approvers": ["human:abuse-response-analyst"],
                   "clauses": [{"id": "analyst-made-up-1", "categories": ["phishing"], "actions": ["suspend"]}]}, open(mine, "w"))
        before = self.custody()
        code, out = self.propose("suspend", "human:abuse-response-analyst", policy=mine)
        self.assertEqual((code, out["refusal"]), (1, "policy-not-owner-file"))
        self.assertEqual(self.custody(), before)

    def test_suspend_without_a_policy_clause_escalates_even_with_a_human(self):
        case = os.path.join(self.tmp, "copyright-case")
        self.intake(COPYRIGHT, "copyright", case)
        code, out = self.propose("suspend", HUMAN, case=case)
        self.assertEqual((code, out["decision"]), (1, "escalate"))
        self.assertIn("no policy clause authorizes suspend for category copyright", out["reasons"][0])

    def test_clause_lists_actions_so_remove_content_is_not_authorized_for_phishing(self):
        code, out = self.propose("remove-content", HUMAN)
        self.assertEqual((code, out["decision"]), (1, "escalate"))
        self.assertIn("no policy clause authorizes remove-content", out["reasons"][0])

    def test_authorized_suspend_is_recorded_for_a_human_to_execute(self):
        code, out = self.propose("suspend", HUMAN)
        self.assertEqual((code, out["decision"], out["state"]), (0, "approved-for-human-execution", "approved-for-human-execution"))
        self.assertEqual((out["clause"], out["approved_by"], out["executed"]), ("AUP-4.2", HUMAN, False))
        self.assertIn("human executes", out["instruction"])
        shown = self.r("show", "--case-dir", self.case)[1]
        self.assertEqual(shown["state"], "approved-for-human-execution")
        self.assertEqual(shown["custody"][-1]["actor"], HUMAN)
        self.assertEqual(self.r("verify", "--case-dir", self.case)[0], 0)
        self.assertEqual(self.listing(), ["custody.jsonl", "evidence/phishing-report-tenant-b.txt", "manifest.json"])

    def test_embedded_instruction_does_not_authorize_anything(self):
        _, flagged = self.propose("escalate")
        self.assertEqual(flagged["report_flagged"], 3)
        code, out = self.propose("suspend")
        self.assertEqual((code, out["state"]), (0, "proposed"))
        self.assertNotEqual(self.r("show", "--case-dir", self.case)[1]["state"], "approved-for-human-execution")
        self.assertEqual(self.listing(), ["custody.jsonl", "evidence/phishing-report-tenant-b.txt", "manifest.json"])

    def test_notify_tenant_writes_a_draft_and_sends_nothing(self):
        code, out = self.propose("notify-tenant")
        self.assertEqual((code, out["decision"], out["sent"]), (0, "draft-recorded", False))
        text = open(os.path.join(self.case, out["draft"])).read()
        self.assertTrue(text.startswith("DRAFT, NOT SENT"))
        self.assertNotIn("collector.example", text)
        self.assertNotIn("bank", text)
        self.assertIn("No action has been taken on your account", text)

    def test_escalate_and_no_action_are_recorded(self):
        self.assertEqual(self.propose("escalate")[1]["state"], "escalated")
        code, out = self.propose("no-action")
        self.assertEqual((code, out["decision"]), (0, "no-action-recorded"))
        self.assertEqual(self.r("show", "--case-dir", self.case)[1]["state"], "no-action-recorded")

    def test_tampered_evidence_refuses_every_action_and_records_nothing(self):
        self.rewrite("evidence/phishing-report-tenant-b.txt", lambda d: d + b"\nextra")
        before = self.custody()
        for action in ac.ACTIONS:
            with self.subTest(action):
                code, out = self.propose(action, HUMAN)
                self.assertEqual((code, out["decision"], out["recorded"]), (1, "refuse", False))
                self.assertIn("evidence failed verification", out["reasons"][0])
        self.assertEqual(self.custody(), before)
        self.assertNotIn("drafts", os.listdir(self.case))

    def test_invalid_input_exits_2_and_other_policies_are_refused(self):
        self.assertEqual(self.propose("suspend", HUMAN, policy=os.path.join(self.tmp, "none.json"))[1]["refusal"], "policy-not-owner-file")
        bad = []
        for name, doc in (("nocl.json", {"label": "SYNTHETIC: x"}),
                          ("badcat.json", {"clauses": [{"id": "X", "categories": ["fraud"], "actions": ["suspend"]}]}),
                          ("badact.json", {"clauses": [{"id": "X", "categories": ["phishing"], "actions": ["notify-tenant"]}]}),
                          ("noid.json", {"clauses": [{"categories": ["phishing"], "actions": ["suspend"]}]})):
            path = os.path.join(self.tmp, name)
            json.dump(doc, open(path, "w"))
            bad.append(path)
        notjson = os.path.join(self.tmp, "nj.json")
        open(notjson, "w").write("{oops")
        for path in bad + [notjson]:
            with self.subTest(path):
                code, out = self.propose("suspend", HUMAN, policy=path)
                self.assertEqual((code, out["refusal"]), (1, "policy-not-owner-file"))
        self.assertEqual(self.propose("vaporize", HUMAN)[0], 2)
        self.assertEqual(self.propose("suspend", "  ")[1]["refusal"], "approver-not-authorized")
        self.assertEqual(self.r("propose", "--case-dir", os.path.join(self.tmp, "none"), "--action", "escalate", "--policy", POLICY)[0], 2)


class OwnerAnchorTests(CaseTest):
    def test_a_case_rewritten_with_recomputed_manifest_and_chain_fails(self):
        self.intake()
        from factory_rig import canon
        ev = os.path.join(self.case, "evidence", "phishing-report-tenant-b.txt")
        os.chmod(ev, 0o644)
        open(ev, "w").write("SYNTHETIC FIXTURE: benign report. Nothing to see.\n")
        os.chmod(ev, 0o444)
        mpath = os.path.join(self.case, "manifest.json")
        m = json.load(open(mpath))
        rel = m["files"][0]["path"]
        m["files"][0].update(sha256=canon.sha_file(ev), size=os.path.getsize(ev))
        m["untrusted_findings"] = []
        os.chmod(mpath, 0o644)
        canon.atomic_write(mpath, json.dumps(m, indent=2, sort_keys=True) + "\n")
        rows = [json.loads(x) for x in open(os.path.join(self.case, "custody.jsonl")) if x.strip()]
        prev, out = rows[0]["prev_sha256"], []
        for e in rows:
            e["prev_sha256"] = prev
            if e["action"] == "intake":
                e["detail"]["files"], e["detail"]["manifest_sha256"] = {rel: m["files"][0]["sha256"]}, canon.sha_file(mpath)
            e["sha256"] = canon.sha({k: v for k, v in e.items() if k != "sha256"})
            prev = e["sha256"]
            out.append(json.dumps(e, sort_keys=True))
        open(os.path.join(self.case, "custody.jsonl"), "w").write("\n".join(out) + "\n")
        code, out = self.r("verify", "--case-dir", self.case)
        self.assertEqual((code, out["verdict"]), (1, "tampered"))
        self.assertIn("differs from the owner's anchor", out["problems"][0])

    def test_the_ledger_is_the_owners_fixed_file_and_never_one_the_caller_names(self):
        args = ("intake", "--report", PHISHING, "--case-dir", self.case, "--tenant", "tenant-b", "--category", "phishing")
        for named in (os.path.join(self.case, "anchors.jsonl"), os.path.join(self.tmp, "mine.jsonl")):
            code, out = run(*args, "--anchors", named)
            self.assertEqual((code, out["refusal"]), (1, "anchors-not-owner-ledger"), named)
        self.assertFalse(os.path.exists(self.case))
        code, out = run("intake", "--report", PHISHING, "--case-dir", os.path.join(ac.OWNER_ROOT, "case"), "--tenant", "tenant-b",
                        "--category", "phishing")
        self.assertEqual((code, out["refusal"]), (1, "case-inside-owner-ledger"))
        code, out = run("intake", "--report", PHISHING, "--case-dir", self.tmp, "--tenant", "tenant-b", "--category", "phishing")
        self.assertEqual((code, out["refusal"]), (1, "anchor-inside-case"))
        self.assertEqual(run(*args, "--anchors", self.anchors)[0], 0, "naming the owner's own ledger is allowed")

    def test_a_rewritten_case_with_its_own_one_line_ledger_is_refused(self):
        """Major 2: the forger writes a ledger holding the forged head in a folder it controls."""
        self.intake()
        self.r("propose", "--case-dir", self.case, "--action", "escalate")
        rows = [json.loads(x) for x in open(os.path.join(self.case, "custody.jsonl")) if x.strip()]
        from factory_rig import canon
        rows[-1]["state"], rows[-1]["detail"]["decision"] = "approved-for-human-execution", "approved-for-human-execution"
        rows[-1]["sha256"] = canon.sha({k: v for k, v in rows[-1].items() if k != "sha256"})
        with open(os.path.join(self.case, "custody.jsonl"), "w") as fh:
            fh.write("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
        mine = os.path.join(self.tmp, "mine.jsonl")
        with open(mine, "w") as fh:
            fh.write(json.dumps({"case_id": rows[0]["case_id"], "seq": rows[-1]["seq"], "head_sha256": rows[-1]["sha256"],
                                 "manifest_sha256": canon.sha_file(os.path.join(self.case, "manifest.json"))}) + "\n")
        self.assertEqual(run("verify", "--case-dir", self.case, "--anchors", mine)[1]["refusal"], "anchors-not-owner-ledger")
        code, out = run("verify", "--case-dir", self.case)
        self.assertEqual((code, out["verdict"]), (1, "tampered"))

    def test_a_lookalike_host_names_no_tenant(self):
        """Minor 11: client-a.example.evil.test is a host under evil.test, not under client-a.example."""
        report = self.report("lookalike.txt", "Phishing at https://client-a.example.evil.test/login and http://evilclient-a.example/\n")
        code, out = self.intake(report, tenant="tenant-a")
        self.assertEqual((code, out["tenant_confirmed"]), (0, False))
        self.assertEqual(out["hosts"], ["client-a.example.evil.test", "evilclient-a.example"])
        self.assertEqual(self.propose("suspend")[1]["decision"], "escalate")

    def test_a_subdomain_and_a_trailing_dot_still_confirm_their_tenant(self):
        report = self.report("sub.txt", "Phishing at https://login.tenant-a.example/verify. Also see client-a.example.\n")
        code, out = self.intake(report, tenant="tenant-a")
        self.assertEqual((code, out["tenant_confirmed"], out["hosts"]), (0, True, ["client-a.example", "login.tenant-a.example"]))

    def test_a_report_naming_two_tenants_confirms_neither(self):
        report = self.report("both.txt", "Pages at https://www.tenant-a.example/x and https://www.tenant-b.example/y\n")
        for tenant in ("tenant-a", "tenant-b"):
            code, out = self.intake(report, tenant=tenant)
            self.assertEqual((code, out["refusal"]), (1, "tenant-ambiguous"), tenant)
        self.assertFalse(os.path.exists(self.case))

    def test_the_same_report_taken_in_twice_is_refused_and_the_first_case_stays_intact(self):
        self.intake()
        self.propose("suspend", HUMAN)
        code, out = self.intake(case=os.path.join(self.tmp, "again"))
        self.assertEqual((code, out["refusal"]), (1, "case-exists"))
        self.assertFalse(os.path.exists(os.path.join(self.tmp, "again")))
        code, out = self.r("verify", "--case-dir", self.case)
        self.assertEqual((code, out["verdict"]), (0, "intact"))

    def test_an_approved_case_is_consumed_once(self):
        self.intake()
        self.propose("suspend", HUMAN)
        case_id = json.load(open(os.path.join(self.case, "manifest.json")))["case_id"]
        self.assertIsNone(ac.consumed(case_id))
        ac.consume_case(case_id, {"account_id": "acct-tenant-b-001"})
        self.assertEqual(ac.consumed(case_id)["account_id"], "acct-tenant-b-001")
        with self.assertRaises(ac.Refusal) as ctx:
            ac.consume_case(case_id, {"account_id": "acct-tenant-b-001"})
        self.assertEqual(ctx.exception.payload["refusal"], "case-consumed")

    def test_non_utf8_custody_exits_2_with_a_named_reason(self):
        self.intake()
        with open(os.path.join(self.case, "custody.jsonl"), "ab") as fh:
            fh.write(b"\xff\xfe\n")
        code, out = self.r("verify", "--case-dir", self.case)
        self.assertEqual(code, 2)
        self.assertIn("not UTF-8", out["error"])
        self.rewrite("manifest.json", lambda d: b"\xff" + d)
        code, out = self.r("verify", "--case-dir", self.case)
        self.assertEqual(code, 2)
        self.assertIn("manifest.json is not UTF-8", out["error"])

    def test_a_report_about_another_tenant_is_refused(self):
        code, out = self.intake(tenant="tenant-a")
        self.assertEqual((code, out["refusal"]), (1, "tenant-mismatch"))
        self.assertFalse(os.path.exists(self.case))


class ShowTests(CaseTest):
    def test_show_reports_state_findings_and_integrity(self):
        self.intake()
        code, out = self.r("show", "--case-dir", self.case)
        self.assertEqual((code, out["state"], out["integrity"]["verdict"]), (0, "preserved", "intact"))
        self.assertEqual(len(out["untrusted_findings"]), 3)
        self.assertEqual([c["action"] for c in out["custody"]], ["intake"])

    def test_show_exits_1_on_a_tampered_case(self):
        self.intake()
        self.rewrite("evidence/phishing-report-tenant-b.txt", lambda d: d + b"x")
        code, out = self.r("show", "--case-dir", self.case)
        self.assertEqual((code, out["integrity"]["verdict"]), (1, "tampered"))


class FixtureLabelTests(unittest.TestCase):
    def test_every_fixture_is_labelled_synthetic(self):
        for name in os.listdir(FIX):
            text = open(os.path.join(FIX, name), encoding="utf-8").read()
            if name.endswith(".json"):
                self.assertTrue(json.loads(text)["label"].startswith("SYNTHETIC:"), name)
            else:
                self.assertTrue(text.startswith("SYNTHETIC FIXTURE:"), name)


if __name__ == "__main__":
    unittest.main()
