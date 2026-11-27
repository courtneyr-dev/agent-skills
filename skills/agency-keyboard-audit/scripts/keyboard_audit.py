#!/usr/bin/env python3
"""Keyboard-path audit: judge a real Tab walk of one page against WCAG 2.2 keyboard criteria.

  keyboard_audit.py --page PAGE.html [--node-modules DIR] [--max-tabs N] [--save-walk FILE]
  keyboard_audit.py --page PAGE.html --walk-json RECORDING.json

The browser walk is keyboard_walk.cjs (Playwright + axe-core, found through --node-modules or
AGENCY_A11Y_NODE_MODULES). --walk-json judges a saved recording without a browser.
Exit 0 = no blocking findings, 1 = blocking findings, 2 = invalid input, 3 = blocked (no browser adapter).
"""
import argparse
import json
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
WALKER = os.path.join(HERE, "keyboard_walk.cjs")
ENV_MODULES = "AGENCY_A11Y_NODE_MODULES"

LIMITS = [
    "One page, one starting point, forward Tab only; flows behind clicks, dialogs and Shift+Tab need their own runs or a human tester.",
    "Click listeners are read per element through the Chrome DevTools Protocol; a listener delegated to document or body is not attributed to the control.",
    "Focus visibility compares computed outline, box-shadow, border, background, color and text decoration; it does not measure contrast or size against WCAG 2.4.11 or 2.4.13.",
    "Headless Chromium only; other browsers and assistive technologies can behave differently, and nothing here replaces testing with disabled users.",
    "It reports defects; it never certifies WCAG conformance.",
]
MANUAL_STEPS = [
    "Load the page and put focus in the address bar, then press Tab repeatedly to the end of the page.",
    "At every stop, note the element and whether you can see where focus is.",
    "Confirm every control you can click is reached by Tab and works with Enter or Space.",
    "If Tab stops advancing or cycles inside one widget, try Escape; record a trap if focus can't leave.",
    "Record each defect with the WCAG criterion, the steps, the expected and the observed result.",
]
RECORDING_KEYS = ("axe_violations", "interactive", "positive_tabindex", "tab_sequence", "reached_end", "escape_releases")


class InputError(Exception):
    pass


def _finding(rule, sc, selector, name, steps, expected, observed, axe_targets, blocking=True):
    return {"rule": rule, "wcag": sc, "blocking": blocking, "selector": selector, "name": name,
            "steps": steps, "expected": expected, "observed": observed,
            "flagged_by_automated_scan": selector in axe_targets}


