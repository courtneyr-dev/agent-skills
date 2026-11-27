"""Behavior tests for restore_exercise.py: real local processes, real failures, measured results."""
from __future__ import annotations

import contextlib
import hashlib
import io
import json
import os
import shutil
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))

import restore_exercise as rx  # noqa: E402

FIX = os.path.normpath(os.path.join(HERE, "..", "..", "..", "company-fleets", "fleets", "hosting", "fixtures",
                                    "restore-exercise"))


def fx(name):
    return os.path.join(FIX, name)


def call(*argv):
    out = io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
        try:
            code = rx.main(list(argv))
        except SystemExit as exc:
            code = exc.code
    return code, json.loads(out.getvalue())


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="rx-test-")
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def write(self, name, doc):
        path = os.path.join(self.tmp, name)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(doc, fh)
        return path


class ExerciseTests(Base):
    def test_unmet_rpo_stays_unmet(self):
        code, rep = call("run", "--targets", fx("targets-proposed.json"))
        self.assertEqual(code, 1)
        self.assertEqual(rep["verdict"], "restored-targets-not-all-met")
        self.assertTrue(rep["measured"]["restore_success"])
        self.assertEqual(rep["measured"]["rpo_lost_writes"], 3)
        self.assertEqual(rep["targets"]["rpo_lost_writes"]["status"], "unmet")
        self.assertEqual(rep["unmet"], ["rpo_lost_writes"])

    def test_all_targets_met_with_relaxed_rpo(self):
        code, rep = call("run", "--targets", fx("targets-relaxed-rpo.json"))
        self.assertEqual((code, rep["verdict"]), (0, "restored-all-targets-met"))
        self.assertEqual(rep["restore"]["content_sha256"], rep["backup"]["content_sha256"])

    def test_zero_writes_after_backup_loses_nothing(self):
        code, rep = call("run", "--targets", fx("targets-proposed.json"), "--writes-after-backup", "0")
        self.assertEqual((code, rep["measured"]["rpo_lost_writes"]), (0, 0))

    def test_each_failure_kind_is_detected_with_its_reason(self):
        reasons = {}
        for kind in ("crash", "corrupt", "delete"):
            code, rep = call("run", "--targets", fx("targets-relaxed-rpo.json"), "--failure", kind)
            self.assertEqual(code, 0, kind)
            reasons[kind] = next(e["reason"] for e in rep["timeline"] if e["event"] == "monitor-detected")
        self.assertIn("unreachable", reasons["crash"])
        self.assertIn("HTTP 500", reasons["corrupt"])
        self.assertIn("HTTP 500", reasons["delete"])

    def test_failover_and_failback(self):
        code, rep = call("run", "--targets", fx("targets-failover.json"), "--mode", "failover")
        self.assertEqual(code, 0)
        self.assertTrue(rep["measured"]["failback_success"])
        events = [e["event"] for e in rep["timeline"]]
        self.assertLess(events.index("router-switched-to-standby"), events.index("failed-back-to-rebuilt-primary"))

    def test_target_the_mode_cannot_measure_is_not_met(self):
        code, rep = call("run", "--targets", fx("targets-failover.json"), "--mode", "restore")
        self.assertEqual(code, 1)
        self.assertEqual(rep["targets"]["failback_success"]["status"], "not-measured")

    def test_no_lab_process_survives(self):
        code, rep = call("run", "--targets", fx("targets-relaxed-rpo.json"))
        urls = [e["url"] for e in rep["timeline"] if "url" in e]
        self.assertTrue(urls)
        for url in urls:
            self.assertFalse(rx.probe(url + "/health", 0.5)["healthy"])

    def test_report_states_it_is_one_lab_run(self):
        _, rep = call("run", "--targets", fx("targets-relaxed-rpo.json"))
        self.assertTrue(any("not an availability percentage" in a for a in rep["assumptions"]))


