"""DevRel fleet guards on synthetic Fixture Co data: untrusted developer feedback, tenant boundaries,
and replay evidence bound to the exact doc bytes a handoff carries. Uses fleetlib's guards, not copies."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

FLEET = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CF = os.path.dirname(os.path.dirname(FLEET))
sys.path.insert(0, os.path.join(CF, "scripts"))

import fleetlib  # noqa: E402,F401  (puts factory-rig on sys.path)
from factory_rig.canon import sha_file  # noqa: E402
from fleetlib.handoff import evidence_errors, open_handoff, apply_worker_update, validate_handoff  # noqa: E402
from fleetlib.tenancy import can_read  # noqa: E402
from fleetlib.untrusted import guarded_update, scan  # noqa: E402

FX = os.path.join(FLEET, "fixtures")
REPLAY = os.path.join(os.path.dirname(CF), "devrel-quickstart-replay", "scripts", "replay.py")


def load(rel):
    with open(os.path.join(FX, rel)) as fh:
        return json.load(fh)


def text(rel):
    with open(os.path.join(FX, rel)) as fh:
        return fh.read()


class UntrustedFeedback(unittest.TestCase):
    def test_scan_flags_the_redirects_as_data(self):
        cats = {f["category"] for f in scan(text("untrusted/docs-feedback.md"), "docs-feedback.md")}
        self.assertTrue({"authority", "evidence", "exfiltration"} <= cats, cats)

    def test_feedback_cannot_move_acceptance_publication_criteria_or_destinations(self):
        owner = load("handoff/owner.json")
        h = open_handoff(owner)
        new, refused, findings = guarded_update(h, {
            "acceptance_owner": "devrel.docs-architect",
            "authority": dict(owner["authority"], publication="human-approved", external_actions="human-approved"),
            "acceptance_criteria": ["Lab text exists"],
            "data": {"classification": "internal", "allowed_destinations": ["external:feedback@collector.example.invalid"]},
            "summary": "FB-3: --contains is used in step 3 before the lab explains it; propose one sentence in step 2.",
        }, [("docs-feedback.md", text("untrusted/docs-feedback.md"))])
        self.assertEqual({r["field"] for r in refused}, {"acceptance_owner", "authority", "acceptance_criteria", "data"})
        self.assertEqual(new["authority"]["publication"], "staged-only")
        self.assertEqual(new["acceptance_owner"], "human:head-of-devrel")
        self.assertIn("--contains", new["summary"])
        self.assertTrue(findings)
        self.assertEqual(validate_handoff(new), [])


class Tenancy(unittest.TestCase):
    def test_devrel_cannot_read_a_community_moderation_case(self):
        case = load(os.path.join("..", "..", "community", "fixtures", "moderation", "case-cm-1.json"))
        record = {k: case[k] for k in ("tenant_id", "classification", "category")}
        record.update(id=case["case_id"], approved_abstraction=True)
        ok, why = can_read({"tenant_id": "fixture-co", "max_classification": "confidential"}, record)
        self.assertFalse(ok)
        self.assertIn("never shared across tenants by default", why)


class CleanReplayHandoff(unittest.TestCase):
    def setUp(self):
        self.ws = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.ws, True)
        shutil.copytree(os.path.join(FX, "docs"), os.path.join(self.ws, "docs"))
        os.makedirs(os.path.join(self.ws, "evidence"))

    def test_replay_evidence_binds_to_doc_bytes_and_goes_stale_after_an_edit(self):
        doc, ev = "docs/quickstart.md", "evidence/replay-quickstart.json"
        out = subprocess.run([sys.executable, REPLAY, os.path.join(self.ws, doc), "--asset", os.path.join(FX, "fixture-co-notes")],
                             capture_output=True, text=True, timeout=120)
        self.assertEqual(out.returncode, 0, out.stdout[-2000:])
        with open(os.path.join(self.ws, ev), "w") as fh:
            fh.write(out.stdout)
        report = json.loads(out.stdout)
        doc_sha = sha_file(os.path.join(self.ws, doc))
        self.assertEqual(report["doc_sha256"], doc_sha)
        self.assertTrue(report["criteria"]["5_unfamiliar_reader_success"].startswith("unverified"))

        owner, contract = load("handoff/owner.json"), load("handoff/contract.json")
        h, refused = apply_worker_update(open_handoff(owner), {
            "outputs": [{"path": doc, "sha256": doc_sha, "artifact_type": "quickstart"}],
            "evidence": [{"path": ev, "sha256": sha_file(os.path.join(self.ws, ev)), "about": doc,
                          "about_sha256": doc_sha, "contract_hash": owner["contract_hash"]}],
            "summary": "Quickstart replays clean; human usability unverified."})
        self.assertEqual(refused, [])
        self.assertEqual(validate_handoff(h), [])
        self.assertEqual(evidence_errors(h, contract, self.ws), [])

        with open(os.path.join(self.ws, doc), "a") as fh:
            fh.write("\nAn edit after the replay.\n")
        errs = evidence_errors(h, contract, self.ws)
        self.assertTrue(any("changed after the handoff recorded it" in e for e in errs), errs)


if __name__ == "__main__":
    unittest.main()
