#!/usr/bin/env python3
"""Test-mode payment and entitlement webhook processor with idempotent fulfillment.

A fake payment provider sends signed webhook events (JSON lines). This processor is the test
integration: it verifies each event, records it once, and turns it into at most one capture, one
fulfillment, one inventory decrement and one refund per order, however often the provider replays
the event or retries it under a new event id. State lives in a SQLite file the caller names, so a
replay, a crash between events, or two processes racing on the same file converge on one result.

Subcommands:
  sign       add HMAC signatures to unsigned fixture events (fixture authoring only)
  process    verify and apply events; prints per-event outcomes and counts
  reconcile  compare captures, fulfillments, refunds and inventory; prints mismatches

Exit: 0 ok, 1 refused events, needs-human outcomes or reconciliation mismatches, 2 invalid input.
Live-mode events are always refused: this integration has no live mode.
"""
from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import sqlite3
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

EVENT_TYPES = {
    "checkout.completed": ("order_id", "customer_id", "sku", "quantity", "amount", "currency"),
    "charge.refunded": ("order_id", "amount"),
    "subscription.canceled": ("customer_id", "sku"),
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS events (event_id TEXT PRIMARY KEY, type TEXT NOT NULL, outcome TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS captures (idempotency_key TEXT PRIMARY KEY, amount INTEGER NOT NULL, currency TEXT NOT NULL, event_id TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS fulfillments (order_id TEXT PRIMARY KEY, sku TEXT NOT NULL, quantity INTEGER NOT NULL, event_id TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS holds (order_id TEXT NOT NULL, reason TEXT NOT NULL, event_id TEXT NOT NULL, PRIMARY KEY (order_id, event_id));
CREATE TABLE IF NOT EXISTS refunds (order_id TEXT PRIMARY KEY, amount INTEGER NOT NULL, event_id TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS entitlements (customer_id TEXT NOT NULL, sku TEXT NOT NULL, state TEXT NOT NULL, export_offered INTEGER NOT NULL DEFAULT 0, changed_at TEXT NOT NULL, PRIMARY KEY (customer_id, sku));
CREATE TABLE IF NOT EXISTS orders (order_id TEXT PRIMARY KEY, customer_id TEXT NOT NULL, sku TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS inventory (sku TEXT PRIMARY KEY, on_hand INTEGER NOT NULL CHECK (on_hand >= 0));
"""


class InvalidInput(Exception):
    pass


def canonical(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def signature(key: str, event: Dict[str, Any]) -> str:
    body = {k: v for k, v in event.items() if k != "signature" and not k.startswith("_")}
    return hmac.new(key.encode("utf-8"), canonical(body), hashlib.sha256).hexdigest()


# ---- boundary: parse files into checked shapes ----

def load_config(path: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            cfg = json.load(fh)
    except (OSError, ValueError) as exc:
        raise InvalidInput("cannot read config %s: %s" % (path, exc))
    if not isinstance(cfg, dict) or cfg.get("schema") != "payment-config.v1":
        raise InvalidInput("config %s is not schema payment-config.v1" % path)
    for field, kind in (("tenant_id", str), ("signing_key", str), ("inventory", dict)):
        if not isinstance(cfg.get(field), kind) or not cfg.get(field):
            raise InvalidInput("config %s needs a non-empty %s" % (path, field))
    for sku, n in cfg["inventory"].items():
        if not isinstance(n, int) or isinstance(n, bool) or n < 0:
            raise InvalidInput("inventory for %s must be a non-negative integer" % sku)
    return cfg


def load_events(path: str, need_signature: bool = True) -> List[Dict[str, Any]]:
    events = []
    try:
        with open(path, "r", encoding="utf-8") as fh:
            lines = fh.read().splitlines()
    except OSError as exc:
        raise InvalidInput("cannot read events %s: %s" % (path, exc))
    for n, line in enumerate(lines, 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        try:
            ev = json.loads(line)
        except ValueError as exc:
            raise InvalidInput("%s line %d is not JSON: %s" % (path, n, exc))
        if not isinstance(ev, dict) or ev.get("schema") != "payment-event.v1":
            raise InvalidInput("%s line %d is not schema payment-event.v1" % (path, n))
        for field in ("id", "type", "tenant_id", "created"):
            if not isinstance(ev.get(field), str) or not ev[field]:
                raise InvalidInput("%s line %d needs %s" % (path, n, field))
        ev["_at"] = utc(ev["created"], "%s line %d created" % (path, n))
        if not isinstance(ev.get("livemode"), bool):
            raise InvalidInput("%s line %d needs livemode true or false" % (path, n))
        if ev["type"] not in EVENT_TYPES:
            raise InvalidInput("%s line %d has unknown type %s" % (path, n, ev["type"]))
        data = ev.get("data")
        missing = [f for f in EVENT_TYPES[ev["type"]] if not isinstance(data, dict) or f not in data]
        if missing:
            raise InvalidInput("%s line %d (%s) lacks data fields %s" % (path, n, ev["id"], ", ".join(missing)))
        if need_signature and not isinstance(ev.get("signature"), str):
            raise InvalidInput("%s line %d (%s) has no signature" % (path, n, ev["id"]))
        events.append(ev)
    return events


def utc(value: str, where: str) -> str:
    """ISO 8601 with a timezone, normalized to a sortable UTC string. Entitlement changes are ordered by it."""
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        raise InvalidInput("%s is not an ISO 8601 time: %r" % (where, value))
    if dt.tzinfo is None:
        raise InvalidInput("%s needs a timezone: %r" % (where, value))
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")


# ---- store ----

def connect(db_path: str, cfg: Dict[str, Any]) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, timeout=30, isolation_level=None)
    conn.executescript(SCHEMA)
    conn.execute("BEGIN IMMEDIATE")
    for sku, n in cfg["inventory"].items():
        conn.execute("INSERT OR IGNORE INTO inventory (sku, on_hand) VALUES (?, ?)", (sku, n))
    conn.execute("COMMIT")
    return conn


def _insert(conn: sqlite3.Connection, sql: str, args: Tuple[Any, ...]) -> bool:
    """True when the row was new; False when its key already existed (the idempotent no-op)."""
    return conn.execute(sql, args).rowcount == 1


def apply_event(conn: sqlite3.Connection, ev: Dict[str, Any]) -> str:
    """Apply one verified event inside the caller's transaction and return its outcome."""
    d = ev["data"]
    if not _insert(conn, "INSERT OR IGNORE INTO events (event_id, type, outcome) VALUES (?, ?, 'pending')", (ev["id"], ev["type"])):
        return "duplicate-event"
    if ev["type"] == "checkout.completed":
        # The order id is the idempotency key the fake provider receives for the capture.
        if not _insert(conn, "INSERT OR IGNORE INTO captures VALUES (?, ?, ?, ?)", (d["order_id"], d["amount"], d["currency"], ev["id"])):
            outcome = "duplicate-order"
        else:
            conn.execute("INSERT OR IGNORE INTO orders VALUES (?, ?, ?)", (d["order_id"], d["customer_id"], d["sku"]))
            try:
                conn.execute("UPDATE inventory SET on_hand = on_hand - ? WHERE sku = ?", (d["quantity"], d["sku"]))
                stocked = conn.execute("SELECT 1 FROM inventory WHERE sku = ?", (d["sku"],)).fetchone()
            except sqlite3.IntegrityError:
                stocked = None
            if stocked is None:
                conn.execute("INSERT OR IGNORE INTO holds VALUES (?, ?, ?)", (d["order_id"], "insufficient inventory for %s" % d["sku"], ev["id"]))
                outcome = "needs-human"
            else:
                conn.execute("INSERT INTO fulfillments VALUES (?, ?, ?, ?)", (d["order_id"], d["sku"], d["quantity"], ev["id"]))
                # Only a newer event changes an entitlement, so a cancel that arrives before its checkout wins.
                conn.execute("INSERT INTO entitlements (customer_id, sku, state, changed_at) VALUES (?, ?, 'active', ?) "
                             "ON CONFLICT (customer_id, sku) DO UPDATE SET state = 'active', changed_at = excluded.changed_at "
                             "WHERE entitlements.changed_at <= excluded.changed_at", (d["customer_id"], d["sku"], ev["_at"]))
                outcome = "fulfilled"
    elif ev["type"] == "charge.refunded":
        order = conn.execute("SELECT customer_id, sku FROM orders WHERE order_id = ?", (d["order_id"],)).fetchone()
        if order is None:
            outcome = "needs-human"
            conn.execute("INSERT OR IGNORE INTO holds VALUES (?, ?, ?)", (d["order_id"], "refund for an order this integration never captured", ev["id"]))
        elif not _insert(conn, "INSERT OR IGNORE INTO refunds VALUES (?, ?, ?)", (d["order_id"], d["amount"], ev["id"])):
            outcome = "duplicate-refund"
        else:
            conn.execute("UPDATE entitlements SET state = 'revoked', changed_at = ? WHERE customer_id = ? AND sku = ? AND changed_at <= ?",
                         (ev["_at"], order[0], order[1], ev["_at"]))
            outcome = "refunded"
    else:  # subscription.canceled
        conn.execute("INSERT INTO entitlements (customer_id, sku, state, export_offered, changed_at) VALUES (?, ?, 'canceled', 1, ?) "
                     "ON CONFLICT (customer_id, sku) DO UPDATE SET state = 'canceled', export_offered = 1, changed_at = excluded.changed_at "
                     "WHERE entitlements.changed_at <= excluded.changed_at", (d["customer_id"], d["sku"], ev["_at"]))
        outcome = "canceled-export-offered"
    conn.execute("UPDATE events SET outcome = ? WHERE event_id = ?", (outcome, ev["id"]))
    return outcome


def refusal(cfg: Dict[str, Any], ev: Dict[str, Any]) -> str:
    if not hmac.compare_digest(ev["signature"], signature(cfg["signing_key"], ev)):
        return "refused-bad-signature"
    if ev["livemode"]:
        return "refused-live-mode"
    if ev["tenant_id"] != cfg["tenant_id"]:
        return "refused-tenant-mismatch"
    return ""


def counts(conn: sqlite3.Connection) -> Dict[str, int]:
    out = {}
    for table in ("events", "captures", "fulfillments", "holds", "refunds"):
        out[table] = conn.execute("SELECT COUNT(*) FROM %s" % table).fetchone()[0]
    return out


def process(cfg: Dict[str, Any], events: List[Dict[str, Any]], db_path: str) -> Dict[str, Any]:
    conn = connect(db_path, cfg)
    results = []
    for ev in events:
        refused = refusal(cfg, ev)
        if refused:
            results.append({"event_id": ev["id"], "outcome": refused})
            continue
        conn.execute("BEGIN IMMEDIATE")
        try:
            outcome = apply_event(conn, ev)
            conn.execute("COMMIT")
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        results.append({"event_id": ev["id"], "outcome": outcome})
    inventory = dict(conn.execute("SELECT sku, on_hand FROM inventory").fetchall())
    entitlements = [dict(zip(("customer_id", "sku", "state", "export_offered"), r))
                    for r in conn.execute("SELECT customer_id, sku, state, export_offered FROM entitlements ORDER BY customer_id, sku")]
    totals = counts(conn)
    conn.close()
    tally: Dict[str, int] = {}
    for r in results:
        tally[r["outcome"]] = tally.get(r["outcome"], 0) + 1
    return {"mode": "test", "events": results, "outcomes": tally, "store": totals, "inventory": inventory,
            "entitlements": entitlements, "live_calls": 0,
            "not_checked": ["real provider API behavior", "tax, shipping and currency conversion", "card-network chargeback rules"]}


def reconcile(db_path: str) -> Dict[str, Any]:
    conn = sqlite3.connect(db_path)
    mismatches = []
    q = conn.execute
    for (key,) in q("SELECT idempotency_key FROM captures WHERE idempotency_key NOT IN (SELECT order_id FROM fulfillments) "
                    "AND idempotency_key NOT IN (SELECT order_id FROM holds)"):
        mismatches.append({"code": "capture-without-fulfillment", "order_id": key})
    for (key,) in q("SELECT order_id FROM fulfillments WHERE order_id NOT IN (SELECT idempotency_key FROM captures)"):
        mismatches.append({"code": "fulfillment-without-capture", "order_id": key})
    for (key,) in q("SELECT order_id FROM refunds WHERE order_id NOT IN (SELECT idempotency_key FROM captures)"):
        mismatches.append({"code": "refund-without-capture", "order_id": key})
    for key, refunded, captured in q("SELECT r.order_id, r.amount, c.amount FROM refunds r JOIN captures c ON c.idempotency_key = r.order_id WHERE r.amount > c.amount"):
        mismatches.append({"code": "refund-exceeds-capture", "order_id": key, "refunded": refunded, "captured": captured})
    holds = [dict(zip(("order_id", "reason"), r)) for r in q("SELECT order_id, reason FROM holds ORDER BY order_id")]
    captured = q("SELECT COALESCE(SUM(amount), 0) FROM captures").fetchone()[0]
    refunded = q("SELECT COALESCE(SUM(amount), 0) FROM refunds").fetchone()[0]
    totals = counts(conn)
    conn.close()
    return {"mismatches": mismatches, "holds_for_human": holds, "captured_total": captured, "refunded_total": refunded,
            "net": captured - refunded, "store": totals, "status": "reconciled" if not mismatches and not holds else "needs-attention"}


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(prog="payment_events")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sign")
    s.add_argument("--config", required=True)
    s.add_argument("--events", required=True)
    p = sub.add_parser("process")
    p.add_argument("--config", required=True)
    p.add_argument("--events", required=True)
    p.add_argument("--db", required=True, help="SQLite file for the disposable test store")
    r = sub.add_parser("reconcile")
    r.add_argument("--db", required=True)
    args = ap.parse_args(argv)
    try:
        if args.cmd == "sign":
            cfg = load_config(args.config)
            with open(args.events, "r", encoding="utf-8") as fh:
                for line in fh:
                    if line.lstrip().startswith("#"):
                        sys.stdout.write(line)
            for ev in load_events(args.events, need_signature=False):
                ev["signature"] = signature(cfg["signing_key"], ev)
                sys.stdout.write(json.dumps({k: v for k, v in ev.items() if not k.startswith("_")}, sort_keys=True) + "\n")
            return 0
        if args.cmd == "process":
            result = process(load_config(args.config), load_events(args.events), args.db)
            bad = [e for e in result["events"] if e["outcome"].startswith("refused") or e["outcome"] == "needs-human"]
            result["status"] = "needs-attention" if bad else "ok"
            print(json.dumps(result, indent=2, sort_keys=True))
            return 1 if bad else 0
        result = reconcile(args.db)
        print(json.dumps(result, indent=2, sort_keys=True))
        return 0 if result["status"] == "reconciled" else 1
    except InvalidInput as exc:
        print(json.dumps({"error": str(exc)}, indent=2))
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
