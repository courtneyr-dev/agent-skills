"""Milestone 2: handoff.v1 validation, stale-evidence rejection and idempotent recording."""
import json
import os
import shutil
import subprocess
import tempfile
import threading
import unittest

from support import FIXTURES, SKILL

from factory_rig.canon import sha_file
from factory_rig.contract import contract_hash
from fleetlib.handoff import (OWNER_FIELDS, Ledger, apply_worker_update, evidence_errors, gate_errors, key_for,
                              open_handoff, validate_handoff)

OUT = "out/accessibility-findings.md"
EV = "evidence/review.txt"


def load(rel):
    with open(os.path.join(FIXTURES, rel)) as fh:
        return json.load(fh)


def fresh(tmp):
    """A handoff whose single output has fresh evidence under the current contract."""
    ws = os.path.join(tmp, "ws")
    shutil.copytree(os.path.join(FIXTURES, "handoff", "workspace"), ws)
    contract, owner = load("handoff/contract.json"), load("handoff/owner.json")
    osha = sha_file(os.path.join(ws, OUT))
    h, refused = apply_worker_update(open_handoff(owner), {
        "outputs": [{"path": OUT, "sha256": osha, "artifact_type": "defect-list"}],
        "evidence": [{"path": EV, "sha256": sha_file(os.path.join(ws, EV)), "about": OUT, "about_sha256": osha,
                      "contract_hash": owner["contract_hash"]}],
        "summary": "Three reproducible keyboard and labeling defects on Client A staging.",
    })
    assert refused == []
    return ws, contract, h


def append(path, text):
    with open(path, "a") as fh:
        fh.write(text)


