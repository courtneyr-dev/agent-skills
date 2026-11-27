#!/usr/bin/env python3
"""Lint a community measurement plan, then compute its consent-aware aggregates.

lint: each metric needs a question, a definition, a source (a CHAOSS metric page, a TODO Group guide,
or a local definition with a rationale), a community, cohort or channel level, a consent basis and a
minimum group size of at least 5. It refuses per-person rankings, inferred burnout or protected traits,
composite scores without published components and weights, metrics over moderation cases, and
participation counted as sales leads.

aggregate: computes only a plan that lints clean. It drops confidential or restricted records,
moderation cases and members who withdrew consent, suppresses any value drawn from fewer people than
the metric's minimum group size, and never prints a person's identifier.

Usage: measures.py lint PLAN.json
       measures.py aggregate --plan PLAN.json --activity ACTIVITY.json
Exit 0: ok. Exit 1: the plan breaks a rule. Exit 2: invalid input.
"""
import argparse
import json
import re
import statistics
import sys
from datetime import datetime

VERSION = "1.0.0"
LEVELS = {"community", "cohort", "channel"}
PUBLISH = {"public", "internal"}
MIN_GROUP_FLOOR = 5
CONFIDENTIAL = {"confidential", "restricted"}
CASE_TYPES = {"moderation-case", "conduct-report"}
KINDS = {"count", "distinct-people", "median-hours"}
RANKING = re.compile(r"\b(rank(ed|ing|ings|s)?|leaderboards?|top \d*\s*(contributors?|members?|volunteers?|maintainers?)"
                     r"|most active|least active|per[- ](person|member|volunteer|contributor|maintainer))\b", re.I)
INFERENCE = re.compile(r"\b(burn-?out|mental health|well-?being|mood|gender|race|racial|ethnicity|age|disabilit(y|ies)"
                       r"|religion|religious|sexual orientation|nationality|pregnan\w*|personality)\b", re.I)
SALES = re.compile(r"\b(sales|leads? (generation|scoring|capture|lists?)|lead-gen|prospects?|MQLs?|SQLs?"
                   r"|conversion to paid|upsell(ing)?)\b", re.I)
CASE_WORDS = re.compile(r"\b(moderation|conduct reports?|code of conduct (reports?|complaints?|cases?|violations?)"
                        r"|coc (complaints?|reports?|cases?|violations?)|complaints?|case log|sanctions?|bans?|banned)\b", re.I)
COMPOSITE = re.compile(r"\b(health score|community score|engagement score|index)\b", re.I)


class InputError(Exception):
    pass


def load(path, kind):
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError) as exc:
        raise InputError("%s: %s" % (path, exc))
    key = "metrics" if kind == "plan" else "records"
    if not isinstance(doc, dict) or not isinstance(doc.get(key), list):
        raise InputError("%s needs a %r list" % (kind, key))
    for i, item in enumerate(doc[key]):
        if not isinstance(item, dict):
            raise InputError("%s.%s[%d] is not an object" % (kind, key, i))
        if kind == "plan" and not isinstance(item.get("id"), str):
            raise InputError("plan.metrics[%d] has no string id" % i)
    return doc


def lint(plan):
    """Return violations {metric, rule, message}. Pure: no I/O."""
    out = []
    ids = {m["id"] for m in plan["metrics"]}
    for m in plan["metrics"]:
        def v(rule, message):
            out.append({"metric": m["id"], "rule": rule, "message": message})

        text = " ".join(str(m.get(k, "")) for k in ("id", "question", "definition")).replace("-", " ")
        if len(str(m.get("question", ""))) < 10:
            v("undefined-metric", "state the question this metric answers")
        if len(str(m.get("definition", ""))) < 20:
            v("undefined-metric", "write a definition someone else could compute")
        src = m.get("source") if isinstance(m.get("source"), dict) else {}
        kind = src.get("kind")
        if kind == "chaoss" and not str(src.get("url", "")).startswith("https://chaoss.community/"):
            v("unsourced", "a CHAOSS source needs its chaoss.community metric URL")
        elif kind == "todo-group" and not str(src.get("url", "")).startswith("https://todogroup.org/"):
            v("unsourced", "a TODO Group source needs its todogroup.org guide URL")
        elif kind == "local" and len(str(src.get("rationale", ""))) < 20:
            v("unsourced", "a local metric needs a rationale for why no CHAOSS metric fits")
        elif kind not in ("chaoss", "todo-group", "local"):
            v("unsourced", "source.kind must be chaoss, todo-group or local")
        if m.get("level") not in LEVELS:
            v("individual-level", "level %r: report at community, cohort or channel level, never per person" % m.get("level"))
        if RANKING.search(text):
            v("ranking", "%r ranks people; report aggregates instead" % RANKING.search(text).group(0))
        if INFERENCE.search(text):
            v("inference", "%r would be inferred from activity; don't infer burnout, wellbeing or protected traits"
              % INFERENCE.search(text).group(0))
        if SALES.search(text):
            v("sales-leads", "%r turns participation into sales leads" % SALES.search(text).group(0))
        if not isinstance(m.get("min_group_size"), int) or m["min_group_size"] < MIN_GROUP_FLOOR:
            v("small-groups", "min_group_size must be an integer of at least %d" % MIN_GROUP_FLOOR)
        if len(str(m.get("consent_basis", "")).strip()) < 10:
            v("no-consent", "state the consent basis for the data this metric reads")
        if m.get("publish") not in PUBLISH:
            v("no-audience", "publish must be public or internal")
        compute = m.get("compute") if isinstance(m.get("compute"), dict) else None
        record_type = str((compute or {}).get("record_type", ""))
        if record_type in CASE_TYPES or CASE_WORDS.search(text + " " + record_type.replace("-", " ")):
            v("confidential-source", "moderation cases never feed metrics; transparency counts come from the case log with human approval")
        if compute is not None:
            if compute.get("kind") not in KINDS:
                v("uncomputable", "compute.kind must be one of %s" % ", ".join(sorted(KINDS)))
        if COMPOSITE.search(text):
            comps, weights = m.get("components"), m.get("weights")
            if not (isinstance(comps, list) and comps and set(comps) <= ids - {m["id"]}
                    and isinstance(weights, dict) and set(weights) == set(comps)
                    and abs(sum(float(w) for w in weights.values()) - 1.0) < 1e-6):
                v("undefined-composite", "a score needs published components that are metrics in this plan, with weights summing to 1")
    return out


