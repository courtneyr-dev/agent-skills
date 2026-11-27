"""Behavior of replay.py: what a reader of the report can observe."""
import io
import json
import os
import pwd
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import replay  # noqa: E402

REAL_HOME = pwd.getpwuid(os.getuid()).pw_dir
TMP = tempfile.mkdtemp(prefix="replay-tests-")


def tearDownModule():
    shutil.rmtree(TMP, ignore_errors=True)


def doc(body, front=""):
    fd, path = tempfile.mkstemp(suffix=".md", dir=TMP)
    with os.fdopen(fd, "w") as fh:
        fh.write(("---\n%s---\n" % front if front else "") + body)
    return path


def run(path, *extra):
    buf = io.StringIO()
    with redirect_stdout(buf):
        code = replay.main([path, "--timeout", "20"] + list(extra))
    return code, json.loads(buf.getvalue())


def block(code, expect=None):
    out = "```sh tier=run\n%s\n```\n" % code
    if expect is not None:
        out += "```text expect\n%s\n```\n" % expect
    return out


class InvalidInput(unittest.TestCase):
    def test_no_runnable_block_is_rejected(self):
        code, report = run(doc("```sh\necho not marked\n```\n"))
        self.assertEqual(code, 2)
        self.assertIn("no tier=run block", report["error"])

    def test_expect_before_any_step_is_rejected(self):
        code, report = run(doc("```text expect\nhello\n```\n" + block("echo hello")))
        self.assertEqual(code, 2)
        self.assertIn("before any tier=run block", report["error"])

    def test_unclosed_fence_is_rejected(self):
        code, report = run(doc("```sh tier=run\necho hello\n"))
        self.assertEqual(code, 2)
        self.assertIn("never closed", report["error"])

    def test_non_shell_runnable_block_is_rejected(self):
        code, report = run(doc("```python tier=run\nprint(1)\n```\n"))
        self.assertEqual(code, 2)
        self.assertIn("must be sh or bash", report["error"])

    def test_missing_doc_and_missing_asset_are_rejected(self):
        self.assertEqual(run("/nonexistent/quickstart.md")[0], 2)
        code, report = run(doc(block("true")), "--asset", "/nonexistent/asset")
        self.assertEqual(code, 2)
        self.assertIn("not a directory", report["error"])


