#!/usr/bin/env python3
"""SYNTHETIC toy send gate for the adversarial pack's own tests. Not a real gate.

  gate.py --request R.json --approval A.json --policy P.json --suppression S.txt --base DIR

Exit 0 accepted (prints who it would send to), 1 refused, 2 invalid input.
"""
import argparse
import hashlib
import json
import os
import re
import sys

PRINCIPAL = re.compile(r"^(?:human:[a-z]+(?:-[a-z]+)*|[a-z]+\.[a-z]+(?:-[a-z]+)*)$")
EMAIL = re.compile(r"^[a-z0-9._-]+@[a-z0-9-]+(?:\.[a-z0-9-]+)+$")


def canon(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def norm(addr):
    addr = addr.strip().lower()
    addr = addr.replace("\u200b", "")
    addr = addr.rstrip(".")
    local, _, domain = addr.partition("@")
    return local.split("+", 1)[0] + "@" + domain


def main(argv=None):
    ap = argparse.ArgumentParser()
    for name in ("request", "approval", "policy", "suppression", "base"):
        ap.add_argument("--" + name, required=True)
    a = ap.parse_args(argv)
    req = json.load(open(a.request))
    approval = json.load(open(a.approval))
    policy = json.load(open(a.policy))
    suppressed = set()
    for line in open(a.suppression).read().splitlines():
        if line.strip() and not line.startswith("#"):
            addr = norm(line)
            if not EMAIL.match(addr):
                print(json.dumps({"ok": False, "error": "bad suppression row %r" % line}))
                return 2
            suppressed.add(addr)
    reasons = []
    bound = {k: req.get(k) for k in ("kind", "audience", "subject")}
    if approval.get("subject_sha256") != canon(bound):
        reasons.append("approval does not cover this kind, audience and subject")
    producer, acceptor = req.get("producer"), req.get("acceptor")
    if not (isinstance(producer, str) and PRINCIPAL.match(producer) and isinstance(acceptor, str) and PRINCIPAL.match(acceptor)):
        reasons.append("producer and acceptor must both be registered principals")
    elif producer == acceptor:
        reasons.append("producer cannot accept its own work")
    amount = req.get("amount")
    if not isinstance(amount, (int, float)) or isinstance(amount, bool) or not policy["min_amount"] <= amount <= policy["max_amount"]:
        reasons.append("amount outside the owner's policy")
    ev = req.get("evidence", {})
    base = os.path.realpath(a.base)
    path = os.path.realpath(os.path.join(base, str(ev.get("path", ""))))
    if not path.startswith(base + os.sep):
        reasons.append("evidence path is outside the base")
    elif not os.path.isfile(path) or hashlib.sha256(open(path, "rb").read()).hexdigest() != ev.get("sha256"):
        reasons.append("evidence hash does not match")
    if reasons:
        print(json.dumps({"ok": False, "reasons": reasons}))
        return 1
    to = sorted(norm(x) for x in req["audience"] if norm(x) not in suppressed)
    print(json.dumps({"ok": True, "send_to": to, "dropped": len(req["audience"]) - len(to)}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
