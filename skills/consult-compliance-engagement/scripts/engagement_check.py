#!/usr/bin/env python3
"""Compliance engagement workflow gate.

Checks one engagement record through six stages in order: applicability, control owners, evidence
collection, gap remediation, independent review, authorized report. Each stage reports its own
errors. A report can be authorized only by a human, only when every earlier stage passes, and only
with claims that keep technical conformance, regulatory applicability, organizational
certification and legal conclusions apart.

Optional input: the JSON output of compliance-os framework_selector.py (alirezarezvani/claude-skills).
Every framework it selects must be resolved (applies or not-applicable with a rationale).

Exit: 0 report may issue or is ready for human authorization, 1 not ready, 2 invalid input.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import date
from typing import Any, Dict, List, Set

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY = os.path.join(HERE, "..", "references", "applicability-registry.json")

DECISIONS = ("applies", "not-applicable", "undetermined")
CLAIM_KINDS = ("technical-conformance", "regulatory-applicability", "organizational-certification", "legal-conclusion")
OVERREACH = re.compile(r"\b(certified|certification|fully compliant|100% compliant|guarantee[sd]?|legally compliant|audit[- ]ready)\b", re.I)
CERTIFY = re.compile(r"\b(certified|certification|certificate|attested|attestation)\b", re.I)
COMPLY = re.compile(r"\b(complies|comply|compliant|compliance|conforms?|conformance|meets)\b", re.I)
LEGAL = re.compile(r"\b(lawful|unlawful|legally|legal exposure|liabilit(y|ies)|meets (its|their) (legal )?obligations)\b", re.I)
ATTESTED_KINDS = ("attestation-criteria", "certifiable-management-standard", "contractual-standard")
LEVEL = re.compile(r"\blevel\s+a{1,3}\b", re.I)
SC = re.compile(r"\b\d+\.\d+\.\d+\b")
STAGES = ("applicability", "control-owners", "evidence-collection", "gap-remediation", "independent-review", "authorized-report")


class InvalidInput(Exception):
    pass


def human(p: Any) -> bool:
    return isinstance(p, str) and p.startswith("human:") and len(p) > 6


def e(code: str, where: str, message: str) -> Dict[str, str]:
    return {"code": code, "where": where, "message": message}


def load(path: str) -> Any:
    try:
        with open(path, "r", encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError) as exc:
        raise InvalidInput("cannot read %s: %s" % (path, exc))


def parse(doc: Any, path: str) -> Dict[str, Any]:
    if not isinstance(doc, dict) or doc.get("schema") != "compliance-engagement.v1":
        raise InvalidInput("%s is not schema compliance-engagement.v1" % path)
    for field, kind in (("engagement_id", str), ("tenant_id", str), ("as_of", str), ("applicability", list),
                        ("controls", list), ("evidence", list), ("exceptions", list), ("review", dict), ("report", dict)):
        if not isinstance(doc.get(field), kind):
            raise InvalidInput("%s needs %s (%s)" % (path, field, kind.__name__))
    try:
        doc["_as_of"] = date.fromisoformat(doc["as_of"])
        for ev in doc["evidence"]:
            ev["_collected"] = date.fromisoformat(ev["collected_on"])
            if not isinstance(ev.get("max_age_days"), int):
                raise InvalidInput("evidence %s needs an integer max_age_days" % ev.get("ref"))
    except (KeyError, TypeError, ValueError) as exc:
        raise InvalidInput("%s has a missing or malformed date: %s" % (path, exc))
    for a in doc["applicability"]:
        if not isinstance(a, dict) or a.get("decision") not in DECISIONS or not isinstance(a.get("framework"), str):
            raise InvalidInput("each applicability entry needs framework and decision in %s" % ", ".join(DECISIONS))
    for c in doc["report"].get("claims", []):
        if c.get("kind") not in CLAIM_KINDS:
            raise InvalidInput("report claim %s kind must be one of %s" % (c.get("id"), ", ".join(CLAIM_KINDS)))
    return doc


# ---- stages ----

def applicability(doc: Dict[str, Any], registry: Dict[str, Any], selected: List[str]) -> List[Dict[str, str]]:
    out = []
    seen = {a["framework"] for a in doc["applicability"]}
    for fid in selected:
        if fid in registry and fid not in seen:
            out.append(e("selector-framework-unresolved", fid, "framework_selector picked %s; record applies or not-applicable with a rationale" % fid))
        elif fid not in registry:
            out.append(e("framework-unregistered", fid, "framework_selector picked %s, which the applicability registry lacks; add it with edition and rights first" % fid))
    for a in doc["applicability"]:
        fid = a["framework"]
        reg = registry.get(fid)
        if reg is None:
            out.append(e("framework-unregistered", fid, "not in references/applicability-registry.json"))
            continue
        if a["decision"] == "undetermined":
            out.append(e("applicability-undetermined", fid, "decide applies or not-applicable before any checklist use"))
            continue
        if a["decision"] == "not-applicable":
            if not a.get("rationale"):
                out.append(e("rationale-missing", fid, "not-applicable needs a rationale"))
            continue
        for field in ("edition", "jurisdiction", "scope"):
            if not a.get(field):
                out.append(e("applicability-incomplete", fid, "applies needs %s" % field))
        if a.get("edition") and a["edition"] != reg["edition"]:
            out.append(e("edition-mismatch", fid, "engagement uses %r; registry edition is %r" % (a["edition"], reg["edition"])))
        if reg["text_rights"] not in ("public",) and a.get("text_rights_status") != "obtained":
            out.append(e("licensed-text-not-obtained", fid, "%s text is %s; obtain it before using its checklist" % (reg["name"], reg["text_rights"])))
        for field in ("evidence_owner", "review_authority"):
            if not human(a.get(field)):
                out.append(e("owner-not-human", fid, "%s must be a named human principal, got %r" % (field, a.get(field))))
    return out


def applicable(doc: Dict[str, Any]) -> Set[str]:
    return {a["framework"] for a in doc["applicability"] if a["decision"] == "applies"}


def control_owners(doc: Dict[str, Any]) -> List[Dict[str, str]]:
    out = []
    live = applicable(doc)
    for c in doc["controls"]:
        if c.get("framework") not in live:
            out.append(e("control-framework-not-applicable", c.get("id", "?"), "control maps to %s, which is not an applicable framework" % c.get("framework")))
        if not human(c.get("owner")):
            out.append(e("control-owner-not-human", c.get("id", "?"), "control owner must be a named human, got %r" % c.get("owner")))
    return out


def artifact_errors(doc: Dict[str, Any], ev: Dict[str, Any], root: str) -> List[Dict[str, str]]:
    """The record's hash and tenant count only if the artifact under <root>/<tenant_id>/<ref> has that hash."""
    ref = str(ev.get("ref", ""))
    parts = ref.replace("\\", "/").split("/")
    if not ref or os.path.isabs(ref) or ".." in parts:
        return [e("evidence-ref-invalid", ref or "?", "ref must be a relative path inside the tenant's evidence store")]
    out = []
    foreign = [p for p in parts if p.startswith("tenant-") and p != doc["tenant_id"]]
    if foreign:
        out.append(e("evidence-ref-names-other-tenant", ref, "ref points into %s, not %s" % (foreign[0], doc["tenant_id"])))
    if not root:
        return out + [e("evidence-hash-unverified", ref, "no --evidence-root; the hash was not recomputed from the artifact")]
    path = os.path.join(root, doc["tenant_id"], ref)
    if not os.path.isfile(path):
        return out + [e("evidence-artifact-missing", ref, "no artifact at <evidence-root>/%s/%s" % (doc["tenant_id"], ref))]
    with open(path, "rb") as fh:
        actual = hashlib.sha256(fh.read()).hexdigest()
    if actual != ev.get("sha256"):
        out.append(e("evidence-hash-mismatch", ref, "artifact hashes to %s, the record says %s" % (actual[:12], str(ev.get("sha256"))[:12])))
    return out


