#!/usr/bin/env python3
"""agreement: rubric-calibration agreement between reviewers, computed only from real human ratings.

  stats RATINGS.json

Input: {"label": "...", "synthetic": false, "rubric_id": "...", "scale": [0, 1, 2, 3],
        "anchors": {"A1": 2}, "ratings": [{"item": "A1", "rater": "human:r1", "score": 2, "source": "human-rated"}]}

Agreement statistics (exact and adjacent agreement, Cohen's kappa, quadratic-weighted kappa) are
computed per rater pair only when every rating is source "human-rated" by a "human:<id>" rater and the
file isn't labeled synthetic. Anything else is practice: the output lists the items to discuss and
claims no agreement, because generated calibration examples prepare reviewers but say nothing about
how real reviewers agree.

Python 3.9+ standard library only. Prints JSON. Exit 0 computed, 1 practice-only, 2 invalid input or usage.
"""
from __future__ import annotations

import argparse
import itertools
import json
import sys
from typing import Any, Dict, List, Optional, Tuple

PRACTICE = "practice-only: no inter-rater agreement claimed"


class InputError(ValueError):
    pass


def validate(doc: Any) -> None:
    if not isinstance(doc, dict):
        raise InputError("the ratings file must be a JSON object")
    scale = doc.get("scale")
    if (not isinstance(scale, list) or len(scale) < 2
            or not all(isinstance(v, (int, str)) and not isinstance(v, bool) for v in scale)
            or len(set(scale)) != len(scale)):
        raise InputError("scale must list at least two distinct integer or text levels, lowest first")
    ratings = doc.get("ratings")
    if not isinstance(ratings, list) or not ratings:
        raise InputError("ratings must be a non-empty list")
    seen = set()
    for n, r in enumerate(ratings):
        if not isinstance(r, dict):
            raise InputError("rating %d must be an object" % n)
        for key in ("item", "rater", "source"):
            if not isinstance(r.get(key), str) or not r[key].strip():
                raise InputError("rating %d needs text %s" % (n, key))
        if isinstance(r.get("score"), (bool, float)) or r.get("score") not in scale:
            raise InputError("rating %d score %r is not on the scale %r" % (n, r.get("score"), scale))
        if (r["item"], r["rater"]) in seen:
            raise InputError("rater %s rated item %s twice" % (r["rater"], r["item"]))
        seen.add((r["item"], r["rater"]))
    if len({r["rater"] for r in ratings}) < 2:
        raise InputError("agreement needs at least two raters")
    anchors = doc.get("anchors", {})
    if not isinstance(anchors, dict) or any(isinstance(v, (bool, float)) or v not in scale for v in anchors.values()):
        raise InputError("anchors must map item ids to scale levels")


def practice_reasons(doc: Dict[str, Any]) -> List[str]:
    reasons = []
    if doc.get("synthetic") is True or "SYNTHETIC" in str(doc.get("label", "")).upper():
        reasons.append("the file is labeled synthetic")
    sources = sorted({r["source"] for r in doc["ratings"] if r["source"] != "human-rated"})
    if sources:
        reasons.append("ratings with source %s are not human ratings" % ", ".join(sources))
    raters = sorted({r["rater"] for r in doc["ratings"] if not r["rater"].startswith("human:")})
    if raters:
        reasons.append("raters %s are not human:<id> principals" % ", ".join(raters))
    return reasons


def kappas(a: List[int], b: List[int], k: int) -> Tuple[Optional[float], Optional[float]]:
    """Cohen's kappa and quadratic-weighted kappa for paired level indices 0..k-1."""
    n = len(a)
    obs = [[0.0] * k for _ in range(k)]
    for x, y in zip(a, b):
        obs[x][y] += 1
    row = [sum(obs[i]) / n for i in range(k)]
    col = [sum(obs[i][j] for i in range(k)) / n for j in range(k)]
    po = sum(obs[i][i] for i in range(k)) / n
    pe = sum(row[i] * col[i] for i in range(k))
    kappa = None if pe >= 1 else (po - pe) / (1 - pe)
    w = [[1 - ((i - j) ** 2) / ((k - 1) ** 2) for j in range(k)] for i in range(k)]
    pow_ = sum(w[i][j] * obs[i][j] for i in range(k) for j in range(k)) / n
    pew = sum(w[i][j] * row[i] * col[j] for i in range(k) for j in range(k))
    wkappa = None if pew >= 1 else (pow_ - pew) / (1 - pew)
    return kappa, wkappa


