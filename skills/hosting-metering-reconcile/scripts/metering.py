#!/usr/bin/env python3
"""metering: usage and quotas, invoice reconciliation, cost attribution, commissions and capacity headroom.

  usage      --events USAGE.jsonl --quotas QUOTAS.json
  reconcile  --events USAGE.jsonl --invoices INVOICES.json [--tolerance 0.00]
  attribute  --costs COSTS.json --events USAGE.jsonl --driver METER
  commission --referrals REFERRALS.json --payouts PAYOUTS.json
  capacity   --series UTIL.json [--threshold 0.8] [--min-points 14]

Fixture Co's owner files are read from fixed paths in the fleet's fixtures (metering/prices.json,
terms.json and disclosure-log.json), never from a flag: --prices, --terms and --disclosures are refused
by name unless they name those same files. --tolerance may not exceed the max_tolerance the price list
states.

Python 3.9+, standard library only. Money is decimal.Decimal, rounded ROUND_HALF_UP to cents. Stdout is
JSON and every result lists its assumptions. Exit 0 ok, 1 refused or a mismatch or violation found,
2 invalid input. The script reads files and never calls out, so it never exits 3.
"""
from __future__ import annotations

import argparse
import datetime
import json
import math
import os
import re
import sys
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from fractions import Fraction
from typing import Any, Dict, List, Optional, Tuple

CENT = Decimal("0.01")
WARN_AT = Decimal("0.80")
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
METER = re.compile(r"^[a-z][a-z0-9_]*$")
OWNER_FILES = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "company-fleets", "fleets",
                                            "hosting", "fixtures", "metering"))
OWNER = {"prices": "prices.json", "terms": "terms.json", "disclosures": "disclosure-log.json"}


class InputError(Exception):
    """Invalid input: exit 2."""


class Refused(Exception):
    """A refusal: exit 1."""

    def __init__(self, refusal: str, detail: str, **extra: Any) -> None:
        super().__init__(detail)
        self.payload = dict(extra, refusal=refusal, detail=detail, verdict="refused")


def emit(obj: Any) -> None:
    print(json.dumps(obj, indent=2, sort_keys=True))


# ---- parsing ---------------------------------------------------------------------------------------------


def dec(value: Any, what: str, minimum: Optional[Decimal] = None) -> Decimal:
    if isinstance(value, bool) or not isinstance(value, (int, Decimal, str)):
        raise InputError("%s must be a number, got %r" % (what, value))
    try:
        out = Decimal(value) if not isinstance(value, str) else Decimal(value.strip())
    except InvalidOperation:
        raise InputError("%s is not a number: %r" % (what, value))
    if not out.is_finite():
        raise InputError("%s must be finite" % what)
    if minimum is not None and out < minimum:
        raise InputError("%s must be at least %s, got %s" % (what, minimum, out))
    return out


def money(value: Decimal) -> Decimal:
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def ms(value: Decimal) -> str:
    return format(money(value), "f")


def qs(value: Decimal) -> str:
    return format(value.normalize(), "f") if value else "0"


def load_json(path: str, what: str) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh, parse_float=Decimal)
    except FileNotFoundError:
        raise InputError("%s not found: %s" % (what, path))
    except (ValueError, OSError) as exc:
        raise InputError("%s is not readable JSON: %s (%s)" % (what, path, exc))


def owner_file(args: argparse.Namespace, key: str) -> str:
    """Fixture Co's own file at its fixed path; a caller-named path is refused by name."""
    fixed = os.path.join(OWNER_FILES, OWNER[key])
    named = getattr(args, key, None)
    if named and os.path.realpath(named) != os.path.realpath(fixed):
        raise Refused("%s-not-owner-file" % key, "the %s come only from Fixture Co's own %s; the caller-named %s is refused"
                      % (key, fixed, named))
    return fixed


def list_of(doc: Any, key: str, what: str) -> List[Dict[str, Any]]:
    items = doc.get(key) if isinstance(doc, dict) else None
    if not isinstance(items, list) or not all(isinstance(i, dict) for i in items):
        raise InputError("%s needs a %r list of objects" % (what, key))
    return items


