"""Behavior tests for keyboard_audit.py.

Recorded walks (fixtures/walk-*.json, raw output of a real Chromium run) make the verdict tests
deterministic. The live test runs only when AGENCY_A11Y_NODE_MODULES points at a node_modules
holding playwright and axe-core, and checks a fresh browser run against the same verdicts.
"""
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.normpath(os.path.join(HERE, "..", "keyboard_audit.py"))
FIX = os.path.normpath(os.path.join(HERE, "..", "..", "fixtures"))
MODULES = os.environ.get("AGENCY_A11Y_NODE_MODULES", "")


def fx(name):
    return os.path.join(FIX, name)


def run(*args, env=None):
    p = subprocess.run([sys.executable, SCRIPT] + list(args), capture_output=True, text=True, env=env, timeout=240)
    return p.returncode, json.loads(p.stdout)


def rules(out):
    return sorted({f["rule"] for f in out["findings"]})


class RecordedWalkTests(unittest.TestCase):
    def test_defects_missed_by_axe_are_found(self):
        code, out = run("--page", fx("donate-before.html"), "--walk-json", fx("walk-before.json"))
        self.assertEqual(code, 1)
        self.assertEqual(out["automated_scan"]["violations"], 0)
        self.assertEqual(rules(out), ["focus-not-visible", "keyboard-trap", "keyboard-unreachable"])
        self.assertEqual(out["missed_by_automated_scan"], ["focus-not-visible", "keyboard-trap", "keyboard-unreachable"])
        by_rule = {f["rule"]: f for f in out["findings"]}
        self.assertEqual(by_rule["keyboard-trap"]["wcag"], "2.1.2")
        self.assertIn("#amount-10", by_rule["keyboard-trap"]["observed"])
        self.assertEqual(by_rule["keyboard-unreachable"]["selector"], "#monthly")
        self.assertEqual(len([f for f in out["findings"] if f["rule"] == "focus-not-visible"]), 3)
        for f in out["findings"]:
            self.assertTrue(f["steps"] and f["expected"] and f["observed"])

    def test_fixed_page_passes_without_false_positives(self):
        code, out = run("--page", fx("donate-after.html"), "--walk-json", fx("walk-after.json"))
        self.assertEqual(code, 0)
        self.assertEqual(out["findings"], [])
        self.assertTrue(out["reached_end"])

    def test_trap_released_by_escape_is_not_blocking(self):
        with open(fx("walk-before.json"), encoding="utf-8") as fh:
            rec = json.load(fh)
        rec["escape_releases"] = True
        rec["interactive"], rec["tab_sequence"] = [], rec["tab_sequence"][3:]
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump(rec, fh)
        try:
            code, out = run("--page", fx("donate-before.html"), "--walk-json", fh.name)
        finally:
            os.unlink(fh.name)
        self.assertEqual(code, 0)
        self.assertEqual([(f["rule"], f["blocking"]) for f in out["findings"]], [("keyboard-trap", False)])

    def test_output_never_claims_conformance(self):
        _, out = run("--page", fx("donate-after.html"), "--walk-json", fx("walk-after.json"))
        self.assertTrue(any("never certifies" in s for s in out["limits"]))
        self.assertNotIn("conformant", json.dumps(out).lower())


class InvalidInputTests(unittest.TestCase):
    def test_missing_page(self):
        code, out = run("--page", fx("nope.html"), "--walk-json", fx("walk-after.json"))
        self.assertEqual(code, 2)
        self.assertIn("not found", out["error"])

    def test_non_html_page(self):
        code, out = run("--page", fx("walk-after.json"), "--walk-json", fx("walk-after.json"))
        self.assertEqual(code, 2)
        self.assertIn(".html", out["error"])

    def test_bad_max_tabs(self):
        code, out = run("--page", fx("donate-after.html"), "--max-tabs", "0")
        self.assertEqual(code, 2)

    def test_malformed_recording(self):
        code, out = run("--page", fx("donate-after.html"), "--walk-json", fx("donate-after.html"))
        self.assertEqual(code, 2)
        self.assertIn("recording", out["error"])


class MissingAdapterTests(unittest.TestCase):
    def test_no_browser_adapter_reports_blocked_with_manual_steps(self):
        env = dict(os.environ, AGENCY_A11Y_NODE_MODULES="/nonexistent/node_modules")
        code, out = run("--page", fx("donate-before.html"), env=env)
        self.assertEqual(code, 3)
        self.assertEqual(out["status"], "blocked")
        self.assertGreaterEqual(len(out["manual_steps"]), 4)
        self.assertNotIn("findings", out)


@unittest.skipUnless(MODULES and os.path.isdir(os.path.join(MODULES, "playwright")),
                     "set AGENCY_A11Y_NODE_MODULES to a node_modules with playwright and axe-core to run the live browser test")
class LiveBrowserTests(unittest.TestCase):
    def test_fresh_runs_match_the_recorded_verdicts(self):
        code, out = run("--page", fx("donate-before.html"), "--max-tabs", "20")
        self.assertEqual(code, 1)
        self.assertEqual(rules(out), ["focus-not-visible", "keyboard-trap", "keyboard-unreachable"])
        self.assertEqual(out["automated_scan"]["violations"], 0)
        code, out = run("--page", fx("donate-after.html"), "--max-tabs", "20")
        self.assertEqual(code, 0)


if __name__ == "__main__":
    unittest.main()