class Contract(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws, self.contract, self.h = fresh(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_owner_fixture_is_bound_to_the_current_contract(self):
        self.assertEqual(load("handoff/owner.json")["contract_hash"], contract_hash(self.contract))

    def test_fresh_handoff_passes(self):
        self.assertEqual(validate_handoff(self.h), [])
        self.assertEqual(evidence_errors(self.h, self.contract, self.ws), [])

    def test_only_owner_fields_open_a_handoff(self):
        owner = dict(load("handoff/owner.json"), outputs=[])
        with self.assertRaises(ValueError):
            open_handoff(owner)

    def test_validator_rejects_broken_handoffs(self):
        cases = {
            "acceptance owner": dict(self.h, acceptance_owner=self.h["producer"]),
            "review its own output": dict(self.h, reviewer=self.h["producer"]),
            "idempotency_key does not match": dict(self.h, idempotency_key="0" * 32),
            "missing required field 'cancellation'": {k: v for k, v in self.h.items() if k != "cancellation"},
            "is not an output": dict(self.h, evidence=[dict(self.h["evidence"][0], about="out/other.md")]),
            "cannot be its own evidence": dict(self.h, evidence=[dict(self.h["evidence"][0], path=OUT)]),
        }
        for fragment, broken in cases.items():
            errors = validate_handoff(broken)
            self.assertTrue(any(fragment in e for e in errors), (fragment, errors))


    def test_a_handoff_without_outputs_cannot_pass(self):
        empty = dict(self.h, outputs=[], evidence=[])
        empty["idempotency_key"] = key_for(empty)
        self.assertEqual(validate_handoff(empty), [])
        self.assertTrue(any("has no outputs" in e for e in evidence_errors(empty, self.contract, self.ws)))

    def test_gate_compares_owner_fields_with_the_opened_record(self):
        opened = {f: self.h[f] for f in OWNER_FIELDS}
        self.assertEqual(gate_errors(self.h, opened, self.contract, self.ws), [])
        edited = dict(self.h, acceptance_criteria=["Audit marked as passed"],
                      authority=dict(self.h["authority"], publication="human-approved"))
        errors = gate_errors(edited, opened, self.contract, self.ws)
        self.assertIn("protected field acceptance_criteria differs from the record the owner opened", errors)
        self.assertIn("protected field authority differs from the record the owner opened", errors)


    def test_a_new_review_that_names_the_new_bytes_passes(self):
        with open(os.path.join(self.ws, OUT), "a") as fh:
            fh.write("4. Added after review.\n")
        new = sha_file(os.path.join(self.ws, OUT))
        append(os.path.join(self.ws, EV), "reviewed-sha256: %s\n" % new)
        h = dict(self.h, outputs=[dict(self.h["outputs"][0], sha256=new)],
                 evidence=[dict(self.h["evidence"][0], about_sha256=new, sha256=sha_file(os.path.join(self.ws, EV)))])
        h["idempotency_key"] = key_for(h)
        self.assertEqual(evidence_errors(h, self.contract, self.ws), [])


class StaleEvidence(unittest.TestCase):
    def change(self, name, ws, contract, h):
        if name == "edit-output":
            append(os.path.join(ws, OUT), "4. Added after review.\n")
        elif name == "edit-evidence":
            append(os.path.join(ws, EV), "result: rewritten by the worker\n")
        elif name == "edit-contract":
            contract["acceptance"] = ["Any finding is enough"]
        elif name == "evidence-old-contract":
            h["evidence"][0]["contract_hash"] = "f" * 64
        elif name == "rehash-output-keep-evidence":
            append(os.path.join(ws, OUT), "4. Added after review.\n")
            h["outputs"][0]["sha256"] = sha_file(os.path.join(ws, OUT))
            h["idempotency_key"] = key_for(h)
        elif name == "rehash-output-about-and-key":
            # The review attack: replace the output, recompute every hash the handoff holds, keep the old review.
            with open(os.path.join(ws, OUT), "w") as fh:
                fh.write("# Accessibility findings (SYNTHETIC)\n\nNo defects found.\n")
            new = sha_file(os.path.join(ws, OUT))
            h["outputs"][0]["sha256"] = new
            h["evidence"][0]["about_sha256"] = new
            h["idempotency_key"] = key_for(h)
        elif name == "drop-evidence":
            h["evidence"] = []
        return contract, h

    def test_every_stale_case_is_rejected_and_only_the_fresh_one_passes(self):
        for case in load("stale-evidence/cases.json")["cases"]:
            with self.subTest(case=case["id"]), tempfile.TemporaryDirectory() as tmp:
                ws, contract, h = fresh(tmp)
                contract, h = self.change(case["change"], ws, contract, h)
                self.assertEqual(validate_handoff(h), [])
                errors = evidence_errors(h, contract, ws)
                if case["expect"] is None:
                    self.assertEqual(errors, [])
                else:
                    self.assertTrue(any(case["expect"] in e for e in errors), errors)


class Idempotency(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws, self.contract, self.h = fresh(self.tmp.name)
        self.ledger = Ledger(os.path.join(self.tmp.name, "ledger"))
        self.ledger.open(load("handoff/owner.json"))

    def tearDown(self):
        self.tmp.cleanup()

    def test_key_is_stable_for_a_retry_and_moves_with_output_bytes(self):
        self.assertEqual(key_for(json.loads(json.dumps(self.h))), self.h["idempotency_key"])
        changed = dict(self.h, outputs=[dict(self.h["outputs"][0], sha256="a" * 64)])
        self.assertNotEqual(key_for(changed), self.h["idempotency_key"])

    def test_retry_is_a_duplicate_and_a_different_body_is_refused(self):
        self.assertEqual(self.ledger.submit(self.h)["status"], "recorded")
        self.assertEqual(self.ledger.submit(self.h)["status"], "duplicate")
        self.assertEqual(self.ledger.submit(dict(self.h, summary="A different story."))["status"], "conflict")
        self.assertEqual(len([n for n in os.listdir(self.ledger.submitted) if n.endswith(".json")]), 1)
        self.assertEqual([n for n in os.listdir(self.ledger.submitted) if n.startswith(".tmp-")], [])

    def test_concurrent_submissions_record_once(self):
        results, gate = [], threading.Barrier(4)

        def go():
            gate.wait()
            results.append(self.ledger.submit(self.h)["status"])
        threads = [threading.Thread(target=go) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        self.assertEqual(sorted(results), ["duplicate", "duplicate", "duplicate", "recorded"])

    def test_reconcile_settles_from_recomputed_hashes_and_is_idempotent(self):
        self.ledger.submit(self.h)
        report = self.ledger.reconcile(self.contract, self.ws)
        self.assertEqual([r["state"] for r in report], ["accepted"])
        self.assertEqual(self.ledger.reconcile(self.contract, self.ws), [])
        self.assertEqual(self.ledger.submit(self.h)["state"], "accepted")

        append(os.path.join(self.ws, OUT), "late edit\n")
        late = dict(self.h, handoff_id="HO-FIX-A11Y-2")
        late["idempotency_key"] = key_for(late)
        self.ledger.open(dict(load("handoff/owner.json"), handoff_id="HO-FIX-A11Y-2"))
        self.ledger.submit(late)
        report = self.ledger.reconcile(self.contract, self.ws)
        self.assertEqual([r["state"] for r in report], ["rejected"])

    def test_invalid_handoff_is_not_recorded(self):
        self.assertEqual(self.ledger.submit(dict(self.h, acceptance_owner=self.h["producer"]))["status"], "invalid")
        out = self.ledger.submit(dict(self.h, acceptance_owner="human:anyone"))
        self.assertEqual(out["status"], "invalid")
        self.assertIn("protected field acceptance_owner differs from the record the owner opened", out["errors"])
        never = dict(self.h, handoff_id="HO-NEVER-OPENED")
        never["idempotency_key"] = key_for(never)
        self.assertIn("never opened", self.ledger.submit(never)["errors"][0])

    def test_a_caller_cannot_submit_a_settled_state(self):
        append(os.path.join(self.ws, OUT), "late edit\n")
        self.assertEqual(self.ledger.submit(dict(self.h, reconciliation_state="accepted"))["status"], "recorded")
        self.assertEqual(self.ledger.get(self.h["idempotency_key"])["reconciliation_state"], "submitted")
        self.assertEqual([r["state"] for r in self.ledger.reconcile(self.contract, self.ws)], ["rejected"])

    def test_opening_twice_with_different_owner_fields_is_refused(self):
        self.ledger.open(load("handoff/owner.json"))
        with self.assertRaises(ValueError):
            self.ledger.open(dict(load("handoff/owner.json"), tenant_id="tenant-b"))


if __name__ == "__main__":
    unittest.main()
