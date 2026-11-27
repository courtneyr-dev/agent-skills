#!/usr/bin/env python3
"""standards_check: keep standards, qualification and professional-source records honest.

  registry  [--registry R]                       validate the standards registry
  orgs      [--orgs O]                           validate the professional-organization registry
  align     FILE [--registry R]                  check objective -> criterion -> standard alignments
  coverage  FILE --record ID --field NAME [--registry R]   label coverage (NBEA areas, ISTE roles)
  org-refs  FILE [--orgs O]                      check how a document refers to organizations

Prints JSON. Exit 0 ok, 1 findings that block the claim or invalid input, 2 usage error.
Python 3.9+ standard library only. The registries hold metadata, never protected standard text.
"""
from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.dirname(HERE)
DEFAULT_REGISTRY = os.path.join(SKILL, "references", "standards-registry.json")
DEFAULT_ORGS = os.path.join(SKILL, "references", "organizations.json")
CF = os.path.normpath(os.path.join(SKILL, "..", "company-fleets"))

KINDS = {"student-standard", "educator-standard", "teacher-standard", "university-curriculum",
         "occupational-assessment", "state-certification", "state-staffing", "state-curriculum",
         "district-curriculum", "local-policy", "design-guideline", "interoperability-spec",
         "course-review-rubric", "accessibility-standard", "research-synthesis"}
AUDIENCES = {"students", "educators", "coaches", "education-leaders", "cs-teachers", "university",
             "teacher-certification", "school-staffing", "course-designers", "all"}
RECORD_STATUS = {"verified", "unverified", "unreachable", "gap"}
RECORD_FIELDS = ("id", "family", "kind", "audience", "grade_band", "authority", "title", "edition",
                 "edition_status", "superseded_by", "id_scheme", "labels", "source_url", "access", "license",
                 "permitted_use", "bundle_text", "status", "verified_on", "evidence", "notes")
ORG_FIELDS = ("id", "name", "acronym", "former_names", "audience", "resources", "professional_learning", "url",
              "terms", "priority", "kind", "installable", "membership", "status", "verified_on", "evidence", "notes")

# Which record kinds can evidence an objective written for each learner audience.
FITS = {
    "students": {"student-standard", "state-curriculum", "district-curriculum", "occupational-assessment"},
    "teachers": {"educator-standard", "teacher-standard", "state-certification", "state-staffing"},
    "university": {"university-curriculum"},
}
NOT_LEARNING_STANDARDS = {"design-guideline", "interoperability-spec", "course-review-rubric",
                          "accessibility-standard", "research-synthesis", "local-policy"}
RANK = {"gap": 0, "unverified": 1, "partial": 2, "verified": 3}
ROW_STATUS = set(RANK) | {"not-applicable"}
CREDENTIAL_RELATIONS = {"member", "membership", "certified", "certified-by", "accredited", "accredited-by",
                        "endorsed", "endorsed-by", "licensed", "licensed-by", "partner", "approved-by"}
SOURCE_RELATIONS = {"knowledge-source", "cites", "resource", "community", "standards-source"}


def _load(path: str) -> Any:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _date_ok(v: Any) -> bool:
    if not isinstance(v, str):
        return False
    try:
        datetime.date.fromisoformat(v)
        return True
    except ValueError:
        return False


def _evidence_ok(rel: Any) -> bool:
    return isinstance(rel, str) and not rel.startswith("/") and ".." not in rel.split("/") \
        and os.path.isfile(os.path.join(CF, rel))


# ---------------------------------------------------------------- registries

