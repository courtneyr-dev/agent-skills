"""The owner path: owner values come only from the hash-chained owner log of the instance the work names,
written under the lease holder's token, at one fixed place per instance."""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

from support import FIXTURES, isolate_owner_root

from factory_rig.canon import sha_file
from factory_rig.contract import contract_hash
from factory_rig.lease import LeaseStore
from fleetlib import cli, ownerlog
from fleetlib.handoff import apply_worker_update, open_handoff
from fleetlib.ownership import claim, lease_identity
from fleetlib.registry import Registry

OUT, EV, INPUT = "out/accessibility-findings.md", "evidence/review.txt", "in/client-a/brief.md"
LABEL = {"tenant_id": "tenant-a", "classification": "confidential", "trust": "untrusted", "source_kind": "client-file"}
COORD = "agency.engagement-director"


def load(rel):
    with open(os.path.join(FIXTURES, rel)) as fh:
        return json.load(fh)


def fleet(*argv, stdin=""):
    """bin/fleet in this process, so the test's owner root applies. Returns (exit, parsed stdout)."""
    out, old = io.StringIO(), sys.stdin
    sys.stdin = io.StringIO(stdin)
    try:
        with contextlib.redirect_stdout(out):
            code = cli.main(list(argv))
    finally:
        sys.stdin = old
    return code, json.loads(out.getvalue())


