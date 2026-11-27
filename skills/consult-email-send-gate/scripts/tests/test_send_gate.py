from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from typing import Any, Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(os.path.dirname(HERE))
SCRIPT = os.path.join(SKILL, "scripts", "send_gate.py")
NOW = "2026-11-25T12:00:00Z"


def fx(name: str) -> str:
    return os.path.join(SKILL, "fixtures", name)


def run(campaign: str, ledger: str = "ledger-fixture-co.json", auth: str = "sender-auth-good.json",
        authorization: Optional[str] = None, now: Optional[str] = NOW) -> Tuple[int, Dict[str, Any]]:
    """Run the CLI. Names resolve under fixtures/; absolute paths (temp files) pass through."""
    p = fx
    cmd: List[str] = [sys.executable, SCRIPT, "--campaign", p(campaign), "--ledger", p(ledger), "--sender-auth", p(auth)]
    if now is not None:
        cmd += ["--now", now]
    if authorization:
        cmd += ["--authorization", p(authorization)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, json.loads(proc.stdout)


def codes(out: Dict[str, Any]) -> List[str]:
    return [d["code"] for d in out["defects"]]


class SendGateTests(unittest.TestCase):
    def assertNoSends(self, out: Dict[str, Any]) -> None:
        self.assertEqual(out["sends_performed"], 0)
        self.assertEqual(out["mode"], "staged")

    def load(self, name: str) -> Dict[str, Any]:
        with open(fx(name), encoding="utf-8") as fh:
            return json.load(fh)

    def tmp_json(self, obj: Any) -> str:
        fd, path = tempfile.mkstemp(suffix=".json")
        self.addCleanup(os.remove, path)
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(obj, fh)
        return path

    def test_positive_clean_campaign(self) -> None:
        rc, out = run("campaign-clean-marketing.json", authorization="authorization-clean.json")
        self.assertEqual(rc, 0)
        self.assertEqual(out["eligible"], ["c1", "c2"])
        self.assertIn({"id": "c3", "reason": "suppressed:unsubscribed"}, out["excluded"])
        self.assertIn({"id": "c4", "reason": "duplicate-address"}, out["excluded"])
        self.assertEqual(out["defects"], [])
        self.assertTrue(out["authorized_for_dispatch"])
        self.assertEqual(out["dispatch_route"], "the tenant's existing authorized email system, by a human")
        self.assertTrue(out["human_review_required"] and out["not_checked"])
        self.assertNoSends(out)

    # ---- review 2026-11-26, defect 1: the approval binds every field that changes who gets what ----
    def approved_variant(self, change) -> Tuple[int, Dict[str, Any]]:
        campaign = self.load("campaign-clean-marketing.json")
        ledger = self.load("ledger-fixture-co.json")
        ledger["contacts"].append({"id": "c10", "email": "new-person@example.com", "tenant_id": "tenant-fixture-co",
                                   "permission": {"marketing": "opted-in", "source": "signup-form-fixture", "at": "2026-11-25T11:00:00Z"}})
        change(campaign)
        return run(self.tmp_json(campaign), ledger=self.tmp_json(ledger), authorization="authorization-clean.json")

    def test_approval_does_not_survive_a_kind_flip_to_transactional(self) -> None:
        def flip(c):
            c["kind"] = "transactional"
            c["audience"] = ["c1", "c3", "c5", "c6"]
        rc, out = self.approved_variant(flip)
        self.assertFalse(out["authorized_for_dispatch"])
        self.assertIn("authorization-invalid", codes(out))
        self.assertEqual(rc, 1)

    def test_approval_does_not_survive_audience_growth(self) -> None:
        rc, out = self.approved_variant(lambda c: c.update(audience=["c1", "c2", "c10"]))
        self.assertFalse(out["authorized_for_dispatch"])
        self.assertIn("authorization-invalid", codes(out))

    def test_approval_does_not_survive_subject_sender_or_header_changes(self) -> None:
        for change in (lambda c: c.update(subject="URGENT: your account will be closed"),
                       lambda c: c.update(from_domain="news.example.com"),
                       lambda c: c["headers"].update({"List-Unsubscribe": "<https://evil.example.invalid/u>"})):
            rc, out = self.approved_variant(change)
            self.assertFalse(out["authorized_for_dispatch"])
            self.assertIn("authorization-invalid", codes(out))

    def test_unchanged_campaign_reports_the_hash_a_human_approved(self) -> None:
        rc, out = run("campaign-clean-marketing.json", authorization="authorization-clean.json")
        self.assertTrue(out["authorized_for_dispatch"])
        self.assertEqual(out["approval_sha256"], self.load("authorization-clean.json")["approval_sha256"])

    # ---- review 2026-11-26, defect 2: suppression matches the mailbox, not the exact string ----
    def test_plus_address_and_trailing_dot_variants_stay_suppressed(self) -> None:
        for variant in ("dee+news@example.com", "dee@example.com.", " DEE+promo@Example.COM. "):
            ledger = self.load("ledger-fixture-co.json")
            ledger["contacts"].append({"id": "c9", "email": variant, "tenant_id": "tenant-fixture-co",
                                       "permission": {"marketing": "opted-in", "source": "signup-form-fixture", "at": "2026-11-01T00:00:00Z"}})
            campaign = self.load("campaign-clean-marketing.json")
            campaign["audience"] = ["c9"]
            rc, out = run(self.tmp_json(campaign), ledger=self.tmp_json(ledger))
            self.assertEqual(out["eligible"], [], variant)
            self.assertIn({"id": "c9", "reason": "suppressed:unsubscribed"}, out["excluded"])

    def test_suppressed_alias_suppresses_the_base_mailbox(self) -> None:
        ledger = self.load("ledger-fixture-co.json")
        ledger["suppressions"].append({"email": "ben+deals@example.com", "reason": "complaint", "at": "2026-10-01T00:00:00Z"})
        rc, out = run("campaign-clean-marketing.json", ledger=self.tmp_json(ledger))
        self.assertNotIn("c2", out["eligible"])
        self.assertIn({"id": "c2", "reason": "suppressed:complaint"}, out["excluded"])

    def test_v1_authorization_that_bound_only_content_is_refused(self) -> None:
        z = self.load("authorization-clean.json")
        z["schema"] = "send-authorization.v1"
        z["content_sha256"] = z.pop("approval_sha256")
        rc, out = run("campaign-clean-marketing.json", authorization=self.tmp_json(z))
        self.assertEqual(rc, 2)
        self.assertIn("re-approve", out["error"])

    def test_no_authorization_is_not_a_defect(self) -> None:
        rc, out = run("campaign-clean-marketing.json")
        self.assertEqual(rc, 0)
        self.assertFalse(out["authorized_for_dispatch"])
        self.assertNoSends(out)

    def test_negative_campaign(self) -> None:
        rc, out = run("campaign-negative.json", authorization="authorization-mismatch.json")
        self.assertEqual(rc, 1)
        c = codes(out)
        self.assertEqual(c.count("one-click-unsubscribe-missing"), 2)
        self.assertIn("a11y-img-alt-missing", c)
        self.assertIn("authorization-invalid", c)
        reasons = " ".join(d["message"] for d in out["defects"] if d["code"] == "authorization-invalid")
        self.assertIn("approval_sha256", reasons)
        self.assertFalse(out["authorized_for_dispatch"])
        self.assertNoSends(out)

    def test_reoptin_after_unsubscribe_stays_suppressed(self) -> None:
        rc, out = run("campaign-reoptin.json")
        self.assertEqual(rc, 0)
        self.assertEqual(out["eligible"], [])
        self.assertEqual(out["excluded"], [{"id": "c5", "reason": "suppressed:unsubscribed"}])
        self.assertNoSends(out)

    def test_transactional_receipt_to_unsubscribed_contact(self) -> None:
        rc, out = run("campaign-transactional.json")
        self.assertEqual(rc, 0)
        self.assertEqual(out["eligible"], ["c6"])
        self.assertEqual(out["excluded"], [{"id": "c8", "reason": "suppressed:hard-bounce"}])
        self.assertEqual(out["defects"], [])
        self.assertNoSends(out)

    def test_expired_authorization(self) -> None:
        rc, out = run("campaign-clean-marketing.json", authorization="authorization-expired.json")
        self.assertEqual(rc, 1)
        self.assertEqual(codes(out), ["authorization-invalid"])
        self.assertIn("expired", out["defects"][0]["message"])
        self.assertFalse(out["authorized_for_dispatch"])
        self.assertNoSends(out)

    def test_authorization_not_human(self) -> None:
        z = self.load("authorization-clean.json")
        z["approved_by"] = "agent:bot"
        rc, out = run("campaign-clean-marketing.json", authorization=self.tmp_json(z))
        self.assertEqual(rc, 1)
        self.assertEqual(codes(out), ["authorization-invalid"])
        self.assertFalse(out["authorized_for_dispatch"])

    def test_cross_tenant_contact(self) -> None:
        rc, out = run("campaign-cross-tenant.json")
        self.assertEqual(rc, 1)
        self.assertEqual(out["eligible"], ["c1"])
        self.assertIn({"id": "c7", "reason": "tenant-mismatch"}, out["excluded"])
        self.assertIn("tenant-mismatch", codes(out))
        self.assertNoSends(out)

    def test_sender_auth_missing(self) -> None:
        a = self.load("sender-auth-good.json")
        a["spf"] = ""
        a["dkim"] = [{"selector": "s1", "present": False}]
        a["dmarc"] = None
        rc, out = run("campaign-clean-marketing.json", auth=self.tmp_json(a))
        self.assertEqual(rc, 1)
        self.assertEqual(codes(out).count("sender-auth-missing"), 3)

    def test_dmarc_policy_none_is_a_warning(self) -> None:
        a = self.load("sender-auth-good.json")
        a["dmarc"] = "v=DMARC1; p=none"
        rc, out = run("campaign-clean-marketing.json", auth=self.tmp_json(a))
        self.assertEqual(rc, 0)
        self.assertEqual(codes(out), ["dmarc-policy-none"])
        self.assertEqual(out["defects"][0]["severity"], "warning")

    def test_accessibility_defects(self) -> None:
        c = self.load("campaign-clean-marketing.json")
        c["content"] = {"html": "<html><body><img src=\"https://example.invalid/a.png\" alt=\"\"></body></html>",
                        "text": "", "lang": ""}
        rc, out = run(self.tmp_json(c))
        self.assertEqual(rc, 1)
        self.assertEqual(sorted(codes(out)), ["a11y-image-only", "a11y-lang-missing", "a11y-text-part-missing"])

    def test_malformed_file_rejected(self) -> None:
        rc, out = run("malformed-campaign.json")
        self.assertEqual(rc, 2)
        self.assertIn("error", out)
        self.assertNotIn("sends_performed", out)

    def test_wrong_schema_tag_rejected(self) -> None:
        rc, out = run("campaign-clean-marketing.json", ledger="campaign-clean-marketing.json")
        self.assertEqual(rc, 2)
        self.assertIn("consent-ledger.v1", out["error"])

    def test_missing_field_rejected(self) -> None:
        c = self.load("campaign-clean-marketing.json")
        del c["audience"]
        rc, out = run(self.tmp_json(c))
        self.assertEqual(rc, 2)
        self.assertIn("audience", out["error"])

    def test_missing_now_rejected(self) -> None:
        rc, out = run("campaign-clean-marketing.json", now=None)
        self.assertEqual(rc, 2)
        self.assertIn("error", out)

    def test_bad_now_rejected(self) -> None:
        rc, out = run("campaign-clean-marketing.json", now="yesterday")
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