def check_registry(doc: Any) -> Tuple[List[str], Dict[str, Dict[str, Any]]]:
    errors: List[str] = []
    if not isinstance(doc, dict) or not isinstance(doc.get("records"), list):
        return ["the registry must be an object with a records list"], {}
    recs: Dict[str, Dict[str, Any]] = {}
    for n, r in enumerate(doc["records"]):
        if not isinstance(r, dict):
            errors.append("records[%d] is not an object" % n)
            continue
        rid = r.get("id", "records[%d]" % n)
        missing = [f for f in RECORD_FIELDS if f not in r]
        if missing:
            errors.append("%s is missing %s" % (rid, ", ".join(missing)))
            continue
        if rid in recs:
            errors.append("duplicate record id %s" % rid)
        recs[rid] = r
        if r["kind"] not in KINDS:
            errors.append("%s kind %r is unknown" % (rid, r["kind"]))
        if r["audience"] not in AUDIENCES:
            errors.append("%s audience %r is unknown" % (rid, r["audience"]))
        if r["status"] not in RECORD_STATUS:
            errors.append("%s status %r is unknown" % (rid, r["status"]))
        if r["status"] == "verified" and not (_date_ok(r["verified_on"]) and _evidence_ok(r["evidence"])):
            errors.append("%s is verified without a verified_on date and an existing evidence file" % rid)
        if r["evidence"] is not None and not _evidence_ok(r["evidence"]):
            errors.append("%s evidence %s does not exist under company-fleets" % (rid, r["evidence"]))
        scheme = r["id_scheme"]
        if scheme is not None:
            try:
                if not re.fullmatch(scheme["pattern"], scheme["example"]):
                    errors.append("%s id_scheme example %r does not match its pattern" % (rid, scheme["example"]))
            except (KeyError, TypeError, re.error) as exc:
                errors.append("%s id_scheme is malformed: %s" % (rid, exc))
        if "ids" in r:
            ids = r["ids"]
            if not isinstance(ids, list) or not ids or not all(isinstance(x, str) for x in ids):
                errors.append("%s ids must be a non-empty list of identifier strings" % rid)
            else:
                if scheme is not None:
                    off = [x for x in ids if not re.fullmatch(scheme.get("pattern", ""), x)]
                    if off:
                        errors.append("%s stores ids outside its own scheme: %s" % (rid, ", ".join(off[:5])))
                if not _evidence_ok(r.get("ids_source")):
                    errors.append("%s ids need an ids_source evidence file that exists under company-fleets" % rid)
        if r["edition_status"] == "superseded" and not r["superseded_by"]:
            errors.append("%s is superseded but names no successor" % rid)
        if not isinstance(r["bundle_text"], bool):
            errors.append("%s bundle_text must be true or false" % rid)
    for rid, r in recs.items():
        if r.get("superseded_by") and r["superseded_by"] not in recs:
            errors.append("%s superseded_by %s, which is not a record" % (rid, r["superseded_by"]))
    return errors, recs


def check_orgs(doc: Any) -> Tuple[List[str], Dict[str, Dict[str, Any]]]:
    errors: List[str] = []
    if not isinstance(doc, dict) or not isinstance(doc.get("records"), list):
        return ["the organizations file must be an object with a records list"], {}
    orgs: Dict[str, Dict[str, Any]] = {}
    for n, o in enumerate(doc["records"]):
        if not isinstance(o, dict):
            errors.append("records[%d] is not an object" % n)
            continue
        oid = o.get("id", "records[%d]" % n)
        missing = [f for f in ORG_FIELDS if f not in o]
        if missing:
            errors.append("%s is missing %s" % (oid, ", ".join(missing)))
            continue
        orgs[oid] = o
        if o["kind"] != "knowledge-source":
            errors.append("%s kind must be knowledge-source; organizations are not packages" % oid)
        if o["installable"] is not False:
            errors.append("%s must not be installable" % oid)
        if o["membership"] != "none":
            errors.append("%s records membership %r; no membership is held or inferred" % (oid, o["membership"]))
        if o["status"] == "verified" and not (_date_ok(o["verified_on"]) and _evidence_ok(o["evidence"])):
            errors.append("%s is verified without a verified_on date and an existing evidence file" % oid)
        if o["status"] not in ("verified", "unverified", "unreachable"):
            errors.append("%s status %r is unknown" % (oid, o["status"]))
    return errors, orgs


# ---------------------------------------------------------------- alignment

def _review_evidence_exists(rel: Any, base_dir: str) -> bool:
    if not isinstance(rel, str) or not rel or rel.startswith("/") or ".." in rel.split("/"):
        return False
    return os.path.isfile(os.path.join(base_dir, rel)) or os.path.isfile(os.path.join(CF, rel))