def evidence_collection(doc: Dict[str, Any], root: str = "") -> List[Dict[str, str]]:
    out = []
    by_control: Dict[str, int] = {}
    reviewer = doc["review"].get("reviewer")
    for ev in doc["evidence"]:
        ref = ev.get("ref", "?")
        by_control[ev.get("control")] = by_control.get(ev.get("control"), 0) + 1
        age = (doc["_as_of"] - ev["_collected"]).days
        if age > ev["max_age_days"]:
            out.append(e("evidence-stale", ref, "collected %s, %d days before %s; limit %d" % (ev["collected_on"], age, doc["as_of"], ev["max_age_days"])))
        if age < 0:
            out.append(e("evidence-future-dated", ref, "collected_on %s is after as_of %s" % (ev["collected_on"], doc["as_of"])))
        if not re.fullmatch(r"[0-9a-f]{64}", str(ev.get("sha256", ""))):
            out.append(e("evidence-unhashed", ref, "evidence needs a sha256 of the collected artifact"))
        if ev.get("tenant_id") != doc["tenant_id"]:
            out.append(e("evidence-cross-tenant", ref, "evidence belongs to %s, engagement is %s" % (ev.get("tenant_id"), doc["tenant_id"])))
        out.extend(artifact_errors(doc, ev, root))
        if ev.get("collected_by") == reviewer:
            out.append(e("collector-is-reviewer", ref, "%s collected evidence it will review" % reviewer))
    for c in doc["controls"]:
        if by_control.get(c.get("id"), 0) == 0:
            out.append(e("control-without-evidence", c.get("id", "?"), "no operating evidence collected"))
    return out


