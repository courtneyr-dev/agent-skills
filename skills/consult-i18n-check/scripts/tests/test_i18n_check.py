from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from typing import Any, Dict, List, Optional, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
SCRIPT = os.path.join(ROOT, "scripts", "i18n_check.py")
FIX = os.path.join(ROOT, "fixtures")

ERROR_AND_WARNING_CODES = {
    "missing-translation", "untranslated", "placeholder-mismatch", "plural-categories",
    "plural-placeholder", "bidi-unbalanced", "rtl-placeholder-unisolated", "direction-mismatch",
    "length-exceeds-max", "hardcoded-format", "terminology-mismatch", "stale-source-revision",
}


def fx(name: str) -> str:
    return os.path.join(FIX, name)


def run(source: str, target: str, glossary: Optional[str] = None) -> Tuple[int, Dict[str, Any]]:
    cmd = [sys.executable, SCRIPT, "--source", source, "--target", target]
    if glossary:
        cmd += ["--glossary", glossary]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return proc.returncode, json.loads(proc.stdout)


def load(name: str) -> Dict[str, Any]:
    with open(fx(name), encoding="utf-8") as fh:
        return json.load(fh)


class I18nCheckTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)

    def write(self, name: str, content: Any) -> str:
        path = os.path.join(self.tmp.name, name)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(content if isinstance(content, str) else json.dumps(content))
        return path

    def test_clean_fr_exits_0(self) -> None:
        code, out = run(fx("source-en.json"), fx("target-fr.json"), fx("glossary.json"))
        self.assertEqual(code, 0)
        self.assertEqual(out["status"], "pass")
        self.assertEqual(out["defects"], [])
        self.assertEqual(out["cldr_version"], "48.0")
        self.assertEqual(out["linguistic_review"]["by"], "human:locale-reviewer")
        self.assertTrue(out["not_checked"])

    def test_ar_exits_1_with_every_code(self) -> None:
        code, out = run(fx("source-en.json"), fx("target-ar-defects.json"), fx("glossary.json"))
        self.assertEqual(code, 1)
        self.assertEqual(out["status"], "defects")
        self.assertEqual(set(out["counts"]), ERROR_AND_WARNING_CODES)
        severities = {d["code"]: d["severity"] for d in out["defects"]}
        self.assertEqual(severities["rtl-placeholder-unisolated"], "warning")
        self.assertEqual(severities["hardcoded-format"], "warning")
        self.assertEqual(severities["bidi-unbalanced"], "error")
        for d in out["defects"]:
            self.assertEqual(set(d), {"code", "severity", "key", "message"})

    def test_unknown_locale_is_blocked_not_guessed(self) -> None:
        code, out = run(fx("source-en.json"), fx("target-tlh-unknown.json"), fx("glossary.json"))
        self.assertEqual(code, 1)
        self.assertEqual(out["status"], "blocked")
        codes = {d["code"] for d in out["defects"]}
        self.assertIn("plural-rules-unknown", codes)
        self.assertNotIn("plural-categories", codes)
        self.assertNotIn("plural-placeholder", codes)
        self.assertIn("placeholder-mismatch", codes)  # other checks still run

    def test_fr_ca_resolves_to_fr(self) -> None:
        target = load("target-fr.json")
        target["locale"] = "fr-CA"
        code, out = run(fx("source-en.json"), self.write("fr-ca.json", target), fx("glossary.json"))
        self.assertEqual(code, 0)
        self.assertEqual(out["target_locale"], "fr-CA")
        self.assertEqual(out["status"], "pass")
        target["messages"]["files.count"]["plural"].pop("many")
        code, out = run(fx("source-en.json"), self.write("fr-ca2.json", target), fx("glossary.json"))
        self.assertEqual(code, 1)
        self.assertIn("plural-categories", out["counts"])

    def test_invalid_inputs_exit_2(self) -> None:
        src = fx("source-en.json")
        no_messages = load("target-fr.json")
        del no_messages["messages"]
        bad_glossary = {"schema": "i18n-glossary.v0", "terms": []}
        cases: List[Tuple[str, str, Optional[str]]] = [
            ("bad json", self.write("bad.json", "{not json"), None),
            ("wrong schema", fx("malformed-wrong-schema.json"), None),
            ("missing messages", self.write("nomsg.json", no_messages), None),
            ("bad glossary", fx("target-fr.json"), self.write("g.json", bad_glossary)),
            ("missing file", os.path.join(self.tmp.name, "absent.json"), None),
        ]
        for label, target, glossary in cases:
            with self.subTest(label):
                code, out = run(src, target, glossary)
                self.assertEqual(code, 2)
                self.assertIn("error", out)

    def test_usage_error_exits_2(self) -> None:
        proc = subprocess.run([sys.executable, SCRIPT, "--source", fx("source-en.json")],
                              capture_output=True, text=True)
        self.assertEqual(proc.returncode, 2)
        self.assertIn("error", json.loads(proc.stdout))

    def test_same_as_source_ok_suppresses_untranslated(self) -> None:
        target = load("target-fr.json")
        target["same_as_source_ok"] = []
        source = load("source-en.json")
        source["same_as_source_ok"] = []
        code, out = run(self.write("s.json", source), self.write("t.json", target), fx("glossary.json"))
        self.assertEqual(code, 1)
        flagged = [d["key"] for d in out["defects"] if d["code"] == "untranslated"]
        self.assertEqual(flagged, ["brand"])
        code, out = run(fx("source-en.json"), fx("target-fr.json"), fx("glossary.json"))
        self.assertNotIn("untranslated", out["counts"])


if __name__ == "__main__":
    unittest.main()