def text_field(obj: Dict[str, Any], key: str, what: str, pattern: "re.Pattern[str]") -> str:
    value = obj.get(key)
    if not isinstance(value, str) or not pattern.match(value):
        raise InputError("%s: %s is missing or malformed: %r" % (what, key, value))
    return value


def parse_day(value: Any, what: str) -> datetime.date:
    if not isinstance(value, str):
        raise InputError("%s must be an ISO date string" % what)
    try:
        return datetime.datetime.fromisoformat(value.strip().replace("Z", "+00:00")).date()
    except ValueError:
        try:
            return datetime.date.fromisoformat(value.strip())
        except ValueError:
            raise InputError("%s is not an ISO date: %r" % (what, value))


def instant(value: Any, what: str) -> Optional[str]:
    """A timestamp as one UTC instant, so 10:00:00Z and 11:00:00+01:00 compare equal. None stays None."""
    if value is None:
        return None
    if not isinstance(value, str):
        raise InputError("%s must be an ISO 8601 string" % what)
    try:
        stamp = datetime.datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError:
        raise InputError("%s is not an ISO 8601 timestamp: %r" % (what, value))
    if stamp.tzinfo is None:
        raise InputError("%s needs a timezone offset or Z: %r" % (what, value))
    return stamp.astimezone(datetime.timezone.utc).isoformat()


class Usage:
    """Deduplicated meter events. A repeated event_id (whitespace stripped) counts once; the first delivery wins.
    A new event_id carrying the same tenant, meter, quantity and ts instant as an earlier event is a suspected
    retry: it counts once and is listed as a conflict for a human to settle."""

    def __init__(self, path: str) -> None:
        try:
            with open(path, "r", encoding="utf-8") as fh:
                lines = fh.read().splitlines()
        except UnicodeDecodeError:
            raise InputError("events file is not UTF-8 text: %s" % path)
        except OSError as exc:
            raise InputError("events file not readable: %s (%s)" % (path, exc))
        self.seen: Dict[str, Tuple[int, Tuple[str, str, Decimal]]] = {}
        payloads: Dict[Tuple[Any, ...], Tuple[int, str]] = {}
        self.duplicates: List[Dict[str, Any]] = []
        self.conflicts: List[Dict[str, Any]] = []
        self.totals: Dict[str, Dict[str, Decimal]] = {}
        for n, line in enumerate(lines, 1):
            if not line.strip():
                continue
            try:
                obj = json.loads(line, parse_float=Decimal)
            except ValueError:
                raise InputError("events line %d is not JSON" % n)
            if not isinstance(obj, dict):
                raise InputError("events line %d is not an object" % n)
            if set(obj) == {"label"}:
                continue
            where = "events line %d" % n
            event_id = obj.get("event_id")
            if not isinstance(event_id, str) or not event_id.strip():
                raise InputError("%s: event_id is missing" % where)
            event_id = event_id.strip()
            key = (text_field(obj, "tenant_id", where, SLUG), text_field(obj, "meter", where, METER),
                   dec(obj.get("quantity"), where + " quantity", Decimal(0)))
            payload = key + (instant(obj.get("ts"), where + " ts"),)
            if event_id in self.seen:
                first_line, first = self.seen[event_id]
                row = {"event_id": event_id, "tenant_id": key[0], "meter": key[1], "quantity": qs(key[2]),
                       "line": n, "first_line": first_line, "identical": first == key}
                self.duplicates.append(row)
                if first != key:
                    self.conflicts.append(row)
                continue
            if payload[-1] is not None and payload in payloads:
                first_line, first_id = payloads[payload]
                self.conflicts.append({"event_id": event_id, "tenant_id": key[0], "meter": key[1], "quantity": qs(key[2]),
                                       "line": n, "first_line": first_line, "same_payload_as": first_id,
                                       "reason": "same-payload-new-id"})
                continue
            payloads[payload] = (n, event_id)
            self.seen[event_id] = (n, key)
            self.totals.setdefault(key[0], {})
            self.totals[key[0]][key[1]] = self.totals[key[0]].get(key[1], Decimal(0)) + key[2]

    def total(self, tenant: str, meter: str) -> Decimal:
        return self.totals.get(tenant, {}).get(meter, Decimal(0))

    def view(self) -> Dict[str, Dict[str, str]]:
        return {t: {m: qs(q) for m, q in sorted(ms_.items())} for t, ms_ in sorted(self.totals.items())}


