"""Real Noodle binary (pinned build) with a fake provider behind the rig's wrapper. Skipped without the binary.

Point FRIG_NOODLE_BIN at the build (or put `noodle` on PATH) and FRIG_YYSUN_SKILL at project-manager
when it is not a sibling of this skill. The policy comes from config/provider-policy.example.json."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(SKILL, "scripts"))

from factory_rig import fixture, noodle_control, orchestrate, yysun  # noqa: E402

NOODLE = os.environ.get("FRIG_NOODLE_BIN") or shutil.which("noodle") or ""
YYSUN = os.environ.get("FRIG_YYSUN_SKILL") or os.path.join(os.path.dirname(SKILL), "project-manager")
POLICY_EXAMPLE = os.path.join(SKILL, "config", "provider-policy.example.json")


def sh(cwd, *a):
    return subprocess.run(list(a), cwd=cwd, capture_output=True, text=True, check=True).stdout.strip()


@unittest.skipUnless(os.path.isfile(NOODLE) and shutil.which("node") and os.path.isdir(YYSUN),
                     "needs the pinned Noodle build (FRIG_NOODLE_BIN or noodle on PATH), node and the project-manager skill")
class NoodleIntegration(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = os.path.join(os.path.realpath(self.tmp.name), "ws")
        fixture.build(self.root, YYSUN)
        self.ws = orchestrate.Workspace(self.root)
        subprocess.run([os.path.join(SKILL, "bin", "frig"), "noodle-init", "--ws", self.root, "--bin-dir", os.path.join(SKILL, "bin")],
                       check=True, capture_output=True)
        sh(self.ws.repo, "git", "add", "-A")
        sh(self.ws.repo, "git", "commit", "-q", "-m", "Noodle config")
        self.audit = os.path.join(self.tmp.name, "audit.jsonl")
        self.policy = os.path.join(self.tmp.name, "provider-policy.json")
        shutil.copy(POLICY_EXAMPLE, self.policy)  # `real` and `audit` are overridden per run below
        self.fake_log = os.path.join(self.tmp.name, "fake.log")
        self.runner = None

    def tearDown(self):
        if self.runner and self.runner.poll() is None:
            self.runner.terminate()
            self.runner.wait(timeout=20)
        self.tmp.cleanup()

    def start_runner(self, mode="ok", exit_when_idle=True, max_sched=3):
        env = dict(os.environ, FRIG_REAL_CODEX=os.path.join(HERE, "fake_codex.py"), FRIG_POLICY=self.policy, FRIG_AUDIT=self.audit,
                   FAKE_LOG=self.fake_log, FAKE_MODE=mode, PYTHONPATH=os.path.join(SKILL, "scripts"))
        args = [sys.executable, "-m", "factory_rig.cli", "noodle-run", "--ws", self.root, "--noodle-bin", NOODLE,
                "--max-scheduler-sessions", str(max_sched), "--max-wall", "120"]
        if exit_when_idle:
            args.append("--exit-when-idle")
        self.runner = subprocess.Popen(args, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        pidf = os.path.join(self.ws.rig_dir, "noodle.pid")
        for _ in range(100):
            if os.path.exists(pidf):
                break
            time.sleep(0.1)
        time.sleep(2)  # let Noodle's start-time scheduler session finish
        return int(open(pidf).read())

    def wait_parked(self, timeout=40):
        for _ in range(timeout * 2):
            if noodle_control.pending_review(self.ws.noodle_runtime):
                return True
            time.sleep(0.5)
        return False

    def runner_result(self, timeout=60):
        out, err = self.runner.communicate(timeout=timeout)
        return json.loads(out)

    def test_happy_path_through_real_noodle_supervised_mode(self):
        pid = self.start_runner()
        base = sh(self.ws.repo, "git", "rev-parse", "main")
        r = orchestrate.dispatch(self.ws, "TASK-MUL", "noodle", pid, provider="codex", model="")
        self.assertTrue(r["ok"], r)
        att = r["attempt"]
        self.assertTrue(self.wait_parked(), "Noodle never parked the candidate for review")
        self.assertEqual(sh(self.ws.repo, "git", "rev-parse", "main"), base, "supervised mode must not merge")
        item = noodle_control.pending_review(self.ws.noodle_runtime)[0]
        self.assertEqual(item["reason"], "supervised mode requires merge approval")
        cand = sh(item["worktree_path"], "git", "rev-parse", "HEAD")
        from factory_rig import gate
        gate.write_review(self.ws.rig_dir, {"task_id": "TASK-MUL", "attempt_id": att["attempt_id"], "contract_hash": att["contract_hash"],
                                            "candidate_sha": cand, "base_sha": att["base_sha"], "verdict": "approve",
                                            "reviewer": {"provider": "claude"}, "implementer": {"provider": "codex"}, "findings": []})
        done = orchestrate.complete(self.ws, att["attempt_id"])
        self.assertEqual(done["state"], "complete", done)
        self.assertEqual(done["noodle_ack"]["status"], "ok")
        self.assertEqual(sh(self.ws.repo, "git", "rev-parse", "main"), cand)
        self.assertEqual(yysun.task_status(self.ws.project, "TASK-MUL"), "done")
        res = self.runner_result()
        self.assertEqual(res["reason"], "all leases settled", res)
        self.assertLessEqual(res["sessions"]["schedule"], 4)
        self.assertEqual(noodle_control.pending_review(self.ws.noodle_runtime), [])
        # provider policy: every launch Noodle made went through the wrapper and lost its bypass flag
        calls = [json.loads(l) for l in open(self.audit)]
        self.assertGreaterEqual(len(calls), 2)
        for c in calls:
            self.assertIn("--dangerously-bypass-approvals-and-sandbox", c["dropped"])
            self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", c["rewritten_argv"])
        for line in open(self.fake_log):
            argv = json.loads(line)["argv"]
            self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", argv)
            self.assertEqual(argv[argv.index("-s") + 1], "workspace-write")

    def test_failed_worker_stops_the_runner_and_caps_scheduler_sessions(self):
        pid = self.start_runner(mode="fail", exit_when_idle=False)
        base = sh(self.ws.repo, "git", "rev-parse", "main")
        r = orchestrate.dispatch(self.ws, "TASK-MUL", "noodle", pid, provider="codex", model="")
        self.assertTrue(r["ok"], r)
        res = self.runner_result(timeout=90)
        self.assertIn("worker stage failed", res["reason"])
        self.assertLessEqual(res["sessions"]["schedule"], 4)  # cap 3 means stop on seeing a 4th, so at most 4 started
        self.assertEqual(sh(self.ws.repo, "git", "rev-parse", "main"), base)
        self.assertEqual(self.ws.leases.status("rig-pilot", "TASK-MUL")["state"], "active")  # holder gone, lease not silently freed
        out = orchestrate.abandon(self.ws, r["attempt"]["attempt_id"], "worker failed in Noodle")
        self.assertEqual(out["state"], "abandoned")
        self.assertEqual(self.ws.leases.status("rig-pilot", "TASK-MUL")["outcome"], "abandoned")
        self.assertEqual(yysun.task_status(self.ws.project, "TASK-MUL"), "in_progress")  # blocked, not done, not ready

    def test_scheduler_budget_stops_a_scheduler_loop(self):
        pid = self.start_runner(exit_when_idle=False, max_sched=0)
        res = self.runner_result(timeout=60)
        self.assertIn("scheduler session budget exceeded", res["reason"])


if __name__ == "__main__":
    unittest.main()
