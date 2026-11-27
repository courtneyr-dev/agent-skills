"""Behavior tests for payment_events.py, run through the CLI the way the fleet runs it."""
import json
import os
import sqlite3
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.normpath(os.path.join(HERE, "..", ".."))
SCRIPT = os.path.join(SKILL, "scripts", "payment_events.py")
FX = os.path.join(SKILL, "fixtures")
CONFIG = os.path.join(FX, "config.json")


def run(*args):
    p = subprocess.run([sys.executable, SCRIPT] + list(args), capture_output=True, text=True)
    return p.returncode, json.loads(p.stdout)


class PaymentEventsTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = os.path.join(self.tmp.name, "store.db")

    def tearDown(self):
        self.tmp.cleanup()

    def process(self, events, db=None):
        return run("process", "--config", CONFIG, "--events", os.path.join(FX, events), "--db", db or self.db)

    def test_replayed_and_retried_events_create_one_capture_and_fulfillment_per_order(self):
        code, out = self.process("replay.jsonl")
        self.assertEqual(code, 0)
        self.assertEqual(out["store"]["captures"], 2)
        self.assertEqual(out["store"]["fulfillments"], 2)
        self.assertEqual(out["store"]["refunds"], 1)
        self.assertEqual(out["inventory"]["forms-pro-annual"], 8)
        self.assertEqual(out["outcomes"]["duplicate-event"], 2)
        self.assertEqual(out["outcomes"]["duplicate-order"], 1)
        self.assertEqual(out["outcomes"]["duplicate-refund"], 1)
        self.assertEqual(out["live_calls"], 0)

    def test_second_full_replay_changes_nothing(self):
        self.process("replay.jsonl")
        code, out = self.process("replay.jsonl")
        self.assertEqual(code, 0)
        self.assertEqual(out["outcomes"], {"duplicate-event": 8})
        self.assertEqual(out["store"]["captures"], 2)
        self.assertEqual(out["inventory"]["forms-pro-annual"], 8)

    def test_refund_revokes_and_cancel_offers_export(self):
        _, out = self.process("replay.jsonl")
        states = {(e["customer_id"], e["state"], e["export_offered"]) for e in out["entitlements"]}
        self.assertIn(("cus_b", "revoked", 0), states)
        self.assertIn(("cus_a", "canceled", 1), states)

    def test_live_tampered_and_foreign_events_are_refused_without_side_effects(self):
        code, out = self.process("refused.jsonl")
        self.assertEqual(code, 1)
        self.assertEqual([e["outcome"] for e in out["events"]],
                         ["refused-live-mode", "refused-bad-signature", "refused-tenant-mismatch"])
        self.assertEqual(out["store"]["captures"], 0)
        self.assertEqual(out["store"]["events"], 0)

    def test_last_unit_race_fulfills_one_order_and_holds_the_other_for_a_human(self):
        code, out = self.process("last-unit.jsonl")
        self.assertEqual(code, 1)
        self.assertEqual(sorted(e["outcome"] for e in out["events"]), ["fulfilled", "needs-human"])
        self.assertEqual(out["inventory"]["forms-pro-founder-edition"], 0)
        rcode, rec = run("reconcile", "--db", self.db)
        self.assertEqual(rcode, 1)
        self.assertEqual(rec["status"], "needs-attention")
        self.assertEqual([h["order_id"] for h in rec["holds_for_human"]], ["ord_3002"])
        self.assertEqual(rec["mismatches"], [])

    def test_two_processes_racing_on_one_store_still_capture_once(self):
        cmd = [sys.executable, SCRIPT, "process", "--config", CONFIG, "--events", os.path.join(FX, "replay.jsonl"), "--db", self.db]
        procs = [subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE) for _ in range(4)]
        for p in procs:
            p.communicate()
            self.assertEqual(p.returncode, 0)
        conn = sqlite3.connect(self.db)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM captures").fetchone()[0], 2)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM fulfillments").fetchone()[0], 2)
        self.assertEqual(conn.execute("SELECT COUNT(*) FROM refunds").fetchone()[0], 1)
        self.assertEqual(conn.execute("SELECT on_hand FROM inventory WHERE sku='forms-pro-annual'").fetchone()[0], 8)
        conn.close()

    def test_resume_after_a_partial_run_converges_to_the_single_run_state(self):
        partial = os.path.join(self.tmp.name, "partial.jsonl")
        with open(os.path.join(FX, "replay.jsonl")) as src, open(partial, "w") as dst:
            dst.writelines(src.readlines()[:4])
        run("process", "--config", CONFIG, "--events", partial, "--db", self.db)
        _, resumed = self.process("replay.jsonl")
        clean_db = os.path.join(self.tmp.name, "clean.db")
        _, single = self.process("replay.jsonl", db=clean_db)
        self.assertEqual(resumed["store"], single["store"])
        self.assertEqual(resumed["inventory"], single["inventory"])
        self.assertEqual(resumed["entitlements"], single["entitlements"])

    def test_reconcile_reports_a_capture_with_no_fulfillment(self):
        self.process("replay.jsonl")
        conn = sqlite3.connect(self.db)
        conn.execute("INSERT INTO captures VALUES ('ord_9999', 100, 'USD', 'evt_manual')")
        conn.commit()
        conn.close()
        code, rec = run("reconcile", "--db", self.db)
        self.assertEqual(code, 1)
        self.assertEqual(rec["mismatches"], [{"code": "capture-without-fulfillment", "order_id": "ord_9999"}])

    # ---- review 2026-11-26, defects 6 and 7 ----
    def signed(self, name, events):
        raw = os.path.join(self.tmp.name, name + ".unsigned.jsonl")
        with open(raw, "w") as fh:
            fh.write("\n".join(json.dumps(e) for e in events) + "\n")
        p = subprocess.run([sys.executable, SCRIPT, "sign", "--config", CONFIG, "--events", raw], capture_output=True, text=True)
        path = os.path.join(self.tmp.name, name + ".jsonl")
        with open(path, "w") as fh:
            fh.write(p.stdout)
        return path

    @staticmethod
    def event(eid, etype, data, created="2026-11-25T10:00:00Z"):
        return {"schema": "payment-event.v1", "id": eid, "type": etype, "livemode": False, "tenant_id": "tenant-fixture-co",
                "created": created, "data": data}

    def checkout(self, eid, order, customer="cus_a", sku="forms-pro-annual", created="2026-11-25T10:00:00Z"):
        return self.event(eid, "checkout.completed", {"order_id": order, "customer_id": customer, "sku": sku, "quantity": 1,
                                                      "amount": 4900, "currency": "USD"}, created)

    def test_refund_hold_then_stockout_does_not_crash_and_reruns_converge(self):
        events = self.signed("p9", [
            self.checkout("e0", "o0", customer="cus_z", sku="forms-pro-founder-edition"),
            self.event("r1", "charge.refunded", {"order_id": "o1", "amount": 4900}),
            self.checkout("e1", "o1", sku="forms-pro-founder-edition"),
            self.checkout("e2", "o2", customer="cus_b")])
        code, out = run("process", "--config", CONFIG, "--events", events, "--db", self.db)
        self.assertEqual(code, 1)
        self.assertEqual([e["outcome"] for e in out["events"]], ["fulfilled", "needs-human", "needs-human", "fulfilled"])
        code, again = run("process", "--config", CONFIG, "--events", events, "--db", self.db)
        self.assertEqual(again["outcomes"], {"duplicate-event": 4})
        _, rec = run("reconcile", "--db", self.db)
        self.assertEqual(sorted(h["order_id"] for h in rec["holds_for_human"]), ["o1", "o1"])

    def test_cancel_that_arrives_before_its_checkout_keeps_the_entitlement_canceled(self):
        events = self.signed("p6", [
            self.event("c1", "subscription.canceled", {"customer_id": "cus_a", "sku": "forms-pro-annual"}, "2026-11-25T10:10:00Z"),
            self.checkout("e1", "o1", created="2026-11-25T10:00:00Z")])
        code, out = run("process", "--config", CONFIG, "--events", events, "--db", self.db)
        self.assertEqual([(e["customer_id"], e["state"]) for e in out["entitlements"]], [("cus_a", "canceled")])

    def test_events_need_a_parseable_created_time(self):
        for created in (None, "yesterday"):
            ev = self.checkout("e1", "o1")
            if created is None:
                del ev["created"]
            else:
                ev["created"] = created
            code, out = run("process", "--config", CONFIG, "--events", self.signed("bad-created", [ev]), "--db", self.db)
            self.assertEqual(code, 2, created)

    def test_invalid_inputs_exit_2(self):
        bad_config = os.path.join(self.tmp.name, "bad-config.json")
        with open(bad_config, "w") as fh:
            json.dump({"schema": "payment-config.v0", "tenant_id": "t", "signing_key": "k", "inventory": {}}, fh)
        for args in (("process", "--config", CONFIG, "--events", os.path.join(FX, "malformed.jsonl"), "--db", self.db),
                     ("process", "--config", bad_config, "--events", os.path.join(FX, "replay.jsonl"), "--db", self.db),
                     ("process", "--config", CONFIG, "--events", os.path.join(FX, "unsigned", "replay.jsonl"), "--db", self.db)):
            code, out = run(*args)
            self.assertEqual(code, 2, args)
            self.assertIn("error", out)
        self.assertFalse(os.path.exists(self.db))


if __name__ == "__main__":
    unittest.main()
