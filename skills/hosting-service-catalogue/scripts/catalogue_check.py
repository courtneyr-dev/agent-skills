#!/usr/bin/env python3
"""catalogue_check: check a hosting service catalogue against one operating profile.

  check  --catalogue F   verdict, violations and assumptions (exit 0 pass, 1 fail)
  matrix --catalogue F [--format json|markdown]   a readable responsibility matrix

Profiles come only from the rig registry, company-fleets/registry/profiles.json, at its fixed path;
--profiles is refused by name unless it names that file. The company named as its own upstream
(upstream:fixture-co) is the company, so it carries the company's duties and limits.

Exit codes: 0 ok or check passed, 1 the check found a violation or refused, 2 invalid input or usage.
Python 3.9+ standard library only.
"""
from __future__ import annotations

import argparse
import json
import math
import os
import re
import sys
from typing import Any, Dict, List, Optional, Set, Tuple

SKILL_DIR = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
FUNCTIONS = os.path.join(SKILL_DIR, "references", "functions.json")
DEFAULT_PROFILES = os.path.normpath(os.path.join(SKILL_DIR, "..", "company-fleets", "registry", "profiles.json"))
COMPANY = "fixture-co"
SLUG = r"[a-z0-9]+(?:-[a-z0-9]+)*"
SLUG_RE = re.compile("^%s$" % SLUG)
UPSTREAM_RE = re.compile("^upstream:(%s)$" % SLUG)
PLACEHOLDERS = {"tbd", "tba", "todo", "none", "n/a", "na", "unknown", "pending", "-", "?"}
ASSUMPTIONS = [
    "Rule 1 counts distinct accountable parties per function across all services; one party listed in two services is one party.",
    "Rule 1 also applies to optional and extra functions a catalogue lists, so an optional function with two owners fails.",
    "Rule 2 refuses the company as accountable or responsible for a must_not_hold function. In a referral_only profile (affiliate) it also refuses any company duty outside the profile's own list, and any capability set.",
    "Rule 3 treats placeholder text (TBD, none, n/a, unknown) as an empty obligations or escalation_path entry.",
    "Rule 3 looks for the upstream_dependencies entry inside the same service as the function.",
    "upstream:fixture-co is the company itself: it counts as fixture-co for every rule, so an affiliate can't make Fixture Co accountable by calling it an upstream.",
    "Function ids and per-profile coverage come from references/functions.json (prompt section 5); profile names come from the registry file.",
]


class InvalidInput(Exception):
    """Exit 2."""


class Refused(Exception):
    """A named refusal: exit 1."""

    def __init__(self, refusal: str, detail: str) -> None:
        super().__init__(detail)
        self.payload = {"verdict": "refused", "refusal": refusal, "detail": detail}


