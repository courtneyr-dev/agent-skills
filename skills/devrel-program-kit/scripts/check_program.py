#!/usr/bin/env python3
"""Check a developer-program plan for the claims a DevRel kit must not make.

Refuses: no explicit non-goals; no usefulness metric; a metric without a definition, instrumentation
or owner; an executive headline built only from reach or business metrics; a business metric without
written attribution limits, or causal revenue wording; quotes, testimonials, customer results,
conference acceptances or case studies without a retained source (quotes and testimonials also need
consent); budget or staffing figures without a source; a context record other than the tenant's
devrel-context.md; a runnable chain artifact without clean-replay evidence; and human usability
marked verified without a human session on record.

Evidence, session records, claim sources and consent are paths to files that must exist under --base
(default: the current directory). Replay evidence must be a passing devrel-quickstart-replay report, and
when the artifact is a file, the report's doc_sha256 must match its current bytes.

Usage: check_program.py PROGRAM.json [--base DIR]
Exit 0: clean. Exit 1: violations listed. Exit 2: invalid input.
"""
import argparse
import hashlib
import json
import os
import re
import sys

VERSION = "1.0.0"
CLASSES = {"reach", "usefulness", "business"}
SOURCED = {"quote", "testimonial", "customer-result", "conference-acceptance", "case-study", "revenue"}
CONSENTED = {"quote", "testimonial"}
RUNNABLE = {"quickstart", "tutorial", "workshop-lab", "demo", "sample-app", "repro"}
CAUSAL = re.compile(r"\b(drove|driven by|caused|generated|resulted in|led to|thanks to (our|the) (devrel|docs|program))\b", re.I)


class InputError(Exception):
    pass


def parse(doc):
    if not isinstance(doc, dict):
        raise InputError("program must be a JSON object")
    for key in ("goals", "non_goals", "metrics", "claims", "reports", "chain"):
        if not isinstance(doc.get(key), list):
            raise InputError("program.%s must be a list" % key)
    for key in ("budget", "staffing"):
        if not isinstance(doc.get(key), dict):
            raise InputError("program.%s must be an object" % key)
    for i, m in enumerate(doc["metrics"]):
        if not isinstance(m, dict) or not isinstance(m.get("id"), str):
            raise InputError("program.metrics[%d] needs a string id" % i)
    return doc


def record(base, rel):
    """The path of an existing file under base, or None."""
    if not isinstance(rel, str) or not rel.strip():
        return None
    path = os.path.join(base, rel)
    return path if os.path.isfile(path) else None