def hours(record, start, end):
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    try:
        return (datetime.strptime(record[end], fmt) - datetime.strptime(record[start], fmt)).total_seconds() / 3600
    except (KeyError, TypeError, ValueError):
        return None


def aggregate(plan, activity):
    """Compute each metric over consented, non-confidential records. Returns no person identifiers."""
    excluded = {"confidential-or-case": 0, "consent-withdrawn": 0}
    usable = []
    for r in activity["records"]:
        if r.get("classification") in CONFIDENTIAL or r.get("type") in CASE_TYPES or r.get("category") in CASE_TYPES:
            excluded["confidential-or-case"] += 1
        elif r.get("consent") == "withdrawn":
            excluded["consent-withdrawn"] += 1
        else:
            usable.append(r)
    results = []
    for m in plan["metrics"]:
        c = m.get("compute")
        if not isinstance(c, dict):
            results.append({"id": m["id"], "computed": False, "reason": "no compute rule; collected outside this tool"})
            continue
        if COMPOSITE.search(" ".join(str(m.get(k, "")) for k in ("id", "question", "definition")).replace("-", " ")):
            results.append({"id": m["id"], "computed": False, "reason": "composite: publish its components and weights, not a single score"})
            continue
        rows = [r for r in usable if r.get("type") == c.get("record_type")
                and all(r.get(k) == val for k, val in (c.get("filter") or {}).items())]
        people = {r.get("person") for r in rows if r.get("person")}
        if len(people) < m["min_group_size"]:
            results.append({"id": m["id"], "computed": False, "suppressed": True,
                            "reason": "fewer than %d people in the group" % m["min_group_size"]})
            continue
        if c["kind"] == "count":
            value, unit = len(rows), "records"
        elif c["kind"] == "distinct-people":
            value, unit = len(people), "people"
        else:
            spans = [h for h in (hours(r, c.get("start"), c.get("end")) for r in rows) if h is not None]
            value, unit = (round(statistics.median(spans), 1) if spans else None), "hours (median)"
        results.append({"id": m["id"], "computed": True, "value": value, "unit": unit,
                        "level": m["level"], "publish": m["publish"]})
    return {"tool": "community-health-measures", "version": VERSION, "community": plan.get("community"),
            "metrics": results, "excluded_records": excluded,
            "note": "aggregates only; no person identifiers; suppressed values are withheld, not estimated"}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Lint a community measurement plan and compute consent-aware aggregates.")
    sub = ap.add_subparsers(dest="cmd", required=True)
    lp = sub.add_parser("lint")
    lp.add_argument("plan")
    ag = sub.add_parser("aggregate")
    ag.add_argument("--plan", required=True)
    ag.add_argument("--activity", required=True)
    args = ap.parse_args(argv)
    try:
        plan = load(args.plan, "plan")
        activity = load(args.activity, "activity") if args.cmd == "aggregate" else None
    except InputError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 2
    violations = lint(plan)
    if violations or args.cmd == "lint":
        print(json.dumps({"ok": not violations, "metrics": len(plan["metrics"]), "violations": violations}, indent=2))
        return 1 if violations else 0
    print(json.dumps(dict(aggregate(plan, activity), ok=True), indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