def _row_findings(row: Dict[str, Any], recs: Dict[str, Dict[str, Any]], ctx: Dict[str, Any],
                  base_dir: str = CF) -> Tuple[str, List[Dict[str, str]]]:
    """Return the highest status the evidence supports and the findings (severity error or note)."""
    out: List[Dict[str, str]] = []

    def err(code: str, msg: str) -> None:
        out.append({"severity": "error", "code": code, "message": msg})

    def note(code: str, msg: str) -> None:
        out.append({"severity": "note", "code": code, "message": msg})

    rec = recs.get(row.get("record_id"))
    if rec is None:
        note("source-not-registered", "%r is not in the standards registry; the alignment is a gap, not a match"
             % row.get("record_id"))
        return "gap", out
    best = "verified"
    if rec["status"] in ("gap", "unreachable") or rec["kind"] in ("district-curriculum", "local-policy") and rec["status"] != "verified":
        note("source-unavailable", "%s is %s in the registry; record the limitation and keep the mapping a gap"
             % (rec["id"], rec["status"]))
        best = "gap"
    elif rec["status"] == "unverified":
        note("source-unverified", "%s was not verified on the live source" % rec["id"])
        best = "unverified"
    if rec["kind"] in NOT_LEARNING_STANDARDS:
        err("not-a-learning-standard", "%s is a %s; cite it as a design or policy reference, not as an objective alignment"
            % (rec["id"], rec["kind"]))
    if rec["kind"] == "occupational-assessment":
        if row.get("standard_id") or row.get("standard_text"):
            err("restricted-assessment-content", "%s restricts incorporation of its content; no competency ids or items "
                "may be mapped without permitted alignment information" % rec["id"])
        note("assessment-not-selected", "no NOCTI credential category and identifier is selected; alignment is a gap")
        best = "gap"
    if row.get("standard_text") and not rec["bundle_text"]:
        err("text-bundled", "%s text may not be bundled (%s); link to %s instead"
            % (rec["id"], rec["license"][:80], rec["source_url"]))
    audience = row.get("audience") or ctx.get("learner_audience")
    if audience in FITS and rec["kind"] not in NOT_LEARNING_STANDARDS:
        fits = FITS[audience]
        if rec["kind"] not in fits:
            if audience == "students" and rec["kind"] == "university-curriculum":
                if not row.get("progression_bridge"):
                    err("university-to-school", "%s is a university curriculum; a school objective needs a stated "
                        "progression_bridge before it can map there" % rec["id"])
            elif audience == "students":
                err("teacher-standard-for-students", "%s is a %s for %s; it cannot evidence a student-learning objective"
                    % (rec["id"], rec["kind"], rec["audience"]))
            elif audience == "teachers" and rec["kind"] == "student-standard":
                err("student-standard-for-teachers", "%s is a student standard; teacher-practice objectives map to "
                    "educator or teacher standards" % rec["id"])
            else:
                err("audience-mismatch", "%s (%s) does not fit a %s objective" % (rec["id"], rec["kind"], audience))
    adopted = set(ctx.get("district_adoptions", []))
    peers = {rid for rid, r in recs.items() if r["family"] == rec["family"] and r["kind"] == rec["kind"]
             and r["audience"] == rec["audience"]}
    adopted_peer = sorted((adopted & peers) - {rec["id"]})
    if adopted_peer and rec["id"] not in adopted:
        err("not-district-adoption", "the district adopted %s; mapping to %s ignores the actual adoption"
            % (", ".join(adopted_peer), rec["id"]))
    elif rec["edition_status"] == "superseded" and rec["id"] not in adopted:
        err("superseded-edition", "%s is superseded by %s and no district adoption of it is recorded"
            % (rec["id"], rec["superseded_by"]))
    elif rec["edition_status"] == "superseded":
        note("adopted-older-edition", "%s is superseded but the district adopted it; kept" % rec["id"])
    if row.get("edition") and str(row["edition"]) not in str(rec["edition"]):
        err("edition-mismatch", "row says edition %r but %s is edition %r" % (row["edition"], rec["id"], rec["edition"]))
    sid = row.get("standard_id")
    scheme = rec["id_scheme"]
    if sid:
        if scheme and not re.fullmatch(scheme["pattern"], str(sid)):
            err("id-not-in-scheme", "%r is not an identifier in %s's scheme (example %s); check the edition and "
                "the student/teacher document" % (sid, rec["id"], scheme["example"]))
        elif isinstance(rec.get("ids"), list):
            if str(sid) not in rec["ids"]:
                err("id-not-published", "%r fits %s's format but is not one of its %d published identifiers "
                    "(list from %s); do not invent ids" % (sid, rec["id"], len(rec["ids"]), rec.get("ids_source")))
        elif best == "verified":
            note("id-list-not-stored" if scheme else "id-unverifiable",
                 "%s has no stored list of published identifiers, so %r can't be confirmed to exist; it stays unverified"
                 % (rec["id"], sid))
            best = "unverified"
    elif best == "verified":
        note("no-identifier", "no standard_id given; a concept-level mapping is partial at best")
        best = "partial"
    reviewer = str(row.get("reviewer", ""))
    if best in ("verified", "partial"):
        ev = row.get("evidence")
        if not (reviewer.startswith("human:") and ev):
            note("no-human-review", "%s needs a human reviewer and a supporting evidence reference" % best)
            best = "unverified"
        elif not _review_evidence_exists(ev, base_dir):
            note("review-evidence-missing", "review evidence %r does not exist next to the alignment file or under "
                 "company-fleets; a reviewer name alone does not verify a mapping" % ev)
            best = "unverified"
    if any(f["severity"] == "error" for f in out):
        best = "gap"
    return best, out


