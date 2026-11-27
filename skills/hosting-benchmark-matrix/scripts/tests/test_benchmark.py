"""Behavior tests for benchmark.py against the dated matrix and its counterexamples."""
from __future__ import annotations

import contextlib
import copy
import io
import hashlib
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import benchmark as bm  # noqa: E402

CF = os.path.normpath(os.path.join(HERE, "..", "..", "..", "company-fleets"))
MATRIX = os.path.join(CF, "fleets", "hosting", "benchmark", "2026-11-26-matrix.json")
BAD = os.path.join(CF, "fleets", "hosting", "fixtures", "benchmark-matrix")


def call(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        try:
            code = bm.main(list(argv))
        except SystemExit as exc:
            code = exc.code
    text = out.getvalue()
    try:
        return code, json.loads(text)
    except ValueError:
        return code, text


def rules(out):
    return sorted({v["rule"] for v in out["violations"]})


class MatrixTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="bm-test-")
        self.addCleanup(shutil.rmtree, self.tmp, True)
        with open(MATRIX, encoding="utf-8") as fh:
            self.doc = json.load(fh)

    def write(self, doc):
        path = os.path.join(self.tmp, "m.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(doc, fh)
        return path

    def dim(self, doc, name):
        return next(d for d in doc["dimensions"] if d["id"] == name)

    def test_dated_matrix_passes_and_keeps_rpo_unmet(self):
        code, out = call("check", "--matrix", MATRIX, "--root", CF)
        self.assertEqual((code, out["verdict"]), (0, "pass"))
        self.assertEqual(out["statuses"]["recovery_objectives"], "unmet")
        self.assertEqual(out["statuses"]["performance_under_load"], "not-measured")

    def test_superiority_and_roster_claims_refused(self):
        code, out = call("check", "--matrix", os.path.join(BAD, "matrix-superiority.json"), "--root", CF)
        self.assertEqual(code, 1)
        self.assertEqual(rules(out), ["roster-size", "superiority"])

    def test_availability_from_lab_refused(self):
        code, out = call("check", "--matrix", os.path.join(BAD, "matrix-availability-from-lab.json"), "--root", CF)
        self.assertEqual(code, 1)
        self.assertEqual(rules(out), ["availability-from-lab", "measured-evidence"])

    def test_edited_measurement_refused(self):
        code, out = call("check", "--matrix", os.path.join(BAD, "matrix-tampered-measurement.json"), "--root", CF)
        self.assertEqual((code, rules(out)), (1, ["measured-evidence"]))

    def test_commitment_without_contract_refused(self):
        code, out = call("check", "--matrix", os.path.join(BAD, "matrix-fabricated-commitment.json"), "--root", CF)
        self.assertEqual((code, rules(out)), (1, ["no-contract"]))

    def test_missing_provider_entry_refused(self):
        code, out = call("check", "--matrix", os.path.join(BAD, "matrix-missing-provider.json"), "--root", CF)
        self.assertEqual((code, rules(out)), (1, ["provider-claims"]))

    def test_not_documented_publicly_counts_as_an_entry(self):
        statuses = [c["status"] for d in self.doc["dimensions"] for c in d["provider_claims"]]
        self.assertIn("not documented publicly", statuses)
        self.assertEqual(call("check", "--matrix", MATRIX, "--root", CF)[0], 0)

    def test_evidence_file_edited_after_recording_refused(self):
        doc = copy.deepcopy(self.doc)
        root = os.path.join(self.tmp, "root")
        ev = self.dim(doc, "restore")["measured_result"]["evidence"]
        os.makedirs(os.path.dirname(os.path.join(root, ev)))
        shutil.copy(os.path.join(CF, ev), os.path.join(root, ev))
        with open(os.path.join(root, ev), "a", encoding="utf-8") as fh:
            fh.write("\n")
        for d in doc["dimensions"]:
            if d["measured_result"] and d["measured_result"]["evidence"] != ev:
                d["measured_result"] = None
        code, out = call("check", "--matrix", self.write(doc), "--root", root)
        self.assertEqual(code, 1)
        self.assertIn("differs from the sha256 its owner recorded", json.dumps(out["violations"]))

    def test_missing_field_refused(self):
        doc = copy.deepcopy(self.doc)
        del self.dim(doc, "cost")["configured_capability"]
        code, out = call("check", "--matrix", self.write(doc), "--root", CF)
        self.assertEqual((code, rules(out)), (1, ["five-fields"]))

    def test_unlabeled_availability_target_refused(self):
        doc = copy.deepcopy(self.doc)
        self.dim(doc, "availability")["proposed_target"] = {"summary": "99.95% monthly"}
        code, out = call("check", "--matrix", self.write(doc), "--root", CF)
        self.assertEqual((code, rules(out)), (1, ["availability-from-lab"]))

    def test_a_lab_measurement_labeled_production_is_still_refused(self):
        doc = copy.deepcopy(self.doc)
        lab = self.dim(doc, "restore")["measured_result"]
        self.dim(doc, "availability")["measured_result"] = dict(lab, value=0.058, kind="production", window_days=30)
        code, out = call("check", "--matrix", self.write(doc), "--root", CF)
        self.assertEqual((code, rules(out)), (1, ["availability-from-lab", "measured-evidence"]))

    def test_a_contract_the_matrix_names_for_itself_is_not_on_record(self):
        doc = copy.deepcopy(self.doc)
        doc["contract"] = "yes"
        self.dim(doc, "availability")["contractual_commitment"] = {"value": "99.99% uptime SLA"}
        code, out = call("check", "--matrix", self.write(doc), "--root", CF)
        self.assertEqual(code, 1)
        self.assertIn("contract-not-on-record", rules(out))

    def test_comparisons_with_named_providers_and_availability_promises_are_refused(self):
        claims = ["Fixture Co restores sites more reliably than Pantheon", "Fixture Co exceeds Acquia and WordPress VIP on recovery",
                  "Fixture Co surpasses Acquia on isolation", "Fixture Co is ahead of all three providers",
                  "Fixture Co out-restores Pantheon", "Fixture Co is more resilient than WordPress VIP"]
        promises = ["Fixture Co offers a 99.99% SLA", "Fixture Co sites stay up 99.99% of the time", "Fixture Co: 99.99% online, every month"]
        for text, rule in [(c, "superiority") for c in claims] + [(p, "availability-from-lab") for p in promises]:
            doc = copy.deepcopy(self.doc)
            doc["statements"] = [{"text": text}]
            code, out = call("check", "--matrix", self.write(doc), "--root", CF)
            self.assertEqual((code, rules(out)), (1, [rule]), text)

    def test_the_json_path_and_target_come_from_the_owner_records(self):
        """Major 6: the matrix chose which evidence field it cited and which target it met."""
        doc = copy.deepcopy(self.doc)
        m = self.dim(doc, "recovery_objectives")["measured_result"]
        m.update(json_path="targets.rpo_lost_writes.target.max", value=0)
        code, out = call("check", "--matrix", self.write(doc), "--root", CF)
        self.assertEqual((code, rules(out), out["statuses"]["recovery_objectives"]), (1, ["measured-evidence"], "evidence-refused"))
        doc = copy.deepcopy(self.doc)
        self.dim(doc, "recovery_objectives")["proposed_target"]["max"] = 5
        code, out = call("check", "--matrix", self.write(doc), "--root", CF)
        self.assertEqual((code, rules(out), out["statuses"]["recovery_objectives"]), (1, ["target-not-on-record"], "unmet"))
        code, out = call("backlog", "--matrix", self.write(doc), "--root", CF)
        self.assertEqual((out["items"][0]["dimension"], out["items"][0]["kind"]), ("recovery_objectives", "close-gap"))
        doc = copy.deepcopy(self.doc)
        self.dim(doc, "cost")["proposed_target"] = {"max": 10, "unit": "USD"}
        self.assertEqual(rules(call("check", "--matrix", self.write(doc), "--root", CF)[1]), ["target-not-on-record"])

    def test_every_phrasing_from_the_re_review_is_refused(self):
        """Major 7: percent spelled out, nines, never-down promises and comparatives outside the old word list."""
        cases = {"Fixture Co sites stay up 99.99 percent of the time": "availability-from-lab",
                 "Fixture Co delivers four nines of uptime": "availability-from-lab",
                 "Fixture Co sites never go down": "availability-from-lab",
                 "Fixture Co offers a 99.99 per cent SLA": "availability-from-lab",
                 "Pantheon trails Fixture Co on recovery": "superiority",
                 "Unlike Acquia, Fixture Co never loses a write": "superiority",
                 "Fixture Co is the most robust WordPress host": "superiority",
                 "Fixture Co wins against WordPress VIP on restores": "superiority",
                 "Fixture Co is the better choice over Pantheon": "superiority",
                 "Fixture Co: the number one host for recovery": "superiority",
                 "Pantheon lags behind Fixture Co": "superiority",
                 "Fixture Co is the #1 host": "superiority",
                 "Fixture Co sites stay up ９９．９９％ of the time": "availability-from-lab",
                 "Fixture Co is the be\u200btter host": "superiority",
                 "P\u0430ntheon trails Fixture Co": "superiority",
                 "Fixture Co outperforms &#80;antheon": "superiority",
                 "Fixture Co is B E T T E R than the rest": "superiority"}
        for text, rule in cases.items():
            doc = copy.deepcopy(self.doc)
            doc["statements"] = [{"text": text}]
            code, out = call("check", "--matrix", self.write(doc), "--root", CF)
            self.assertEqual(code, 1, text)
            self.assertIn(rule, rules(out), text)

    def test_subject_contract_note_claim_summaries_and_sources_are_scanned(self):
        """Minor 4: provider_claims[].claim, subject, contract_note and a source key were not scanned."""
        edits = [lambda d: d.update(subject="Fixture Co beats Acquia, Pantheon and WP VIP"),
                 lambda d: d.update(contract_note="Fixture Co guarantees 99.99% uptime"),
                 lambda d: self.dim(d, "restore")["provider_claims"][0].update(claim="Restores slower than Fixture Co"),
                 lambda d: self.dim(d, "restore")["provider_claims"][0].update(claim="Fixture Co guarantees 99.99% uptime"),
                 lambda d: self.dim(d, "restore").update(configured_capability={"summary": "nightly backups",
                                                                                "source": "Faster than Acquia, Pantheon and WP VIP"})]
        for i, edit in enumerate(edits):
            doc = copy.deepcopy(self.doc)
            edit(doc)
            code, out = call("check", "--matrix", self.write(doc), "--root", CF)
            self.assertEqual(code, 1, i)
            self.assertTrue(set(rules(out)) & {"superiority", "availability-from-lab"}, i)
        self.assertEqual(call("check", "--matrix", MATRIX, "--root", CF)[0], 0, "documented provider percentages stay allowed")

    def test_string_shaped_fields_are_invalid_input_not_a_crash(self):
        for edit in (lambda d: self.dim(d, "restore").update(measured_result="0.058 seconds"),
                     lambda d: d.update(statements=["Fixture Co beats Pantheon"]),
                     lambda d: self.dim(d, "restore").update(provider_claims="see docs"),
                     lambda d: d.update(subject=["x"])):
            doc = copy.deepcopy(self.doc)
            edit(doc)
            code, out = call("check", "--matrix", self.write(doc), "--root", CF)
            self.assertEqual(code, 2)
            self.assertIn("error", out)

    def test_claims_hidden_in_dimension_fields_are_refused(self):
        doc = copy.deepcopy(self.doc)
        self.dim(doc, "restore")["configured_capability"] = {"summary": "Faster restores than Acquia, Pantheon and WP VIP"}
        self.assertEqual(rules(call("check", "--matrix", self.write(doc), "--root", CF)[1]), ["superiority"])
        doc = copy.deepcopy(self.doc)
        self.dim(doc, "availability")["proposed_target"] = {"summary": "Not a hypothesis: 99.99% uptime, guaranteed", "hypothesis": True}
        self.assertEqual(rules(call("check", "--matrix", self.write(doc), "--root", CF)[1]), ["availability-from-lab"])

    def test_evidence_rewritten_with_a_recomputed_hash_is_refused(self):
        root = os.path.join(self.tmp, "root")
        ev = "fleets/hosting/evidence/restore-exercise-2026-11-26.json"
        os.makedirs(os.path.dirname(os.path.join(root, ev)))
        with open(os.path.join(CF, ev), encoding="utf-8") as fh:
            evidence = json.load(fh)
        evidence["measured"]["rpo_lost_writes"] = 0
        with open(os.path.join(root, ev), "w", encoding="utf-8") as fh:
            json.dump(evidence, fh)
        doc = copy.deepcopy(self.doc)
        for d in doc["dimensions"]:
            m = d["measured_result"]
            if m and m["evidence"] == ev:
                m["evidence_sha256"] = hashlib.sha256(open(os.path.join(root, ev), "rb").read()).hexdigest()
            if d["id"] == "recovery_objectives":
                m["value"] = 0
        for other in ("isolation-records", "migration-rollback", "portability-roundtrip"):
            shutil.copy(os.path.join(CF, "fleets/hosting/evidence/%s-2026-11-26.json" % other), os.path.join(root, "fleets/hosting/evidence"))
        code, out = call("check", "--matrix", self.write(doc), "--root", root)
        self.assertEqual(code, 1)
        self.assertEqual(out["statuses"]["recovery_objectives"], "evidence-refused")

    def test_a_non_numeric_window_is_invalid_input(self):
        doc = copy.deepcopy(self.doc)
        self.dim(doc, "availability")["measured_result"] = dict(self.dim(doc, "restore")["measured_result"], window_days="thirty")
        self.assertEqual(call("check", "--matrix", self.write(doc), "--root", CF)[0], 2)

    def test_unknown_dimension_is_exit_2(self):
        doc = copy.deepcopy(self.doc)
        doc["dimensions"].append(dict(self.dim(doc, "cost"), id="vibes"))
        self.assertEqual(call("check", "--matrix", self.write(doc))[0], 2)

    def test_missing_as_of_is_exit_2(self):
        doc = copy.deepcopy(self.doc)
        del doc["as_of"]
        self.assertEqual(call("check", "--matrix", self.write(doc))[0], 2)

    def test_backlog_puts_unmet_first(self):
        code, out = call("backlog", "--matrix", MATRIX, "--root", CF)
        self.assertEqual(code, 0)
        self.assertEqual((out["items"][0]["dimension"], out["items"][0]["kind"]), ("recovery_objectives", "close-gap"))
        self.assertTrue(all(i["kind"] != "close-gap" for i in out["items"][1:]))

    def test_render_has_one_row_per_dimension(self):
        code, text = call("render", "--matrix", MATRIX)
        self.assertEqual(code, 0)
        self.assertEqual(sum(1 for line in text.splitlines() if line.startswith("| ") and "---" not in line), 13)


if __name__ == "__main__":
    unittest.main()