class InvalidInputTests(Base):
    def test_unknown_target_is_exit_2(self):
        code, out = call("run", "--targets", fx("targets-invalid.json"))
        self.assertEqual(code, 2)
        self.assertIn("unknown target", out["error"])

    def test_boolean_max_is_exit_2(self):
        path = self.write("t.json", {"targets": {"rto_seconds": {"max": True}}})
        self.assertEqual(call("run", "--targets", path)[0], 2)

    def test_required_false_is_exit_2(self):
        path = self.write("t.json", {"targets": {"restore_success": {"required": False}}})
        self.assertEqual(call("run", "--targets", path)[0], 2)

    def test_missing_targets_file_is_exit_2(self):
        self.assertEqual(call("run", "--targets", os.path.join(self.tmp, "nope.json"))[0], 2)

    def test_non_empty_workdir_is_exit_2(self):
        os.makedirs(os.path.join(self.tmp, "w", "lab"))
        open(os.path.join(self.tmp, "w", "lab", "x"), "w").close()
        self.assertEqual(call("run", "--targets", fx("targets-relaxed-rpo.json"), "--workdir",
                              os.path.join(self.tmp, "w"))[0], 2)

    def test_negative_seed_rows_is_exit_2(self):
        self.assertEqual(call("run", "--targets", fx("targets-relaxed-rpo.json"), "--seed-rows", "0")[0], 2)


class MonitorTests(Base):
    def test_dead_port_is_unhealthy(self):
        code, out = call("monitor", "--url", "http://127.0.0.1:9/health", "--timeout", "0.5")
        self.assertEqual(code, 1)
        self.assertIn("unreachable", out["reason"])

    def test_unreadable_router_is_exit_2(self):
        self.assertEqual(call("monitor", "--router", os.path.join(self.tmp, "nope.json"))[0], 2)

    def test_only_loopback_http_is_monitored(self):
        for url in ("file:///etc/hosts", "http://example.com/health", "https://127.0.0.1/health"):
            code, out = call("monitor", "--url", url)
            self.assertEqual(code, 2, url)
            self.assertIn("loopback", out["error"].replace("127.0.0.1, localhost or ::1", "loopback"))