class OwnerPath(unittest.TestCase):
    def setUp(self):
        isolate_owner_root(self)
        self.tmp = tempfile.mkdtemp(prefix="ownerlog-")
        self.addCleanup(shutil.rmtree, self.tmp)
        self.ws = os.path.join(self.tmp, "ws")
        shutil.copytree(os.path.join(FIXTURES, "handoff", "workspace"), self.ws)
        for folder, text in (("in/client-a", "Client A brief\n"), ("in/client-b", "Client B confidential brief\n")):
            os.makedirs(os.path.join(self.ws, folder))
            with open(os.path.join(self.ws, folder, "brief.md"), "w") as fh:
                fh.write(text)
        self.contract, self.owner = load("handoff/contract.json"), load("handoff/owner.json")
        self.ident = ("tenant-a", self.owner["workload_id"], self.contract["task_id"])
        self.root = ownerlog.owner_dir("agency", self.contract["task_id"])
        self.lease = ownerlog.open_ledger(self.root, Registry(), *self.ident, COORD, os.getpid(), contract_hash(self.contract), exclusive=True)

    def record(self, kind, rec, lease=None, token=None):
        lease = lease or self.lease
        return ownerlog.append(self.root, kind, rec, *self.ident, lease["epoch"], lease["token"] if token is None else token, base=self.ws)

    def opened(self, inputs=((INPUT, LABEL),)):
        self.record("open", {k: v for k, v in self.owner.items() if k != "contract_hash"})
        self.record("intake", {"handoff_id": self.owner["handoff_id"], "inputs": [dict(lbl, path=p) for p, lbl in inputs]})

    def submission(self, inputs=((INPUT, LABEL),)):
        osha = sha_file(os.path.join(self.ws, OUT))
        h, _ = apply_worker_update(open_handoff(dict(self.owner, contract_hash=contract_hash(self.contract))), {
            "inputs": [dict(lbl, ref=p, sha256=sha_file(os.path.join(self.ws, p))) for p, lbl in inputs],
            "outputs": [{"path": OUT, "sha256": osha, "artifact_type": "defect-list"}],
            "evidence": [{"path": EV, "sha256": sha_file(os.path.join(self.ws, EV)), "about": OUT, "about_sha256": osha,
                          "contract_hash": contract_hash(self.contract)}]})
        return h

    def check(self, h, contract=None):
        return ownerlog.check_submission(h, contract or self.contract, self.ws)

    def lines(self):
        with open(os.path.join(self.root, ownerlog.LOG)) as fh:
            return fh.read().splitlines()

    def write_lines(self, lines):
        with open(os.path.join(self.root, ownerlog.LOG), "w") as fh:
            fh.write("".join(l + "\n" for l in lines))

    def test_owner_recorded_handoff_passes_the_consumer_gate(self):
        self.opened()
        self.assertEqual(self.check(self.submission()), [])

    def test_the_epoch_alone_cannot_write_without_the_claim_token(self):
        for token in ("", "1", "0" * 32):
            with self.subTest(token=token):
                with self.assertRaises(ownerlog.OwnerLogError) as cm:
                    self.record("roster", {"humans": ["human:delivery-owner"]}, token=token)
                self.assertEqual(cm.exception.reason, "not-the-lease-holder")

    def test_a_closed_ledger_takes_no_record_and_no_claim(self):
        self.opened()
        ownerlog.close_ledger(self.root, *self.ident, self.lease["epoch"], self.lease["token"], "done")
        with self.assertRaises(ownerlog.OwnerLogError) as cm:
            self.record("roster", {"humans": ["human:delivery-owner"]})
        self.assertEqual(cm.exception.reason, "stale-epoch")
        for exclusive, reason in ((True, "ledger-exists"), (False, "ledger-closed")):
            with self.subTest(exclusive=exclusive), self.assertRaises(ownerlog.OwnerLogError) as cm:
                ownerlog.open_ledger(self.root, Registry(), *self.ident, COORD, os.getpid(), contract_hash(self.contract), exclusive=exclusive)
            self.assertEqual(cm.exception.reason, reason)
        # A lease taken on the ledger's own store by other means gets epoch 2, but the closed log refuses the record.
        newer = claim(LeaseStore(os.path.join(self.root, "leases")), Registry(), *self.ident, COORD, os.getpid(), contract_hash(self.contract))
        with self.assertRaises(ownerlog.OwnerLogError) as cm:
            self.record("roster", {"humans": ["human:me"]}, lease=newer)
        self.assertEqual(cm.exception.reason, "ledger-closed")
        self.assertEqual(self.check(self.submission()), [])

    def test_a_takeover_after_expiry_cannot_write_without_a_transition_in_the_log(self):
        """The reviewer's D8: the holder's lease expires with its process gone and someone claims the lease again."""
        dead = subprocess.Popen(["true"])
        dead.wait()
        root = ownerlog.owner_dir("agency", "EXPIRY-1")
        first = ownerlog.open_ledger(root, Registry(), "tenant-a", self.owner["workload_id"], "EXPIRY-1", COORD, dead.pid, "c", exclusive=True, ttl=0.01)
        store = LeaseStore(os.path.join(root, "leases"))
        time.sleep(0.05)
        taker = claim(store, Registry(), "tenant-a", self.owner["workload_id"], "EXPIRY-1", COORD, os.getpid(), "c")
        self.assertEqual(taker["epoch"], first["epoch"] + 1)
        with self.assertRaises(ownerlog.OwnerLogError) as cm:
            ownerlog.append(root, "roster", {"humans": ["human:me"]}, "tenant-a", self.owner["workload_id"], "EXPIRY-1", taker["epoch"], taker["token"])
        self.assertEqual(cm.exception.reason, "epoch-without-transition")
        code, out = fleet("claim", "--tenant", "tenant-a", "--workload", self.owner["workload_id"], "--instance", "EXPIRY-1", "--role", COORD,
                          "--owner-pid", str(os.getpid()), "--contract-hash", "c")
        self.assertEqual((code, out["refused"]), (1, "ledger-exists"))

    def test_submitter_added_input_is_refused_by_the_consumer(self):
        self.opened()
        h = self.submission(((INPUT, LABEL), ("in/client-b/brief.md", LABEL)))
        self.assertIn("input in/client-b/brief.md is not in the owner's intake record", self.check(h))

    def test_submitter_relabel_is_refused_by_the_consumer(self):
        self.opened()
        h = self.submission(((INPUT, dict(LABEL, classification="public", trust="trusted")),))
        self.assertTrue(any("classification, trust" in e for e in self.check(h)))

    def test_symlink_to_another_tenant_folder_is_refused_at_intake_and_at_the_gate(self):
        link = os.path.join(self.ws, "in/client-a/linked.md")
        os.symlink("../client-b/brief.md", link)
        with self.assertRaises(ownerlog.OwnerLogError) as cm:
            self.opened(((INPUT, LABEL), ("in/client-a/linked.md", LABEL)))
        self.assertEqual(cm.exception.reason, "input-symlink-leaves-folder")
        os.remove(link)
        self.record("intake", {"handoff_id": self.owner["handoff_id"], "inputs": [dict(LABEL, path=INPUT)]})
        os.remove(os.path.join(self.ws, INPUT))
        os.symlink("../client-b/brief.md", os.path.join(self.ws, INPUT))
        self.assertTrue(any("input-symlink-leaves-folder" in e for e in self.check(self.submission())))

    def test_input_edited_after_intake_is_refused(self):
        self.opened()
        h = self.submission()
        with open(os.path.join(self.ws, INPUT), "a") as fh:
            fh.write("Client B text pasted in later\n")
        self.assertIn("input %s changed after the owner's intake recorded it" % INPUT, self.check(h))

    def test_intake_is_write_once(self):
        self.opened()
        with self.assertRaises(ownerlog.OwnerLogError) as cm:
            self.record("intake", {"handoff_id": self.owner["handoff_id"], "inputs": [dict(LABEL, path="in/client-b/brief.md")]})
        self.assertEqual(cm.exception.reason, "intake-conflict")
        self.assertEqual(self.record("intake", {"handoff_id": self.owner["handoff_id"], "inputs": [dict(LABEL, path=INPUT)]})[0], "duplicate")

    def test_a_handoff_for_another_tenant_or_workload_cannot_be_opened_here(self):
        for field, value, reason in (("tenant_id", "tenant-b", "tenant-mismatch"), ("workload_id", "agency.workload.cms-migration", "workload-mismatch")):
            rec = dict({k: v for k, v in self.owner.items() if k != "contract_hash"}, **{field: value})
            if field == "tenant_id":
                rec["data"] = dict(rec["data"], allowed_destinations=["tenant:tenant-b"])
            with self.subTest(field), self.assertRaises(ownerlog.OwnerLogError) as cm:
                self.record("open", rec)
            self.assertEqual(cm.exception.reason, reason)

    def test_the_consumer_reads_only_the_ledger_of_the_contract_and_handoff_it_judges(self):
        self.opened()
        h = self.submission()
        other = dict(self.contract, title="another engagement's contract")
        self.assertTrue(self.check(h, other)[0].startswith("ledger-not-for-this-work"), self.check(h, other))
        moved = dict(self.contract, task_id="FIX-A11Y-2")
        self.assertTrue(self.check(dict(h, contract_hash=contract_hash(moved)), moved)[0].startswith("owner-log-missing"))
        self.assertTrue(self.check(dict(h, tenant_id="tenant-b"))[0].startswith("ledger-not-for-this-work"))

    def test_edited_deleted_or_forged_entries_break_the_log(self):
        self.opened()
        good = self.lines()
        e = json.loads(good[2])
        e["body"]["inputs"].append(dict(LABEL, path="in/client-b/brief.md", sha256="0" * 64))
        cases = {"edited": good[:2] + [json.dumps(e)], "deleted": [good[0], good[2]], "reordered": [good[1], good[0], good[2]]}
        for name, body in cases.items():
            with self.subTest(name):
                self.write_lines(body)
                self.assertTrue(self.check(self.submission())[0].startswith("owner-log-broken"), self.check(self.submission()))
        forged = dict(e, seq=4, prev=json.loads(good[2])["hash"], lease=dict(e["lease"], epoch=7))
        forged["hash"] = ownerlog._entry_hash(forged)
        self.write_lines(good + [json.dumps(forged)])
        with open(os.path.join(self.root, ownerlog.HEAD), "w") as fh:
            json.dump({"count": 4, "hash": forged["hash"]}, fh)
        self.assertTrue(self.check(self.submission())[0].startswith("owner-entry-without-lease"))

    def test_a_dropped_tail_or_a_substituted_log_is_detected_by_the_head(self):
        """The reviewer's F1 and F13: remove the owner's last entry, or swap in another ledger's log."""
        self.opened()
        good = self.lines()
        self.write_lines(good[:-1])
        self.assertTrue(self.check(self.submission())[0].startswith("owner-log-truncated"))
        self.write_lines(good)
        self.assertEqual(self.check(self.submission()), [])
        other = ownerlog.owner_dir("agency", "OTHER-1")
        ownerlog.open_ledger(other, Registry(), *self.ident[:2], "OTHER-1", COORD, os.getpid(), contract_hash(self.contract), exclusive=True)
        shutil.copy(os.path.join(other, ownerlog.LOG), os.path.join(self.root, ownerlog.LOG))
        self.assertIn(self.check(self.submission())[0].split(":")[0], ("owner-log-truncated", "owner-log-broken"))

    def test_non_utf8_bytes_in_the_log_are_refused_by_name(self):
        self.opened()
        with open(os.path.join(self.root, ownerlog.LOG), "ab") as fh:
            fh.write(b"\xff\xfe\n")
        self.assertTrue(self.check(self.submission())[0].startswith("owner-log-broken"))

    def test_unopened_handoff_fails_closed(self):
        self.record("roster", {"humans": ["human:delivery-owner"]})
        self.assertTrue(self.check(self.submission())[0].startswith("handoff-not-opened"))