class Replay(unittest.TestCase):
    def test_passing_doc_reports_every_criterion_and_leaves_the_reader_unverified(self):
        code, report = run(doc(block("echo hello world", "hello <who>")))
        self.assertEqual(code, 0)
        self.assertTrue(report["ok"])
        self.assertTrue(report["criteria"]["2_outputs_match"])
        self.assertTrue(report["criteria"]["5_unfamiliar_reader_success"].startswith("unverified"))

    def test_missing_expected_line_fails_and_names_the_step(self):
        code, report = run(doc(block("echo one") + block("echo two", "three")))
        self.assertEqual(code, 1)
        self.assertIn("step 2", report["failure"])
        self.assertFalse(report["criteria"]["2_outputs_match"])

    def test_expected_lines_must_appear_in_order(self):
        code, _ = run(doc(block("echo b; echo a", "a\nb")))
        self.assertEqual(code, 1)

    def test_failing_command_stops_later_steps(self):
        code, report = run(doc(block("echo one") + block("false") + block("echo three", "three")))
        self.assertEqual(code, 1)
        self.assertEqual(report["failure"], "step 2 exited 1 at command 1: false")
        self.assertEqual([s["ran"] for s in report["steps"]], [True, True, False])

    def test_inherited_environment_does_not_leak_in(self):
        os.environ["REPLAY_TEST_SHOULD_NOT_LEAK"] = "leaked"
        try:
            code, report = run(doc(block('test -z "${REPLAY_TEST_SHOULD_NOT_LEAK:-}" && echo clean', "clean")))
        finally:
            del os.environ["REPLAY_TEST_SHOULD_NOT_LEAK"]
        self.assertEqual(code, 0, report["failure"])
        self.assertEqual(report["isolation"]["env_keys"], ["HOME", "LANG", "PATH", "TMPDIR"])

    def test_home_is_empty_and_not_the_real_home(self):
        code, report = run(doc(block('test "$HOME" != "%s" && test -z "$(ls -A "$HOME")" && echo empty' % REAL_HOME, "empty")))
        self.assertEqual(code, 0, report["failure"])

    @unittest.skipUnless(sys.platform == "darwin" and os.path.exists("/usr/bin/sandbox-exec"), "sandbox-exec is macOS only")
    def test_reads_of_the_real_home_are_denied(self):
        code, report = run(doc(block('ls "%s" >/dev/null' % REAL_HOME)))
        self.assertEqual(code, 1)
        self.assertIn("sandbox-exec", report["isolation"]["sandbox"])

    def test_background_processes_do_not_outlive_the_replay(self):
        path = doc(block("sleep 30 &\necho $! > pid.txt"))
        code, report = run(path, "--keep")
        self.assertEqual(code, 0, report["failure"])
        root = report["isolation"]["kept_at"]
        pid = int(open(os.path.join(root, "work", "pid.txt")).read())
        shutil.rmtree(root)
        with self.assertRaises(ProcessLookupError):
            os.kill(pid, 0)

    def test_exceeding_the_declared_budget_fails(self):
        code, report = run(doc(block("sleep 1.2"), "replay_budget_seconds: 0.5\n"))
        self.assertEqual(code, 1)
        self.assertIs(report["criteria"]["4_within_budget"], False)
        self.assertIn("budget", report["failure"])

    def test_undeclared_tool_fails_before_any_step(self):
        code, report = run(doc(block("echo never"), "replay_requires: sh, no-such-tool-xyz\n"))
        self.assertEqual(code, 1)
        self.assertIn("no-such-tool-xyz", report["failure"])
        self.assertFalse(any(s["ran"] for s in report["steps"]))

    def test_assets_are_copied_and_hashed(self):
        asset = tempfile.mkdtemp(dir=TMP)
        with open(os.path.join(asset, "hello.sh"), "w") as fh:
            fh.write("echo from asset\n")
        code, report = run(doc(block("sh %s/hello.sh" % os.path.basename(asset), "from asset")), "--asset", asset)
        self.assertEqual(code, 0, report["failure"])
        self.assertEqual(len(report["assets"][0]["tree_sha256"]), 64)


class EachCommandChecked(unittest.TestCase):
    """Review defect 1: a failure set -e skips must still fail the step."""

    def assertFails(self, body, step):
        code, report = run(doc(body))
        self.assertEqual(code, 1, report.get("failure"))
        self.assertFalse(report["criteria"]["1_commands_succeed_verbatim"])
        self.assertIn("step %d" % step, report["failure"])
        return report

    def test_failure_inside_an_and_list_fails_the_step(self):
        report = self.assertFails(block("cd /no/such/dir && echo entered"), 1)
        self.assertIn("cd /no/such/dir", report["failure"])

    def test_failure_inside_a_pipeline_fails_the_step(self):
        self.assertFails(block("false | cat"), 1)

    def test_set_plus_e_in_an_earlier_step_does_not_hide_a_later_failure(self):
        self.assertFails(block("set +e") + block("false\necho after", "after"), 2)

    def test_handled_failure_and_multiline_commands_still_pass(self):
        body = block("false || echo handled", "handled")
        body += block("for i in 1 2; do\n  echo loop $i\ndone", "loop 1\nloop 2")
        body += block("cat <<EOF\nfrom heredoc\nEOF", "from heredoc")
        code, report = run(doc(body))
        self.assertEqual(code, 0, report.get("failure"))


class WholeLineExpectations(unittest.TestCase):
    """Review defect 2: a documented line must match a whole printed line, not a substring."""

    def test_documented_value_that_is_a_substring_fails(self):
        self.assertEqual(run(doc(block('echo "notes: 12"', "notes: 1")))[0], 1)
        self.assertEqual(run(doc(block('echo "status: not ok"', "ok")))[0], 1)

    def test_placeholders_still_match_one_volatile_token(self):
        code, report = run(doc(block('echo "version 3.9.6 ready"', "version <v> ready")))
        self.assertEqual(code, 0, report.get("failure"))


if __name__ == "__main__":
    unittest.main()