def gap_remediation(doc: Dict[str, Any]) -> List[Dict[str, str]]:
    out = []
    for x in doc["exceptions"]:
        xid = x.get("id", "?")
        status = x.get("status")
        if status == "risk-accepted" and not (human(x.get("accepted_by")) and x.get("expires")):
            out.append(e("exception-acceptance-invalid", xid, "risk acceptance needs a named human accepted_by and an expiry"))
        elif status == "remediated" and not x.get("retest_evidence"):
            out.append(e("remediation-unverified", xid, "remediated needs retest evidence"))
        elif status == "open":
            out.append(e("exception-open", xid, "open gap: remediate, or a named human accepts the risk"))
        elif status not in ("risk-accepted", "remediated", "open"):
            out.append(e("exception-status-unknown", xid, "status %r" % status))
    return out


def independent_review(doc: Dict[str, Any]) -> List[Dict[str, str]]:
    out = []
    review = doc["review"]
    reviewer = review.get("reviewer")
    producers = {ev.get("collected_by") for ev in doc["evidence"]} | {doc["report"].get("author")}
    if not reviewer:
        out.append(e("review-missing", "review", "no independent reviewer recorded"))
        return out
    if reviewer in producers:
        out.append(e("reviewer-not-independent", "review", "%s produced evidence or the report it reviews" % reviewer))
    missing = applicable(doc) - set(review.get("scope_covered", []))
    if missing:
        out.append(e("review-scope-incomplete", "review", "review did not cover %s" % ", ".join(sorted(missing))))
    if review.get("result") not in ("no-findings", "findings-recorded"):
        out.append(e("review-not-complete", "review", "review result is %r" % review.get("result")))
    return out


