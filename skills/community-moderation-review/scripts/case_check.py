#!/usr/bin/env python3
"""Check an agent-drafted moderation recommendation against its case record.

A draft is advice for the human decision maker the case names. This check refuses a draft that
decides an allegation, issues a sanction, sends a message, cites records the case doesn't hold,
ignores a conflict of interest, changes the appeal route, or puts case details in a public output.

Usage: case_check.py --case CASE.json --draft DRAFT.json
Exit 0: the draft stays inside an agent's authority. Exit 1: violations listed. Exit 2: invalid input.
"""
import argparse
import json
import re
import sys

VERSION = "1.0.0"
AGENT_FINDINGS = {"unproven", "needs-information"}
DRAFT_ACTIONS = {"recommended", "draft"}
DRAFT_STATUS = "draft-for-human-decision"
# Fields an agent's draft keeps between itself and the decision maker. Everything else, and any message
# not addressed to a party, is treated as public.
INTERNAL = {"label", "case_id", "prepared_by", "status", "findings", "recommended_actions", "handling",
            "appeal_route", "untrusted_content_noted", "messages"}
QUOTE_WORDS = 6
CONCLUSIVE = re.compile(
    r"\b(guilty|proven|substantiated|clearly violated|violated the code of conduct|beyond (any )?doubt"
    r"|is an? (harasser|abuser|troll|bully))\b", re.I)


class InputError(Exception):
    pass


def need(obj, key, kind, where):
    if not isinstance(obj, dict) or not isinstance(obj.get(key), kind):
        raise InputError("%s.%s is missing or not a %s" % (where, key, kind.__name__ if isinstance(kind, type) else "valid value"))
    return obj[key]


def parse_case(case):
    for key, kind in (("case_id", str), ("parties", list), ("reports", list), ("evidence", list),
                      ("moderators", list), ("authority", dict), ("appeal_route", dict)):
        need(case, key, kind, "case")
    need(case["authority"], "decision_maker", str, "case.authority")
    need(case["appeal_route"], "reviewer", str, "case.appeal_route")
    need(case["appeal_route"], "window_days", int, "case.appeal_route")
    for coll in ("parties", "reports", "evidence", "moderators"):
        for i, item in enumerate(case[coll]):
            need(item, "id", str, "case.%s[%d]" % (coll, i))
    for i, m in enumerate(case["moderators"]):
        need(m, "conflicts", list, "case.moderators[%d]" % i)
    return case


def parse_draft(draft):
    for key, kind in (("case_id", str), ("prepared_by", str), ("status", str), ("findings", list),
                      ("recommended_actions", list), ("handling", dict)):
        need(draft, key, kind, "draft")
    need(draft["handling"], "assigned_reviewers", list, "draft.handling")
    need(draft["handling"], "recused", list, "draft.handling")
    for i, f in enumerate(draft["findings"]):
        for key, kind in (("report", str), ("status", str), ("evidence", list), ("reasoning", str)):
            need(f, key, kind, "draft.findings[%d]" % i)
    for i, a in enumerate(draft["recommended_actions"]):
        for key in ("action", "status", "decision_by"):
            need(a, key, str, "draft.recommended_actions[%d]" % i)
    for i, msg in enumerate(draft.get("messages", [])):
        need(msg, "status", str, "draft.messages[%d]" % i)
    return draft