class Cli(unittest.TestCase):
    """The reviewer's CLI-only attacks: no file writes, only fleet commands."""

    def setUp(self):
        isolate_owner_root(self)
        self.tmp = tempfile.mkdtemp(prefix="ownercli-")
        self.addCleanup(shutil.rmtree, self.tmp)
        self.ws = os.path.join(self.tmp, "ws")
        shutil.copytree(os.path.join(FIXTURES, "handoff", "workspace"), self.ws)
        self.contract, self.owner = load("handoff/contract.json"), load("handoff/owner.json")
        self.cpath = os.path.join(FIXTURES, "handoff", "contract.json")
        self.lease_args = ["--tenant", "tenant-a", "--workload", self.owner["workload_id"], "--instance", self.contract["task_id"]]

    def claim(self, *extra):
        return fleet("claim", *(self.lease_args + ["--role", COORD, "--owner-pid", str(os.getpid()), "--contract-hash", contract_hash(self.contract)] + list(extra)))

    def record(self, kind, rec, token, epoch=1):
        path = os.path.join(self.tmp, "%s.json" % kind)
        with open(path, "w") as fh:
            json.dump(rec, fh)
        return fleet("owner-record", *(self.lease_args + ["--epoch", str(epoch), "--kind", kind, "--record", path, "--base", self.ws]), stdin=token + "\n")

    def test_owner_record_and_handoff_check_through_the_cli(self):
        code, out = self.claim()
        self.assertEqual(code, 0)
        token = out["lease"]["token"]
        self.assertEqual(out["ledger"], ownerlog.owner_dir("agency", self.contract["task_id"]))
        opened = {k: v for k, v in self.owner.items() if k != "contract_hash"}
        self.assertEqual(self.record("open", opened, "not-the-token")[0], 1)
        self.assertEqual(self.record("open", opened, token)[0], 0)
        osha = sha_file(os.path.join(self.ws, OUT))
        h, _ = apply_worker_update(open_handoff(self.owner), {
            "outputs": [{"path": OUT, "sha256": osha, "artifact_type": "defect-list"}],
            "evidence": [{"path": EV, "sha256": sha_file(os.path.join(self.ws, EV)), "about": OUT, "about_sha256": osha,
                          "contract_hash": self.owner["contract_hash"]}]})
        hp = os.path.join(self.tmp, "handoff.json")
        check = ["handoff-check", "--handoff", hp, "--contract", self.cpath, "--base", self.ws]
        with open(hp, "w") as fh:
            json.dump(h, fh)
        self.assertEqual(fleet(*check)[0], 0)
        with open(hp, "w") as fh:
            json.dump(dict(h, data=dict(h["data"], classification="public")), fh)
        code, out = fleet(*check)
        self.assertEqual(code, 1)
        self.assertIn("protected field data differs", " ".join(out["errors"]))
        with open(hp, "w") as fh:
            json.dump(h, fh)
        with open(os.path.join(self.ws, OUT), "a") as fh:
            fh.write("late edit\n")
        code, out = fleet(*check)
        self.assertEqual(code, 1)
        self.assertIn("changed after the handoff recorded it", " ".join(out["errors"]))
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as cm:
                cli.main(check + ["--ledger", os.path.join(self.tmp, "minted")])
        self.assertEqual(cm.exception.code, 2, "no flag picks the ledger")

    def test_a_second_ledger_for_a_claimed_instance_cannot_be_minted(self):
        """The reviewer's E3: a submitter runs fleet claim for the owner's instance."""
        self.assertEqual(self.claim()[0], 0)
        code, out = self.claim()
        self.assertEqual((code, out["refused"]), (1, "ledger-exists"))

    def test_release_closes_the_ledger_and_a_copy_cannot_be_claimed(self):
        """The reviewer's D9-D17: a released ledger, or a copy of it, re-claimed at epoch 2."""
        code, out = self.claim()
        token, root = out["lease"]["token"], out["ledger"]
        self.assertEqual(self.record("roster", {"humans": ["human:delivery-owner"]}, token)[0], 0)
        self.assertEqual(fleet("release", *(self.lease_args + ["--epoch", "1"]), stdin="wrong\n")[1]["refused"], "not-the-lease-holder")
        self.assertEqual(fleet("release", *(self.lease_args + ["--epoch", "1"]), stdin=token + "\n")[0], 0)
        self.assertEqual(ownerlog.state(ownerlog.read(root))["closed"], True)
        copy = os.path.join(self.tmp, "copy")
        shutil.copytree(root, copy)
        self.assertEqual(self.claim()[1]["refused"], "ledger-exists")
        for store in (os.path.join(copy, "leases"), os.path.join(root, "leases")):
            with self.subTest(store=store):
                self.assertEqual(self.claim("--lease-root", store), (1, {"refused": "owner-ledger-lease-store", "detail": self.claim("--lease-root", store)[1]["detail"]}))

    def test_non_utf8_record_file_is_refused_by_name(self):
        code, out = self.claim()
        path = os.path.join(self.tmp, "bad.json")
        with open(path, "wb") as fh:
            fh.write(b'{"humans": ["human:\xff"]}')
        code, out = fleet("owner-record", *(self.lease_args + ["--epoch", "1", "--kind", "roster", "--record", path]), stdin=out["lease"]["token"] + "\n")
        self.assertEqual((code, out["refused"]), (1, "input-not-utf8"))

    def test_a_plain_lease_claim_keeps_working(self):
        leases = os.path.join(self.tmp, "leases")
        code, out = self.claim("--lease-root", leases)
        self.assertEqual((code, out["lease"]["epoch"]), (0, 1))
        self.assertEqual(self.claim("--lease-root", leases)[0], 1)
        self.assertFalse(os.path.exists(ownerlog.owner_dir("agency", self.contract["task_id"])))
        repo, task = lease_identity("tenant-a", self.owner["workload_id"], self.contract["task_id"])
        self.assertEqual(LeaseStore(leases).status(repo, task)["state"], "active")


if __name__ == "__main__":
    unittest.main()
