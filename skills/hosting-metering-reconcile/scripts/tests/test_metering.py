"""Behavior tests for metering.py: exit codes and JSON fields a caller sees."""
import datetime
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from decimal import Decimal

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.normpath(os.path.join(HERE, "..", "metering.py"))
SKILLS = os.path.normpath(os.path.join(HERE, "..", "..", ".."))
FIX = os.path.join(SKILLS, "company-fleets", "fleets", "hosting", "fixtures", "metering")
sys.path.insert(0, os.path.join(SKILLS, "company-fleets", "fleets", "hosting", "tools"))
import mirror  # noqa: E402


def run(*args, script=SCRIPT):
    proc = subprocess.run([sys.executable, "-W", "ignore", script] + [str(a) for a in args],
                          capture_output=True, text=True)
    try:
        doc = json.loads(proc.stdout)
    except ValueError:
        doc = None
    return proc.returncode, doc


def fx(name):
    return os.path.join(FIX, name)


class Workdir(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp(prefix="metering-test-")
        self.addCleanup(shutil.rmtree, self.dir, True)

    def json_file(self, name, obj):
        path = os.path.join(self.dir, name)
        with open(path, "w") as fh:
            json.dump(obj, fh)
        return path

    def events(self, rows, name="events.jsonl"):
        path = os.path.join(self.dir, name)
        with open(path, "w") as fh:
            fh.write("\n".join(json.dumps(r) for r in rows) + "\n")
        return path


def ev(event_id, tenant, meter, quantity):
    return {"event_id": event_id, "tenant_id": tenant, "meter": meter, "quantity": quantity}


class Usage(Workdir):
    def quota(self, limit, published="same", visible=True, unit="GB"):
        row = {"tenant_id": "tenant-a", "meter": "bandwidth_gb", "limit": limit,
               "unit": unit, "customer_visible": visible, "published_limit": limit if published == "same" else published}
        return self.json_file("q.json", {"quotas": [row]})

    def status(self, used, limit=100, **kw):
        code, out = run("usage", "--events", self.events([ev("e1", "tenant-a", "bandwidth_gb", used)]), "--quotas", self.quota(limit, **kw))
        return code, out

    def test_duplicate_event_counts_once_and_is_listed(self):
        code, out = run("usage", "--events", fx("usage-events.jsonl"), "--quotas", fx("quotas.json"))
        self.assertEqual(out["totals"]["tenant-a"]["bandwidth_gb"], "250.5")
        self.assertEqual([d["event_id"] for d in out["duplicates"]], ["evt-a-003"])
        self.assertTrue(out["duplicates"][0]["identical"])

    def test_shipped_quotas_cover_ok_warn_over_and_flag_the_unpublished_one(self):
        code, out = run("usage", "--events", fx("usage-events.jsonl"), "--quotas", fx("quotas.json"))
        got = {(q["tenant_id"], q["meter"]): q["status"] for q in out["quotas"]}
        self.assertEqual(got, {("tenant-a", "bandwidth_gb"): "warn", ("tenant-a", "storage_gb"): "ok",
                               ("tenant-b", "bandwidth_gb"): "over", ("tenant-b", "storage_gb"): "ok"})
        self.assertEqual(code, 1)
        self.assertEqual(out["violations"], [{"tenant_id": "tenant-b", "meter": "storage_gb", "reasons": ["missing-published-value"]}])

    def test_quota_thresholds(self):
        for used, expected in (("79.99", "ok"), ("80", "warn"), ("100", "warn"), ("100.01", "over")):
            code, out = self.status(used)
            self.assertEqual(out["quotas"][0]["status"], expected, used)
            self.assertEqual(code, 0)

    def test_quota_publication_rules(self):
        for kwargs, reason in (({"visible": False}, "not-customer-visible"), ({"published": None}, "missing-published-value"),
                               ({"published": 90}, "published-differs-from-enforced"), ({"unit": ""}, "missing-unit")):
            code, out = self.status("10", **kwargs)
            self.assertEqual(code, 1, kwargs)
            self.assertIn(reason, out["violations"][0]["reasons"])

    def test_duplicate_quota_rows_refuse_the_file(self):
        row = {"tenant_id": "tenant-a", "meter": "bandwidth_gb", "limit": 300, "unit": "GB", "customer_visible": True, "published_limit": 300}
        quotas = self.json_file("dup.json", {"quotas": [row, dict(row, limit=100000, published_limit=100000)]})
        self.assertEqual(run("usage", "--events", fx("usage-events.jsonl"), "--quotas", quotas)[0], 2)

    def test_conflicting_duplicate_fails_and_first_value_counts(self):
        rows = [ev("e1", "tenant-a", "bandwidth_gb", 10), ev("e1", "tenant-a", "bandwidth_gb", 99)]
        code, out = run("usage", "--events", self.events(rows), "--quotas", self.quota(100))
        self.assertEqual(code, 1)
        self.assertEqual(out["totals"]["tenant-a"]["bandwidth_gb"], "10")
        self.assertFalse(out["duplicates"][0]["identical"])

    def test_invalid_input_exits_2(self):
        good = self.events([ev("e1", "tenant-a", "bandwidth_gb", 1)])
        for rows in ([ev("e1", "tenant-a", "bandwidth_gb", -1)], [ev("", "tenant-a", "bandwidth_gb", 1)],
                     [ev("e1", "Tenant A", "bandwidth_gb", 1)], [ev("e1", "tenant-a", "bandwidth_gb", "lots")],
                     [ev("e1", "tenant-a", "bandwidth_gb", True)]):
            self.assertEqual(run("usage", "--events", self.events(rows), "--quotas", self.quota(100))[0], 2, rows)
        with open(os.path.join(self.dir, "broken.jsonl"), "w") as fh:
            fh.write("not json\n")
        self.assertEqual(run("usage", "--events", os.path.join(self.dir, "broken.jsonl"), "--quotas", self.quota(100))[0], 2)
        self.assertEqual(run("usage", "--events", good, "--quotas", self.quota(0))[0], 2)
        self.assertEqual(run("usage", "--events", good, "--quotas", os.path.join(self.dir, "nope.json"))[0], 2)
        self.assertEqual(run("usage", "--events", good)[0], 2)
        self.assertEqual(run()[0], 2)


class Reconcile(Workdir):
    """Prices come from the owner's prices.json (bandwidth_gb 0.08, storage_gb 0.023 USD, max_tolerance 0.05)."""

    def invoices(self, *lines, tenant="tenant-a"):
        return self.json_file("inv.json", {"invoices": [{"invoice_id": "inv-1", "tenant_id": tenant, "currency": "USD",
                                                          "lines": [{"meter": m, "amount": a} for m, a in lines]}]})

    def rec(self, rows, invoices, *extra):
        return run("reconcile", "--events", self.events(rows), "--invoices", invoices, *extra)

    def test_clean_invoices_reconcile(self):
        code, out = run("reconcile", "--events", fx("usage-events.jsonl"), "--prices", fx("prices.json"), "--invoices", fx("invoices-clean.json"))
        self.assertEqual((code, out["verdict"], len(out["matched"])), (0, "ok", 4))

    def test_overbilled_line_is_reported_with_its_amount(self):
        code, out = run("reconcile", "--events", fx("usage-events.jsonl"), "--prices", fx("prices.json"), "--invoices", fx("invoices.json"))
        self.assertEqual(code, 1)
        row = out["overbilled"][0]
        self.assertEqual((row["tenant_id"], row["meter"], row["expected_amount"], row["billed_amount"], row["difference"]),
                         ("tenant-b", "bandwidth_gb", "40.02", "42.50", "2.48"))
        self.assertEqual(out["amounts"]["overbilled"], "2.48")
        self.assertEqual(len(out["matched"]), 3)

    def test_underbilled_unbilled_and_billed_unmetered(self):
        rows = [ev("e1", "tenant-a", "bandwidth_gb", 100), ev("e2", "tenant-a", "storage_gb", 1000)]
        code, out = self.rec(rows, self.invoices(("bandwidth_gb", "7.00"), ("egress_other", "3.00")))
        self.assertEqual(code, 1)
        self.assertEqual(out["underbilled"][0]["difference"], "-1.00")
        self.assertEqual(out["unbilled_usage"][0]["meter"], "storage_gb")
        self.assertEqual(out["unbilled_usage"][0]["expected_amount"], "23.00")
        self.assertEqual(out["billed_unmetered"][0]["meter"], "egress_other")
        self.assertEqual(out["amounts"], {"billed_unmetered": "3.00", "overbilled": "0.00", "underbilled": "1.00", "unbilled_usage": "23.00"})

    def test_tolerance_decides_what_counts_as_a_mismatch(self):
        rows = [ev("e1", "tenant-a", "bandwidth_gb", 100)]
        inv = self.invoices(("bandwidth_gb", "8.02"))
        self.assertEqual(self.rec(rows, inv)[0], 1)
        code, out = self.rec(rows, inv, "--tolerance", "0.02")
        self.assertEqual(code, 0)
        self.assertEqual(len(out["within_tolerance"]), 1)
        self.assertEqual(self.rec(rows, inv, "--tolerance", "0.01")[0], 1)

    def test_tolerance_and_prices_come_from_the_owner_price_list(self):
        """Minor 6: --tolerance had no cap and --prices was a caller file."""
        rows = [ev("e1", "tenant-a", "bandwidth_gb", 100)]
        inv = self.invoices(("bandwidth_gb", "999.00"))
        code, out = self.rec(rows, inv, "--tolerance", "1000")
        self.assertEqual((code, out["refusal"]), (1, "tolerance-above-owner-max"))
        cheap = self.json_file("mine.json", {"currency": "USD", "prices": [{"meter": "bandwidth_gb", "unit_price": 9.99}]})
        code, out = self.rec(rows, inv, "--prices", cheap)
        self.assertEqual((code, out["refusal"]), (1, "prices-not-owner-file"))
        code, out = self.rec(rows, self.invoices(("bandwidth_gb", "8.00")), "--prices", fx("prices.json"), "--tolerance", "0.05")
        self.assertEqual((code, out["max_tolerance"]), (0, "0.05"))

    def test_retried_delivery_is_not_billed_twice(self):
        once = [ev("e1", "tenant-a", "bandwidth_gb", 100)]
        twice = once + once
        inv = self.invoices(("bandwidth_gb", "8.00"))
        self.assertEqual(self.rec(twice, inv)[0], 0)
        doubled = self.invoices(("bandwidth_gb", "16.00"))
        code, out = self.rec(twice, doubled)
        self.assertEqual((code, out["overbilled"][0]["difference"]), (1, "8.00"))

    def test_rounding_is_half_up_to_cents(self):
        code, out = self.rec([ev("e1", "tenant-a", "storage_gb", 75)], self.invoices(("storage_gb", "1.73")))
        self.assertEqual((code, out["matched"][0]["expected_amount"]), (0, "1.73"))  # 75 x 0.023 = 1.725

    def test_invoice_lines_for_one_meter_sum(self):
        inv = self.json_file("two.json", {"invoices": [
            {"invoice_id": "i1", "tenant_id": "tenant-a", "currency": "USD", "lines": [{"meter": "bandwidth_gb", "amount": 5}]},
            {"invoice_id": "i2", "tenant_id": "tenant-a", "currency": "USD", "lines": [{"meter": "bandwidth_gb", "amount": 3}]}]})
        self.assertEqual(self.rec([ev("e1", "tenant-a", "bandwidth_gb", 100)], inv)[0], 0)

    def test_invalid_input_exits_2(self):
        rows = [ev("e1", "tenant-a", "bandwidth_gb", 100)]
        self.assertEqual(self.rec(rows, self.invoices(("bandwidth_gb", "-1.00")))[0], 2)
        self.assertEqual(self.rec(rows, self.invoices(("bandwidth_gb", "8")), "--tolerance", "-1")[0], 2)
        self.assertEqual(self.rec(rows, self.invoices(("bandwidth_gb", "8")), "--tolerance", "abc")[0], 2)
        self.assertEqual(self.rec([ev("e1", "tenant-a", "gpu_hours", 1)], self.invoices(("gpu_hours", "1")))[0], 2)
        self.assertEqual(self.rec(rows, self.json_file("bad.json", {"invoices": "no"}))[0], 2)
        self.assertEqual(run("reconcile", "--events", self.events(rows))[0], 2)
        self.assertEqual(self.rec(rows, self.invoices(("bandwidth_gb", "20.035")))[0], 2)

    def clean(self, edit):
        with open(fx("invoices-clean.json")) as fh:
            doc = json.load(fh)
        edit(doc["invoices"])
        return run("reconcile", "--events", fx("usage-events.jsonl"), "--prices", fx("prices.json"),
                   "--invoices", self.json_file("edited.json", doc))

    def test_currency_total_and_billed_quantity_are_checked(self):
        code, out = self.clean(lambda invs: [i.update(currency="EUR") for i in invs])
        self.assertEqual((code, len(out["currency_mismatch"])), (1, 2))
        code, out = self.clean(lambda invs: invs[0].update(total=999.99))
        self.assertEqual((code, out["total_mismatch"][0]["sum_of_lines"]), (1, "20.96"))
        code, out = self.clean(lambda invs: invs[0]["lines"][0].update(quantity=9999))
        self.assertEqual((code, out["quantity_mismatch"][0]["metered_quantity"]), (1, "250.5"))
        code, out = self.clean(lambda invs: invs[0].update(total=20.96))
        self.assertEqual((code, out["verdict"]), (0, "ok"))

    def test_padded_or_renamed_retries_count_once_and_fail(self):
        base = [ev("e1", "tenant-a", "bandwidth_gb", 100)]
        base[0]["ts"] = "2026-11-03T10:00:00Z"
        padded = base + [dict(base[0], event_id="e1 ")]
        code, out = self.rec(padded, self.invoices(("bandwidth_gb", "8.00")))
        self.assertEqual((code, out["matched"][0]["metered_quantity"]), (0, "100"))
        renamed = base + [dict(base[0], event_id="e1-retry-7f3a")]
        code, out = self.rec(renamed, self.invoices(("bandwidth_gb", "8.00")))
        self.assertEqual((code, out["matched"][0]["metered_quantity"], out["conflicts"][0]["reason"]), (1, "100", "same-payload-new-id"))

    def test_a_renamed_retry_with_the_same_instant_in_another_format_counts_once(self):
        """Minor 6: 10:00:00Z and 11:00:00+01:00 are one instant, so the renamed retry is a retry."""
        base = dict(ev("e1", "tenant-a", "bandwidth_gb", 100), ts="2026-11-03T10:00:00Z")
        for other in ("2026-11-03T11:00:00+01:00", "2026-11-03T10:00:00.000+00:00", " 2026-11-03T10:00:00Z"):
            code, out = self.rec([base, dict(base, event_id="e1-retry", ts=other)], self.invoices(("bandwidth_gb", "8.00")))
            self.assertEqual((code, out["matched"][0]["metered_quantity"], out["conflicts"][0]["reason"]), (1, "100", "same-payload-new-id"), other)
        self.assertEqual(self.rec([dict(base, ts="2026-11-03T10:00:00")], self.invoices(("bandwidth_gb", "8.00")))[0], 2)

    def test_non_utf8_events_exit_2_with_a_named_reason(self):
        path = os.path.join(self.dir, "bad.jsonl")
        with open(path, "wb") as fh:
            fh.write(b"\xff\xfe{}\n")
        code, out = run("reconcile", "--events", path, "--invoices", fx("invoices-clean.json"))
        self.assertEqual(code, 2)
        self.assertIn("not UTF-8", out["error"])


class Attribute(Workdir):
    def alloc(self, pools, rows, driver="bandwidth_gb"):
        costs = self.json_file("costs.json", {"pools": [{"pool_id": "p%d" % i, "amount": a} for i, a in enumerate(pools)]})
        return run("attribute", "--costs", costs, "--events", self.events(rows), "--driver", driver)

    def test_shipped_pools_sum_exactly_and_remainder_goes_to_largest_fraction(self):
        code, out = run("attribute", "--costs", fx("costs.json"), "--events", fx("usage-events.jsonl"), "--driver", "bandwidth_gb")
        self.assertEqual(code, 0)
        first = out["pools"][0]
        self.assertEqual([(a["tenant_id"], a["amount"]) for a in first["allocations"]], [("tenant-a", "333.67"), ("tenant-b", "666.33")])
        for pool in out["pools"]:
            self.assertEqual(sum(Decimal(a["amount"]) for a in pool["allocations"]), Decimal(pool["amount"]))

    def test_remainder_cent_goes_to_the_larger_fraction_not_the_first_tenant(self):
        rows = [ev("e1", "tenant-a", "bandwidth_gb", 1), ev("e2", "tenant-b", "bandwidth_gb", 2)]
        code, out = self.alloc(["0.01"], rows)
        self.assertEqual({a["tenant_id"]: a["amount"] for a in out["pools"][0]["allocations"]}, {"tenant-a": "0.00", "tenant-b": "0.01"})

    def test_ties_break_by_tenant_id(self):
        rows = [ev("e%d" % i, t, "bandwidth_gb", 10) for i, t in enumerate(("tenant-c", "tenant-a", "tenant-b"))]
        code, out = self.alloc(["1.00"], rows)
        got = {a["tenant_id"]: a["amount"] for a in out["pools"][0]["allocations"]}
        self.assertEqual(got, {"tenant-a": "0.34", "tenant-b": "0.33", "tenant-c": "0.33"})

    def test_allocations_sum_to_the_pool_for_awkward_weights(self):
        weights = [Decimal("0.1"), Decimal("0.7"), Decimal("3.333"), Decimal("17"), Decimal("0.001")]
        rows = [ev("e%d" % i, "tenant-%d" % i, "bandwidth_gb", float(w)) for i, w in enumerate(weights)]
        for amount in ("0.01", "0.02", "1.00", "99.99", "1234567.89", "0.00"):
            code, out = self.alloc([amount], rows)
            self.assertEqual(code, 0)
            self.assertEqual(sum(Decimal(a["amount"]) for a in out["pools"][0]["allocations"]), Decimal(amount), amount)

    def test_driver_usage_is_deduplicated(self):
        rows = [ev("e1", "tenant-a", "bandwidth_gb", 10), ev("e1", "tenant-a", "bandwidth_gb", 10), ev("e2", "tenant-b", "bandwidth_gb", 10)]
        code, out = self.alloc(["10.00"], rows)
        self.assertEqual([a["amount"] for a in out["pools"][0]["allocations"]], ["5.00", "5.00"])

    def test_no_driver_usage_is_refused(self):
        code, out = self.alloc(["10.00"], [ev("e1", "tenant-a", "storage_gb", 5)])
        self.assertEqual((code, out["refusal"]), (1, "no-driver-usage"))

    def test_invalid_input_exits_2(self):
        rows = [ev("e1", "tenant-a", "bandwidth_gb", 5)]
        self.assertEqual(self.alloc(["10.005"], rows)[0], 2)
        self.assertEqual(self.alloc(["-1.00"], rows)[0], 2)
        self.assertEqual(self.alloc(["1.00"], rows, driver="Bad Meter")[0], 2)
        self.assertEqual(run("attribute", "--costs", os.path.join(self.dir, "nope.json"), "--events", self.events(rows), "--driver", "bandwidth_gb")[0], 2)


class Commission(Workdir):
    """Terms and the disclosure log are Fixture Co's owner files at fixed paths; each test writes them in its own mirror."""

    def setUp(self):
        super().setUp()
        self.root = mirror.make(os.path.join(self.dir, "rig"))
        self.script = mirror.script(self.root, "hosting-metering-reconcile", "metering.py")

    def owner_writes(self, name, doc):
        with open(mirror.fixtures(self.root, "metering", name), "w") as fh:
            json.dump(doc, fh)

    def go(self, referrals, payouts, rate=0.10, clawback=30, shown=None, page="checkout", rendered="2026-01-01"):
        """shown: referral ids in Fixture Co's own disclosure log; by default every row whose disclosure_shown is true."""
        shown = [r["referral_id"] for r in referrals if r.get("disclosure_shown") is True] if shown is None else shown
        self.owner_writes("terms.json", {"rate": rate, "clawback_days": clawback})
        self.owner_writes("disclosure-log.json", {"shown": [{"referral_id": r, "page": page, "rendered_at": rendered} for r in shown]})
        return run("commission", "--referrals", self.json_file("r.json", {"referrals": referrals}),
                   "--payouts", self.json_file("p.json", {"payouts": [{"referral_id": k, "amount": v} for k, v in payouts]}),
                   script=self.script)

    @staticmethod
    def ref(rid="r1", qualified=True, disclosure=True, order=100.00, converted="2026-10-01", refunded=None):
        return {"referral_id": rid, "affiliate_id": "aff-1", "qualified": qualified, "disclosure_shown": disclosure,
                "order_amount": order, "converted_at": converted, "refunded_at": refunded}

    def test_shipped_fixture_flags_undisclosed_and_clawback(self):
        code, out = run("commission", "--referrals", fx("referrals.json"), "--payouts", fx("payouts.json"))
        self.assertEqual(code, 1)
        self.assertEqual([r["referral_id"] for r in out["paid_without_disclosure"]], ["ref-002"])
        self.assertEqual([(r["referral_id"], r["clawback_due"]) for r in out["paid_not_earned"]], [("ref-003", "10.00")])
        self.assertEqual([r["referral_id"] for r in out["matched"]], ["ref-001", "ref-004"])
        self.assertEqual(out["expected_total"], "32.50")

    def test_clawback_window_boundary_is_inclusive(self):
        inside = self.ref(converted="2026-10-01", refunded="2026-10-31")  # day 30
        outside = self.ref("r2", converted="2026-10-01", refunded="2026-11-01")  # day 31
        code, out = self.go([inside, outside], [("r1", 10.0), ("r2", 10.0)])
        self.assertEqual(code, 1)
        self.assertEqual([r["referral_id"] for r in out["paid_not_earned"]], ["r1"])
        self.assertEqual([r["referral_id"] for r in out["matched"]], ["r2"])

    def test_unqualified_referral_earns_nothing(self):
        code, out = self.go([self.ref(qualified=False)], [("r1", 10.0)])
        self.assertEqual([r["referral_id"] for r in out["paid_not_earned"]], ["r1"])
        self.assertEqual(out["paid_not_earned"][0]["ineligible_reasons"], ["not-qualified"])

    def test_overpaid_underpaid_unpaid_and_unknown(self):
        refs = [self.ref("r1"), self.ref("r2"), self.ref("r3")]
        code, out = self.go(refs, [("r1", 11.0), ("r2", 9.0), ("ghost", 5.0)])
        self.assertEqual((code, out["overpaid"][0]["difference"], out["underpaid"][0]["referral_id"]), (1, "1.00", "r2"))
        self.assertEqual([r["referral_id"] for r in out["underpaid"]], ["r2", "r3"])
        self.assertEqual(out["unknown_referral"][0]["referral_id"], "ghost")

    def test_correct_payouts_pass_with_half_up_rounding(self):
        code, out = self.go([self.ref(order=10.05)], [("r1", 1.01)])  # 10.05 x 0.10 = 1.005
        self.assertEqual((code, out["verdict"]), (0, "ok"))

    def test_disclosure_comes_from_the_owner_log_not_the_row(self):
        code, out = self.go([self.ref()], [("r1", 10.0)], shown=[])
        self.assertEqual((code, [r["referral_id"] for r in out["paid_without_disclosure"]]), (1, ["r1"]))
        self.assertIn("disclosure-claim-unverified", out["paid_without_disclosure"][0]["ineligible_reasons"])

    def test_caller_disclosure_log_and_terms_are_refused(self):
        """Major 1: --disclosures my-disclosures.json turned ref-002's undisclosed payout into ok."""
        args = ["commission", "--referrals", fx("referrals.json"), "--payouts", fx("payouts.json")]
        mine = self.json_file("my-disclosures.json", {"shown": [{"referral_id": r, "page": "checkout", "rendered_at": "2026-09-01"}
                                                                for r in ("ref-001", "ref-002", "ref-003", "ref-004")]})
        code, out = run(*args, "--disclosures", mine)
        self.assertEqual((code, out["refusal"]), (1, "disclosures-not-owner-file"))
        code, out = run(*args, "--terms", self.json_file("t.json", {"rate": 0.9, "clawback_days": 0}))
        self.assertEqual((code, out["refusal"]), (1, "terms-not-owner-file"))
        code, out = run(*args, "--disclosures", fx("disclosure-log.json"), "--terms", fx("terms.json"))
        self.assertEqual((code, out["verdict"], out["paid_without_disclosure"][0]["referral_id"]), (1, "mismatch", "ref-002"))

    def test_a_disclosure_entry_counts_only_at_checkout_on_or_before_conversion(self):
        """Minor 14: an entry dated 2027, or on another page, counted as disclosure."""
        for page, rendered in (("checkout", "2027-01-01"), ("blog", "2026-09-01")):
            code, out = self.go([self.ref()], [("r1", 10.0)], page=page, rendered=rendered)
            self.assertEqual(code, 1, (page, rendered))
            self.assertEqual(out["paid_without_disclosure"][0]["ineligible_reasons"], ["no-disclosure", "disclosure-entry-invalid", "disclosure-claim-unverified"])
        code, out = self.go([self.ref()], [("r1", 10.0)], rendered="2026-10-01")
        self.assertEqual((code, out["verdict"]), (0, "ok"), "rendered the day it converted")

    def test_a_duplicate_referral_row_refuses_the_file(self):
        self.assertEqual(self.go([self.ref(), self.ref()], [("r1", 10.0)])[0], 2)

    def test_undisclosed_and_unpaid_is_fine(self):
        code, out = self.go([self.ref(disclosure=False)], [])
        self.assertEqual((code, out["paid_without_disclosure"]), (0, []))

    def test_invalid_input_exits_2(self):
        self.assertEqual(self.go([self.ref()], [], rate=0)[0], 2)
        self.assertEqual(self.go([self.ref()], [], rate=1.5)[0], 2)
        self.assertEqual(self.go([self.ref()], [], clawback=-1)[0], 2)
        bad = self.ref()
        bad["disclosure_shown"] = "yes"
        self.assertEqual(self.go([bad], [])[0], 2)
        self.assertEqual(self.go([self.ref(converted="2026-10-10", refunded="2026-10-01")], [])[0], 2)
        self.assertEqual(self.go([self.ref(converted="last week")], [])[0], 2)
        self.assertEqual(self.go([self.ref()], [("r1", -5)])[0], 2)


class Capacity(Workdir):
    def series(self, values, start=datetime.date(2026, 10, 1), step=1):
        pts = [{"date": (start + datetime.timedelta(days=step * i)).isoformat(), "utilization": v} for i, v in enumerate(values)]
        return self.json_file("s.json", {"points": pts})

    def test_thirty_rising_points_project_a_date(self):
        code, out = run("capacity", "--series", fx("utilization-30.json"), "--threshold", "0.8")
        self.assertEqual(code, 0)
        self.assertEqual(out["status"], "projected")
        self.assertEqual(out["days_until_threshold"], 11)
        self.assertEqual(out["projected_date"], "2026-12-06")
        self.assertTrue(any("straight line" in a for a in out["assumptions"]))
        self.assertLessEqual(out["band_days"]["earliest"], out["days_until_threshold"])
        self.assertGreaterEqual(out["band_days"]["latest"], out["days_until_threshold"])

    def test_a_last_point_already_over_the_threshold_is_reached(self):
        code, out = run("capacity", "--series", self.series([0.30] * 13 + [0.95]), "--threshold", "0.8")
        self.assertEqual((code, out["status"], out["days_until_threshold"]), (0, "reached", 0))
        self.assertEqual(out["fit"]["observed_utilization_at_last_point"], 0.95)

    def test_too_few_points_is_refused(self):
        code, out = run("capacity", "--series", fx("utilization-5.json"))
        self.assertEqual((code, out["refusal"], out["points"]), (1, "insufficient-points", 5))
        self.assertEqual(run("capacity", "--series", fx("utilization-5.json"), "--min-points", "5")[0], 0)
        thirteen = self.series([0.5 + 0.01 * i for i in range(13)])
        self.assertEqual(run("capacity", "--series", thirteen)[0], 1)
        fourteen = self.series([0.5 + 0.01 * i for i in range(14)])
        self.assertEqual(run("capacity", "--series", fourteen)[0], 0)

    def test_flat_or_falling_trend_is_not_reached(self):
        code, out = run("capacity", "--series", self.series([0.6 - 0.005 * i for i in range(20)]))
        self.assertEqual((code, out["days_until_threshold"], out["status"]), (0, "not-reached", "not-reached"))
        code, out = run("capacity", "--series", self.series([0.5] * 20))
        self.assertEqual(out["status"], "not-reached")

    def test_already_past_the_threshold(self):
        code, out = run("capacity", "--series", self.series([0.7 + 0.01 * i for i in range(20)]))
        self.assertEqual((out["status"], out["days_until_threshold"]), ("reached", 0))

    def test_projection_past_the_observed_span_is_flagged(self):
        code, out = run("capacity", "--series", self.series([0.40 + 0.002 * i for i in range(14)]))
        self.assertTrue(out["extrapolation_warning"])

    def test_uneven_dates_use_the_calendar_not_the_index(self):
        code, out = run("capacity", "--series", self.series([0.4 + 0.02 * i for i in range(15)], step=2))
        self.assertAlmostEqual(out["fit"]["slope_per_day"], 0.01, places=6)

    def test_invalid_input_exits_2(self):
        good = self.series([0.5 + 0.01 * i for i in range(20)])
        self.assertEqual(run("capacity", "--series", good, "--threshold", "0")[0], 2)
        self.assertEqual(run("capacity", "--series", good, "--threshold", "1.5")[0], 2)
        self.assertEqual(run("capacity", "--series", good, "--min-points", "2")[0], 2)
        self.assertEqual(run("capacity", "--series", good, "--min-points", "many")[0], 2)
        self.assertEqual(run("capacity", "--series", self.series([0.5, 1.2, 0.6]), "--min-points", "3")[0], 2)
        self.assertEqual(run("capacity", "--series", self.series([0.5, 0.6, 0.7], step=0), "--min-points", "3")[0], 2)
        self.assertEqual(run("capacity", "--series", os.path.join(self.dir, "nope.json"))[0], 2)
        self.assertEqual(run("capacity", "--series", self.json_file("b.json", {"points": [{"date": "x", "utilization": 0.5}]}))[0], 2)


if __name__ == "__main__":
    unittest.main()
