#!/usr/bin/env python3
"""benchmark: keep a dated hosting benchmark honest.

  check   --matrix M.json [--root DIR]   validate the matrix; exit 1 on any violation
  backlog --matrix M.json [--root DIR]   production-readiness backlog from gaps (JSON, plus --markdown)
  render  --matrix M.json                Markdown table, one row per dimension
  record-evidence --path REL [--dimension D --json-path P]
                                         the evidence owner records a file's sha256 in the rig's manifest,
                                         and which file and JSON path measure a dimension

Each dimension keeps five fields apart: documented provider claims, proposed target, configured
capability, measured test result, contractual commitment. A measured value must equal the value at the
JSON path the evidence owner recorded for that dimension, in the evidence file the owner recorded for
it, whose sha256 matches the owner's manifest in the rig; a matrix that names another file or path is
refused. Targets and statuses come from the owner's targets file (benchmark/targets.json); a matrix
target that differs is refused and never decides a status. A contract counts only when the rig's
contracts registry lists it. An availability measurement counts only when its evidence is an slo-check
availability claim covering at least 30 days; a matrix's own kind or window label decides nothing.
Claims of superiority, claims that rest on agent or role counts, and availability promises are refused
in statements, the subject, the contract note, provider claim summaries and every dimension field except
provider quotes, after the text is normalized the way a reader sees it (entities, NFKC, format characters,
look-alike letters, case). --root is where evidence paths resolve (default: the company-fleets folder
beside this skill); the manifest, targets and registry always come from the rig. Exit 0 ok, 1 violation,
2 invalid input.
Python 3.9+ standard library only.
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import html
import json
import os
import re
import sys
import unicodedata
from typing import Any, Dict, List, Optional

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "company-fleets"))
EVIDENCE_MANIFEST = os.path.join(DEFAULT_ROOT, "fleets", "hosting", "evidence", "benchmark-evidence-manifest.json")
CONTRACTS = os.path.join(DEFAULT_ROOT, "fleets", "hosting", "benchmark", "contracts.json")
TARGETS = os.path.join(DEFAULT_ROOT, "fleets", "hosting", "benchmark", "targets.json")
DIMENSIONS = ("restore", "recovery_objectives", "isolation", "deployment_reversibility", "performance_under_load",
              "observability", "support_coverage", "accessibility", "data_portability", "regional_constraints",
              "cost", "availability")
FIELDS = ("provider_claims", "proposed_target", "configured_capability", "measured_result", "contractual_commitment")
PROVIDERS = ("acquia", "pantheon", "wpvip")
CLAIM_STATUS = ("documented", "not documented publicly", "page unreachable")
QUALITY = r"(?:robust|reliable|resilient|secure|stable|available|trusted|advanced|dependable|performant|scalable)"
SUPERIORITY = re.compile(r"\b(more " + QUALITY + r"|most " + QUALITY + r"|better|best|outperform\w*|superior\w*|beats?|"
                         r"wins?|winning|industry[- ]leading|market[- ]leading|stronger than|faster than|number one|no\. ?1|"
                         r"top[- ]rated|unmatched|unrivall?ed|second to none)\b|(?<!\w)#1\b", re.I)
RIVAL = re.compile(r"\b(pantheon|wordpress vip|wp ?vip|acquia|providers?|competitors?|rivals?|other hosts?)\b", re.I)
COMPANY = re.compile(r"\bfixture co\b", re.I)
COMPARATIVE = re.compile(r"\b(than|exceed\w*|surpass\w*|ahead of|outpace\w*|outrun\w*|out-\w+|outperform\w*|beat\w*|"
                         r"superior|leads?|leading|tops?|trails?|trailing|lags?|lagging|behind|unlike|versus|vs|"
                         r"against|slower|weaker|worse)\b", re.I)
AVAILABILITY_WORDS = re.compile(r"\b(uptime|availab\w*|up|online|sla|slo|guarantee\w*|downtime|nines)\b", re.I)
NEVER_DOWN = re.compile(r"\b(never (?:go(?:es)? down|goes? offline|fails?|loses?|lose|drops?)|zero downtime|no downtime|"
                        r"always (?:up|online|available|on))\b", re.I)
PROMISE = re.compile(r"(?<!not a )\b(guarantee\w*|promise\w*|commit\w*)\b|\bnot a hypothesis\b", re.I)
ROSTER = re.compile(r"\b(\d+\s+(agents?|roles?|personas?|specialists?)|agent roster|roster size|more agents|more roles)\b", re.I)
PERCENT = re.compile(r"\d+(?:\.\d+)?\s*(?:%|percent\b|per\s*cent\b|pct\b)|\b(?:two|three|four|five|six|seven|\d)\s+nines\b", re.I)
_LOOKALIKES = str.maketrans({"а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "у": "y", "х": "x", "і": "i", "ј": "j",
                             "ѕ": "s", "ԁ": "d", "һ": "h", "ӏ": "l", "ο": "o", "α": "a", "ε": "e", "ι": "i", "κ": "k",
                             "ν": "v", "ρ": "p", "τ": "t", "υ": "u", "χ": "x"})


def reader_text(text: str) -> str:
    """What a reader sees, as corporate-claims-check normalizes it: entities decoded, NFKC, format and combining
    characters dropped, spaced-out letters rejoined, look-alike letters folded, case folded, spaces collapsed."""
    text = unicodedata.normalize("NFKC", html.unescape(text))
    text = "".join(c for c in text if unicodedata.category(c) not in ("Cf", "Mn", "Me"))
    text = re.sub(r"\b(?:[^\W\d_] ){3,}[^\W\d_]\b", lambda m: m.group(0).replace(" ", ""), text)
    return re.sub(r"\s+", " ", text.casefold().translate(_LOOKALIKES)).strip()
MIN_AVAILABILITY_DAYS = 30


class InputError(Exception):
    pass


def load(path: str) -> Dict[str, Any]:
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError) as exc:
        raise InputError("cannot read %s: %s" % (path, exc))
    if not isinstance(doc, dict) or not isinstance(doc.get("dimensions"), list):
        raise InputError("matrix needs a 'dimensions' list")
    for key in ("subject", "contract_note"):
        if key in doc and not isinstance(doc[key], str):
            raise InputError("matrix %s must be text" % key)
    statements = doc.get("statements", [])
    if not isinstance(statements, list) or not all(isinstance(c, dict) and isinstance(c.get("text"), str) for c in statements):
        raise InputError("matrix statements must be a list of objects with a text string")
    try:
        datetime.date.fromisoformat(str(doc.get("as_of")))
    except ValueError:
        raise InputError("matrix needs an ISO 'as_of' date")
    for d in doc["dimensions"]:
        if not isinstance(d, dict) or d.get("id") not in DIMENSIONS:
            raise InputError("unknown dimension %r; known: %s" % (d.get("id") if isinstance(d, dict) else d,
                                                                 ", ".join(DIMENSIONS)))
        for f in ("proposed_target", "configured_capability", "measured_result", "contractual_commitment"):
            if d.get(f) is not None and not isinstance(d[f], dict):
                raise InputError("%s %s must be an object or null" % (d["id"], f))
        claims = d.get("provider_claims", [])
        if not isinstance(claims, list) or not all(isinstance(c, dict) for c in claims):
            raise InputError("%s provider_claims must be a list of objects" % d["id"])
        m = d.get("measured_result")
        if isinstance(m, dict) and "window_days" in m and (not isinstance(m["window_days"], int) or isinstance(m["window_days"], bool)):
            raise InputError("%s measured_result window_days must be a whole number of days, got %r" % (d["id"], m["window_days"]))
    return doc


def read_owner(path: str, key: str) -> Dict[str, Any]:
    """An owner file in the rig, never one the matrix or --root supplies."""
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError) as exc:
        raise InputError("cannot read owner file %s: %s" % (path, exc))
    if not isinstance(doc, dict) or not isinstance(doc.get(key), (dict, list)):
        raise InputError("owner file %s needs %r" % (path, key))
    return doc


def owner_targets() -> Dict[str, Dict[str, Any]]:
    return read_owner(TARGETS, "targets")["targets"]


def comparable(target: Any) -> Dict[str, Any]:
    return {k: target[k] for k in ("max", "equals") if isinstance(target, dict) and k in target}


def is_availability_claim(ev: Any) -> bool:
    """The evidence itself must be an slo-check availability claim whose events cover a window of 30 days or more."""
    claim = ev.get("availability_claim") if isinstance(ev, dict) else None
    return (isinstance(ev, dict) and ev.get("command") == "slo-check" and isinstance(claim, dict)
            and isinstance(claim.get("window_days"), int) and claim["window_days"] >= MIN_AVAILABILITY_DAYS
            and (ev.get("coverage") or {}).get("covers_window") is True)


def texts(d: Dict[str, Any]) -> List[str]:
    """Every author-written text in a dimension, provider quotes and claim summaries excluded (checked apart)."""
    out: List[str] = []

    def walk(node: Any) -> None:
        if isinstance(node, str):
            out.append(node)
        elif isinstance(node, dict):
            for k, v in node.items():
                if k not in ("evidence", "evidence_sha256", "json_path"):
                    walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)
    for f in ("proposed_target", "configured_capability", "measured_result", "contractual_commitment"):
        walk(d.get(f))
    return out


def sha_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def lookup(doc: Any, path: str) -> Any:
    for part in path.split("."):
        doc = doc[int(part)] if isinstance(doc, list) else doc[part]
    return doc


def check(doc: Dict[str, Any], root: str) -> List[Dict[str, str]]:
    v: List[Dict[str, str]] = []

    def bad(rule: str, dim: str, msg: str) -> None:
        v.append({"rule": rule, "dimension": dim, "message": msg})

    def wording(raw: str, where: str, availability_ok: bool = False, rival: Any = RIVAL) -> None:
        text = reader_text(raw)
        if SUPERIORITY.search(text) or (rival.search(text) and COMPARATIVE.search(text)):
            bad("superiority", where, "comparative claim %r; this matrix holds no provider measurements, "
                "so it cannot support a superiority claim" % raw[:80])
        if ROSTER.search(text):
            bad("roster-size", where, "claim rests on agent or role counts: %r" % raw[:80])
        if NEVER_DOWN.search(text) or (not availability_ok and PERCENT.search(text) and AVAILABILITY_WORDS.search(text)):
            bad("availability-from-lab", where, "availability percentage or uptime promised: %r" % raw[:80])

    seen = [d["id"] for d in doc["dimensions"]]
    for dim in DIMENSIONS:
        if seen.count(dim) != 1:
            bad("dimension-coverage", dim, "appears %d times; every dimension appears once" % seen.count(dim))
    registry = read_owner(CONTRACTS, "contracts")["contracts"]
    owner = read_owner(EVIDENCE_MANIFEST, "files")
    manifest, measures = owner["files"], owner.get("measurements") or {}
    targets = owner_targets()
    contract = doc.get("contract")
    has_contract = False
    if contract is not None:
        listed = next((c for c in registry if isinstance(c, dict) and c.get("id") == contract), None)
        if listed is None:
            bad("contract-not-on-record", "contract", "contract %r is not in the rig's contracts registry %s" % (contract, CONTRACTS))
        else:
            has_contract = True
    for d in doc["dimensions"]:
        dim = d["id"]
        for f in FIELDS:
            if f not in d:
                bad("five-fields", dim, "%s is missing; write null when there is none" % f)
        claims = d.get("provider_claims") or []
        for p in PROVIDERS:
            if not any(c.get("provider") == p for c in claims):
                bad("provider-claims", dim, "no %s entry; record 'not documented publicly' when the docs say nothing" % p)
        for c in claims:
            if c.get("status") not in CLAIM_STATUS or not str(c.get("url", "")).startswith("https://"):
                bad("provider-claims", dim, "%s claim needs a status and an https URL" % c.get("provider"))
            if not re.match(r"^\d{4}-\d{2}-\d{2}$", str(c.get("retrieved_on", ""))):
                bad("provider-claims", dim, "%s claim needs retrieved_on" % c.get("provider"))
            if len(str(c.get("quote", "")).split()) > 25:
                bad("provider-claims", dim, "%s quote is over 25 words" % c.get("provider"))
        for c in claims:
            wording(str(c.get("claim", "")), "%s.%s claim" % (dim, c.get("provider")),
                    availability_ok=not COMPANY.search(reader_text(str(c.get("claim", "")))), rival=COMPANY)
        m = d.get("measured_result")
        recorded = measures.get(dim)
        if m is not None:
            ev = m.get("evidence")
            path = os.path.realpath(os.path.join(root, str(ev)))
            evidence: Any = None
            if not isinstance(recorded, dict) or not recorded.get("evidence") or not recorded.get("json_path"):
                bad("measured-evidence", dim, "the evidence owner's manifest records no evidence file and JSON path for %s" % dim)
            elif (ev, m.get("json_path")) != (recorded["evidence"], recorded["json_path"]):
                bad("measured-evidence", dim, "the matrix cites %s at %s; the evidence owner recorded %s at %s for %s" % (
                    ev, m.get("json_path"), recorded["evidence"], recorded["json_path"], dim))
            elif not ev or not os.path.isfile(path) or not path.startswith(os.path.realpath(root) + os.sep):
                bad("measured-evidence", dim, "measured result cites missing evidence or a path outside the root: %s" % ev)
            elif manifest.get(str(ev)) is None:
                bad("measured-evidence", dim, "evidence %s is not in the evidence owner's manifest" % ev)
            elif sha_file(path) != manifest[str(ev)] or m.get("evidence_sha256") != manifest[str(ev)]:
                bad("measured-evidence", dim, "evidence %s differs from the sha256 its owner recorded" % ev)
            else:
                try:
                    with open(path, encoding="utf-8") as fh:
                        evidence = json.load(fh)
                    actual = lookup(evidence, str(recorded["json_path"]))
                except (ValueError, KeyError, IndexError, TypeError):
                    actual = "<missing>"
                if actual != m.get("value"):
                    bad("measured-evidence", dim, "value %r does not match %s at %s (%r)" % (
                        m.get("value"), ev, recorded["json_path"], actual))
            if dim == "availability" and not is_availability_claim(evidence):
                bad("availability-from-lab", dim, "an availability percentage needs evidence that is an slo-check availability "
                    "claim covering at least %d days; this evidence is not, whatever the matrix labels it" % MIN_AVAILABILITY_DAYS)
        if d.get("contractual_commitment") is not None and not has_contract:
            bad("no-contract", dim, "a commitment is recorded but no plan or contract is on record")
        target = d.get("proposed_target")
        if comparable(target) != comparable(targets.get(dim)):
            bad("target-not-on-record", dim, "the matrix target %s differs from the owner's target %s in %s; the owner's decides "
                "the status" % (json.dumps(comparable(target)), json.dumps(comparable(targets.get(dim))), TARGETS))
        if dim == "availability" and target is not None and PERCENT.search(reader_text(json.dumps(target, ensure_ascii=False))) and \
                (target.get("hypothesis") is not True or PROMISE.search(json.dumps(target))):
            bad("availability-from-lab", dim, "an availability target must carry hypothesis: true and no guarantee or promise wording")
        for text in texts(d):
            wording(text, dim, availability_ok=(dim == "availability"))
    for i, claim in enumerate(doc.get("statements", [])):
        wording(claim["text"], "statements.%d" % i)
    for key in ("subject", "contract_note"):
        if key in doc:
            wording(doc[key], key)
    return v


def status(d: Dict[str, Any], targets: Dict[str, Dict[str, Any]]) -> str:
    """Met or unmet against the owner's target for the dimension, never the matrix's own."""
    t, m = targets.get(d["id"]), d.get("measured_result")
    if m is None:
        return "not-measured"
    if t is None:
        return "measured-no-target"
    if "max" in t:
        return "met" if isinstance(m["value"], (int, float)) and m["value"] <= t["max"] else "unmet"
    if "equals" in t:
        return "met" if m["value"] == t["equals"] else "unmet"
    return "measured-no-target"


def backlog(doc: Dict[str, Any], targets: Dict[str, Dict[str, Any]]) -> List[Dict[str, Any]]:
    items = []
    for d in doc["dimensions"]:
        st = status(d, targets)
        if st == "unmet":
            t = dict(targets[d["id"]], note=(d.get("proposed_target") or {}).get("note", "no remediation noted"))
            items.append({"dimension": d["id"], "kind": "close-gap", "detail": "measured %s against target %s; %s" % (
                json.dumps(d["measured_result"]["value"]), json.dumps({k: t[k] for k in ("max", "equals") if k in t}),
                t.get("note", "no remediation noted"))})
        elif st == "not-measured":
            items.append({"dimension": d["id"], "kind": "measure", "detail": "no lab or production measurement on record"})
        if d.get("configured_capability") is None:
            items.append({"dimension": d["id"], "kind": "configure", "detail": "no configured capability on record"})
        if d.get("contractual_commitment") is None:
            items.append({"dimension": d["id"], "kind": "commit", "detail": "no plan or contract; a commercial owner decides whether to commit"})
    order = {"close-gap": 0, "measure": 1, "configure": 2, "commit": 3}
    return sorted(items, key=lambda i: (order[i["kind"]], DIMENSIONS.index(i["dimension"])))


def cell(value: Any) -> str:
    if value is None:
        return "none"
    if isinstance(value, dict):
        text = str(value.get("value", value.get("summary", "")))
        return text.replace("|", "/")
    return str(value).replace("|", "/")


def render(doc: Dict[str, Any], targets: Dict[str, Dict[str, Any]]) -> str:
    lines = ["# Hosting benchmark matrix, %s" % doc["as_of"], "",
             "Provider claims are public documentation as retrieved, not tested. Measured results are one "
             "synthetic lab run for Fixture Co. Commitments stay empty while no contract exists.", "",
             "| Dimension | Acquia claim | Pantheon claim | WordPress VIP claim | Proposed target | Configured | Measured | Status | Commitment |",
             "|---|---|---|---|---|---|---|---|---|"]
    for d in doc["dimensions"]:
        claims = {c["provider"]: c for c in d.get("provider_claims", [])}
        row = [d["id"]] + ["%s ([source](%s))" % (claims[p]["claim"].replace("|", "/"), claims[p]["url"]) if p in claims
                           else "none" for p in PROVIDERS]
        row += [cell(d.get("proposed_target")), cell(d.get("configured_capability")), cell(d.get("measured_result")),
                status(d, targets), cell(d.get("contractual_commitment"))]
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines) + "\n"


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="benchmark")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("check", "backlog", "render"):
        p = sub.add_parser(name)
        p.add_argument("--matrix", required=True)
        p.add_argument("--root", default=DEFAULT_ROOT)
        if name == "backlog":
            p.add_argument("--markdown", action="store_true")
    r = sub.add_parser("record-evidence")
    r.add_argument("--path", required=True, help="evidence path relative to the rig's company-fleets folder")
    r.add_argument("--dimension", choices=DIMENSIONS, help="the dimension this file measures")
    r.add_argument("--json-path", dest="json_path", help="with --dimension: the JSON path of the measured value in the file")
    args = ap.parse_args(argv)
    if args.cmd == "record-evidence":
        full = os.path.realpath(os.path.join(DEFAULT_ROOT, args.path))
        if not full.startswith(os.path.realpath(DEFAULT_ROOT) + os.sep) or not os.path.isfile(full):
            print(json.dumps({"error": "evidence %s is not a file inside %s" % (args.path, DEFAULT_ROOT)}, indent=2))
            return 2
        if bool(args.dimension) != bool(args.json_path):
            print(json.dumps({"error": "--dimension and --json-path go together"}, indent=2))
            return 2
        doc = read_owner(EVIDENCE_MANIFEST, "files") if os.path.isfile(EVIDENCE_MANIFEST) else {
            "label": "Evidence owner's manifest: the sha256 of each benchmark evidence file, recorded by benchmark.py record-evidence when the evidence was produced.",
            "files": {}}
        if args.dimension:
            try:
                with open(full, encoding="utf-8") as fh:
                    lookup(json.load(fh), args.json_path)
            except (ValueError, KeyError, IndexError, TypeError):
                print(json.dumps({"error": "%s has no value at %s" % (args.path, args.json_path)}, indent=2))
                return 2
            doc.setdefault("measurements", {})[args.dimension] = {"evidence": args.path, "json_path": args.json_path}
        doc["files"][args.path] = sha_file(full)
        tmp = EVIDENCE_MANIFEST + ".tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=2, sort_keys=True)
            fh.write("\n")
        os.replace(tmp, EVIDENCE_MANIFEST)
        print(json.dumps({"recorded": args.path, "sha256": doc["files"][args.path], "measures": args.dimension}, indent=2))
        return 0
    try:
        doc = load(args.matrix)
        targets = owner_targets()
    except InputError as exc:
        print(json.dumps({"error": str(exc)}, indent=2))
        return 2
    if args.cmd == "render":
        sys.stdout.write(render(doc, targets))
        return 0
    try:
        violations = check(doc, args.root)
    except InputError as exc:
        print(json.dumps({"error": str(exc)}, indent=2))
        return 2
    if args.cmd == "check":
        refused = {v["dimension"] for v in violations if v["rule"] == "measured-evidence"}
        print(json.dumps({"verdict": "fail" if violations else "pass", "violations": violations,
                          "statuses": {d["id"]: "evidence-refused" if d["id"] in refused else status(d, targets) for d in doc["dimensions"]},
                          "as_of": doc["as_of"],
                          "assumptions": ["Provider claims are what public pages said on retrieved_on; they are not tested.",
                                          "A measured value counts only at the evidence file and JSON path the evidence owner "
                                          "recorded for its dimension, while the file's hash matches.",
                                          "Targets and statuses come from the owner's benchmark/targets.json; a process running as "
                                          "the same OS user can rewrite the owner's files, which only separate OS accounts or "
                                          "signed records stop."]},
                         indent=2, sort_keys=True))
        return 1 if violations else 0
    items = backlog(doc, targets)
    if args.markdown:
        sys.stdout.write("# Production-readiness backlog from the %s benchmark\n\n" % doc["as_of"] + "\n".join(
            "%d. %s, %s: %s" % (n, i["dimension"], i["kind"], i["detail"]) for n, i in enumerate(items, 1)) + "\n")
    else:
        print(json.dumps({"as_of": doc["as_of"], "items": items, "matrix_violations": violations}, indent=2, sort_keys=True))
    return 1 if violations else 0


if __name__ == "__main__":
    sys.exit(main())