# ---- usage -----------------------------------------------------------------------------------------------


def cmd_usage(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    usage = Usage(args.events)
    quotas = list_of(load_json(args.quotas, "quotas file"), "quotas", "quotas file")
    rows, violations, seen = [], [], set()
    for i, q in enumerate(quotas, 1):
        where = "quota %d" % i
        tenant, meter = text_field(q, "tenant_id", where, SLUG), text_field(q, "meter", where, METER)
        if (tenant, meter) in seen:
            raise InputError("%s: %s already has a %s quota; one limit per tenant and meter" % (where, tenant, meter))
        seen.add((tenant, meter))
        limit = dec(q.get("limit"), where + " limit")
        if limit <= 0:
            raise InputError("%s: limit must be above 0" % where)
        used = usage.total(tenant, meter)
        ratio = used / limit
        status = "over" if used > limit else ("warn" if ratio >= WARN_AT else "ok")
        reasons = []
        if q.get("customer_visible") is not True:
            reasons.append("not-customer-visible")
        published = q.get("published_limit")
        if published is None:
            reasons.append("missing-published-value")
        elif dec(published, where + " published_limit") != limit:
            reasons.append("published-differs-from-enforced")
        if not isinstance(q.get("unit"), str) or not q["unit"].strip():
            reasons.append("missing-unit")
        rows.append({"tenant_id": tenant, "meter": meter, "limit": qs(limit), "unit": q.get("unit"), "used": qs(used),
                     "utilization": format(ratio.quantize(Decimal("0.0001")), "f"), "status": status})
        if reasons:
            violations.append({"tenant_id": tenant, "meter": meter, "reasons": reasons})
    for conflict in usage.conflicts:
        violations.append({"event_id": conflict["event_id"], "reasons": [conflict.get("reason", "conflicting-duplicate-event")]})
    bad = bool(violations)
    return (1 if bad else 0), {
        "command": "usage", "verdict": "violation" if bad else "ok", "totals": usage.view(),
        "duplicates": usage.duplicates, "quotas": rows, "violations": violations,
        "policy": {"warn_at": format(WARN_AT, "f"), "over_means": "used > limit"},
        "assumptions": [
            "A repeated event_id counts once (first delivery wins) and is listed under duplicates, so a retried meter delivery never double-bills. Ids are compared with surrounding whitespace stripped.",
            "A new event_id with the same tenant, meter, quantity and ts as an earlier event counts once and fails the check as same-payload-new-id: a human decides whether it is a retry.",
            "A duplicate event_id carrying a different tenant, meter or quantity is a conflict: the first value counts and the check fails.",
            "Quota status is a stated policy: warn at or above 80 percent of the limit, over only when used exceeds the limit.",
            "A quota is publishable only when it is customer-visible, has a unit, and its published value equals the enforced limit.",
            "Usage has no time window here: pass the events for one billing period."]}


# ---- reconcile -------------------------------------------------------------------------------------------


def cmd_reconcile(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    usage = Usage(args.events)
    tolerance = dec(args.tolerance, "--tolerance", Decimal(0))
    prices = {}
    price_path = owner_file(args, "prices")
    price_doc = load_json(price_path, "prices file")
    currency = price_doc.get("currency") if isinstance(price_doc, dict) else None
    if not isinstance(currency, str) or not re.match(r"^[A-Z]{3}$", currency):
        raise InputError("prices file needs a three-letter currency")
    max_tolerance = dec(price_doc.get("max_tolerance", "0.00"), "prices file max_tolerance", Decimal(0))
    if tolerance > max_tolerance:
        raise Refused("tolerance-above-owner-max", "--tolerance %s is above the max_tolerance %s that Fixture Co's price list %s "
                      "allows" % (ms(tolerance), ms(max_tolerance), price_path))
    for i, p in enumerate(list_of(price_doc, "prices", "prices file"), 1):
        prices[text_field(p, "meter", "price %d" % i, METER)] = dec(p.get("unit_price"), "price %d unit_price" % i, Decimal(0))
    billed: Dict[Tuple[str, str], Dict[str, Any]] = {}
    invoice_checks: Dict[str, List[Dict[str, Any]]] = {"currency_mismatch": [], "total_mismatch": []}
    for i, inv in enumerate(list_of(load_json(args.invoices, "invoices file"), "invoices", "invoices file"), 1):
        where = "invoice %d" % i
        tenant = text_field(inv, "tenant_id", where, SLUG)
        if not isinstance(inv.get("invoice_id"), str) or not inv["invoice_id"]:
            raise InputError("%s needs an invoice_id" % where)
        if not isinstance(inv.get("currency"), str) or not re.match(r"^[A-Z]{3}$", inv["currency"]):
            raise InputError("%s needs a three-letter currency" % where)
        if inv["currency"] != currency:
            invoice_checks["currency_mismatch"].append({"invoice_id": inv["invoice_id"], "tenant_id": tenant,
                                                        "invoice_currency": inv["currency"], "price_currency": currency})
        line_sum = Decimal(0)
        for j, line in enumerate(list_of(inv, "lines", where), 1):
            lwhere = "%s line %d" % (where, j)
            meter = text_field(line, "meter", lwhere, METER)
            entry = billed.setdefault((tenant, meter), {"amount": Decimal(0), "quantity": None, "invoices": []})
            amount = dec(line.get("amount"), lwhere + " amount", Decimal(0))
            if amount != money(amount):
                raise InputError("%s amount has fractions of a cent: %s" % (lwhere, amount))
            entry["amount"] += amount
            line_sum += amount
            if line.get("quantity") is not None:
                entry["quantity"] = (entry["quantity"] or Decimal(0)) + dec(line["quantity"], lwhere + " quantity", Decimal(0))
            entry["invoices"].append(inv["invoice_id"])
        if inv.get("total") is not None and dec(inv["total"], where + " total", Decimal(0)) != line_sum:
            invoice_checks["total_mismatch"].append({"invoice_id": inv["invoice_id"], "tenant_id": tenant,
                                                     "stated_total": ms(dec(inv["total"], where + " total")), "sum_of_lines": ms(line_sum)})
    keys = sorted(set(billed) | {(t, m) for t, ms_ in usage.totals.items() for m in ms_})
    groups: Dict[str, List[Dict[str, Any]]] = {k: [] for k in
                                                ("matched", "within_tolerance", "overbilled", "underbilled", "unbilled_usage", "billed_unmetered",
                                                 "quantity_mismatch")}
    sums = {"overbilled": Decimal(0), "underbilled": Decimal(0), "unbilled_usage": Decimal(0), "billed_unmetered": Decimal(0)}
    for tenant, meter in keys:
        metered = usage.total(tenant, meter)
        entry = billed.get((tenant, meter))
        billed_amount = entry["amount"] if entry else Decimal(0)
        if metered > 0 and meter not in prices:
            raise InputError("meter %s has usage for %s but no price" % (meter, tenant))
        expected = money(metered * prices[meter]) if metered > 0 else Decimal(0)
        diff = billed_amount - expected
        row = {"tenant_id": tenant, "meter": meter, "metered_quantity": qs(metered),
               "billed_quantity": qs(entry["quantity"]) if entry and entry["quantity"] is not None else None,
               "unit_price": qs(prices[meter]) if meter in prices else None, "expected_amount": ms(expected),
               "billed_amount": ms(billed_amount), "difference": ms(diff), "invoices": entry["invoices"] if entry else []}
        if entry and entry["quantity"] is not None and entry["quantity"] != metered:
            groups["quantity_mismatch"].append(row)
        if abs(diff) > tolerance:
            kind = ("billed_unmetered" if metered == 0 else "unbilled_usage" if entry is None
                    else "overbilled" if diff > 0 else "underbilled")
            groups[kind].append(row)
            sums[kind] += abs(diff)
        else:
            groups["matched" if diff == 0 else "within_tolerance"].append(row)
    bad = any(groups[k] for k in sums) or bool(groups["quantity_mismatch"]) or any(invoice_checks.values())
    out = {"command": "reconcile", "verdict": "mismatch" if bad or usage.conflicts else "ok", "tolerance": ms(tolerance),
           "max_tolerance": ms(max_tolerance),
           "currency": currency,
           "duplicates": usage.duplicates, "conflicts": usage.conflicts,
           "amounts": {k: ms(v) for k, v in sums.items()}}
    out.update(groups)
    out.update(invoice_checks)
    out["assumptions"] = [
        "Metered quantity is deduplicated by event_id first; a retried delivery is not billed twice.",
        "Every invoice must be in the price file's currency (currency_mismatch otherwise); a stated invoice total must equal the sum of its lines (total_mismatch); a billed quantity must equal the metered quantity (quantity_mismatch). Amounts with fractions of a cent are invalid input.",
        "Expected amount = metered quantity x unit price per tenant and meter, rounded ROUND_HALF_UP to cents; invoice lines for one tenant and meter are summed.",
        "A mismatch is an absolute amount difference above the tolerance (default 0.00); differences inside it list under within_tolerance.",
        "Prices and the largest allowed tolerance come from Fixture Co's own price list at its fixed path, as given: no tiers, discounts, taxes or credits. Negative amounts are rejected as invalid input."]
    return (1 if bad or usage.conflicts else 0), out


# ---- attribute -------------------------------------------------------------------------------------------


def cmd_attribute(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    usage = Usage(args.events)
    if not METER.match(args.driver):
        raise InputError("--driver must be a meter name like bandwidth_gb")
    pools = []
    for i, p in enumerate(list_of(load_json(args.costs, "costs file"), "pools", "costs file"), 1):
        amount = dec(p.get("amount"), "pool %d amount" % i, Decimal(0))
        if amount != money(amount):
            raise InputError("pool %d amount has fractions of a cent: %s" % (i, amount))
        if not isinstance(p.get("pool_id"), str) or not p["pool_id"]:
            raise InputError("pool %d needs a pool_id" % i)
        pools.append((p["pool_id"], amount))
    weights = {t: m[args.driver] for t, m in usage.totals.items() if m.get(args.driver, Decimal(0)) > 0}
    if not weights:
        raise Refused("no-driver-usage", "no tenant has %s usage, so there is no basis to allocate" % args.driver)
    whole = sum((Fraction(w) for w in weights.values()), Fraction(0))
    result, per_tenant = [], {t: Decimal(0) for t in weights}
    for pool_id, amount in pools:
        cents = int(amount * 100)
        exact = {t: Fraction(cents) * Fraction(w) / whole for t, w in weights.items()}
        floors = {t: x.numerator // x.denominator for t, x in exact.items()}
        leftover = cents - sum(floors.values())
        order = sorted(weights, key=lambda t: (-(exact[t] - floors[t]), t))
        bonus = set(order[:leftover])
        rows = []
        for t in sorted(weights):
            got = Decimal(floors[t] + (1 if t in bonus else 0)) / 100
            per_tenant[t] += got
            rows.append({"tenant_id": t, "driver_quantity": qs(weights[t]), "share": format((Decimal(weights[t]) / Decimal(sum(weights.values()))).quantize(Decimal("0.000001")), "f"),
                         "amount": ms(got), "got_remainder_cent": t in bonus})
        assert sum((Decimal(r["amount"]) for r in rows), Decimal(0)) == amount
        result.append({"pool_id": pool_id, "amount": ms(amount), "allocations": rows,
                       "allocated": ms(sum((Decimal(r["amount"]) for r in rows), Decimal(0)))})
    return (1 if usage.conflicts else 0), {
        "command": "attribute", "verdict": "conflict" if usage.conflicts else "ok", "driver": args.driver, "pools": result, "conflicts": usage.conflicts,
        "tenant_totals": {t: ms(v) for t, v in sorted(per_tenant.items())}, "duplicates": usage.duplicates,
        "assumptions": [
            "Each pool splits in proportion to each tenant's deduplicated %s usage; tenants without it get nothing." % args.driver,
            "Allocations sum to the pool exactly. Rounding down to cents leaves a remainder; it goes one cent at a time to the tenant with the largest fractional cent, ties broken by tenant id ascending.",
            "The driver is a proxy for cost, not a measurement of it; pick the meter that moves the pool's cost."]}


# ---- commission ------------------------------------------------------------------------------------------


def cmd_commission(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    terms_path, log_path = owner_file(args, "terms"), owner_file(args, "disclosures")
    terms = load_json(terms_path, "terms file")
    if not isinstance(terms, dict):
        raise InputError("terms file must be an object")
    rate = dec(terms.get("rate"), "terms rate")
    if not (0 < rate <= 1):
        raise InputError("terms rate must be above 0 and at most 1")
    clawback = terms.get("clawback_days")
    if not isinstance(clawback, int) or isinstance(clawback, bool) or clawback < 0:
        raise InputError("terms clawback_days must be a whole number of days, 0 or more")
    log = list_of(load_json(log_path, "disclosure log"), "shown", "disclosure log")
    shown: Dict[str, List[Tuple[str, datetime.date]]] = {}
    for i, d in enumerate(log, 1):
        if not isinstance(d.get("referral_id"), str) or not d["referral_id"]:
            raise InputError("disclosure log entry %d needs a referral_id" % i)
        if not isinstance(d.get("page"), str) or not d["page"].strip():
            raise InputError("disclosure log entry %d needs the page it was rendered on" % i)
        shown.setdefault(d["referral_id"], []).append((d["page"].strip(), parse_day(d.get("rendered_at"), "disclosure log entry %d rendered_at" % i)))
    paid: Dict[str, Decimal] = {}
    for i, p in enumerate(list_of(load_json(args.payouts, "payouts file"), "payouts", "payouts file"), 1):
        rid = p.get("referral_id")
        if not isinstance(rid, str) or not rid:
            raise InputError("payout %d needs a referral_id" % i)
        paid[rid] = paid.get(rid, Decimal(0)) + dec(p.get("amount"), "payout %d amount" % i, Decimal(0))
    flags: Dict[str, List[Dict[str, Any]]] = {k: [] for k in
                                               ("paid_without_disclosure", "paid_not_earned", "overpaid", "underpaid", "unknown_referral")}
    matched, expected_total, paid_total, known = [], Decimal(0), Decimal(0), set()
    for i, r in enumerate(list_of(load_json(args.referrals, "referrals file"), "referrals", "referrals file"), 1):
        where = "referral %d" % i
        rid = r.get("referral_id")
        if not isinstance(rid, str) or not rid:
            raise InputError("%s needs a referral_id" % where)
        if rid in known:
            raise InputError("%s: referral_id %s appears twice" % (where, rid))
        for flag in ("qualified", "disclosure_shown"):
            if not isinstance(r.get(flag), bool):
                raise InputError("%s: %s must be true or false" % (where, flag))
        order = dec(r.get("order_amount"), where + " order_amount", Decimal(0))
        converted = parse_day(r.get("converted_at"), where + " converted_at")
        refunded = parse_day(r["refunded_at"], where + " refunded_at") if r.get("refunded_at") else None
        if refunded is not None and refunded < converted:
            raise InputError("%s: refunded_at is before converted_at" % where)
        known.add(rid)
        reasons = []
        if not r["qualified"]:
            reasons.append("not-qualified")
        entries = shown.get(rid, [])
        disclosed = any(page == "checkout" and day <= converted for page, day in entries)
        if not disclosed:
            reasons.append("no-disclosure")
            if entries:
                reasons.append("disclosure-entry-invalid")
        if r["disclosure_shown"] and not disclosed:
            reasons.append("disclosure-claim-unverified")
        if refunded is not None and (refunded - converted).days <= clawback:
            reasons.append("refunded-in-window")
        expected = Decimal(0) if reasons else money(order * rate)
        got = paid.get(rid, Decimal(0))
        row = {"referral_id": rid, "affiliate_id": r.get("affiliate_id"), "ineligible_reasons": reasons,
               "expected_commission": ms(expected), "paid": ms(got)}
        expected_total += expected
        paid_total += got
        if got > 0 and not disclosed:
            flags["paid_without_disclosure"].append(row)
        elif got > 0 and reasons:
            flags["paid_not_earned"].append(dict(row, clawback_due=ms(got)))
        elif got > expected:
            flags["overpaid"].append(dict(row, difference=ms(got - expected)))
        elif got < expected:
            flags["underpaid"].append(dict(row, difference=ms(expected - got)))
        else:
            matched.append(row)
    for rid in sorted(set(paid) - known):
        flags["unknown_referral"].append({"referral_id": rid, "paid": ms(paid[rid])})
    bad = any(flags.values())
    out = {"command": "commission", "verdict": "mismatch" if bad else "ok", "matched": matched,
           "expected_total": ms(expected_total), "paid_total": ms(paid_total),
           "clawback_window_days": clawback, "rate": format(rate, "f")}
    out.update(flags)
    out["assumptions"] = [
        "A referral earns commission only when it is qualified, the affiliate disclosure was shown, and it was not refunded within clawback_days of converted_at (inclusive).",
        "Commission = order_amount x rate, rounded ROUND_HALF_UP to cents. Payouts for one referral are summed.",
        "Disclosure comes from Fixture Co's own disclosure log at its fixed path, never from the referral row or a caller file; a row that claims disclosure_shown with no log entry is ineligible and flagged disclosure-claim-unverified.",
        "A log entry counts only when it was rendered on the checkout page on or before the day the referral converted; any other entry is flagged disclosure-entry-invalid.",
        "Rate and clawback_days come from Fixture Co's own terms file at its fixed path.",
        "A payout to a referral with no disclosure is flagged whatever else is true of it, because that payout needs a human decision."]
    return (1 if bad else 0), out


# ---- capacity --------------------------------------------------------------------------------------------


def cmd_capacity(args: argparse.Namespace) -> Tuple[int, Dict[str, Any]]:
    threshold = dec(args.threshold, "--threshold")
    if not (0 < threshold <= 1):
        raise InputError("--threshold must be above 0 and at most 1")
    if args.min_points < 3:
        raise InputError("--min-points must be at least 3: a line through 2 points has no error estimate")
    doc = load_json(args.series, "series file")
    points = list_of(doc, "points", "series file")
    days, ys = [], []
    for i, p in enumerate(points, 1):
        day = parse_day(p.get("date"), "point %d date" % i)
        if days and day <= days[-1]:
            raise InputError("point %d: dates must be strictly increasing" % i)
        u = dec(p.get("utilization"), "point %d utilization" % i, Decimal(0))
        if u > 1:
            raise InputError("point %d: utilization is a fraction from 0 to 1, got %s" % (i, u))
        days.append(day)
        ys.append(float(u))
    n = len(points)
    base = {"command": "capacity", "points": n, "min_points": args.min_points, "threshold": float(threshold)}
    if n < args.min_points:
        base.update(verdict="refused", refusal="insufficient-points",
                    detail="%d points is below the minimum of %d; a trend from so few days is noise" % (n, args.min_points))
        return 1, base
    xs = [float((d - days[0]).days) for d in days]
    xbar, ybar = sum(xs) / n, sum(ys) / n
    sxx = sum((x - xbar) ** 2 for x in xs)
    slope = sum((x - xbar) * (y - ybar) for x, y in zip(xs, ys)) / sxx
    intercept = ybar - slope * xbar
    sse = sum((y - intercept - slope * x) ** 2 for x, y in zip(xs, ys))
    syy = sum((y - ybar) ** 2 for y in ys)
    se = math.sqrt(sse / (n - 2) / sxx)
    fitted_now = intercept + slope * xs[-1]
    gap = float(threshold) - fitted_now
    span = xs[-1]

    def days_to(rate: float) -> Any:
        return "not-reached" if rate <= 0 else int(Decimal(gap / rate).quantize(Decimal(1), rounding=ROUND_HALF_UP))

    if gap <= 0 or ys[-1] >= float(threshold):
        status, days_out, early, late = "reached", 0, 0, 0
    elif slope <= 0:
        status, days_out, early, late = "not-reached", "not-reached", days_to(slope + 2 * se), days_to(slope - 2 * se)
    else:
        status, days_out, early, late = "projected", days_to(slope), days_to(slope + 2 * se), days_to(slope - 2 * se)
    projected = None
    if isinstance(days_out, int):
        projected = (days[-1] + datetime.timedelta(days=days_out)).isoformat()
    r2 = None if syy == 0 else round(1 - sse / syy, 4)
    base.update(
        verdict="ok", status=status, days_until_threshold=days_out, projected_date=projected,
        band_days={"earliest": early, "latest": late},
        fit={"slope_per_day": round(slope, 6), "slope_stderr": round(se, 6), "r_squared": r2,
             "fitted_utilization_at_last_point": round(fitted_now, 4), "observed_utilization_at_last_point": round(ys[-1], 4),
             "observed_span_days": int(span),
             "last_date": days[-1].isoformat()},
        extrapolation_warning=isinstance(days_out, int) and days_out > span,
        assumptions=[
            "Utilization follows a straight line in time (least squares over the dates given). Real load has weekly cycles, launches and step changes that a line ignores; treat the date as a planning signal, not a promise.",
            "The band holds the fitted level at the last point and varies the slope by plus or minus 2 standard errors (a rough 95 percent band that assumes independent, evenly spread residuals). Daily series are autocorrelated, so the true band is wider.",
            "A projection farther out than the observed span (extrapolation_warning) rests on more forecast than data.",
            "status is reached when the last observed point is at or over the threshold, whatever the fitted line says.",
            "This is infrastructure headroom. Staffing a support queue is a different question for the capacity-planner skill."])
    return 0, base


# ---- CLI -------------------------------------------------------------------------------------------------


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # JSON on stdout, exit 2
        emit({"error": message})
        raise SystemExit(2)


def build_parser() -> argparse.ArgumentParser:
    p = Parser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", parser_class=Parser)
    u = sub.add_parser("usage")
    u.add_argument("--events", required=True)
    u.add_argument("--quotas", required=True)
    r = sub.add_parser("reconcile")
    r.add_argument("--events", required=True)
    r.add_argument("--prices", help="refused unless it is Fixture Co's prices.json")
    r.add_argument("--invoices", required=True)
    r.add_argument("--tolerance", default="0.00")
    a = sub.add_parser("attribute")
    a.add_argument("--costs", required=True)
    a.add_argument("--events", required=True)
    a.add_argument("--driver", required=True)
    c = sub.add_parser("commission")
    c.add_argument("--referrals", required=True)
    c.add_argument("--terms", help="refused unless it is Fixture Co's terms.json")
    c.add_argument("--payouts", required=True)
    c.add_argument("--disclosures", help="refused unless it is Fixture Co's disclosure-log.json")
    k = sub.add_parser("capacity")
    k.add_argument("--series", required=True)
    k.add_argument("--threshold", default="0.8")
    k.add_argument("--min-points", dest="min_points", type=int, default=14)
    return p


COMMANDS = {"usage": cmd_usage, "reconcile": cmd_reconcile, "attribute": cmd_attribute,
            "commission": cmd_commission, "capacity": cmd_capacity}


def main(argv: Optional[List[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    if not args.cmd:
        emit({"error": "choose a subcommand: %s" % ", ".join(COMMANDS)})
        return 2
    try:
        code, out = COMMANDS[args.cmd](args)
    except InputError as exc:
        emit({"error": str(exc)})
        return 2
    except Refused as exc:
        emit(exc.payload)
        return 1
    emit(out)
    return code


if __name__ == "__main__":
    sys.exit(main())