def authorized_report(doc: Dict[str, Any], earlier_failed: bool, registry: Dict[str, Any]) -> List[Dict[str, str]]:
    out = []
    rep = doc["report"]
    evidenced = {c["id"] for c in doc["controls"] if any(ev.get("control") == c["id"] for ev in doc["evidence"])}
    for c in rep.get("claims", []):
        cid, kind, text = c.get("id", "?"), c["kind"], c.get("text", "")
        basis = c.get("basis") or {}
        fkind = registry.get(c.get("framework"), {}).get("kind")
        # A label can only make a claim stricter: the text and the framework decide what it asserts.
        if kind != "organizational-certification" and (CERTIFY.search(text) or (COMPLY.search(text) and fkind in ATTESTED_KINDS)):
            kind = "organizational-certification"
        elif kind != "legal-conclusion" and (LEGAL.search(text) or (COMPLY.search(text) and fkind == "regulation")):
            kind = "legal-conclusion"
        if kind == "technical-conformance" and c.get("framework") == "wcag_2_2":
            named = SC.findall(text)
            broad = LEVEL.search(text) or (COMPLY.search(text) and not named)
            if broad and not (basis.get("kind") == "full-evaluation" and basis.get("ref")):
                out.append(e("conformance-claim-exceeds-evidence", cid, "a level or whole-standard conformance claim needs a full-evaluation basis covering every criterion in scope"))
            for sc in named:
                if "WCAG-%s" % sc not in evidenced:
                    out.append(e("conformance-claim-exceeds-evidence", cid, "success criterion %s has no evidenced control" % sc))
        if kind == "organizational-certification" and not (basis.get("kind") == "external-attestation" and basis.get("ref") and human(basis.get("issued_by"))):
            out.append(e("certification-claim-without-attestation", cid, "a certification claim needs an external attestation (%s)"
                         % registry.get(c.get("framework"), {}).get("attestation", "issuer named by the framework")))
        if kind == "legal-conclusion" and not (basis.get("kind") == "legal-opinion" and human(basis.get("issued_by"))):
            out.append(e("legal-conclusion-without-counsel", cid, "a legal conclusion needs counsel's opinion; the practice does not give one"))
        if kind in ("technical-conformance", "regulatory-applicability") and OVERREACH.search(text):
            out.append(e("claim-category-overreach", cid, "%s claim uses %r; keep conformance, applicability, certification and legal conclusions apart"
                         % (kind, OVERREACH.search(text).group(0))))
    if rep.get("status") == "authorized":
        if not human(rep.get("authorized_by")):
            out.append(e("report-not-authorized-by-human", "report", "authorized_by must be a named human, got %r" % rep.get("authorized_by")))
        if rep.get("authorized_by") in {ev.get("collected_by") for ev in doc["evidence"]} | {rep.get("author")}:
            out.append(e("report-self-authorized", "report", "the report's author or an evidence collector authorized it"))
        if earlier_failed:
            out.append(e("report-authorized-with-open-errors", "report", "report marked authorized while earlier stages fail"))
    return out


def check(doc: Dict[str, Any], registry: Dict[str, Any], selected: List[str], root: str = "") -> Dict[str, Any]:
    results = [
        ("applicability", applicability(doc, registry, selected)),
        ("control-owners", control_owners(doc)),
        ("evidence-collection", evidence_collection(doc, root)),
        ("gap-remediation", gap_remediation(doc)),
        ("independent-review", independent_review(doc)),
    ]
    earlier_failed = any(errs for _, errs in results)
    results.append(("authorized-report", authorized_report(doc, earlier_failed, registry)))
    stages = [{"stage": name, "status": "fail" if errs else "pass", "errors": errs} for name, errs in results]
    ready = not any(s["errors"] for s in stages)
    authorized = doc["report"].get("status") == "authorized"
    return {
        "engagement_id": doc["engagement_id"],
        "stages": stages,
        "decision": "report-may-issue" if ready and authorized else ("ready-for-human-authorization" if ready else "not-ready"),
        "human_decisions_required": ["Applicability sign-off by each review_authority", "Risk acceptance for any open gap",
                                     "Report authorization by the engagement owner", "Any certification or legal conclusion by its external issuer"],
        "not_checked": ["whether a control is designed well", "the content of each evidence artifact", "the current edition at the publisher",
                        "contractual or sector obligations not listed in the applicability record"],
    }


def main(argv: List[str]) -> int:
    ap = argparse.ArgumentParser(prog="engagement_check")
    ap.add_argument("--engagement", required=True)
    ap.add_argument("--selector", help="JSON output of compliance-os framework_selector.py --output json")
    ap.add_argument("--evidence-root", default="", help="directory holding <tenant_id>/<ref> evidence artifacts to rehash")
    args = ap.parse_args(argv)
    try:
        doc = parse(load(args.engagement), args.engagement)
        registry = load(REGISTRY)["frameworks"]
        selected: List[str] = []
        if args.selector:
            sel = load(args.selector)
            if not isinstance(sel, dict) or not isinstance(sel.get("applicable_frameworks"), list):
                raise InvalidInput("%s is not framework_selector output (applicable_frameworks missing)" % args.selector)
            selected = [f["id"] for f in sel["applicable_frameworks"] if isinstance(f, dict) and "id" in f]
    except InvalidInput as exc:
        print(json.dumps({"error": str(exc)}, indent=2))
        return 2
    result = check(doc, registry, selected, args.evidence_root)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 1 if result["decision"] == "not-ready" else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