def check_alignment(doc: Any, recs: Dict[str, Dict[str, Any]], base_dir: str = CF) -> Tuple[int, Dict[str, Any]]:
    if not isinstance(doc, dict) or not isinstance(doc.get("alignments"), list) or not doc["alignments"]:
        return 1, {"ok": False, "status": "invalid", "errors": ["the file needs a non-empty alignments list"]}
    ctx = doc.get("context", {}) if isinstance(doc.get("context"), dict) else {}
    invalid, rows = [], []
    for n, row in enumerate(doc["alignments"]):
        if not isinstance(row, dict):
            invalid.append("alignments[%d] is not an object" % n)
            continue
        for f in ("objective_id", "criterion_id", "record_id", "status"):
            if not row.get(f):
                invalid.append("alignments[%d] is missing %s" % (n, f))
        if row.get("status") and row["status"] not in ROW_STATUS:
            invalid.append("alignments[%d] status %r is not one of %s" % (n, row["status"], ", ".join(sorted(ROW_STATUS))))
    if invalid:
        return 1, {"ok": False, "status": "invalid", "errors": invalid}
    for row in doc["alignments"]:
        claimed = row["status"]
        if claimed == "not-applicable":
            findings = [] if row.get("reason") else [{"severity": "error", "code": "no-reason",
                                                      "message": "not-applicable needs a reason"}]
            rows.append({"objective_id": row["objective_id"], "criterion_id": row["criterion_id"],
                         "record_id": row["record_id"], "claimed": claimed, "supported": "not-applicable",
                         "findings": findings})
            continue
        supported, findings = _row_findings(row, recs, ctx, base_dir)
        if RANK[claimed] > RANK[supported]:
            findings.append({"severity": "error", "code": "overclaimed",
                             "message": "claims %s but the evidence supports %s" % (claimed, supported)})
        rows.append({"objective_id": row["objective_id"], "criterion_id": row["criterion_id"],
                     "record_id": row["record_id"], "standard_id": row.get("standard_id"), "claimed": claimed,
                     "supported": supported, "findings": findings})
    errors = sum(1 for r in rows for f in r["findings"] if f["severity"] == "error")
    by_obj: Dict[str, str] = {}
    for r in rows:
        if r["supported"] in RANK:
            prev = by_obj.get(r["objective_id"])
            by_obj[r["objective_id"]] = r["supported"] if prev is None or RANK[r["supported"]] > RANK[prev] else prev
    counts = {s: sum(1 for r in rows if r["supported"] == s) for s in list(RANK) + ["not-applicable"]}
    coverage = "verified" if by_obj and all(v == "verified" for v in by_obj.values()) else \
        ("gap" if all(v == "gap" for v in by_obj.values()) else "partial")
    return (1 if errors else 0), {"ok": errors == 0, "errors": errors, "coverage": coverage,
                                  "supported_counts": counts, "objectives": by_obj, "rows": rows,
                                  "label": doc.get("label", "")}


def check_coverage(doc: Any, recs: Dict[str, Dict[str, Any]], record: str, field: str) -> Tuple[int, Dict[str, Any]]:
    rec = recs.get(record)
    if rec is None or not rec["labels"]:
        return 1, {"ok": False, "status": "invalid", "errors": ["%s has no labels in the registry" % record]}
    items = doc.get("courses") or doc.get("items") if isinstance(doc, dict) else None
    if not isinstance(items, list) or not items:
        return 1, {"ok": False, "status": "invalid", "errors": ["the file needs a non-empty courses or items list"]}
    labels = list(rec["labels"])
    seen: Dict[str, List[str]] = {l: [] for l in labels}
    unknown = []
    for it in items:
        for lab in it.get(field, []) if isinstance(it, dict) else []:
            if lab in seen:
                seen[lab].append(it.get("id", "?"))
            else:
                unknown.append({"item": it.get("id", "?"), "label": lab})
    missing = [l for l in labels if not seen[l]]
    result = {"ok": not missing and not unknown, "record": record, "covered": {l: v for l, v in seen.items() if v},
              "missing": missing, "unknown_labels": unknown, "label": doc.get("label", "")}
    covered = [l for l in labels if seen[l]]
    if record.startswith("nbea") and covered and set(covered) <= {"Information Technology"}:
        result["finding"] = "a computing-only curriculum does not satisfy the ten NBEA content areas"
    return (0 if result["ok"] else 1), result