def replay_problem(base, step):
    """Why a chain step's evidence doesn't prove a clean replay of its artifact, or None."""
    ev = record(base, step.get("evidence"))
    if step.get("verified_by") != "devrel-quickstart-replay" or ev is None:
        return "needs a clean replay with retained evidence; %r isn't a file under the base" % step.get("evidence")
    with open(ev, encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    if '"tool": "devrel-quickstart-replay"' not in text or '"ok": true' not in text:
        return "evidence %s isn't a passing devrel-quickstart-replay report" % step["evidence"]
    art = record(base, step.get("artifact"))
    if art is not None:
        with open(art, "rb") as fh:
            if hashlib.sha256(fh.read()).hexdigest() not in text:
                return "evidence %s replayed a different version of %s" % (step["evidence"], step["artifact"])
    return None


def check(p, base="."):
    """Return violations {rule, where, message}. Reads only the files the plan names under base."""
    out = []

    def v(rule, where, message):
        out.append({"rule": rule, "where": where, "message": message})

    if not p["non_goals"]:
        v("no-non-goals", "non_goals", "state what the program won't do")
    metrics = {m["id"]: m for m in p["metrics"]}
    for i, m in enumerate(p["metrics"]):
        where = "metrics[%d]" % i
        if m.get("class") not in CLASSES:
            v("undefined-metric", where + ".class", "class must be reach, usefulness or business")
        for f in ("definition", "instrumentation", "owner"):
            if len(str(m.get(f, ""))) < 3:
                v("undefined-metric", "%s.%s" % (where, f), "%s %s is missing" % (m["id"], f))
        if m.get("class") == "business":
            if len(str(m.get("attribution", ""))) < 20:
                v("causal-revenue", where + ".attribution", "%s needs written attribution limits" % m["id"])
            if CAUSAL.search(str(m.get("definition", ""))):
                v("causal-revenue", where + ".definition", "%r asserts causation the data can't show" % CAUSAL.search(m["definition"]).group(0))
    if not any(m.get("class") == "usefulness" for m in metrics.values()):
        v("no-usefulness-metric", "metrics", "add one: successful developer tasks, repeat use, friction removed, feedback closure or contribution outcomes")
    for i, r in enumerate(p["reports"]):
        heads = r.get("headline_metrics", []) if isinstance(r, dict) else []
        for h in heads:
            if h not in metrics:
                v("unknown-metric", "reports[%d]" % i, "%s isn't defined in metrics" % h)
        if heads and not any(metrics.get(h, {}).get("class") == "usefulness" for h in heads):
            v("reach-headline", "reports[%d]" % i, "the %s headline has no usefulness metric; reach isn't success" % r.get("audience", "report"))
    for i, c in enumerate(p["claims"]):
        where = "claims[%d]" % i
        kind = c.get("kind") if isinstance(c, dict) else None
        if kind not in SOURCED:
            v("unknown-claim", where, "claim kind %r can't be checked; use %s, or cut the claim" % (kind, ", ".join(sorted(SOURCED))))
            continue
        if record(base, c.get("source")) is None:
            v("fabrication-risk", where, "a %s needs a retained source record file; %r isn't one" % (kind, c.get("source")))
        if kind in CONSENTED and record(base, c.get("consent")) is None:
            v("fabrication-risk", where, "a %s needs the speaker's recorded consent file; %r isn't one" % (kind, c.get("consent")))
        if kind == "revenue" and CAUSAL.search(str(c.get("text", ""))):
            v("causal-revenue", where, "%r asserts causation the data can't show" % CAUSAL.search(c["text"]).group(0))
    for key in ("budget", "staffing"):
        b = p[key]
        if b.get("status") not in ("provided", "owner-to-provide"):
            v("invented-budget", key, "status must be provided (with a source) or owner-to-provide")
        elif b["status"] == "provided" and len(str(b.get("source", ""))) < 5:
            v("invented-budget", key, "%s figures need the owner's source record" % key)
        elif b["status"] == "owner-to-provide" and any(k in b for k in ("amount", "headcount")):
            v("invented-budget", key, "figures appear while the owner hasn't provided any")
    if not str(p.get("context_record", "")).endswith("devrel-context.md"):
        v("competing-context", "context_record", "program state lives in the tenant's devrel-context.md, not a new store")
    for i, s in enumerate(p["chain"]):
        where = "chain[%d]" % i
        if not isinstance(s, dict):
            continue
        problem = replay_problem(base, s) if s.get("type") in RUNNABLE else None
        if problem:
            v("untested-chain", where, "%s %s %s" % (s.get("type"), s.get("artifact"), problem))
        if s.get("human_usability") == "verified" and record(base, s.get("human_evidence")) is None:
            v("unmeasured-usability", where, "human usability is verified only by a recorded session file with real readers; %r isn't one"
              % s.get("human_evidence"))
        elif s.get("human_usability") not in ("verified", "unverified"):
            v("unmeasured-usability", where, "human_usability must be verified (with human_evidence) or unverified")
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Check a developer-program plan's claims.")
    ap.add_argument("program")
    ap.add_argument("--base", default=".", help="directory that evidence, session, source and consent paths are relative to")
    args = ap.parse_args(argv)
    try:
        with open(args.program, encoding="utf-8") as fh:
            program = parse(json.load(fh))
    except (OSError, ValueError, InputError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 2
    violations = check(program, args.base)
    print(json.dumps({"tool": "devrel-program-kit/check_program", "version": VERSION,
                      "ok": not violations, "violations": violations}, indent=2))
    return 0 if not violations else 1


if __name__ == "__main__":
    sys.exit(main())
