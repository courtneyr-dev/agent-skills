import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import evalrun  # noqa: E402


def quiet(argv):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = evalrun.main(argv)
    return code, buf.getvalue()


class ExpectTests(unittest.TestCase):
    def test_met_and_not_met(self):
        cmd = ["--", sys.executable, "-c", "print('alpha')"]
        self.assertEqual(quiet(["expect", "--exit", "0", "--contains", "alpha"] + cmd)[0], 0)
        self.assertEqual(quiet(["expect", "--exit", "1"] + cmd)[0], 1)
        self.assertEqual(quiet(["expect", "--exit", "0", "--absent", "alpha"] + cmd)[0], 1)
        self.assertEqual(quiet(["expect", "--exit", "0", "--contains", "beta"] + cmd)[0], 1)

    def test_usage_errors(self):
        self.assertEqual(quiet(["expect", "--exit", "0"])[0], 2)
        self.assertEqual(quiet(["bogus"])[0], 2)


class RunTests(unittest.TestCase):
    def test_run_writes_evidence_and_outcomes(self):
        rel = "fleets/bcit-education/evidence/tmp-test-evalrun.txt"
        doc = {"evals": [
            {"id": "bcit-education.eval.tmp-pass", "check": {"method": "script", "argv": [sys.executable, "-c", "print(1)"]},
             "outcome": {"status": "not-run", "evidence": rel}},
            {"id": "bcit-education.eval.tmp-skip", "check": {"method": "model-judgment"}, "outcome": {"status": "not-run"}}]}
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump(doc, fh)
        try:
            code, out = quiet(["run", "--file", fh.name, "--write"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(out)["ran"], 1)
            with open(fh.name) as f:
                cases = json.load(f)["evals"]
            self.assertEqual(cases[0]["outcome"]["status"], "pass")
            self.assertEqual(cases[1]["outcome"]["status"], "not-run")
            with open(os.path.join(evalrun.CF, rel)) as f:
                self.assertTrue(f.read().startswith("$ "))
        finally:
            os.unlink(fh.name)
            if os.path.exists(os.path.join(evalrun.CF, rel)):
                os.unlink(os.path.join(evalrun.CF, rel))

    def test_failing_case_is_recorded_as_fail(self):
        doc = {"evals": [{"id": "bcit-education.eval.tmp-fail", "check": {"method": "script", "argv": [sys.executable, "-c", "raise SystemExit(3)"]},
                          "outcome": {"status": "not-run", "evidence": "fleets/bcit-education/evidence/tmp-test-fail.txt"}}]}
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump(doc, fh)
        try:
            code, out = quiet(["run", "--file", fh.name, "--write"])
            self.assertEqual(code, 1)
            with open(fh.name) as f:
                self.assertEqual(json.load(f)["evals"][0]["outcome"]["status"], "fail")
        finally:
            os.unlink(fh.name)
            p = os.path.join(evalrun.CF, "fleets/bcit-education/evidence/tmp-test-fail.txt")
            if os.path.exists(p):
                os.unlink(p)


class DryRunKeepsRetainedEvidence(unittest.TestCase):
    def test_run_without_write_leaves_evidence_and_outcomes_alone(self):
        rel = "fleets/bcit-education/evidence/tmp-test-retained.txt"
        dest = os.path.join(evalrun.CF, rel)
        with open(dest, "w") as f:
            f.write("retained raw output from an earlier run\n")
        doc = {"evals": [{"id": "bcit-education.eval.tmp-dry", "check": {"method": "script", "argv": [sys.executable, "-c", "print(2)"]},
                          "outcome": {"status": "pass", "evidence": rel, "run_on": "2026-11-25"}}]}
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
            json.dump(doc, fh)
        try:
            code, out = quiet(["run", "--file", fh.name])
            self.assertEqual(code, 0)
            with open(dest) as f:
                self.assertEqual(f.read(), "retained raw output from an earlier run\n")
            with open(fh.name) as f:
                self.assertEqual(json.load(f)["evals"][0]["outcome"]["run_on"], "2026-11-25")
            scratch = json.loads(out)["results"][0]["evidence"]
            self.assertTrue(os.path.isabs(scratch) and os.path.isfile(scratch))
        finally:
            os.unlink(fh.name)
            os.unlink(dest)


if __name__ == "__main__":
    unittest.main()
