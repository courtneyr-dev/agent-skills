#!/usr/bin/env python3
"""Check a community operating kit (one Markdown file) for the eight sections and their load-bearing parts.

Sections (## headings): Charter, Onboarding path, Governance map, Moderation and escalation, Event
playbook, Contributor journey, Measurement plan, Improvement loop. Each must name the parts listed in
SECTIONS. The governance map is a table whose every decision has a human owner, a record location and
a review or appeal route, and which covers funding and sponsorship. The measurement plan links a JSON
plan; when community-health-measures sits beside this skill, the plan is linted too. Anywhere in the
kit, ranking volunteers or turning members into sales leads is refused.

Usage: kit_check.py KIT.md
Exit 0: complete. Exit 1: gaps listed. Exit 2: invalid input.
"""
import argparse
import importlib.util
import json
import os
import re
import sys

VERSION = "1.0.0"
SECTIONS = {
    "charter": ["purpose", "membership model", "non-goals"],
    "onboarding path": ["purpose", "onboarding", "first meaningful participation", "ongoing contribution", "leadership development"],
    "governance map": ["funding", "sponsor"],
    "moderation and escalation": ["conflict of interest", "appeal", "decision maker", "evidence", "confidential"],
    "event playbook": ["accessibility", "volunteer", "contingency", "post-event", "code of conduct"],
    "contributor journey": ["good first", "environment setup", "review", "recognition", "succession", "maintainer"],
    "measurement plan": ["consent", "aggregate"],
    "improvement loop": ["evidence", "review", "contribution path", "onboarding", "follow-up"],
}
GOV_COLUMNS = ["decision", "owner", "record", "review"]
FORBIDDEN = re.compile(r"\b(leaderboards?|top \d+ (contributors|members|volunteers)|rank(ing|ed)? (volunteers|contributors|members)"
                       r"|sales leads?|lead (generation|scoring|capture)|prospects? list)\b", re.I)
NEGATED = re.compile(r"\b(no|never|not|nothing|none|isn't|aren't|don't|doesn't|won't|avoid|without)\b[^.\n]{0,40}$", re.I)
MEASURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "community-health-measures", "scripts", "measures.py")


class InputError(Exception):
    pass


def split_sections(text):
    out, current = {}, None
    for line in text.splitlines():
        m = re.match(r"^##\s+(.+?)\s*$", line)
        if m:
            current = m.group(1).strip().lower()
            out[current] = []
        elif current is not None:
            out[current].append(line)
    return {k: "\n".join(v) for k, v in out.items()}


def table_rows(body):
    rows = [[c.strip() for c in line.strip().strip("|").split("|")] for line in body.splitlines() if line.strip().startswith("|")]
    rows = [r for r in rows if not all(re.fullmatch(r":?-{3,}:?", c) for c in r)]
    return rows[0] if rows else [], rows[1:]


def lint_plan(path):
    if not os.path.isfile(MEASURES):
        return None, "community-health-measures isn't installed beside this skill, so the plan wasn't linted"
    spec = importlib.util.spec_from_file_location("measures", MEASURES)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    try:
        return mod.lint(mod.load(path, "plan")), None
    except mod.InputError as exc:
        return [{"metric": "-", "rule": "invalid-plan", "message": str(exc)}], None


def check(text, kit_dir):
    """Return (violations, notes). Violations are {rule, section, message}."""
    out, notes = [], []

    def v(rule, section, message):
        out.append({"rule": rule, "section": section, "message": message})

    sections = split_sections(text)
    for name, parts in SECTIONS.items():
        if name not in sections:
            v("missing-section", name, "add a '## %s' section" % name.capitalize())
            continue
        body = sections[name].lower()
        for p in parts:
            if p not in body:
                v("missing-part", name, "name the %r part" % p)

    if "governance map" in sections:
        header, rows = table_rows(sections["governance map"])
        cols = [h.lower() for h in header]
        idx = {c: next((i for i, h in enumerate(cols) if h.startswith(c)), None) for c in GOV_COLUMNS}
        if None in idx.values() or not rows:
            v("governance-table", "governance map", "use a table with columns Decision | Owner | Record | Review or appeal")
        else:
            for r in rows:
                cell = lambda c: r[idx[c]] if idx[c] < len(r) else ""  # noqa: E731
                if not re.fullmatch(r"`?human:[a-z0-9-]+`?", cell("owner")):
                    v("non-human-owner", "governance map", "%r: decision owners are named humans, got %r" % (cell("decision"), cell("owner")))
                for c in ("record", "review"):
                    if len(cell(c)) < 3:
                        v("governance-table", "governance map", "%r has no %s" % (cell("decision"), c))

    if "measurement plan" in sections:
        links = re.findall(r"\(([^)\s]+\.json)\)|`([^`\s]+\.json)`", sections["measurement plan"])
        paths = [a or b for a, b in links]
        if not paths:
            v("no-plan", "measurement plan", "link the measurement plan JSON")
        for p in paths:
            full = os.path.normpath(os.path.join(kit_dir, p))
            if not os.path.isfile(full):
                v("no-plan", "measurement plan", "%s doesn't exist" % p)
                continue
            violations, note = lint_plan(full)
            if note:
                notes.append(note)
            for x in violations or []:
                v("plan-" + x["rule"], "measurement plan", "%s: %s" % (x["metric"], x["message"]))

    for n, line in enumerate(text.splitlines(), 1):
        m = FORBIDDEN.search(line)
        if m and not NEGATED.search(line[:m.start()]):
            v("ranking-or-sales", "line %d" % n, "%r ranks volunteers or turns members into sales leads" % m.group(0))
    return out, notes


def main(argv=None):
    ap = argparse.ArgumentParser(description="Check a community operating kit.")
    ap.add_argument("kit")
    args = ap.parse_args(argv)
    try:
        with open(args.kit, encoding="utf-8") as fh:
            text = fh.read()
    except OSError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}))
        return 2
    if not re.search(r"^##\s", text, re.M):
        print(json.dumps({"ok": False, "error": "no '## ' sections found; is this a kit file?"}))
        return 2
    violations, notes = check(text, os.path.dirname(os.path.abspath(args.kit)))
    print(json.dumps({"tool": "community-operating-kit", "version": VERSION, "ok": not violations,
                      "violations": violations, "notes": notes}, indent=2))
    return 0 if not violations else 1


if __name__ == "__main__":
    sys.exit(main())