def _r(x: Optional[float]) -> Optional[float]:
    return None if x is None else round(x, 4)


def discussion(doc: Dict[str, Any]) -> List[Dict[str, Any]]:
    anchors = doc.get("anchors", {})
    by_item: Dict[str, Dict[str, Any]] = {}
    for r in doc["ratings"]:
        by_item.setdefault(r["item"], {})[r["rater"]] = r["score"]
    out = []
    for item in sorted(by_item):
        scores = by_item[item]
        levels = [doc["scale"].index(s) for s in scores.values()]
        anchor = anchors.get(item)
        off_anchor = anchor is not None and any(s != anchor for s in scores.values())
        if max(levels) != min(levels) or off_anchor:
            out.append({"item": item, "scores": scores, "anchor": anchor, "spread_levels": max(levels) - min(levels)})
    return out


def stats(doc: Dict[str, Any]) -> Dict[str, Any]:
    validate(doc)
    reasons = practice_reasons(doc)
    result: Dict[str, Any] = {"rubric_id": doc.get("rubric_id"), "discussion": discussion(doc)}
    if reasons:
        result.update({"status": "practice-only", "message": PRACTICE, "reasons": reasons})
        return result
    k = len(doc["scale"])
    scores: Dict[str, Dict[str, int]] = {}
    for r in doc["ratings"]:
        scores.setdefault(r["rater"], {})[r["item"]] = doc["scale"].index(r["score"])
    pairs = []
    for ra, rb in itertools.combinations(sorted(scores), 2):
        shared = sorted(set(scores[ra]) & set(scores[rb]))
        if len(shared) < 2:
            pairs.append({"raters": [ra, rb], "n_items": len(shared), "notes": ["fewer than 2 shared items; not computed"]})
            continue
        a = [scores[ra][i] for i in shared]
        b = [scores[rb][i] for i in shared]
        kappa, wkappa = kappas(a, b, k)
        notes = []
        if kappa is None:
            notes.append("kappa undefined: both raters used one level for every item")
        if len(shared) < 10:
            notes.append("fewer than 10 shared items: a calibration signal, not a reliability estimate")
        pairs.append({
            "raters": [ra, rb], "n_items": len(shared),
            "exact_agreement": _r(sum(x == y for x, y in zip(a, b)) / len(a)),
            "adjacent_agreement": _r(sum(abs(x - y) <= 1 for x, y in zip(a, b)) / len(a)),
            "kappa": _r(kappa), "weighted_kappa_quadratic": _r(wkappa), "notes": notes,
        })
    if not any("exact_agreement" in p for p in pairs):
        raise InputError("no rater pair shares two or more items")
    result.update({"status": "computed", "pairs": pairs})
    return result


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="agreement")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("stats", help="agreement statistics from real reviewer ratings")
    s.add_argument("ratings")
    try:
        args = ap.parse_args(argv)
    except SystemExit as exc:
        return 2 if exc.code else 0
    try:
        with open(args.ratings, encoding="utf-8") as fh:
            result = stats(json.load(fh))
    except (OSError, ValueError) as exc:
        sys.stdout.write(json.dumps({"status": "invalid-input", "error": str(exc)}, indent=2) + "\n")
        return 2
    sys.stdout.write(json.dumps(result, indent=2, sort_keys=True) + "\n")
    return 0 if result["status"] == "computed" else 1


if __name__ == "__main__":
    sys.exit(main())
