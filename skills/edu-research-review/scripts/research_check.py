#!/usr/bin/env python3
"""research_check: deterministic checks for education research review, design and program evaluation.

  claims    STUDY.json                 overclaim lint over a structured study card
  design    PLAN.json                  completeness and ethics-boundary check for a research plan
  program   PROGRAM.json               program-evaluation check: dimensions, actual evidence, standards hand-off
  citations REFS.json [--offline RESOLVER.json] [--record RESOLVER.json]
                                       resolve each reference (DOI via Crossref, arXiv id via the arXiv API,
                                       otherwise a Crossref bibliographic search) and compare title, year, first author

Prints JSON. Exit 0 ok, 1 findings that block (errors, or citations not all verified), 2 usage or invalid input.
Python 3.9+ standard library only. Shapes are documented in references/json-shapes.md.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
import sys
import time
import unicodedata
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Callable, Dict, List, Optional, Tuple


class InputError(Exception):
    """The input file is missing, unreadable or has the wrong shape."""


def _load(path: str) -> Dict[str, Any]:
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError) as exc:
        raise InputError("cannot read %s: %s" % (path, exc))
    if not isinstance(doc, dict):
        raise InputError("%s must hold a JSON object" % path)
    return doc


def _need(doc: Dict[str, Any], key: str, kind: type, where: str) -> Any:
    if key not in doc:
        raise InputError("%s is missing %r" % (where, key))
    if not isinstance(doc[key], kind):
        raise InputError("%s.%s must be %s" % (where, key, kind.__name__))
    return doc[key]


# ---------------------------------------------------------------- claims

EXPERIMENTAL = {"rct", "matched-random", "experimental"}
DESIGNS = EXPERIMENTAL | {"quasi-experimental", "correlational", "descriptive", "qualitative", "design-based",
                          "case-study", "systematic-review", "meta-analysis"}
LEVELS = {"k12", "higher-ed", "workplace", "general"}
EVIDENCE_TYPES = {"peer-reviewed-study", "preprint", "systematic-review", "conference-talk",
                  "association-webpage", "practitioner-guidance"}
WEAK_EVIDENCE = {"conference-talk", "association-webpage", "practitioner-guidance"}
CAUSAL = re.compile(r"\b(causes?|caused|causing|leads? to|led to|results? in|improv(e|es|ed|ing)|increas(e|es|ed)|"
                    r"boost(s|ed)?|rais(e|es|ed)|reduc(e|es|ed)|effect of|impact of|makes? .{0,20}better|"
                    r"drives?|produces?)\b", re.I)
UNIVERSAL = re.compile(r"\b(all (students|learners|k-?12|teachers|classrooms|novices)|every (student|learner|classroom)|"
                       r"students in general|any (student|learner)|always|universally|regardless of)\b", re.I)
HEDGE = re.compile(r"\b(may|might|could|can|suggests?|encouraging|potentially|initial|preliminary|exploratory|"
                   r"appears?|indicates?)\b", re.I)
LEARNING = re.compile(r"\b(learn(ing|ed|s)?|understand(ing|s)?|knowledge|skills?|retention|achievement|mastery)\b", re.I)
NULL_AS_EQUIV = re.compile(r"\b(no difference|does not impede|did not (reduce|decrease|harm)|not decreas(e|ing)|"
                           r"as well as|equivalent|no (harm|negative effect)|just as well)\b", re.I)
NONSIG_ACK = re.compile(r"\b(not (reach|statistically) significan\w*|did not reach statistical significance|not significant)\b", re.I)


def _finding(rule: str, severity: str, message: str, claim: Optional[str] = None) -> Dict[str, Any]:
    f = {"rule": rule, "severity": severity, "message": message}
    if claim:
        f["claim"] = claim
    return f


def check_claims(doc: Dict[str, Any]) -> Dict[str, Any]:
    design = _need(doc, "design", str, "study")
    if design not in DESIGNS:
        raise InputError("study.design %r is not one of %s" % (design, sorted(DESIGNS)))
    etype = _need(doc, "evidence_type", str, "study")
    if etype not in EVIDENCE_TYPES:
        raise InputError("study.evidence_type %r is not one of %s" % (etype, sorted(EVIDENCE_TYPES)))
    sample = _need(doc, "sample", dict, "study")
    n = _need(sample, "n", int, "study.sample")
    sites = _need(sample, "sites", int, "study.sample")
    level = _need(sample, "level", str, "study.sample")
    if level not in LEVELS - {"general"}:
        raise InputError("study.sample.level must be k12, higher-ed or workplace")
    selection = sample.get("selection", "unknown")
    setting = sample.get("setting", "unknown")
    claims = _need(doc, "claims", list, "study")
    if not claims:
        raise InputError("study.claims is empty; there is nothing to check")
    measures = {m["name"]: m for m in doc.get("measures", []) if isinstance(m, dict) and "name" in m}
    analysis = doc.get("analysis", {})
    controls = doc.get("confound_controls", [])
    experimental = design in EXPERIMENTAL and doc.get("comparison_group") is True and doc.get("random_assignment") is True

    findings: List[Dict[str, Any]] = []
    att = sample.get("attrition") or {}
    if att.get("started") and att.get("analyzed") is not None and att["analyzed"] / att["started"] < 0.8:
        findings.append(_finding("attrition", "warn",
                                 "analyzed %d of %d who started (%.0f%%); completers-only results can be biased if dropout differs by condition"
                                 % (att["analyzed"], att["started"], 100.0 * att["analyzed"] / att["started"])))
    if design == "quasi-experimental" and not controls:
        findings.append(_finding("no-confound-controls", "error",
                                 "quasi-experimental design lists no confound controls; group differences cannot be attributed to the treatment"))
    if selection in ("volunteer", "convenience"):
        findings.append(_finding("selection", "warn",
                                 "%s sample from %s; results describe these participants, not a defined population" % (selection, setting)))

    for c in claims:
        if not isinstance(c, dict) or not isinstance(c.get("id"), str) or not isinstance(c.get("text"), str):
            raise InputError("each claim needs string id and text")
        cid, text = c["id"], c["text"]
        scope = c.get("scope", {})
        hedged = bool(HEDGE.search(text))
        sev = "warn" if hedged else "error"
        if CAUSAL.search(text) and not experimental:
            controlled_quasi = design == "quasi-experimental" and doc.get("comparison_group") is True and controls
            findings.append(_finding("causal-from-nonexperimental", "warn" if controlled_quasi else "error",
                                     "causal wording (%r) but the design is %s without random assignment to a comparison group%s"
                                     % (CAUSAL.search(text).group(0), design,
                                        "; name the remaining threats" if controlled_quasi else ""), cid))
        if UNIVERSAL.search(text) and (sites <= 1 or n < 100 or selection in ("volunteer", "convenience")):
            findings.append(_finding("universal-from-narrow-sample", "error",
                                     "universal wording (%r) from n=%d at %d site(s), %s selection"
                                     % (UNIVERSAL.search(text).group(0), n, sites, selection), cid))
        if n < 30 and sites <= 1 and not c.get("exploratory"):
            findings.append(_finding("small-single-site", "error",
                                     "n=%d at one site supports a local observation, not a teaching rule; mark it exploratory" % n, cid))
        claim_level = scope.get("level", level)
        if claim_level not in LEVELS:
            raise InputError("claim %s scope.level %r is not one of %s" % (cid, claim_level, sorted(LEVELS)))
        if claim_level != level and not c.get("transfer_argument"):
            rule = "transfer-beyond-sample" if not (level == "higher-ed" and claim_level in ("k12", "workplace")) \
                else "higher-ed-to-other-level"
            findings.append(_finding(rule, "error" if rule == "higher-ed-to-other-level" else sev,
                                     "claim targets %s but the sample is %s; give a transfer argument or narrow the claim"
                                     % (claim_level, level), cid))
        claim_setting = scope.get("setting")
        if claim_setting and claim_setting != setting and not c.get("transfer_argument"):
            findings.append(_finding("setting-shift", "warn",
                                     "claim names setting %s; the study ran in %s" % (claim_setting, setting), cid))
        basis = c.get("basis", [])
        kinds = [measures[b].get("kind") for b in basis if b in measures]
        if LEARNING.search(text) and kinds and all(k == "self-report" for k in kinds):
            findings.append(_finding("self-report-learning", "error",
                                     "learning claim rests only on self-report measures (%s)" % ", ".join(basis), cid))
        if NULL_AS_EQUIV.search(text) and not analysis.get("equivalence_test"):
            findings.append(_finding("null-as-equivalence", "warn",
                                     "a non-significant difference (%r) is not evidence of equivalence without an equivalence test or power analysis"
                                     % NULL_AS_EQUIV.search(text).group(0), cid))
        if c.get("result_significant") is False and CAUSAL.search(text) and not NONSIG_ACK.search(text):
            findings.append(_finding("nonsignificant-as-effect", "warn",
                                     "directional wording (%r) for a result the study reports as not statistically significant"
                                     % CAUSAL.search(text).group(0), cid))
        if c.get("subgroup") and analysis.get("subgroup_post_hoc"):
            findings.append(_finding("post-hoc-subgroup", "warn",
                                     "subgroup result from a post hoc split; treat as a hypothesis for a new study", cid))
        if etype in WEAK_EVIDENCE and c.get("strength") == "established":
            findings.append(_finding("weak-evidence-type", "error",
                                     "%s presented as an established finding; trace it to a peer-reviewed study or review" % etype, cid))

    errors = sum(f["severity"] == "error" for f in findings)
    return {"ok": errors == 0, "mode": "claims", "study": doc.get("citation", {}).get("title", ""),
            "counts": {"error": errors, "warn": sum(f["severity"] == "warn" for f in findings), "claims": len(claims)},
            "findings": findings}


# ---------------------------------------------------------------- design

APPROACHES = {"qualitative", "quantitative", "mixed", "experimental", "quasi-experimental", "design-based"}
QUESTION_TYPES = {"descriptive", "causal", "exploratory", "design", "relational"}
FITS = {"causal": {"experimental", "quasi-experimental", "mixed"},
        "descriptive": APPROACHES, "exploratory": {"qualitative", "mixed", "design-based"},
        "design": {"design-based", "mixed"}, "relational": {"quantitative", "mixed", "quasi-experimental"}}


def check_design(doc: Dict[str, Any]) -> Dict[str, Any]:
    findings: List[Dict[str, Any]] = []
    for key in ("question", "question_type", "rationale", "method", "participants", "instruments",
                "analysis", "ethics", "data_management"):
        if key not in doc or doc[key] in ("", None, [], {}):
            findings.append(_finding("missing-section", "error", "plan has no %s" % key))
    qtype, method = doc.get("question_type"), doc.get("method") or {}
    approach = method.get("approach") if isinstance(method, dict) else None
    if qtype is not None and qtype not in QUESTION_TYPES:
        raise InputError("plan.question_type %r is not one of %s" % (qtype, sorted(QUESTION_TYPES)))
    if approach is not None and approach not in APPROACHES:
        raise InputError("plan.method.approach %r is not one of %s" % (approach, sorted(APPROACHES)))
    if qtype and approach and approach not in FITS[qtype]:
        findings.append(_finding("method-question-mismatch", "error",
                                 "a %s question cannot be answered by a %s approach" % (qtype, approach)))
    if isinstance(method, dict) and method and not method.get("justification"):
        findings.append(_finding("no-method-rationale", "error", "method has no question-to-method justification"))
    if approach == "quasi-experimental" and not method.get("confound_controls"):
        findings.append(_finding("no-confound-controls", "error", "quasi-experimental plan names no confound controls"))
    for i, ins in enumerate(doc.get("instruments") or []):
        if not isinstance(ins, dict) or not ins.get("construct") or not (ins.get("validity_evidence") or ins.get("validity_plan")):
            findings.append(_finding("instrument-validity", "error",
                                     "instrument %d needs a construct and validity evidence or a validity plan" % (i + 1)))
    ethics = doc.get("ethics") or {}
    status = ethics.get("status")
    if status == "approved" and not ethics.get("approval_evidence"):
        findings.append(_finding("approval-claimed-without-evidence", "error",
                                 "ethics approval is claimed with no approval reference; the rig cannot grant or assume IRB/REB approval"))
    elif status == "approved":
        findings.append(_finding("approval-unconfirmed", "warn",
                                 "approval reference %s is recorded but not confirmed by the rig; a human checks the document"
                                 % ethics.get("approval_evidence")))
    if status not in (None, "not-submitted", "submitted", "approved"):
        raise InputError("plan.ethics.status %r is not one of not-submitted, submitted, approved" % status)
    participants = doc.get("participants") or {}
    if participants.get("minors") and not ethics.get("consent_assent"):
        findings.append(_finding("minors-without-assent", "error", "minors are in scope but no parental consent and child assent process is described"))
    if doc.get("participant_data"):
        findings.append(_finding("participant-data-present", "error",
                                 "plan already holds %d participant record(s); collection waits for the approved process"
                                 % len(doc["participant_data"])))
    dm = doc.get("data_management") or {}
    for key in ("storage", "retention", "access", "deidentification"):
        if isinstance(dm, dict) and dm and not dm.get(key):
            findings.append(_finding("data-management", "error", "data management plan has no %s" % key))
    errors = sum(f["severity"] == "error" for f in findings)
    return {"ok": errors == 0, "mode": "design", "question": doc.get("question", ""),
            "counts": {"error": errors, "warn": len(findings) - errors}, "findings": findings}


# ---------------------------------------------------------------- program

DIMENSIONS = {"business-subject-mastery", "technology-fluency", "pedagogical-competence",
              "occupational-assessment-readiness", "computing-understanding"}
FOCI = {"coherence", "assessment-validity", "accessibility", "participation", "evidence-of-learning"}
ACTUAL = {"scored-student-work", "assessment-results", "classroom-observation", "credential-results",
          "enrollment-records", "completion-records", "accessibility-audit", "curriculum-document"}
NOT_LEARNING = {"satisfaction-survey", "generated-lesson", "simulated-learner", "self-report", "plan"}


def check_program(doc: Dict[str, Any]) -> Dict[str, Any]:
    foci = set(_need(doc, "evaluation_foci", list, "program"))
    evidence = {e["id"]: e for e in _need(doc, "evidence", list, "program") if isinstance(e, dict) and "id" in e}
    conclusions = _need(doc, "conclusions", list, "program")
    findings: List[Dict[str, Any]] = []
    for missing in sorted(FOCI - foci):
        findings.append(_finding("focus-missing", "error", "program evaluation does not examine %s" % missing))
    for eid, e in evidence.items():
        if e.get("kind") not in ACTUAL | NOT_LEARNING:
            raise InputError("evidence %s kind %r is not recognized" % (eid, e.get("kind")))
    for c in conclusions:
        if not isinstance(c, dict) or "id" not in c or "dimension" not in c:
            raise InputError("each conclusion needs id and dimension")
        cid, dim = c["id"], c["dimension"]
        if dim not in DIMENSIONS:
            raise InputError("conclusion %s dimension %r is not one of %s" % (cid, dim, sorted(DIMENSIONS)))
        cited = [evidence[x] for x in c.get("evidence", []) if x in evidence]
        unknown = [x for x in c.get("evidence", []) if x not in evidence]
        if unknown:
            findings.append(_finding("unknown-evidence", "error", "cites evidence not in the record: %s" % ", ".join(unknown), cid))
        if not cited:
            findings.append(_finding("no-evidence", "error", "conclusion cites no evidence", cid))
            continue
        if not any(dim in e.get("dimensions", []) for e in cited):
            findings.append(_finding("cross-dimension", "error",
                                     "concludes about %s but the cited evidence covers %s; evidence for one dimension does not establish another"
                                     % (dim, ", ".join(sorted({d for e in cited for d in e.get("dimensions", [])})) or "nothing"), cid))
        if c.get("about_learning") and all(e.get("kind") in NOT_LEARNING for e in cited):
            findings.append(_finding("not-learning-evidence", "error",
                                     "learning conclusion rests on %s, which is not evidence of learning"
                                     % ", ".join(sorted({e["kind"] for e in cited})), cid))
    sc = doc.get("standards_check")
    if doc.get("standards_mapping") and not sc:
        findings.append(_finding("standards-unchecked", "error",
                                 "standards or credential mapping is present but has no edu-standards-alignment result attached"))
    errors = sum(f["severity"] == "error" for f in findings)
    return {"ok": errors == 0, "mode": "program", "program": doc.get("name", ""),
            "counts": {"error": errors, "warn": len(findings) - errors}, "findings": findings}


# ---------------------------------------------------------------- citations

TIMEOUT = 20


def _norm(text: str) -> str:
    text = unicodedata.normalize("NFKD", text or "")
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).lower()
    return " ".join(re.findall(r"[a-z0-9]+", text))


def _similarity(a: str, b: str) -> float:
    return difflib.SequenceMatcher(None, _norm(a), _norm(b)).ratio()


def _crossref_meta(item: Dict[str, Any]) -> Dict[str, Any]:
    titles = item.get("title") or [""]
    subs = item.get("subtitle") or []
    variants = [titles[0]] + ["%s: %s" % (titles[0], s) for s in subs]
    years = sorted({dp[0][0] for k in ("issued", "published-print", "published-online", "published")
                    for dp in [((item.get(k) or {}).get("date-parts") or [[None]])] if dp and dp[0] and dp[0][0]})
    people = item.get("author") or item.get("editor") or []  # edited volumes list editors, not authors
    return {"titles": variants, "years": years, "authors": [a.get("family", a.get("name", "")) for a in people],
            "doi": item.get("DOI", ""), "source": "crossref"}


def _http_json(url: str) -> Optional[Dict[str, Any]]:
    """GET JSON with a 1 s pause before each call and up to 2 retries on HTTP 429 (waits capped at 10 s)."""
    for attempt in range(3):
        time.sleep(1.0)
        try:
            with urllib.request.urlopen(url, timeout=TIMEOUT) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            if exc.code != 429 or attempt == 2:
                raise
            wait = exc.headers.get("Retry-After", "") if exc.headers else ""
            time.sleep(min(10.0, float(wait)) if wait.isdigit() else 5.0 * (attempt + 1))
    return None


def live_resolver(key: str) -> Optional[Dict[str, Any]]:
    kind, _, value = key.partition(":")
    if kind == "doi":
        doc = _http_json("https://api.crossref.org/works/" + urllib.parse.quote(value, safe="/"))
        return _crossref_meta(doc["message"]) if doc else None
    if kind == "arxiv":
        url = "https://export.arxiv.org/api/query?id_list=" + urllib.parse.quote(value)
        with urllib.request.urlopen(url, timeout=TIMEOUT) as resp:
            raw = resp.read()
        if b"<!DOCTYPE" in raw or b"<!ENTITY" in raw:  # stdlib only: refuse DTDs instead of parsing them
            raise ValueError("arXiv response carries a DTD or entity declaration; refused")
        root = ET.fromstring(raw)
        ns = {"a": "http://www.w3.org/2005/Atom", "x": "http://arxiv.org/schemas/atom"}
        entry = root.find("a:entry", ns)
        if entry is None or entry.find("a:title", ns) is None or "api/errors" in (entry.findtext("a:id", "", ns)):
            return None
        title = " ".join(entry.findtext("a:title", "", ns).split())
        year = int(entry.findtext("a:published", "0", ns)[:4] or 0)
        return {"titles": [title], "years": [year], "authors": [a.findtext("a:name", "", ns) for a in entry.findall("a:author", ns)],
                "doi": entry.findtext("x:doi", "", ns), "source": "arxiv"}
    if kind == "search":
        url = "https://api.crossref.org/works?rows=3&query.bibliographic=" + urllib.parse.quote(value)
        doc = _http_json(url)
        items = (doc or {}).get("message", {}).get("items", [])
        return {"candidates": [_crossref_meta(i) for i in items], "source": "crossref-search"} if items else None
    raise InputError("unknown resolver key %s" % key)


def _keys(ref: Dict[str, Any]) -> Tuple[str, str]:
    if ref.get("doi"):
        return "doi:" + ref["doi"].lower(), "doi"
    if ref.get("arxiv"):
        return "arxiv:" + ref["arxiv"], "arxiv"
    cited = ref["cited"]
    q = "%s %s %s" % (cited["title"], " ".join(cited.get("authors", [])[:2]), cited.get("year", ""))
    return "search:" + _norm(q), "search"


def _compare(cited: Dict[str, Any], meta: Dict[str, Any]) -> Dict[str, Any]:
    sim = max(_similarity(cited["title"], t) for t in meta["titles"]) if meta["titles"] else 0.0
    year_ok = cited.get("year") in meta["years"]
    first = _norm((cited.get("authors") or [""])[0])
    if not meta["authors"]:
        author_ok: Optional[bool] = None  # registry lists no people (corporate author): unchecked, not wrong
    else:
        # one-word surnames match a whole token; multi-word corporate names match as a phrase ("The X Collective")
        author_ok = bool(first) and any((first in _norm(a)) if " " in first else (first in _norm(a).split())
                                        for a in meta["authors"])
    return {"title_similarity": round(sim, 3), "year_ok": year_ok, "first_author_ok": author_ok,
            "resolved_title": meta["titles"][0] if meta["titles"] else "", "resolved_years": meta["years"],
            "resolved_doi": meta.get("doi", ""), "resolved_by": meta.get("source", "")}


def check_citations(doc: Dict[str, Any], resolver: Callable[[str], Optional[Dict[str, Any]]],
                    recorder: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    refs = _need(doc, "references", list, "refs")
    if not refs:
        raise InputError("refs.references is empty")
    results = []
    for ref in refs:
        if not isinstance(ref, dict) or not isinstance(ref.get("id"), str) or not isinstance(ref.get("cited"), dict):
            raise InputError("each reference needs a string id and a cited object")
        cited = ref["cited"]
        if not isinstance(cited.get("title"), str) or not isinstance(cited.get("year"), int):
            raise InputError("reference %s needs cited.title (string) and cited.year (integer)" % ref["id"])
        key, how = _keys(ref)
        try:
            meta = resolver(key)
        except InputError:
            raise
        except Exception as exc:  # network failures become an honest unresolved status
            results.append({"id": ref["id"], "status": "unresolved", "key": key, "reason": "lookup failed: %s" % exc})
            continue
        if recorder is not None:
            recorder[key] = meta
        if meta is None:
            results.append({"id": ref["id"], "status": "unresolved", "key": key, "reason": "identifier or search found no record"})
            continue
        if how == "search":
            scored = [(_compare(cited, m), m) for m in meta.get("candidates", [])]
            best = max(scored, key=lambda s: s[0]["title_similarity"])[0] if scored else None
            if best is None or best["title_similarity"] < 0.6:
                results.append({"id": ref["id"], "status": "unresolved", "key": key,
                                "reason": "no search candidate resembles the cited title", "best": best})
                continue
            cmp_ = best
        else:
            cmp_ = _compare(cited, meta)
        checks = (("title", cmp_["title_similarity"] >= 0.85), ("year", cmp_["year_ok"]),
                  ("first_author", cmp_["first_author_ok"]))
        bad = [f for f, ok in checks if ok is False]
        unchecked = [f for f, ok in checks if ok is None]
        results.append(dict({"id": ref["id"], "status": "verified" if not bad else "mismatch", "key": key,
                             "mismatched": bad, "unchecked": unchecked}, **cmp_))
    counts = {s: sum(r["status"] == s for r in results) for s in ("verified", "mismatch", "unresolved")}
    return {"ok": counts["verified"] == len(results), "mode": "citations", "source": doc.get("source", ""),
            "counts": counts, "results": results}


def offline_resolver(path: str) -> Callable[[str], Optional[Dict[str, Any]]]:
    table = _load(path)
    entries = table.get("entries")
    if not isinstance(entries, dict):
        raise InputError("%s must hold an object 'entries' keyed by doi:/arxiv:/search: keys" % path)

    def resolve(key: str) -> Optional[Dict[str, Any]]:
        return entries.get(key)
    return resolve


# ---------------------------------------------------------------- cli

def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="research_check")
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("claims", "design", "program"):
        sub.add_parser(name).add_argument("file")
    c = sub.add_parser("citations")
    c.add_argument("file")
    c.add_argument("--offline", help="resolver JSON; no network")
    c.add_argument("--record", help="write every lookup to this resolver JSON for offline reruns")
    try:
        args = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    try:
        doc = _load(args.file)
        if args.cmd == "claims":
            out = check_claims(doc)
        elif args.cmd == "design":
            out = check_design(doc)
        elif args.cmd == "program":
            out = check_program(doc)
        else:
            recorder: Optional[Dict[str, Any]] = {} if args.record else None
            resolver = offline_resolver(args.offline) if args.offline else live_resolver
            out = check_citations(doc, resolver, recorder)
            out["resolver"] = "offline:" + args.offline if args.offline else "live"
            if args.record:
                with open(args.record, "w", encoding="utf-8") as fh:
                    json.dump({"label": "Resolver responses recorded live by research_check citations --record; "
                                        "replay with --offline for repeatable runs.", "entries": recorder},
                              fh, indent=2, ensure_ascii=False, sort_keys=True)
                    fh.write("\n")
    except InputError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, indent=2))
        return 2
    print(json.dumps(out, indent=2, ensure_ascii=False))
    return 0 if out["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
