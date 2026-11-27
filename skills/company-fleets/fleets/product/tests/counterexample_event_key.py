#!/usr/bin/env python3
"""Counterexample for the payment idempotency eval: does the replay fixture catch a naive processor?

Copies product-payment-events' processor into a temporary directory and mutates it to key captures and
fulfillments on the webhook event id instead of the order id (dedupe by event only). Runs the real and
the mutant processor on the same replay fixture and prints both store counts.

Exit 0 when the mutant's counts differ from the real ones (the fixture discriminates), 1 when they match
(the fixture would miss the regression), 2 when the mutation target is gone (the processor drifted).
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile

SKILL = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "..", "product-payment-events"))
SCRIPT = os.path.join(SKILL, "scripts", "payment_events.py")
MUTATIONS = [
    ('"INSERT OR IGNORE INTO captures VALUES (?, ?, ?, ?)", (d["order_id"],', '"INSERT OR IGNORE INTO captures VALUES (?, ?, ?, ?)", (ev["id"],'),
    ('"INSERT INTO fulfillments VALUES (?, ?, ?, ?)", (d["order_id"],', '"INSERT INTO fulfillments VALUES (?, ?, ?, ?)", (ev["id"],'),
]


def run(script, db):
    p = subprocess.run([sys.executable, script, "process", "--config", os.path.join(SKILL, "fixtures", "config.json"),
                        "--events", os.path.join(SKILL, "fixtures", "replay.jsonl"), "--db", db], capture_output=True, text=True)
    out = json.loads(p.stdout)
    return {"captures": out["store"]["captures"], "fulfillments": out["store"]["fulfillments"],
            "inventory": out["inventory"]["forms-pro-annual"]}


def main():
    with open(SCRIPT, encoding="utf-8") as fh:
        source = fh.read()
    for old, new in MUTATIONS:
        if source.count(old) != 1:
            print(json.dumps({"error": "mutation target not found; the processor changed: %s" % old}))
            return 2
        source = source.replace(old, new)
    tmp = tempfile.mkdtemp(prefix="pe-mutant-")
    try:
        mutant = os.path.join(tmp, "payment_events_mutant.py")
        with open(mutant, "w", encoding="utf-8") as fh:
            fh.write(source)
        real = run(SCRIPT, os.path.join(tmp, "real.db"))
        bad = run(mutant, os.path.join(tmp, "mutant.db"))
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    caught = real != bad
    print(json.dumps({"label": "SYNTHETIC Fixture Co replay fixture", "mutation": "captures and fulfillments keyed on event id",
                      "real_captures": real["captures"], "mutant_captures": bad["captures"],
                      "real": real, "mutant": bad, "fixture_catches_regression": caught}, indent=2, sort_keys=True))
    return 0 if caught else 1


if __name__ == "__main__":
    sys.exit(main())
