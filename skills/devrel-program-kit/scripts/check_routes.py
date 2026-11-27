#!/usr/bin/env python3
"""Check that every skill samber's developer-relations-kickoff can route to is installed.

scan:   collect every `samber/<collection>@<skill>` reference in the given skill directories and
        classify each one: installed, drift (named in this collection but absent from its tree), or a
        sibling collection that isn't installed.
routes: check one kickoff short-list ({"routes": [{"skill": ..., "order": n}]}) and attach the
        fallback from references/fallbacks.json to each route that doesn't resolve.

Usage: check_routes.py --skills-root DIR scan SKILL_DIR [SKILL_DIR ...]
       check_routes.py --skills-root DIR routes ROUTES.json
Exit 0: everything resolves. Exit 1: unresolved routes listed. Exit 2: invalid input.
"""
import argparse
import json
import os
import re
import sys

VERSION = "1.0.0"
REF = re.compile(r"samber/([a-z0-9-]+)@([a-z0-9-]+)")
NAME = re.compile(r"^(?:samber/([a-z0-9-]+)@)?([a-z0-9-]+)$")
HERE = os.path.dirname(os.path.abspath(__file__))
FALLBACKS = os.path.join(HERE, "..", "references", "fallbacks.json")


class InputError(Exception):
    pass


def load_fallbacks():
    with open(FALLBACKS, encoding="utf-8") as fh:
        return json.load(fh)


def installed(skills_root, skill):
    return os.path.isfile(os.path.join(skills_root, skill, "SKILL.md"))


def classify(ref, skills_root, fb):
    """ref is 'samber/<collection>@<skill>' or a bare skill name."""
    m = NAME.match(ref)
    if not m:
        raise InputError("%r is not a skill name or samber/<collection>@<skill>" % ref)
    collection, skill = m.group(1), m.group(2)
    if installed(skills_root, skill):
        return {"ref": ref, "status": "installed", "skill": skill}
    own = collection in (None, fb["collection"].split("/", 1)[1])
    entry = fb["fallbacks"].get(ref, fb["default"])
    return {"ref": ref, "status": "drift" if own else "sibling-not-installed", "skill": skill,
            "fallback": [s for s in entry["use"] if installed(skills_root, s)],
            "coverage": entry["coverage"], "why": entry["why"]}


def scan(dirs, skills_root, fb):
    refs = set()
    for d in dirs:
        if not os.path.isdir(d):
            raise InputError("%s is not a directory" % d)
        for dirpath, _, files in os.walk(d):
            for f in files:
                if f.endswith(".md"):
                    with open(os.path.join(dirpath, f), encoding="utf-8", errors="replace") as fh:
                        refs.update("samber/%s@%s" % m for m in REF.findall(fh.read()))
    return [classify(r, skills_root, fb) for r in sorted(refs)]


def routes(path, skills_root, fb):
    try:
        with open(path, encoding="utf-8") as fh:
            doc = json.load(fh)
    except (OSError, ValueError) as exc:
        raise InputError("%s: %s" % (path, exc))
    items = doc.get("routes") if isinstance(doc, dict) else None
    if not isinstance(items, list) or not items:
        raise InputError("routes file needs a non-empty 'routes' list")
    out = []
    for i, r in enumerate(items):
        if not isinstance(r, dict) or not isinstance(r.get("skill"), str):
            raise InputError("routes[%d] needs a 'skill' string" % i)
        out.append(dict(classify(r["skill"], skills_root, fb), order=r.get("order", i + 1)))
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(description="Check that kickoff routes resolve to installed skills.")
    ap.add_argument("--skills-root", default=os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")))
    sub = ap.add_subparsers(dest="cmd", required=True)
    sc = sub.add_parser("scan")
    sc.add_argument("dirs", nargs="+")
    rt = sub.add_parser("routes")
    rt.add_argument("file")
    args = ap.parse_args(argv)
    try:
        if not os.path.isdir(args.skills_root):
            raise InputError("skills root %s is not a directory" % args.skills_root)
        fb = load_fallbacks()
        results = scan(args.dirs, args.skills_root, fb) if args.cmd == "scan" else routes(args.file, args.skills_root, fb)
    except InputError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 2
    bad = [r for r in results if r["status"] != "installed"]
    counts = {}
    for r in results:
        counts[r["status"]] = counts.get(r["status"], 0) + 1
    print(json.dumps({"tool": "devrel-program-kit/check_routes", "version": VERSION, "ok": not bad,
                      "counts": counts, "unresolved": bad,
                      "installed": [r["ref"] for r in results if r["status"] == "installed"]}, indent=2))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
