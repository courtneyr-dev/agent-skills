import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, ".."))
import package_check as pc  # noqa: E402

UNIT = os.path.normpath(os.path.join(HERE, "..", "..", "..", "company-fleets", "fleets", "bcit-education",
                                     "fixtures", "bcit-unit-store"))


def run(pkg_path, *extra):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = pc.main(["check", pkg_path] + list(extra))
    return code, json.loads(buf.getvalue())


def write_variant(mutate):
    with open(os.path.join(UNIT, "package.json"), encoding="utf-8") as fh:
        pkg = json.load(fh)
    mutate(pkg)
    fh = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, dir=UNIT, prefix="tmp-test-")
    json.dump(pkg, fh)
    fh.close()
    return fh.name


class PackageTests(unittest.TestCase):
    def test_demo_unit_passes_and_reports_partial_standards(self):
        code, out = run(os.path.join(UNIT, "package.json"))
        self.assertEqual(code, 0, out["errors"])
        self.assertEqual(set(out["checks"]), {"assessment", "answer_key", "alignment"})
        self.assertIn("partial", out["notes"][0])

    def test_incomplete_package_fails_each_rule(self):
        code, out = run(os.path.join(UNIT, "package-incomplete.json"))
        self.assertEqual(code, 1)
        self.assertEqual({e["code"] for e in out["errors"]},
                         {"file-missing", "section-missing", "demand-lowered", "invented-learning-evidence", "assessment-failed"})

    def test_collected_evidence_needs_human_source(self):
        path = write_variant(lambda p: p.update(learning_evidence={"status": "collected", "source": "model"}))
        try:
            code, out = run(path)
        finally:
            os.unlink(path)
        self.assertIn("invented-learning-evidence", {e["code"] for e in out["errors"]})

    def test_missing_sibling_is_missing_capability(self):
        with tempfile.TemporaryDirectory() as empty:
            code, out = run(os.path.join(UNIT, "package.json"), "--skills-root", empty)
        self.assertEqual(code, 1)
        self.assertEqual({e["code"] for e in out["errors"]}, {"missing-capability"})

    def test_heading_pointer_must_exist(self):
        path = write_variant(lambda p: p["sections"].update(extension="teacher-guide.md#No such heading"))
        try:
            code, out = run(path)
        finally:
            os.unlink(path)
        self.assertIn("section-missing", {e["code"] for e in out["errors"]})


class InvalidInputTests(unittest.TestCase):
    def test_not_json_and_not_object(self):
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            fh.write("[1, 2]")
        try:
            code, out = run(fh.name)
        finally:
            os.unlink(fh.name)
        self.assertEqual(code, 1)
        self.assertEqual(out["status"], "invalid")

    def test_usage(self):
        self.assertEqual(pc.main([]), 2)


if __name__ == "__main__":
    unittest.main()