def check(case, draft):
    """Return a list of violations, each {rule, where, message}. Pure: no I/O."""
    out = []

    def v(rule, where, message):
        out.append({"rule": rule, "where": where, "message": message})

    reports = {r["id"] for r in case["reports"]}
    evidence = {e["id"]: e for e in case["evidence"]}
    parties = {p["id"] for p in case["parties"]}
    decider = case["authority"]["decision_maker"]
    appeal = case["appeal_route"]
    conflicted = {m["id"]: [c.get("with") for c in m["conflicts"] if c.get("with") in parties]
                  for m in case["moderators"]}
    conflicted = {k: w for k, w in conflicted.items() if w}

    if draft["case_id"] != case["case_id"]:
        v("case-mismatch", "case_id", "draft is for %s, case is %s" % (draft["case_id"], case["case_id"]))
    if draft["status"] != DRAFT_STATUS:
        v("draft-marked-final", "status", "an agent's output stays %r until %s decides; got %r" % (DRAFT_STATUS, decider, draft["status"]))

    for i, f in enumerate(draft["findings"]):
        where = "findings[%d]" % i
        if f["report"] not in reports:
            v("invented-record", where + ".report", "%s is not a report in the case log" % f["report"])
        for e in f["evidence"]:
            if e not in evidence:
                v("invented-record", where + ".evidence", "%s is not evidence in the case log" % e)
            elif evidence[e].get("available") is False:
                v("unavailable-evidence", where + ".evidence", "%s is described but not held, so it can't support a finding" % e)
        if f["status"] not in AGENT_FINDINGS:
            v("decided-allegation", where + ".status", "an agent may record only %s; %r is %s's call"
              % (" or ".join(sorted(AGENT_FINDINGS)), f["status"], decider))
        if CONCLUSIVE.search(f["reasoning"]):
            v("conclusive-language", where + ".reasoning", "reasoning states a verdict (%r); describe what the evidence shows instead"
              % CONCLUSIVE.search(f["reasoning"]).group(0))

    for i, a in enumerate(draft["recommended_actions"]):
        where = "recommended_actions[%d]" % i
        if a["status"] not in DRAFT_ACTIONS:
            v("sanction-issued", where + ".status", "%r: an agent recommends; only %s acts" % (a["status"], decider))
        if a["decision_by"] != decider:
            v("wrong-decider", where + ".decision_by", "%s is not the case's decision maker %s" % (a["decision_by"], decider))

    assigned = draft["handling"]["assigned_reviewers"]
    recused = {r.get("id") for r in draft["handling"]["recused"] if isinstance(r, dict)}
    for mod, withs in sorted(conflicted.items()):
        if mod in assigned:
            v("conflict-not-recused", "handling.assigned_reviewers", "%s has a conflict with %s and can't review" % (mod, ", ".join(withs)))
        if mod not in recused:
            v("conflict-not-recused", "handling.recused", "%s has a declared conflict and must be listed as recused" % mod)
    if draft["prepared_by"] in assigned:
        v("self-review", "handling.assigned_reviewers", "%s prepared the draft and can't review it" % draft["prepared_by"])
    roster = {m["id"] for m in case["moderators"]}
    for r in assigned:
        if r in parties:
            v("party-as-reviewer", "handling.assigned_reviewers", "%s is a party to the case and can't review it" % r)
        elif r not in roster and r != draft["prepared_by"]:
            v("unknown-reviewer", "handling.assigned_reviewers", "%s isn't one of the case's moderators" % r)
    for who, label in ((decider, "decision maker"), (appeal["reviewer"], "appeal reviewer")):
        if who in conflicted:
            v("conflicted-authority", "case", "the case's %s %s has a conflict; escalate before any decision" % (label, who))

    route = draft.get("appeal_route")
    if not isinstance(route, dict):
        v("appeal-route-dropped", "appeal_route", "the draft must carry the case's appeal route unchanged")
    else:
        if route.get("reviewer") != appeal["reviewer"]:
            v("appeal-route-changed", "appeal_route.reviewer", "%s replaced %s" % (route.get("reviewer"), appeal["reviewer"]))
        if not isinstance(route.get("window_days"), int) or route["window_days"] < appeal["window_days"]:
            v("appeal-route-changed", "appeal_route.window_days", "window %r is shorter than the policy's %d days"
              % (route.get("window_days"), appeal["window_days"]))
        if route.get("documented_in") != appeal.get("documented_in"):
            v("appeal-route-changed", "appeal_route.documented_in", "the policy reference changed")
    if appeal["reviewer"] == decider:
        v("appeal-not-independent", "case.appeal_route", "the appeal reviewer is the original decision maker")

    for i, msg in enumerate(draft.get("messages", [])):
        if msg["status"] != "draft":
            v("message-sent", "messages[%d].status" % i, "%r: messages stay drafts until a human sends them" % msg["status"])

    public = [(k, json.dumps(val)) for k, val in draft.items() if k not in INTERNAL]
    public += [("messages[%d]" % i, json.dumps(m)) for i, m in enumerate(draft.get("messages", []))
               if m.get("to") not in parties]
    identifiers = {case["case_id"]} | reports | set(evidence) | parties
    quotes = {(r["id"], q) for r in case["reports"] for q in shingles(str(r.get("text", "")))}
    for where, text in public:
        for ident in sorted(identifiers):
            if re.search(r"(?<![\w-])%s(?![\w-])" % re.escape(ident), text, re.I):
                v("public-leak", where, "%s from a confidential case appears in a public output" % ident)
        said = shingles(text)
        for rid in sorted({rid for rid, q in quotes if q in said}):
            v("public-leak", where, "quotes the text of report %s" % rid)
    return out


def shingles(text):
    words = re.findall(r"[a-z0-9']+", text.lower())
    return {" ".join(words[i:i + QUOTE_WORDS]) for i in range(len(words) - QUOTE_WORDS + 1)}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Check a drafted moderation recommendation against its case record.")
    ap.add_argument("--case", required=True)
    ap.add_argument("--draft", required=True)
    args = ap.parse_args(argv)
    try:
        with open(args.case, encoding="utf-8") as fh:
            case = parse_case(json.load(fh))
        with open(args.draft, encoding="utf-8") as fh:
            draft = parse_draft(json.load(fh))
    except (OSError, ValueError, InputError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 2
    violations = check(case, draft)
    print(json.dumps({
        "tool": "community-moderation-review", "version": VERSION, "case_id": case["case_id"],
        "ok": not violations, "violations": violations,
        "authority": "advisory: %s decides the case; this check only bounds what an agent may draft" % case["authority"]["decision_maker"],
    }, indent=2))
    return 0 if not violations else 1


if __name__ == "__main__":
    sys.exit(main())
