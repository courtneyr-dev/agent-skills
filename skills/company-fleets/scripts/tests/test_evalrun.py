"""bin/fleet eval-run: one engine reads every runner's dialect and one check.expect format."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest

from support import SKILL

from fleetlib import evalrun
from fleetlib.evalrun import PlanError, plan

PY = sys.executable


def case(argv, **check):
    return {"id": "x.eval.y", "check": dict({"method": "script", "argv": argv}, **check)}


class Dialects(unittest.TestCase):
    def test_each_runner_is_parsed_into_one_shape(self):
        p = plan(case(["python3", "fleets/corporate/run_evals.py", "expect", "--exit", "1", "--contains", "a", "--absent", "b",
                       "--env", "HOME_X=~/x", "--", "sh", "-c", "exit 1"]))
        self.assertEqual((p.cmd, p.expect["exit"], p.expect["contains"], p.expect["absent"]), (["sh", "-c", "exit 1"], [1], ["a"], ["b"]))
        self.assertEqual(p.env["HOME_X"], os.path.expanduser("~/x"))
        p = plan(case(["python3", "fleets/product/tests/expect.py", "--exit", "0", "--", "python3", "-c", "print(1)"]))
        self.assertEqual(p.cmd[0], sys.executable)
        self.assertTrue(p.tmp)
        p = plan(case(["python3", "fleets/hosting/tools/evalrun.py", "expect", "--exit", "0", "--exit", "1", "--json", "verdict=leak",
                       "--json", "failed=[]", "--", "true"]))
        self.assertEqual((p.expect["exit"], p.expect["json"]), ([0, 1], {"verdict": "leak", "failed": []}))
        p = plan(case(["python3", "fleets/bcit-education/evalrun.py", "expect", "--exit", "2", "--exit", "0", "--", "true"]))
        self.assertEqual((p.expect["exit"], p.timeout), ([0], 120))
        p = plan(case(["sh", "-c", "true"]))
        self.assertEqual((p.runner, p.expect["exit"]), ("raw", [0]))

    def test_unsupported_shapes_are_refused_not_guessed(self):
        for argv in (["python3", "fleets/product/tests/expect.py", "--exit", "0", "--json", "a=1", "--", "true"],
                     ["python3", "fleets/hosting/tools/evalrun.py", "run", "--write"],
                     ["python3", "fleets/corporate/run_evals.py", "expect", "--exit", "0", "true"],
                     ["python3", "fleets/bcit-education/evalrun.py", "expect", "--contains", "x", "--", "true"]):
            with self.assertRaises(PlanError, msg=argv):
                plan(case(argv))

    def test_check_expect_is_the_one_format(self):
        p = plan(case(["true"], expect={"exit": [0], "contains": ["x"], "json": {"a.0": 1}}))
        self.assertEqual(p.runner, "check.expect")
        self.assertEqual(p.expect, {"exit": [0], "contains": ["x"], "absent": [], "json": {"a.0": 1}})


class Engine(unittest.TestCase):
    def run_case(self, argv, **check):
        return evalrun.execute(plan(case(argv, **check)), SKILL)

    def test_exit_text_and_json_assertions(self):
        ok = self.run_case([PY, "-c", "import json;print(json.dumps({'v':'leak','l':[{'r':'B'}]}))"],
                           expect={"exit": [0], "contains": ["leak"], "absent": ["secret"], "json": {"v": "leak", "l.0.r": "B"}})
        self.assertEqual(ok["status"], "pass", ok["problems"])
        bad = self.run_case([PY, "-c", "print('{\"v\": \"ok\"}')"], expect={"json": {"v": "leak", "missing.path": 1}})
        self.assertEqual(bad["status"], "fail")
        self.assertEqual(len(bad["problems"]), 2)

    def test_exit_three_is_blocked_unless_expected(self):
        self.assertEqual(self.run_case([PY, "-c", "raise SystemExit(3)"])["status"], "blocked")
        self.assertEqual(self.run_case([PY, "-c", "raise SystemExit(3)"], expect={"exit": [3]})["status"], "pass")

    def test_tmp_is_a_fresh_folder_for_dialects_that_use_it(self):
        r = self.run_case([PY, "-c", "import os,sys;print(os.path.isdir(sys.argv[1]))", "{tmp}"], expect={"contains": ["True"]})
        self.assertEqual(r["status"], "pass")


class Run(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = self.tmp.name
        os.makedirs(os.path.join(self.root, "fleets", "demo", "evidence"))
        self.evals = os.path.join(self.root, "fleets", "demo", "evals.json")
        json.dump({"schema_version": 1, "fleet": "demo", "evals": [
            {"id": "demo.eval.passes", "kind": "positive", "target": "demo.role", "input": "x", "expected": "y",
             "check": {"method": "script", "argv": [PY, "-c", "print('fine')"], "expect": {"contains": ["fine"]}},
             "outcome": {"status": "not-run"}},
            {"id": "demo.eval.fails", "kind": "negative", "target": "demo.role", "input": "x", "expected": "y",
             "check": {"method": "script", "argv": [PY, "-c", "raise SystemExit(1)"]}, "outcome": {"status": "not-run"}},
            {"id": "demo.eval.judged", "kind": "boundary", "target": "demo.role", "input": "x", "expected": "y",
             "check": {"method": "model-judgment"}, "outcome": {"status": "not-run"}}]}, open(self.evals, "w"))

    def tearDown(self):
        self.tmp.cleanup()

    def digest(self):
        return hashlib.sha256(open(self.evals, "rb").read()).hexdigest(), sorted(os.listdir(os.path.join(self.root, "fleets", "demo", "evidence")))

    def test_without_write_nothing_changes_and_only_script_cases_run(self):
        before = self.digest()
        out = evalrun.run(self.root)
        self.assertEqual(out["counts"], {"pass": 1, "fail": 1, "blocked": 0})
        self.assertEqual(self.digest(), before)

    def test_write_records_evidence_and_outcomes_and_filters_apply(self):
        out = evalrun.run(self.root, "demo", ["demo.eval.passes"], write=True)
        self.assertEqual(out["ran"], 1)
        doc = json.load(open(self.evals))
        self.assertEqual(doc["evals"][0]["outcome"]["evidence"], "fleets/demo/evidence/demo.eval.passes.txt")
        self.assertEqual(doc["evals"][1]["outcome"], {"status": "not-run"})
        text = open(os.path.join(self.root, "fleets/demo/evidence/demo.eval.passes.txt")).read()
        self.assertIn("fine", text)
        self.assertIn("# status pass", text)

    def test_cli_exit_code_follows_failures(self):
        base = [os.path.join(SKILL, "bin", "fleet"), "--root", self.root, "eval-run"]
        self.assertEqual(subprocess.run(base + ["--id", "demo.eval.passes"], capture_output=True, timeout=120).returncode, 0)
        self.assertEqual(subprocess.run(base, capture_output=True, timeout=120).returncode, 1)


DEMO = """import datetime, os, sys
here = os.path.dirname(os.path.abspath(__file__))
stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
os.makedirs(os.path.join(here, "runs", stamp))
open(os.path.join(here, "runs", stamp, "out.txt"), "w").write("synthetic run")
open(os.path.join(here, "runs", "LATEST"), "w").write(stamp)
print("run", stamp)
"""


class Sandbox(unittest.TestCase):
    """eval-run copies the skills root and runs there; only --write (evidence) or --in-place reaches the real tree."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = os.path.join(self.tmp.name, "repo")
        skills = os.path.join(self.repo, "skills")
        self.root = os.path.join(skills, "company-fleets")
        for d in ("fleets/demo/demo/runs", "fleets/demo/evidence"):
            os.makedirs(os.path.join(self.root, d))
        os.makedirs(os.path.join(skills, "other-skill"))
        open(os.path.join(self.root, "SKILL.md"), "w").write("---\nname: company-fleets\n---\n")
        open(os.path.join(self.root, "fleets/demo/demo/run_demo.py"), "w").write(DEMO)
        open(os.path.join(self.root, "fleets/demo/demo/runs/LATEST"), "w").write("none yet")
        open(os.path.join(skills, "other-skill", "write.py"), "w").write(
            "import os\nopen(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'touched.txt'), 'w').write('x')\n")
        cases = [("writes-a-file", [PY, "-c", "open('fleets/demo/touched.txt', 'w').write('x')"]),
                 ("demo-run", [PY, "fleets/demo/demo/run_demo.py"]),
                 ("sibling-write", [PY, "../other-skill/write.py"]),
                 ("absolute-path", [PY, os.path.join(os.path.realpath(skills), "other-skill", "write.py")])]
        json.dump({"schema_version": 1, "fleet": "demo", "evals": [
            {"id": "demo.eval." + slug, "kind": "positive", "target": "demo.role", "input": "x", "expected": "y",
             "check": {"method": "script", "argv": argv}, "outcome": {"status": "not-run"}} for slug, argv in cases]},
            open(os.path.join(self.root, "fleets/demo/evals.json"), "w"))
        subprocess.run(["git", "init", "-q", self.repo], check=True)
        subprocess.run(["git", "-C", self.repo, "add", "-A"], check=True)
        self.before = self.status()

    def tearDown(self):
        self.tmp.cleanup()

    def status(self):
        out = subprocess.run(["git", "-C", self.repo, "status", "--porcelain", "--untracked-files=all"],
                             capture_output=True, text=True, check=True).stdout
        return set(out.splitlines())

    def changed(self):
        return {line[3:] for line in self.status() - self.before}

    def test_default_run_leaves_git_status_unchanged(self):
        out = evalrun.run(self.root)
        self.assertEqual(out["counts"], {"pass": 4, "fail": 0, "blocked": 0}, out["results"])
        self.assertEqual(self.changed(), set())
        self.assertEqual(out["wrote"], [])

    def test_write_touches_only_the_evidence_files_and_evals_json(self):
        out = evalrun.run(self.root, write=True)
        ev = {"skills/company-fleets/fleets/demo/evidence/demo.eval.%s.txt" % s
              for s in ("writes-a-file", "demo-run", "sibling-write", "absolute-path")}
        self.assertEqual(self.changed(), ev | {"skills/company-fleets/fleets/demo/evals.json"})
        self.assertEqual(sorted(out["wrote"]), sorted([p[len("skills/company-fleets/"):] for p in ev] + ["fleets/demo/evals.json"]))

    def test_in_place_is_the_only_way_case_commands_reach_the_tree(self):
        evalrun.run(self.root, in_place=True)
        changed = self.changed()
        self.assertIn("skills/company-fleets/fleets/demo/demo/runs/LATEST", changed)
        self.assertIn("skills/company-fleets/fleets/demo/touched.txt", changed)
        self.assertIn("skills/other-skill/touched.txt", changed)

    def test_a_root_that_is_not_a_skill_is_copied_alone(self):
        os.remove(os.path.join(self.root, "SKILL.md"))
        subprocess.run(["git", "-C", self.repo, "add", "-A"], check=True)
        self.before = self.status()
        out = evalrun.run(self.root, ids=["demo.eval.sibling-write", "demo.eval.writes-a-file"])
        self.assertEqual({r["id"]: r["status"] for r in out["results"]},
                         {"demo.eval.sibling-write": "fail", "demo.eval.writes-a-file": "pass"})
        self.assertEqual(self.changed(), set())

    def test_a_copy_into_itself_is_refused(self):
        with self.assertRaises(OSError):
            evalrun.Sandbox(tempfile.gettempdir())

    def test_cli_runs_sandboxed_unless_in_place(self):
        base = [os.path.join(SKILL, "bin", "fleet"), "--root", self.root, "eval-run"]
        self.assertEqual(subprocess.run(base, capture_output=True, timeout=120).returncode, 0)
        self.assertEqual(self.changed(), set())
        self.assertEqual(subprocess.run(base + ["--in-place"], capture_output=True, timeout=120).returncode, 0)
        self.assertIn("skills/company-fleets/fleets/demo/demo/runs/LATEST", self.changed())


if __name__ == "__main__":
    unittest.main()