def read_json(path: str, what: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            doc = json.load(fh)
    except FileNotFoundError:
        raise InvalidInput("%s file not found: %s" % (what, path))
    except (ValueError, OSError) as exc:
        raise InvalidInput("%s file is not valid JSON: %s (%s)" % (what, path, exc))
    if not isinstance(doc, dict):
        raise InvalidInput("%s file must hold a JSON object: %s" % (what, path))
    return doc


def need(doc: Dict[str, Any], key: str, kind: type, where: str) -> Any:
    val = doc.get(key)
    if not isinstance(val, kind) or (kind is str and not val.strip()):
        raise InvalidInput("%s: %r must be a non-empty %s" % (where, key, kind.__name__))
    return val


def optional_list(doc: Dict[str, Any], key: str, where: str) -> List[Any]:
    val = doc.get(key, [])
    if not isinstance(val, list):
        raise InvalidInput("%s: %r must be a list" % (where, key))
    return val


def load_vocabulary() -> Dict[str, Any]:
    vocab = read_json(FUNCTIONS, "function vocabulary")
    ids: Set[str] = set()
    for spec in list(vocab["profiles"].values()) + list(vocab["capability_sets"].values()):
        for group in ("must_hold", "optional", "must_not_hold"):
            ids.update(spec.get(group, []))
    vocab["_ids"] = ids
    return vocab


def load_profiles(named: Optional[str], vocab: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    if named and os.path.realpath(named) != os.path.realpath(DEFAULT_PROFILES):
        raise Refused("profiles-not-registry-file", "profiles come only from the rig registry %s; the caller-named %s is refused"
                      % (DEFAULT_PROFILES, named))
    doc = read_json(DEFAULT_PROFILES, "profiles")
    hosting = {}
    for p in need(doc, "profiles", list, "profiles"):
        if not isinstance(p, dict) or p.get("kind") != "hosting":
            continue
        for key, kind in (("id", str), ("name", str), ("responsible_for", list), ("not_responsible_for", list)):
            need(p, key, kind, "profiles entry %s" % p.get("id"))
        hosting[p["id"]] = p
    missing = sorted(set(vocab["profiles"]) - set(hosting))
    if missing:
        raise InvalidInput("profiles file lacks hosting profiles that references/functions.json covers: %s" % ", ".join(missing))
    return hosting


def is_party(value: Any) -> bool:
    return isinstance(value, str) and (value in (COMPANY, "customer") or bool(UPSTREAM_RE.match(value)))


def as_party(value: str) -> str:
    """upstream:fixture-co is the company, not an upstream: one name per party for every rule."""
    m = UPSTREAM_RE.match(value)
    return COMPANY if m and m.group(1) == COMPANY else value


def load_catalogue(path: str, vocab: Dict[str, Any], hosting: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
    cat = read_json(path, "catalogue")
    if need(cat, "company", str, "catalogue") != COMPANY:
        raise InvalidInput("catalogue: company must be %s, got %r" % (COMPANY, cat["company"]))
    profile = need(cat, "profile", str, "catalogue")
    if profile not in hosting or profile not in vocab["profiles"]:
        raise InvalidInput("catalogue: profile %r is not a hosting profile with function coverage in references/functions.json (%s)"
                           % (profile, ", ".join(sorted(set(hosting) & set(vocab["profiles"])))))
    for cs in optional_list(cat, "capability_sets", "catalogue"):
        if cs not in vocab["capability_sets"]:
            raise InvalidInput("catalogue: unknown capability set %r (known: %s)" % (cs, ", ".join(sorted(vocab["capability_sets"]))))
    parties = need(cat, "parties", list, "catalogue")
    for party in parties:
        if not is_party(party):
            raise InvalidInput("catalogue: party %r must be %s, customer or upstream:<slug>" % (party, COMPANY))
    seen: Set[str] = set()
    for svc in need(cat, "services", list, "catalogue"):
        if not isinstance(svc, dict):
            raise InvalidInput("catalogue: every service must be an object")
        sid = need(svc, "id", str, "service")
        if not SLUG_RE.match(sid) or sid in seen:
            raise InvalidInput("service id %r must be a unique kebab-case slug" % sid)
        seen.add(sid)
        need(svc, "name", str, "service %s" % sid)
        for entry in need(svc, "functions", list, "service %s" % sid):
            if not isinstance(entry, dict):
                raise InvalidInput("service %s: every function entry must be an object" % sid)
            fn = need(entry, "function", str, "service %s function" % sid)
            if fn not in vocab["_ids"]:
                raise InvalidInput("service %s: unknown function id %r (see references/functions.json)" % (sid, fn))
            for who in [entry.get("accountable")] + optional_list(entry, "responsible", "service %s function %s" % (sid, fn)):
                if not is_party(who) or who not in parties:
                    raise InvalidInput("service %s function %s: party %r is not declared in parties" % (sid, fn, who))
        for lim in optional_list(svc, "customer_visible_limits", "service %s" % sid):
            if not isinstance(lim, dict):
                raise InvalidInput("service %s: every customer_visible_limits entry must be an object" % sid)
        for dep in optional_list(svc, "upstream_dependencies", "service %s" % sid):
            if not isinstance(dep, dict) or not SLUG_RE.match(str(dep.get("provider", ""))):
                raise InvalidInput("service %s: every upstream_dependencies entry needs a kebab-case provider slug" % sid)
            for key in ("obligations", "escalation_path"):
                if not all(isinstance(x, str) for x in optional_list(dep, key, "service %s dependency %s" % (sid, dep["provider"]))):
                    raise InvalidInput("service %s dependency %s: %s must be a list of strings" % (sid, dep["provider"], key))
    return cat


def coverage(cat: Dict[str, Any], vocab: Dict[str, Any]) -> Tuple[List[str], List[str], Set[str]]:
    spec = vocab["profiles"][cat["profile"]]
    must_hold = list(spec["must_hold"])
    for cs in cat.get("capability_sets", []):
        must_hold += [f for f in vocab["capability_sets"][cs]["must_hold"] if f not in must_hold]
    return must_hold, list(spec["optional"]), set(spec["must_not_hold"])


def is_limit(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0


def violation(rule: int, name: str, service: Optional[str], function: Optional[str], message: str) -> Dict[str, Any]:
    return {"rule": rule, "name": name, "service": service, "function": function, "message": message}


def find_violations(cat: Dict[str, Any], vocab: Dict[str, Any]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
    must_hold, optional, must_not_hold = coverage(cat, vocab)
    spec = vocab["profiles"][cat["profile"]]
    referral_only = set(spec["must_hold"]) | set(spec["optional"]) if spec.get("referral_only") else None
    owners: Dict[str, Dict[str, List[str]]] = {}  # function -> accountable party -> services listing it
    out: List[Dict[str, Any]] = []
    for svc in cat["services"]:
        holds_quotas = any(e["function"] == "quotas" for e in svc["functions"])
        for entry in svc["functions"]:
            fn, who = entry["function"], as_party(entry["accountable"])
            owners.setdefault(fn, {}).setdefault(who, []).append(svc["id"])
            duty = "accountable" if who == COMPANY else "responsible" if COMPANY in [as_party(r) for r in entry.get("responsible", [])] else None
            if duty and fn in must_not_hold:
                out.append(violation(2, "must-not-hold", svc["id"], fn,
                                     "%s cannot be %s for %s in a %s catalogue; name the party that controls it" % (COMPANY, duty, fn, cat["profile"])))
            elif duty and referral_only is not None and fn not in referral_only:
                out.append(violation(2, "beyond-referral", svc["id"], fn,
                                     "an %s catalogue is referral only; %s cannot be %s for %s" % (cat["profile"], COMPANY, duty, fn)))
            up = UPSTREAM_RE.match(who)
            if up:
                dep = next((d for d in svc.get("upstream_dependencies", []) if d["provider"] == up.group(1)), None)
                if dep is None:
                    out.append(violation(3, "upstream-dependency", svc["id"], fn, "%s is accountable to %s but the service has no upstream_dependencies entry for %s" % (fn, who, up.group(1))))
                else:
                    for key in ("obligations", "escalation_path"):
                        if not [x for x in dep.get(key, []) if x.strip() and x.strip().lower().rstrip(".") not in PLACEHOLDERS]:
                            out.append(violation(3, "upstream-dependency", svc["id"], fn, "upstream dependency %s for %s has no %s" % (up.group(1), fn, key)))
        limits = svc.get("customer_visible_limits", [])
        for lim in limits:
            label = lim.get("name") if isinstance(lim.get("name"), str) and lim["name"].strip() else "(unnamed)"
            if not is_limit(lim.get("value")):
                out.append(violation(4, "customer-visible-limit", svc["id"], None, "limit %s needs a finite number of 0 or more, got %s" % (label, json.dumps(lim.get("value")))))
            if not isinstance(lim.get("unit"), str) or not lim["unit"].strip():
                out.append(violation(4, "customer-visible-limit", svc["id"], None, "limit %s needs a unit" % label))
        if holds_quotas and not limits:
            out.append(violation(4, "customer-visible-limit", svc["id"], "quotas", "a service that holds quotas must list at least one customer-visible limit"))
    if referral_only is not None:
        for cs in cat.get("capability_sets", []):
            out.append(violation(2, "beyond-referral", None, None, "an %s catalogue is referral only and cannot declare capability set %s" % (cat["profile"], cs)))
    for fn in must_hold:
        if fn not in owners:
            out.append(violation(1, "accountable-party", None, fn, "no service lists %s, so nobody is accountable for it" % fn))
    for fn, parties in sorted(owners.items()):
        if len(parties) > 1:
            who = "; ".join("%s (%s)" % (p, ", ".join(s)) for p, s in sorted(parties.items()))
            out.append(violation(1, "accountable-party", None, fn, "%s has %d accountable parties: %s" % (fn, len(parties), who)))
    out.sort(key=lambda v: (v["rule"], v["service"] or "", v["function"] or "", v["message"]))
    absent = [f for f in optional if f not in owners]
    return out, {"profile": cat["profile"], "capability_sets": cat.get("capability_sets", []), "must_hold": must_hold,
                 "optional_absent": absent, "optional_present": [f for f in optional if f in owners]}


def profile_summary(hosting: Dict[str, Dict[str, Any]], pid: str) -> Dict[str, Any]:
    p = hosting[pid]
    return {"id": pid, "name": p["name"], "responsible_for": p["responsible_for"], "not_responsible_for": p["not_responsible_for"]}


def md(cell: Any) -> str:
    return str(cell).replace("|", "\\|").replace("\n", " ")


def render_matrix(cat: Dict[str, Any], summary: Dict[str, Any]) -> Tuple[str, List[Dict[str, Any]]]:
    rows = [{"service": s["id"], "function": e["function"], "accountable": e["accountable"], "responsible": e.get("responsible", [])}
            for s in cat["services"] for e in s["functions"]]
    lines = ["# Responsibility matrix: %s, %s (%s)" % (cat["company"], summary["name"], summary["id"]), "",
             "Capability sets: %s" % (", ".join(cat.get("capability_sets", [])) or "none"), "",
             "| Service | Function | Accountable | Responsible |", "| --- | --- | --- | --- |"]
    lines += ["| %s | %s | %s | %s |" % (md(r["service"]), md(r["function"]), md(r["accountable"]), md(", ".join(r["responsible"]) or "none")) for r in rows]
    limits = [(s["id"], l) for s in cat["services"] for l in s.get("customer_visible_limits", [])]
    if limits:
        lines += ["", "## Customer-visible limits", "", "| Service | Limit | Value | Unit |", "| --- | --- | --- | --- |"]
        lines += ["| %s | %s | %s | %s |" % (md(s), md(l.get("name", "")), md(l.get("value", "")), md(l.get("unit", ""))) for s, l in limits]
    deps = [(s["id"], d) for s in cat["services"] for d in s.get("upstream_dependencies", [])]
    if deps:
        lines += ["", "## Upstream dependencies", "", "| Service | Provider | Provider service | Obligations | Escalation path |", "| --- | --- | --- | --- | --- |"]
        lines += ["| %s | %s | %s | %s | %s |" % (md(s), md(d["provider"]), md(d.get("service", "")), md("; ".join(d.get("obligations", [])) or "none"),
                                                  md(" > ".join(d.get("escalation_path", [])) or "none")) for s, d in deps]
    return "\n".join(lines) + "\n", rows


class Parser(argparse.ArgumentParser):
    def error(self, message: str) -> None:  # type: ignore[override]
        raise InvalidInput(message)


def build_parser() -> Parser:
    ap = Parser(prog="catalogue_check", description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True, parser_class=Parser)
    for name in ("check", "matrix"):
        p = sub.add_parser(name)
        p.add_argument("--catalogue", required=True)
        p.add_argument("--profiles", help="refused unless it is the rig registry's company-fleets/registry/profiles.json")
    sub.choices["matrix"].add_argument("--format", choices=["json", "markdown"], default="json")
    return ap


def execute(argv: List[str]) -> Tuple[int, Any]:
    try:
        args = build_parser().parse_args(argv)
        vocab = load_vocabulary()
        hosting = load_profiles(args.profiles, vocab)
        cat = load_catalogue(args.catalogue, vocab, hosting)
        summary = profile_summary(hosting, cat["profile"])
        if args.cmd == "matrix":
            text, rows = render_matrix(cat, summary)
            return 0, text if args.format == "markdown" else {"profile": summary, "markdown": text, "rows": rows, "assumptions": ASSUMPTIONS}
        violations, checked = find_violations(cat, vocab)
        return (1 if violations else 0), {"verdict": "fail" if violations else "pass", "profile": summary, "violations": violations,
                                         "checked": checked, "assumptions": ASSUMPTIONS}
    except Refused as exc:
        return 1, exc.payload
    except InvalidInput as exc:
        return 2, {"error": str(exc)}


def main(argv: Optional[List[str]] = None) -> int:
    code, out = execute(list(sys.argv[1:] if argv is None else argv))
    sys.stdout.write(out if isinstance(out, str) else json.dumps(out, indent=2, sort_keys=True) + "\n")
    return code


if __name__ == "__main__":
    sys.exit(main())
