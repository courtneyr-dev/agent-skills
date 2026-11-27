"""Behavior tests for release_gate.py. Each variant is a temporary copy of fixtures/ with one change."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, ".."))

import fixture_handoff  # noqa: E402
import release_gate  # noqa: E402

SKILL = os.path.normpath(os.path.join(HERE, "..", ".."))
SCRIPT = os.path.join(SKILL, "scripts", "release_gate.py")
FX = os.path.join(SKILL, "fixtures")

ADAPTERS = all(os.path.isfile(p) for p in (release_gate.SEMVER, release_gate.CHANGELOG))
needs_adapters = unittest.skipUnless(
    ADAPTERS, "needs the release-engineering skill (magnus919/agent-skills) installed beside this one")


def run(*args):
    p = subprocess.run([sys.executable, SCRIPT] + list(args), capture_output=True, text=True)
    return p.returncode, json.loads(p.stdout)


def codes(result, stage):
    return [e["code"] for s in result["stages"] if s["stage"] == stage for e in s["errors"]]


def status(result, stage):
    return next(s["status"] for s in result["stages"] if s["stage"] == stage)


class Variant:
    """A temporary fixtures copy; edit JSON files, then rebind the handoff to the edited bytes."""

    def __init__(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = os.path.join(self.tmp.name, "fx")
        shutil.copytree(FX, self.dir)

    def edit(self, name, fn):
        path = os.path.join(self.dir, name)
        with open(path) as fh:
            doc = json.load(fh)
        fn(doc)
        with open(path, "w") as fh:
            fh.write(json.dumps(doc, indent=2) + "\n")

    def rebind(self, review=True, reviewer=fixture_handoff.REVIEWER):
        """review=True models a real re-review; review=False is the attack: rehash the edited inputs, keep old reviews."""
        if review:
            fixture_handoff.write_reviews(self.dir, "candidate-ok.json", reviewer=reviewer)
        fixture_handoff.write(os.path.join(self.dir, "handoff.json"), fixture_handoff.build(self.dir))

    def gate(self, candidate="candidate-ok.json"):
        return run("gate", "--candidate", os.path.join(self.dir, candidate))

    def close(self):
        self.tmp.cleanup()


class ReleaseGateTest(unittest.TestCase):
    def setUp(self):
        self.v = Variant()

    def tearDown(self):
        self.v.close()

    @unittest.skipIf(ADAPTERS, "release-engineering is installed; the ready path is tested instead")
    def test_missing_adapters_block_their_stages_and_the_release(self):
        code, out = self.v.gate()
        self.assertEqual(code, 1)
        self.assertNotEqual(out["decision"], "ready-for-human-approval")
        for stage in ("semver-and-channel", "changelog"):
            self.assertEqual(status(out, stage), "blocked", stage)

    @needs_adapters
    def test_complete_candidate_is_ready_for_human_approval_not_approved(self):
        code, out = self.v.gate()
        self.assertEqual(code, 0)
        self.assertEqual(out["decision"], "ready-for-human-approval")
        self.assertEqual(out["approval_owner"], "human:release-owner")
        self.assertTrue(all(s["status"] == "pass" for s in out["stages"]))

    def test_incompatible_host_is_refused_before_any_packaging_stage_runs(self):
        code, out = self.v.gate("candidate-incompatible-host.json")
        self.assertEqual(code, 1)
        self.assertEqual(out["stages"][0]["stage"], "compatibility")
        self.assertEqual(codes(out, "compatibility"), ["incompatible-host"])
        self.assertTrue(all(s["status"] == "not-run" for s in out["stages"][1:]))

    def test_retired_api_version_is_refused_at_compatibility(self):
        self.v.edit("candidate-ok.json", lambda c: c.update(compat_matrix="compat-retired-api.json"))
        code, out = self.v.gate()
        self.assertEqual(code, 1)
        self.assertEqual(codes(out, "compatibility"), ["api-version-not-served"])

    def test_matrix_for_another_version_cannot_satisfy_the_gate(self):
        self.v.edit("compat-ok.json", lambda m: m["product"].update(version="1.4.2"))
        self.v.rebind()
        code, out = self.v.gate()
        self.assertEqual(code, 1)
        self.assertIn("matrix-product-mismatch", codes(out, "compatibility"))

    def test_matrix_edited_after_review_is_stale(self):
        code, out = self.v.gate("candidate-stale-evidence.json")
        self.assertEqual(code, 1)
        self.assertEqual(status(out, "evidence-freshness"), "fail")
        joined = " ".join(e["message"] for e in out["stages"][-1]["errors"])
        self.assertIn("changed after the handoff recorded it", joined)

    def test_contract_edited_after_review_makes_all_evidence_stale(self):
        self.v.edit("contract.json", lambda c: c["acceptance"].append("Added after review"))
        code, out = self.v.gate()
        self.assertEqual(code, 1)
        joined = " ".join(e["message"] for e in out["stages"][-1]["errors"])
        self.assertIn("is bound to contract", joined)
        self.assertIn("it was produced under contract", joined)

    def test_wordpress_review_does_not_validate_a_shopify_app(self):
        self.v.edit("candidate-ok.json", lambda c: c["product"].update(platform="shopify-app"))
        self.v.edit("compat-ok.json", lambda m: m["product"].update(platform="shopify-app"))
        self.v.rebind()
        code, out = self.v.gate()
        self.assertEqual(code, 1)
        self.assertEqual(codes(out, "marketplace-policy"), ["marketplace-platform-mismatch"])

    def test_platform_without_a_pinned_checklist_blocks_instead_of_passing(self):
        def chrome(c):
            c["product"]["platform"] = "browser-extension-chrome"
            c["marketplace_review"] = None
        self.v.edit("candidate-ok.json", chrome)
        self.v.edit("compat-ok.json", lambda m: m["product"].update(platform="browser-extension-chrome"))
        self.v.rebind()
        code, out = self.v.gate()
        self.assertEqual(code, 1)
        self.assertEqual(out["decision"], "blocked")
        self.assertEqual(status(out, "marketplace-policy"), "blocked")

    @needs_adapters
    def test_breaking_change_needs_a_major_version(self):
        self.v.edit("candidate-ok.json", lambda c: c["product"].update(version="1.5.0"))
        self.v.edit("compat-ok.json", lambda m: m["product"].update(version="1.5.0"))
        self.v.rebind()
        _, out = self.v.gate()
        self.assertIn("breaking-change-without-major", codes(out, "semver-and-channel"))
        self.assertIn("changelog-missing-version", codes(out, "changelog"))

    @needs_adapters
    def test_beta_channel_needs_a_prerelease(self):
        self.v.edit("candidate-ok.json", lambda c: c.update(channel="beta"))
        _, out = self.v.gate()
        self.assertEqual(codes(out, "semver-and-channel"), ["channel-prerelease-mismatch"])

    def test_disallowed_license_and_open_critical_advisory_are_refused(self):
        self.v.edit("sbom.json", lambda s: s["components"].append(
            {"name": "fixture-pdf", "version": "0.9.0", "licenses": [{"license": {"id": "AGPL-3.0-only"}}]}))
        self.v.edit("candidate-ok.json", lambda c: c["vulnerabilities"].append(
            {"id": "FX-ADV-0009", "component": "fixture-http-client", "severity": "critical", "status": "open"}))
        self.v.rebind()
        code, out = self.v.gate()
        self.assertEqual(code, 1)
        self.assertEqual(sorted(codes(out, "supply-chain")), ["license-not-allowed", "open-vulnerability"])

    def test_schema_change_without_a_rollback_test_is_refused(self):
        self.v.edit("candidate-ok.json", lambda c: c["migration"].update(down="not-run", data_retention=""))
        _, out = self.v.gate()
        self.assertEqual(sorted(codes(out, "migration-and-rollback")), ["retention-undefined", "rollback-untested"])

    def test_missing_semver_adapter_blocks_the_stage(self):
        saved = release_gate.SEMVER
        release_gate.SEMVER = os.path.join(self.v.dir, "no-such-semver_check.py")
        try:
            c = release_gate.parse_candidate(os.path.join(self.v.dir, "candidate-ok.json"))
            out = release_gate.gate(c, self.v.dir)
        finally:
            release_gate.SEMVER = saved
        self.assertEqual(status(out, "semver-and-channel"), "blocked")
        self.assertEqual(out["decision"], "blocked")

    # ---- review 2026-11-26, defects 3 and 5: candidate claims are hash-bound and every review names the bytes it read ----
    def test_candidate_claims_edited_and_rebound_without_review_are_refused(self):
        edits = {
            "A8 migration removed": lambda c: c.update(migration=None),
            "A11 AGPL allowed by the candidate": lambda c: c["license_policy"]["allowed"].append("AGPL-3.0-only"),
            "A15b open critical flipped to fixed": lambda c: c["vulnerabilities"].append(
                {"id": "FX-ADV-9", "component": "fixture-csv", "severity": "critical", "status": "fixed"}),
        }
        for label, fn in edits.items():
            v = Variant()
            try:
                v.edit("candidate-ok.json", fn)
                v.rebind(review=False)
                code, out = v.gate()
                self.assertEqual(code, 1, label)
                self.assertIn("review-not-bound-to-output", codes(out, "evidence-freshness"), label)
            finally:
                v.close()

    def test_rehash_without_a_new_review_is_refused(self):
        def fork(s):
            s["components"][0].update(name="fixture-http-client-fork", version="9.9.9")
        self.v.edit("sbom.json", fork)
        self.v.rebind(review=False)
        code, out = self.v.gate()
        self.assertEqual(code, 1)
        self.assertIn("review-not-bound-to-output", codes(out, "evidence-freshness"))
        self.assertEqual(out["decision"], "refused")

    def test_review_written_by_the_producer_is_refused(self):
        self.v.edit("sbom.json", lambda s: s["components"][0].update(version="3.1.1"))
        self.v.rebind(review=True, reviewer="product.release-engineer")
        code, out = self.v.gate()
        self.assertEqual(code, 1)
        self.assertIn("review-wrong-reviewer", codes(out, "evidence-freshness"))

    def test_migration_must_be_declared_even_without_a_schema_change(self):
        self.v.edit("candidate-ok.json", lambda c: c.update(migration=None))
        self.v.rebind(review=True)
        code, out = self.v.gate()
        self.assertEqual(code, 1)
        self.assertEqual(codes(out, "migration-and-rollback"), ["migration-undeclared"])

    # ---- review 2026-11-26, defect 4: compatibility needs something tested ----
    def test_inverted_range_with_no_tests_is_refused(self):
        def invert(m):
            m["declares"]["hosts"]["wordpress"] = {"min": "6.9", "max": "6.4"}
            m["tests"] = [t for t in m["tests"] if t["host"] != "wordpress"]
        self.v.edit("compat-ok.json", invert)
        self.v.rebind(review=True)
        code, out = self.v.gate()
        self.assertEqual(code, 1)
        self.assertIn("declared-range-inverted", codes(out, "compatibility"))

    def test_matrix_declaring_nothing_is_refused(self):
        def empty(m):
            m["declares"] = {"hosts": {}, "apis": {}}
            m["tests"] = []
        self.v.edit("compat-ok.json", empty)
        self.v.rebind(review=True)
        code, out = self.v.gate()
        self.assertEqual(code, 1)
        self.assertEqual(codes(out, "compatibility"), ["no-hosts-declared"])

    def test_review_file_edited_after_binding_is_stale(self):
        with open(os.path.join(self.v.dir, "evidence", "sbom.json.review.txt"), "a") as fh:
            fh.write("reviewer note added later\n")
        code, out = self.v.gate()
        self.assertEqual(code, 1)
        joined = " ".join(e["message"] for e in out["stages"][-1]["errors"])
        self.assertIn("its file was edited after it was recorded", joined)

    def test_compat_subcommand_rejects_untested_maximum(self):
        code, out = run("compat", "--matrix", os.path.join(FX, "compat-untested-max.json"))
        self.assertEqual(code, 1)
        self.assertEqual([e["code"] for e in out["errors"]], ["untested-host-version"])

    def test_invalid_inputs_exit_2(self):
        bad_json = os.path.join(self.v.dir, "bad.json")
        with open(bad_json, "w") as fh:
            fh.write("{not json")
        wrong = os.path.join(self.v.dir, "wrong.json")
        with open(wrong, "w") as fh:
            json.dump({"schema": "release-candidate.v0"}, fh)
        for args in (("gate", "--candidate", bad_json), ("gate", "--candidate", wrong),
                     ("gate", "--candidate", os.path.join(FX, "candidate-invalid.json")),
                     ("compat", "--matrix", wrong)):
            code, out = run(*args)
            self.assertEqual(code, 2, args)
            self.assertIn("error", out)


if __name__ == "__main__":
    unittest.main()