class EvidenceGateTests(Base):
    def handoff(self, targets="targets-proposed.json", owner="handoff-owner.json", reviewed=True):
        """The producer runs, then the reviewer reviews in a separate command."""
        folder = os.path.join(self.tmp, "handoff-" + targets)
        call("run", "--targets", fx(targets), "--handoff-dir", folder, "--workdir", os.path.join(self.tmp, "lab-" + targets))
        if reviewed:
            self.assertEqual(call("review", "--handoff-dir", folder, "--targets", fx(targets))[0], 0)
        return folder

    def gate(self, folder, targets="targets-proposed.json", *flags):
        return call("evidence-gate", "--handoff-dir", folder, "--targets", fx(targets), *flags,
                    "--workdir", os.path.join(self.tmp, "gate-%d" % len(os.listdir(self.tmp))))

    def owner_edits(self, name, doc):
        """The owner rewrites one of its own files: repoint the module's fixed path to the edited copy."""
        attr = {"contract.json": "CONTRACT", "handoff-owner.json": "OWNER_RECORD"}[name]
        self.addCleanup(setattr, rx, attr, getattr(rx, attr))
        setattr(rx, attr, self.write("owner-" + name, doc))

    def test_fresh_evidence_passes_and_every_stale_case_fails(self):
        code, out = self.gate(self.handoff())
        self.assertEqual((code, out["verdict"]), (0, "stale-evidence-rejected"))
        self.assertTrue(out["fresh"]["accepted"])
        self.assertEqual(out["unmet"], ["rpo_lost_writes"])
        self.assertTrue(out["review"]["statuses_match"])
        self.assertTrue(out["review"]["monitor_saw_fault_then_recovery"])
        self.assertEqual(sorted(out["stale_cases"]), ["contract-relaxed-after-review", "monitor-log-edited",
                                                      "report-edited", "review-check-edited"])
        self.assertIn("file was edited", " ".join(out["stale_cases"]["review-check-edited"]["errors"]))
        for name, case in out["stale_cases"].items():
            self.assertFalse(case["accepted"], name)
        self.assertIn("changed after the handoff recorded it", " ".join(out["stale_cases"]["report-edited"]["errors"]))
        self.assertIn("bound to contract", " ".join(out["stale_cases"]["contract-relaxed-after-review"]["errors"]))

    def test_producer_is_not_the_acceptor(self):
        _, out = self.gate(self.handoff())
        self.assertNotEqual(out["handoff"]["producer"], out["handoff"]["acceptance_owner"])
        self.assertNotEqual(out["handoff"]["producer"], out["handoff"]["reviewer"])

    def test_relaxed_targets_are_not_the_contract_spec(self):
        code, out = self.gate(self.handoff(), targets="targets-relaxed-rpo.json")
        self.assertEqual((code, out["verdict"], out["refusal"]), (1, "refused", "targets-not-in-contract"))

    def test_an_all_met_run_still_rejects_an_edited_report(self):
        contract = json.load(open(fx("contract.json")))
        contract["spec"]["sha256"] = hashlib.sha256(open(fx("targets-relaxed-rpo.json"), "rb").read()).hexdigest()
        self.owner_edits("contract.json", contract)
        code, out = self.gate(self.handoff("targets-relaxed-rpo.json"), "targets-relaxed-rpo.json")
        self.assertEqual((code, out["verdict"], out["unmet"]), (0, "stale-evidence-rejected", []))
        self.assertFalse(out["stale_cases"]["report-edited"]["accepted"])

    def test_a_caller_contract_or_owner_record_is_refused(self):
        """Major 1: --contract replaced the owner's contract and its hash, so relaxed targets passed as met."""
        mine = json.load(open(fx("contract.json")))
        mine["spec"]["sha256"] = hashlib.sha256(open(fx("targets-relaxed-rpo.json"), "rb").read()).hexdigest()
        folder = self.handoff("targets-relaxed-rpo.json")
        code, out = self.gate(folder, "targets-relaxed-rpo.json", "--contract", self.write("contract-mine.json", mine))
        self.assertEqual((code, out["refusal"]), (1, "contract-not-owner-file"))
        code, out = self.gate(folder, "targets-relaxed-rpo.json")
        self.assertEqual((code, out["refusal"]), (1, "targets-not-in-contract"))
        owner = json.load(open(fx("handoff-owner.json")))
        owner["reviewer"] = "human:someone-else"
        code, out = self.gate(folder, "targets-relaxed-rpo.json", "--owner", self.write("owner-mine.json", owner))
        self.assertEqual((code, out["refusal"]), (1, "owner-record-not-owner-file"))
        code, out = call("review", "--handoff-dir", folder, "--targets", fx("targets-relaxed-rpo.json"), "--owner",
                         self.write("owner-mine2.json", owner))
        self.assertEqual((code, out["refusal"]), (1, "owner-record-not-owner-file"))
        code, out = self.gate(self.handoff(), "targets-proposed.json", "--contract", fx("contract.json"), "--owner", fx("handoff-owner.json"))
        self.assertEqual((code, out["verdict"]), (0, "stale-evidence-rejected"), "naming the owner's own files is allowed")

    def test_a_reused_gate_workdir_and_a_non_utf8_monitor_log_exit_2(self):
        folder = self.handoff()
        workdir = os.path.join(self.tmp, "reused")
        os.makedirs(os.path.join(workdir, "handoff"))
        code, out = call("evidence-gate", "--handoff-dir", folder, "--targets", fx("targets-proposed.json"), "--workdir", workdir)
        self.assertEqual(code, 2)
        self.assertIn("must be absent or empty", out["error"])
        with open(os.path.join(folder, "monitor-log.jsonl"), "ab") as fh:
            fh.write(b"\xff\xfe\n")
        code, out = call("review", "--handoff-dir", folder, "--targets", fx("targets-proposed.json"))
        self.assertEqual(code, 2)
        self.assertIn("not UTF-8", out["error"])

    def test_the_review_is_a_separate_step_and_never_the_producers(self):
        folder = self.handoff(reviewed=False)
        code, out = self.gate(folder)
        self.assertEqual((code, out["refusal"]), (1, "handoff-incomplete"))
        owner = json.load(open(fx("handoff-owner.json")))
        owner["reviewer"] = owner["producer"]
        self.owner_edits("handoff-owner.json", owner)
        code, out = call("review", "--handoff-dir", folder, "--targets", fx("targets-proposed.json"))
        self.assertEqual((code, out["refusal"]), (1, "self-review"))
        self.assertFalse(os.path.exists(os.path.join(folder, "review-check.txt")))


if __name__ == "__main__":
    unittest.main()