def check_org_refs(doc: Any, orgs: Dict[str, Dict[str, Any]]) -> Tuple[int, Dict[str, Any]]:
    refs = doc.get("references") if isinstance(doc, dict) else None
    if not isinstance(refs, list) or not refs:
        return 1, {"ok": False, "status": "invalid", "errors": ["the file needs a non-empty references list"]}
    names: Dict[str, str] = {}
    former: Dict[str, str] = {}
    for oid, o in orgs.items():
        for n in (o["name"], o["acronym"]):
            if n:
                names[n.lower()] = oid
        for n in o["former_names"]:
            former[n.lower()] = oid
    results, errors = [], 0
    for ref in refs:
        name = str(ref.get("name", "")).strip()
        relation = str(ref.get("relation", "")).strip().lower()
        findings = []
        oid = names.get(name.lower())
        if oid is None and name.lower() in former:
            oid = former[name.lower()]
            findings.append({"severity": "error", "code": "former-name",
                             "message": "%s is a former name; the current name is %s" % (name, orgs[oid]["name"])})
        if oid is None:
            findings.append({"severity": "error", "code": "unknown-organization",
                             "message": "%s is not in the verified organizations registry" % name})
        elif orgs[oid]["status"] != "verified":
            findings.append({"severity": "note", "code": "unverified-organization",
                             "message": "%s was %s on the live source" % (orgs[oid]["name"], orgs[oid]["status"])})
        if relation in CREDENTIAL_RELATIONS:
            findings.append({"severity": "error", "code": "credential-claim",
                             "message": "relation %r claims a membership, credential or permission; organizations here "
                                        "are knowledge sources only" % relation})
        elif relation not in SOURCE_RELATIONS:
            findings.append({"severity": "error", "code": "unknown-relation",
                             "message": "relation %r is not one of %s" % (relation, ", ".join(sorted(SOURCE_RELATIONS)))})
        errors += sum(1 for f in findings if f["severity"] == "error")
        results.append({"name": name, "organization": oid, "relation": relation, "findings": findings})
    return (1 if errors else 0), {"ok": errors == 0, "errors": errors, "references": results}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="standards_check")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("registry")
    r.add_argument("--registry", default=DEFAULT_REGISTRY)
    o = sub.add_parser("orgs")
    o.add_argument("--orgs", default=DEFAULT_ORGS)
    a = sub.add_parser("align")
    a.add_argument("file")
    a.add_argument("--registry", default=DEFAULT_REGISTRY)
    c = sub.add_parser("coverage")
    c.add_argument("file")
    c.add_argument("--record", required=True)
    c.add_argument("--field", required=True)
    c.add_argument("--registry", default=DEFAULT_REGISTRY)
    g = sub.add_parser("org-refs")
    g.add_argument("file")
    g.add_argument("--orgs", default=DEFAULT_ORGS)
    try:
        args = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0

    def emit(code: int, obj: Dict[str, Any]) -> int:
        print(json.dumps(obj, indent=2, ensure_ascii=False))
        return code

    try:
        if args.cmd in ("orgs", "org-refs"):
            org_errors, orgs = check_orgs(_load(args.orgs))
            if args.cmd == "orgs":
                counts = {s: sum(1 for x in orgs.values() if x["status"] == s) for s in ("verified", "unverified", "unreachable")}
                return emit(1 if org_errors else 0, {"ok": not org_errors, "errors": org_errors, "counts": counts})
            if org_errors:
                return emit(1, {"ok": False, "status": "invalid-registry", "errors": org_errors})
            return emit(*check_org_refs(_load(args.file), orgs))
        reg_errors, recs = check_registry(_load(args.registry))
        if args.cmd == "registry":
            counts = {s: sum(1 for x in recs.values() if x["status"] == s) for s in sorted(RECORD_STATUS)}
            return emit(1 if reg_errors else 0, {"ok": not reg_errors, "errors": reg_errors, "records": len(recs),
                                                 "counts": counts})
        if reg_errors:
            return emit(1, {"ok": False, "status": "invalid-registry", "errors": reg_errors})
        doc = _load(args.file)
        if args.cmd == "align":
            return emit(*check_alignment(doc, recs, os.path.dirname(os.path.abspath(args.file))))
        return emit(*check_coverage(doc, recs, args.record, args.field))
    except (OSError, ValueError) as exc:
        return emit(1, {"ok": False, "status": "invalid", "errors": [str(exc)]})


if __name__ == "__main__":
    sys.exit(main())
