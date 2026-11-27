#!/usr/bin/env python3
"""Deterministic check of a draft search-claims report against a source register.

Rejects fabricated citations, quotes absent from the captured source,
guaranteed-placement promises, and ranking-factor or forecast claims stated
as fact without primary evidence. No network calls; reads only the paths given.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

REPORT_SCHEMA = "search-claims.v1"
REGISTER_SCHEMA = "source-register.v1"
KINDS = ("observation", "recommendation", "ranking-factor", "forecast")
STATUSES = ("observed", "hypothesis", "estimate", "recommendation")
SOURCE_KINDS = ("primary-platform-doc", "first-party-measurement", "secondary")
PRIMARY_KINDS = ("primary-platform-doc", "first-party-measurement")
MIN_QUOTE_WORDS = 4
MIN_SHARED_TERMS = 2
STOPWORDS = {"that", "this", "with", "from", "have", "will", "your", "been", "they", "than", "into", "more", "most", "about",
             "which", "their", "there", "when", "what", "were", "also", "only", "such", "each", "must", "should", "page's"}
PATTERNS_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "references", "guarantee-patterns.json"
)

HUMAN_REVIEW = [
    "Observed visibility needs the tenant's own Search Console or analytics exports",
    "Every claim the script passes still needs a human read, including guarantee wording outside the pattern list",
    "Recommendations are judgment calls; the script only checks their evidence and wording",
]
NOT_CHECKED = [
    "whether a cited source is itself accurate",
    "whether a quote supports the claim it is attached to",
    "live search or AI-answer state",
    "whether a primary source's current text still matches the capture",
]


class InputError(Exception):
    pass


def load_json(path: str, what: str) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except OSError as exc:
        raise InputError("cannot read %s file %s: %s" % (what, path, exc.strerror))
    except ValueError as exc:
        raise InputError("%s file is not valid JSON: %s" % (what, exc))
    if not isinstance(data, dict):
        raise InputError("%s file must be a JSON object" % what)
    return data


def require_str(obj: Dict[str, Any], key: str, where: str) -> str:
    val = obj.get(key)
    if not isinstance(val, str) or not val.strip():
        raise InputError("%s: missing or empty string field '%s'" % (where, key))
    return val


def validate_register(reg: Dict[str, Any]) -> Dict[str, Dict[str, str]]:
    if reg.get("schema") != REGISTER_SCHEMA:
        raise InputError("register schema must be '%s'" % REGISTER_SCHEMA)
    require_str(reg, "label", "register")
    sources = reg.get("sources")
    if not isinstance(sources, list):
        raise InputError("register: 'sources' must be a list")
    out = {}  # type: Dict[str, Dict[str, str]]
    for i, src in enumerate(sources):
        where = "register source #%d" % i
        if not isinstance(src, dict):
            raise InputError("%s must be an object" % where)
        for key in ("id", "url", "title", "retrieved", "capture_path", "sha256"):
            require_str(src, key, where)
        for key in ("registered_by", "verified_by"):
            if key in src and not isinstance(src[key], str):
                raise InputError("%s: %s must be a string" % (where, key))
        if src.get("kind") not in SOURCE_KINDS:
            raise InputError("%s: kind must be one of %s" % (where, ", ".join(SOURCE_KINDS)))
        cap = src["capture_path"]
        if os.path.isabs(cap) or ".." in cap.replace("\\", "/").split("/"):
            raise InputError("%s: capture_path must stay inside the register directory" % where)
        if src["id"] in out:
            raise InputError("register: duplicate source id '%s'" % src["id"])
        out[src["id"]] = src
    return out


def validate_report(rep: Dict[str, Any]) -> List[Dict[str, Any]]:
    if rep.get("schema") != REPORT_SCHEMA:
        raise InputError("report schema must be '%s'" % REPORT_SCHEMA)
    for key in ("label", "report_id", "tenant_id"):
        require_str(rep, key, "report")
    claims = rep.get("claims")
    if not isinstance(claims, list):
        raise InputError("report: 'claims' must be a list")
    seen = set()
    for i, claim in enumerate(claims):
        where = "claim #%d" % i
        if not isinstance(claim, dict):
            raise InputError("%s must be an object" % where)
        cid = require_str(claim, "id", where)
        require_str(claim, "text", where)
        if cid in seen:
            raise InputError("duplicate claim id '%s'" % cid)
        seen.add(cid)
        if claim.get("kind") not in KINDS:
            raise InputError("%s: kind must be one of %s" % (where, ", ".join(KINDS)))
        if claim.get("status_label") not in STATUSES:
            raise InputError("%s: status_label must be one of %s" % (where, ", ".join(STATUSES)))
        ev = claim.get("evidence")
        if not isinstance(ev, list):
            raise InputError("%s: 'evidence' must be a list" % where)
        for j, item in enumerate(ev):
            if not isinstance(item, dict):
                raise InputError("%s evidence #%d must be an object" % (where, j))
            require_str(item, "source_id", "%s evidence #%d" % (where, j))
            if not isinstance(item.get("quote"), str):
                raise InputError("%s evidence #%d: 'quote' must be a string" % (where, j))
    return claims


def load_patterns(path: str = PATTERNS_PATH) -> List[Tuple[str, "re.Pattern[str]"]]:
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    return [(p["id"], re.compile(p["regex"], re.IGNORECASE)) for p in data["patterns"]]


def normalize(text: str) -> str:
    table = {
        0x2018: "'", 0x2019: "'", 0x201A: "'", 0x201B: "'",
        0x201C: '"', 0x201D: '"', 0x201E: '"', 0x201F: '"',
    }
    return " ".join(text.translate(table).lower().split())


def terms(text: str) -> set:
    return {w for w in re.findall(r"[a-z0-9]+", normalize(text)) if len(w) >= 4 and w not in STOPWORDS}


def verified_primary(src: Dict[str, str]) -> bool:
    """A primary source counts as primary only when a human other than whoever registered it verified the capture."""
    who = src.get("verified_by", "")
    return src["kind"] in PRIMARY_KINDS and who.startswith("human:") and len(who) > 6 and who != src.get("registered_by")


def defect(code: str, claim_id: str, message: str) -> Dict[str, str]:
    return {"code": code, "severity": "error", "claim_id": claim_id, "message": message}


def check_capture(src: Dict[str, str], register_dir: str) -> Tuple[Optional[str], Optional[Tuple[str, str]]]:
    """Return (capture_text, None) when usable, else (None, (code, message))."""
    path = os.path.join(register_dir, src["capture_path"])
    try:
        with open(path, "rb") as fh:
            raw = fh.read()
    except OSError:
        return None, ("capture-missing", "capture file for source '%s' not found at %s" % (src["id"], src["capture_path"]))
    digest = hashlib.sha256(raw).hexdigest()
    if digest != src["sha256"].lower():
        return None, (
            "capture-hash-mismatch",
            "capture for source '%s' hashes to %s, register says %s (edited or stale capture)"
            % (src["id"], digest, src["sha256"]),
        )
    return raw.decode("utf-8", errors="replace"), None


def check_claim(
    claim: Dict[str, Any],
    sources: Dict[str, Dict[str, str]],
    captures: Dict[str, Tuple[Optional[str], Optional[Tuple[str, str]]]],
    patterns: List[Tuple[str, "re.Pattern[str]"]],
) -> List[Dict[str, str]]:
    cid = claim["id"]
    defects = []  # type: List[Dict[str, str]]
    for pid, rx in patterns:
        if rx.search(claim["text"]):
            defects.append(defect("guaranteed-placement", cid, "text promises placement (pattern %s)" % pid))
            break
    evidence = claim["evidence"]
    if not evidence and (claim["kind"] == "observation" or claim["status_label"] == "observed"):
        defects.append(defect("observation-without-evidence", cid, "observed claim cites no evidence"))
    primary_ok = False
    for item in evidence:
        sid = item["source_id"]
        src = sources.get(sid)
        if src is None:
            defects.append(defect("citation-unknown-source", cid, "source_id '%s' is not in the register" % sid))
            continue
        text, problem = captures[sid]
        if problem is not None:
            defects.append(defect(problem[0], cid, problem[1]))
            continue
        nq = normalize(item["quote"])
        if not nq or nq not in normalize(text or ""):
            defects.append(defect("quote-not-found", cid, "quote not found in capture of source '%s'" % sid))
            continue
        if len(nq.split()) < MIN_QUOTE_WORDS:
            defects.append(defect("quote-too-short", cid, "quote from '%s' has fewer than %d words, too short to support a claim" % (sid, MIN_QUOTE_WORDS)))
            continue
        if len(terms(item["quote"]) & terms(claim["text"])) < MIN_SHARED_TERMS:
            defects.append(defect("quote-unrelated", cid, "quote from '%s' shares fewer than %d content words with the claim" % (sid, MIN_SHARED_TERMS)))
            continue
        if verified_primary(src):
            primary_ok = True
    if claim["kind"] == "ranking-factor" and claim["status_label"] != "hypothesis" and not primary_ok:
        defects.append(defect(
            "ranking-factor-unsupported", cid,
            "ranking factor stated as fact without a verified primary-platform-doc or first-party-measurement quote; label it hypothesis or add primary evidence",
        ))
    if claim["kind"] == "forecast" and claim["status_label"] not in ("hypothesis", "estimate"):
        defects.append(defect("forecast-unlabeled", cid, "forecast must carry status_label hypothesis or estimate"))
    return defects


def verdict_for(claim: Dict[str, Any], defects: List[Dict[str, str]]) -> str:
    if any(d["severity"] == "error" for d in defects):
        return "rejected"
    if claim["status_label"] in ("hypothesis", "estimate"):
        return "hypothesis"
    return "supported"


def run_check(report: Dict[str, Any], register: Dict[str, Any], register_dir: str,
              patterns: List[Tuple[str, "re.Pattern[str]"]]) -> Dict[str, Any]:
    claims = validate_report(report)
    sources = validate_register(register)
    captures = {}  # type: Dict[str, Tuple[Optional[str], Optional[Tuple[str, str]]]]
    for claim in claims:
        for item in claim["evidence"]:
            sid = item["source_id"]
            if sid in sources and sid not in captures:
                captures[sid] = check_capture(sources[sid], register_dir)
    results = []
    by_code = {}  # type: Dict[str, int]
    tally = {"supported": 0, "hypothesis": 0, "rejected": 0}
    errors = 0
    for claim in claims:
        defects = check_claim(claim, sources, captures, patterns)
        verdict = verdict_for(claim, defects)
        tally[verdict] += 1
        for d in defects:
            by_code[d["code"]] = by_code.get(d["code"], 0) + 1
            errors += 1 if d["severity"] == "error" else 0
        results.append({"id": claim["id"], "verdict": verdict, "defects": defects})
    return {
        "report_id": report["report_id"],
        "status": "defects" if errors else "pass",
        "claims": results,
        "counts": {"claims": len(claims), "errors": errors, "by_code": by_code,
                   "supported": tally["supported"], "hypothesis": tally["hypothesis"],
                   "rejected": tally["rejected"]},
        "human_review_required": HUMAN_REVIEW,
        "not_checked": NOT_CHECKED,
    }


def emit(obj: Dict[str, Any]) -> None:
    print(json.dumps(obj, indent=2, sort_keys=True))


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Check a search-claims.v1 report against a source-register.v1 file.")
    parser.add_argument("--claims", required=True, help="path to the draft report JSON")
    parser.add_argument("--sources", required=True, help="path to the source register JSON")
    args = parser.parse_args(argv)
    try:
        report = load_json(args.claims, "claims")
        register = load_json(args.sources, "sources")
        patterns = load_patterns()
        result = run_check(report, register, os.path.dirname(os.path.abspath(args.sources)), patterns)
    except InputError as exc:
        emit({"error": str(exc)})
        return 2
    emit(result)
    return 1 if result["status"] == "defects" else 0


if __name__ == "__main__":
    sys.exit(main())