def judge(rec, page):
    """Pure: a walker recording in, the findings and summary out."""
    axe_targets = {t for v in rec["axe_violations"] for t in v["targets"]}
    seq = rec["tab_sequence"]
    reached = {s["selector"] for s in seq}
    findings = []

    seen = set()
    for s in seq:
        if s["selector"] in seen or s["baseline_style"] is None:
            continue
        seen.add(s["selector"])
        if s["focused_style"] == s["baseline_style"]:
            findings.append(_finding(
                "focus-not-visible", "2.4.7", s["selector"], s["name"],
                "Open %s and press Tab until %s ('%s') has focus." % (page, s["selector"], s["name"]),
                "A visible change marks the focused control.",
                "Outline, box-shadow, border, background, color and text decoration are identical focused and unfocused.",
                axe_targets))

    for el in rec["interactive"]:
        if not el["focusable"] and el["selector"] not in reached:
            findings.append(_finding(
                "keyboard-unreachable", "2.1.1", el["selector"], el["name"],
                "Open %s and press Tab through the whole page." % page,
                "%s ('%s') receives focus and works from the keyboard." % (el["selector"], el["name"]),
                "It is never focused%s." % (", yet it responds to pointer clicks" if el["click_listener"] else ""),
                axe_targets))

    if not rec["reached_end"]:
        tail = seq[len(seq) // 2:]
        cycle = sorted({s["selector"] for s in tail})
        findings.append(_finding(
            "keyboard-trap", "2.1.2", cycle[0] if cycle else "body", ", ".join(cycle),
            "Open %s, press Tab %d times, then press Escape and Tab again." % (page, rec["max_tabs"]),
            "Tab moves past the widget to the end of the page.",
            "Focus cycles among %s and never reaches the end of the page; Escape %s." % (
                ", ".join(cycle), "releases it" if rec["escape_releases"] else "does not release it"),
            axe_targets, blocking=not rec["escape_releases"]))

    for sel in rec["positive_tabindex"]:
        findings.append(_finding(
            "focus-order-positive-tabindex", "2.4.3", sel, "",
            "Inspect the tabindex of %s in %s." % (sel, page),
            "Tab order follows the reading order.",
            "A positive tabindex moves this control ahead of the reading order; a human confirms the order still makes sense.",
            axe_targets, blocking=False))

    missed = sorted({f["rule"] for f in findings if not f["flagged_by_automated_scan"]})
    return {
        "ok": not any(f["blocking"] for f in findings),
        "page": page,
        "adapter": rec.get("adapter"),
        "automated_scan": {"tool": "axe-core", "violations": len(rec["axe_violations"]),
                           "ids": sorted(v["id"] for v in rec["axe_violations"])},
        "tab_stops": len(seen),
        "reached_end": rec["reached_end"],
        "findings": findings,
        "missed_by_automated_scan": missed,
        "limits": LIMITS,
    }


def blocked(page, reason):
    return {"ok": False, "status": "blocked", "page": page, "reason": reason, "manual_steps": MANUAL_STEPS,
            "result": "unverified until a browser adapter or a human tester runs the steps", "limits": LIMITS}


def read_page(path):
    if not os.path.isfile(path):
        raise InputError("page not found: %s" % path)
    if not path.lower().endswith((".html", ".htm")):
        raise InputError("page must be an .html or .htm file: %s" % path)
    with open(path, encoding="utf-8", errors="replace") as fh:
        head = fh.read(4096).lower()
    if "<html" not in head and "<body" not in head:
        raise InputError("page has no <html> or <body> in its first 4 KB: %s" % path)


def read_recording(path):
    try:
        with open(path, encoding="utf-8") as fh:
            rec = json.load(fh)
    except (OSError, ValueError) as exc:
        raise InputError("cannot read walk recording %s: %s" % (path, exc))
    if not isinstance(rec, dict) or any(k not in rec for k in RECORDING_KEYS + ("max_tabs",)):
        raise InputError("walk recording %s lacks one of: %s" % (path, ", ".join(RECORDING_KEYS)))
    return rec


def run_walker(page, modules, max_tabs):
    """Returns (recording or None, blocked reason or None)."""
    node = shutil.which("node")
    if not node:
        return None, "node is not on PATH"
    if not modules or not os.path.isdir(os.path.join(modules, "playwright")) or not os.path.isdir(os.path.join(modules, "axe-core")):
        return None, "no node_modules with playwright and axe-core (pass --node-modules or set %s)" % ENV_MODULES
    env = dict(os.environ, NODE_PATH=modules)
    p = subprocess.run([node, WALKER, page, "--max-tabs", str(max_tabs)], capture_output=True, text=True, env=env, timeout=180)
    try:
        rec = json.loads(p.stdout)
    except ValueError:
        return None, "walker printed no JSON (exit %d): %s" % (p.returncode, p.stderr.strip()[:200])
    if p.returncode == 3:
        return None, "walker could not load its adapter: %s" % rec.get("detail")
    if p.returncode != 0:
        return None, "walker failed: %s" % rec.get("detail", rec.get("error"))
    return rec, None


def main(argv=None):
    ap = argparse.ArgumentParser(description="Keyboard-path audit of one page.")
    ap.add_argument("--page", required=True)
    ap.add_argument("--node-modules", default=os.environ.get(ENV_MODULES, ""))
    ap.add_argument("--max-tabs", type=int, default=60)
    ap.add_argument("--walk-json", help="judge a saved recording instead of launching a browser")
    ap.add_argument("--save-walk", help="write the raw walker recording to this file")
    try:
        args = ap.parse_args(argv)
    except SystemExit as exc:
        if exc.code not in (0, None):
            print(json.dumps({"error": "usage: --page PAGE.html [--node-modules DIR] [--max-tabs N] [--walk-json FILE]"}, indent=2))
            return 2
        raise
    try:
        if args.max_tabs < 1 or args.max_tabs > 500:
            raise InputError("--max-tabs must be between 1 and 500")
        read_page(args.page)
        if args.walk_json:
            rec = read_recording(args.walk_json)
        else:
            rec, reason = run_walker(args.page, args.node_modules, args.max_tabs)
            if reason:
                print(json.dumps(blocked(os.path.basename(args.page), reason), indent=2, sort_keys=True))
                return 3
            if args.save_walk:
                with open(args.save_walk, "w", encoding="utf-8") as fh:
                    fh.write(json.dumps(rec, indent=2, sort_keys=True) + "\n")
    except InputError as exc:
        print(json.dumps({"error": str(exc)}, indent=2, sort_keys=True))
        return 2
    result = judge(rec, os.path.basename(args.page))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
