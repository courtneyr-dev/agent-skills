#!/usr/bin/env python3
"""progression: check a prerequisite map and course sequence.

  check <graph.json>

Errors: unknown or duplicate concepts, prerequisite cycles, a concept sequenced before its
prerequisite, a concept placed below its grade band (a university concept in a K-12 unit) without a
bridge justification, and concepts that are neither sequenced nor marked prior. Warnings: concepts
no task assesses. Prints JSON with a valid prerequisite order when the graph is acyclic.

Exit 0 no errors (warnings allowed), 1 errors, 2 usage error or invalid input. Python 3.9+ stdlib only.
"""
from __future__ import annotations

import json
import re
import sys
from typing import Any, Dict, List, Optional, Tuple

BAND = re.compile(r"^(PK|K|[1-9]|1[0-2])(?:-([1-9]|1[0-2]))?$")


class Invalid(Exception):
    pass


def band_min(band: str) -> int:
    """Lowest grade a band covers: PK=-1, K=0, 1..12, university=13."""
    if band == "university":
        return 13
    m = BAND.match(band or "")
    if not m:
        raise Invalid("unknown band %r (use PK-2, 3-5, 6-8, 9-10, 11-12, 9-12 or university)" % band)
    first = m.group(1)
    return {"PK": -1, "K": 0}[first] if first in ("PK", "K") else int(first)


def unit_grade(value: Any) -> int:
    if value == "university":
        return 13
    if isinstance(value, int) and -1 <= value <= 13:
        return value
    raise Invalid("unit grade must be an integer -1..12 or 'university' (got %r)" % (value,))


def _parse(doc: Any) -> Tuple[Dict[str, Dict[str, Any]], List[Dict[str, Any]], List[str]]:
    if not isinstance(doc, dict) or not isinstance(doc.get("concepts"), list) or not isinstance(doc.get("sequence"), list):
        raise Invalid("graph needs a 'concepts' list and a 'sequence' list")
    concepts: Dict[str, Dict[str, Any]] = {}
    errors: List[str] = []
    for c in doc["concepts"]:
        if not isinstance(c, dict) or not isinstance(c.get("id"), str) or not c["id"]:
            raise Invalid("every concept needs a string id")
        if c["id"] in concepts:
            errors.append("duplicate concept %s" % c["id"])
            continue
        band_min(c.get("band", ""))
        if not isinstance(c.get("prereqs", []), list):
            raise Invalid("concept %s prereqs must be a list" % c["id"])
        concepts[c["id"]] = c
    for u in doc["sequence"]:
        if not isinstance(u, dict) or not isinstance(u.get("concepts"), list):
            raise Invalid("every sequence unit needs a concepts list")
        unit_grade(u.get("grade"))
    return concepts, doc["sequence"], errors


def _order(concepts: Dict[str, Dict[str, Any]]) -> Tuple[List[str], List[str]]:
    """Kahn's algorithm in declaration order. Returns (order, nodes left in or behind a cycle)."""
    indeg = {cid: 0 for cid in concepts}
    users: Dict[str, List[str]] = {cid: [] for cid in concepts}
    for cid, c in concepts.items():
        for p in c.get("prereqs", []):
            if p in concepts:
                indeg[cid] += 1
                users[p].append(cid)
    ready = [cid for cid in concepts if indeg[cid] == 0]
    order: List[str] = []
    while ready:
        cid = ready.pop(0)
        order.append(cid)
        for u in users[cid]:
            indeg[u] -= 1
            if indeg[u] == 0:
                ready.append(u)
    return order, [cid for cid in concepts if cid not in order]


def check(doc: Any) -> Dict[str, Any]:
    concepts, sequence, errors = _parse(doc)
    warnings: List[str] = []
    for cid, c in concepts.items():
        for p in c.get("prereqs", []):
            if p not in concepts:
                errors.append("%s names unknown prerequisite %s" % (cid, p))
    order, stuck = _order(concepts)
    if stuck:
        errors.append("prerequisite cycle among: %s" % ", ".join(stuck))

    position: Dict[str, Tuple[int, int, int]] = {}
    for ui, unit in enumerate(sequence):
        grade = unit_grade(unit.get("grade"))
        for pi, cid in enumerate(unit["concepts"]):
            if cid not in concepts:
                errors.append("unit %s places unknown concept %s" % (unit.get("unit"), cid))
                continue
            if cid in position:
                errors.append("concept %s is placed twice" % cid)
                continue
            position[cid] = (ui, pi, grade)
            c = concepts[cid]
            if band_min(c["band"]) > grade and not str(c.get("bridge") or "").strip():
                errors.append("%s (band %s) sits in unit %s at grade %s without a bridge justification"
                              % (cid, c["band"], unit.get("unit"), unit.get("grade")))
    for cid, c in concepts.items():
        if c.get("prior"):
            continue
        if cid not in position:
            errors.append("concept %s is neither sequenced nor marked prior" % cid)
            continue
        for p in c.get("prereqs", []):
            if p in concepts and not concepts[p].get("prior") and p in position and position[p][:2] >= position[cid][:2]:
                errors.append("%s comes before its prerequisite %s in the sequence" % (cid, p))
    unassessed = [cid for cid, c in concepts.items() if not c.get("prior") and not c.get("assessed_by")]
    warnings += ["concept %s is not assessed by any task" % cid for cid in unassessed]
    return {"ok": not errors, "errors": errors, "warnings": warnings, "unassessed": unassessed,
            "order": order if not stuck else None,
            "note": "A valid order shows the map is coherent, not that learners will learn in it. Teacher and faculty review decide use."}


def main(argv: Optional[List[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if len(argv) != 2 or argv[0] != "check":
        print(json.dumps({"error": "usage: progression.py check <graph.json>"}))
        return 2
    try:
        with open(argv[1], encoding="utf-8") as fh:
            doc = json.load(fh)
        result = check(doc)
    except (OSError, ValueError, Invalid) as exc:
        print(json.dumps({"error": "invalid input", "detail": str(exc)}))
        return 2
    print(json.dumps(result, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
