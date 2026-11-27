"""Deterministic tests: contract frontier, leases, receipts, provider launch policy."""
import json
import multiprocessing
import os
import signal
import subprocess
import sys
import tempfile
import time
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.normpath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(SKILL, "scripts"))

from factory_rig import contract as C  # noqa: E402
from factory_rig.canon import sha_file  # noqa: E402
from factory_rig.lease import LeaseDenied, LeaseStore, StaleEpoch  # noqa: E402
from factory_rig.receipts import ReceiptStore  # noqa: E402


def make_contract(tid="TASK-A", deps=None, backends=("noodle",), spec_sha="x", decisions=("DEC-1",)):
    return {"schema_version": 1, "task_id": tid, "repo": "r", "title": "t", "spec": {"id": "S", "revision": "1", "sha256": spec_sha},
            "depends_on": list(deps or []), "required_decisions": list(decisions), "backends": list(backends),
            "base_branch": "main", "verify": {"argv": ["true"]}, "acceptance": ["a"]}


class FrontierTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.specs = self.tmp.name
        self.spec_path = os.path.join(self.specs, "S.md")
        self.write_spec('revision: "1"\nstatus: "accepted"\ndecisions: {"DEC-1": "accepted"}')

    def write_spec(self, fm):
        with open(self.spec_path, "w") as fh:
            fh.write("---\n" + fm + "\n---\nbody\n")
        self.sha = sha_file(self.spec_path)

    def run_frontier(self, tasks, contracts, backend="noodle"):
        return C.frontier(tasks, contracts, self.specs, backend)

    def test_ready_task_with_done_dependency_is_eligible(self):
        tasks = {"TASK-A": {"status": "done"}, "TASK-B": {"status": "ready", "depends_on": ["TASK-A"]}}
        con = {"TASK-B": make_contract("TASK-B", ["TASK-A"], spec_sha=self.sha)}
        el, rej = self.run_frontier(tasks, con)
        self.assertEqual(el, ["TASK-B"])

    def test_blocked_cyclic_incomplete_and_missing_dependency_cannot_enter(self):
        tasks = {
            "TASK-A": {"status": "ready", "depends_on": ["TASK-B"]},
            "TASK-B": {"status": "ready", "depends_on": ["TASK-A"]},
            "TASK-C": {"status": "ready", "depends_on": ["TASK-GHOST"]},
            "TASK-D": {"status": "planned"},
            "TASK-E": {"status": "ready", "depends_on": ["TASK-D"]},
            "TASK-F": {"status": "ready", "blocked_by": ["waiting on legal"]},
        }
        con = {t: make_contract(t, tasks[t].get("depends_on"), spec_sha=self.sha) for t in tasks}
        el, rej = self.run_frontier(tasks, con)
        self.assertEqual(el, [])
        self.assertIn("task is in a dependency cycle", rej["TASK-A"])
        self.assertTrue(any("does not exist" in r for r in rej["TASK-C"]))
        self.assertTrue(any("not ready" in r for r in rej["TASK-D"]))
        self.assertTrue(any("is planned, not done" in r for r in rej["TASK-E"]))
        self.assertTrue(any("explicit blockers" in r for r in rej["TASK-F"]))

    def test_unresolved_decision_blocks(self):
        self.write_spec('revision: "1"\nstatus: "accepted"\ndecisions: {"DEC-1": "proposed"}')
        tasks = {"TASK-A": {"status": "ready"}}
        el, rej = self.run_frontier(tasks, {"TASK-A": make_contract(spec_sha=self.sha)})
        self.assertEqual(el, [])
        self.assertTrue(any("decision DEC-1 is proposed" in r for r in rej["TASK-A"]))

    def test_spec_edit_after_contract_invalidates(self):
        tasks = {"TASK-A": {"status": "ready"}}
        con = {"TASK-A": make_contract(spec_sha=self.sha)}
        self.assertEqual(self.run_frontier(tasks, con)[0], ["TASK-A"])
        self.write_spec('revision: "1"\nstatus: "accepted"\ndecisions: {"DEC-1": "accepted"}\nnote: "edited"')
        el, rej = self.run_frontier(tasks, con)
        self.assertEqual(el, [])
        self.assertTrue(any("bytes changed" in r for r in rej["TASK-A"]))

    def test_backend_not_listed_is_ineligible(self):
        tasks = {"TASK-A": {"status": "ready"}}
        con = {"TASK-A": make_contract(backends=("pmo",), spec_sha=self.sha)}
        el, rej = self.run_frontier(tasks, con, backend="noodle")
        self.assertEqual(el, [])

    def test_shell_string_verify_is_rejected(self):
        c = make_contract()
        c["verify"] = {"argv": "pytest; rm -rf /"}
        self.assertTrue(any("never a shell string" in e for e in C.validate_contract(c)))

    def test_find_cycles(self):
        self.assertEqual(C.find_cycles({"A": ["B"], "B": []}), [])
        self.assertTrue(C.find_cycles({"A": ["B"], "B": ["C"], "C": ["A"]}))


def _race(args):
    root, backend, q = args
    store = LeaseStore(root)
    try:
        store.acquire("r", "TASK-A", "h", backend, "att-" + backend, "/wt", os.getpid(), ttl=60)
        q.put(backend)
    except LeaseDenied:
        q.put(None)
    time.sleep(0.2)


class LeaseTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = LeaseStore(self.tmp.name)

    def test_competing_backends_one_winner_across_processes(self):
        ctx = multiprocessing.get_context("spawn")
        q = ctx.Queue()
        procs = [ctx.Process(target=_race, args=((self.tmp.name, b, q),)) for b in ["noodle", "pmo", "curia", "noodle2", "pmo2", "x", "y", "z"]]
        for p in procs:
            p.start()
        for p in procs:
            p.join(30)
        results = [q.get(timeout=5) for _ in procs]
        self.assertEqual(len([r for r in results if r]), 1, results)

    def test_different_checkout_same_logical_repo_still_contends(self):
        self.store.acquire("r", "TASK-A", "h", "noodle", "a1", "/checkout-one", os.getpid())
        with self.assertRaises(LeaseDenied):
            self.store.acquire("r", "TASK-A", "h", "curia", "a2", "/checkout-two", os.getpid())

    def test_expired_lease_with_live_holder_is_uncertain_not_reclaimed(self):
        self.store.acquire("r", "TASK-A", "h", "noodle", "a1", "/wt", os.getpid(), ttl=1, now=1000.0)
        with self.assertRaises(LeaseDenied) as cm:
            self.store.acquire("r", "TASK-A", "h", "pmo", "a2", "/wt", os.getpid(), ttl=60, now=5000.0)
        self.assertIn("still running", cm.exception.reason)
        self.assertEqual(self.store.status("r", "TASK-A")["state"], "uncertain")
        with self.assertRaises(LeaseDenied):  # uncertain stays blocked
            self.store.acquire("r", "TASK-A", "h", "pmo", "a2", "/wt", os.getpid(), ttl=60, now=9000.0)

    def test_expired_lease_with_dead_holder_is_taken_over_with_higher_epoch(self):
        dead = subprocess.Popen(["sleep", "0.1"])
        self.store.acquire("r", "TASK-A", "h", "noodle", "a1", "/wt", dead.pid, ttl=1, now=1000.0)
        dead.wait()
        rec = self.store.acquire("r", "TASK-A", "h", "pmo", "a2", "/wt", os.getpid(), ttl=60, now=5000.0)
        self.assertEqual(rec["epoch"], 2)
        with self.assertRaises(StaleEpoch):
            self.store.heartbeat("r", "TASK-A", 1)
        self.assertEqual([e["event"] for e in self.store.history("r", "TASK-A")], ["acquired", "superseded", "acquired"])

    def test_unexpired_lease_is_never_taken_even_if_holder_dead(self):
        dead = subprocess.Popen(["sleep", "0.1"])
        self.store.acquire("r", "TASK-A", "h", "noodle", "a1", "/wt", dead.pid, ttl=600)
        dead.wait()
        with self.assertRaises(LeaseDenied):
            self.store.acquire("r", "TASK-A", "h", "pmo", "a2", "/wt", os.getpid())

    def test_fence_terminates_live_holder_then_takeover_allowed(self):
        worker = subprocess.Popen(["sleep", "60"], start_new_session=True)
        self.store.acquire("r", "TASK-A", "h", "noodle", "a1", "/wt", worker.pid, ttl=1, now=1000.0)
        self.store.fence("r", "TASK-A")
        worker.wait(timeout=10)
        self.assertIsNotNone(worker.returncode)
        rec = self.store.acquire("r", "TASK-A", "h", "pmo", "a2", "/wt", os.getpid(), now=5000.0)
        self.assertEqual(rec["epoch"], 2)
        ev = [e for e in self.store.history("r", "TASK-A") if e["event"] == "fenced"][0]
        self.assertIn("unverified", ev["note"])

    def test_fence_does_not_signal_our_own_process_group(self):
        # holder shares the caller's process group: fencing it must not terminate the caller
        worker = subprocess.Popen(["sleep", "60"])  # same group as this test process
        self.assertEqual(os.getpgid(worker.pid), os.getpgrp())
        self.store.acquire("r", "TASK-A", "h", "noodle", "a1", "/wt", worker.pid, ttl=1, now=1000.0)
        self.store.fence("r", "TASK-A")
        worker.wait(timeout=10)
        self.assertIsNotNone(worker.returncode)  # holder stopped; this test is still running

    def test_fence_with_expected_epoch_refuses_a_newer_holder(self):
        self.store.acquire("r", "TASK-A", "h", "noodle", "a1", "/wt", os.getpid())
        with self.assertRaises(StaleEpoch):
            self.store.fence("r", "TASK-A", expected_epoch=7)
        self.assertEqual(self.store.status("r", "TASK-A")["state"], "active")  # nothing was fenced

    def test_release_then_reacquire(self):
        r = self.store.acquire("r", "TASK-A", "h", "noodle", "a1", "/wt", os.getpid())
        self.store.release("r", "TASK-A", r["epoch"], "complete")
        self.assertEqual(self.store.acquire("r", "TASK-A", "h", "pmo", "a2", "/wt", os.getpid())["epoch"], 2)


class ReceiptTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.store = ReceiptStore(self.tmp.name)

    def test_duplicate_begin_returns_existing_and_advance_is_idempotent(self):
        a = self.store.begin("k", {"task_id": "T"})
        b = self.store.begin("k", {"task_id": "DIFFERENT"})
        self.assertEqual(b["data"]["task_id"], "T")
        self.store.advance("k", "integrated")
        again = self.store.advance("k", "integrated")
        self.assertEqual(len([l for l in again["log"] if l["step"] == "integrated"]), 1)

    def test_cannot_skip_a_step(self):
        self.store.begin("k", {})
        with self.assertRaises(ValueError):
            self.store.advance("k", "state_recorded")

    def test_reconcile_completes_only_what_the_world_shows(self):
        self.store.begin("k1", {"task_id": "T1"})
        self.store.begin("k2", {"task_id": "T2"})
        released = []
        rep = self.store.reconcile(lambda d: d["task_id"] == "T1", lambda d: d["task_id"] == "T1", lambda d: released.append(d["task_id"]))
        steps = {r["task_id"]: r["step"] for r in rep}
        self.assertEqual(steps, {"T1": "complete", "T2": "intent"})
        self.assertEqual(released, ["T1"])
        self.assertEqual([r["key"] for r in self.store.open_receipts()], ["k2"])


FAKE = """#!/bin/sh
# fake provider: record argv (one per line), stdin, cwd, HOME, then exit
out="$FAKE_OUT"
: > "$out.args"
for a in "$@"; do printf '%s\\n' "$a" >> "$out.args"; done
cat > "$out.stdin"
pwd > "$out.cwd"
printf '%s' "$HOME" > "$out.home"
printf '%s' "${CODEX_HOME-unset}" > "$out.codexhome"
exit "${FAKE_EXIT:-0}"
"""

SLEEPER = """#!/bin/sh
trap 'echo TERM > "$FAKE_OUT.sig"; exit 143' TERM
echo started > "$FAKE_OUT.started"
sleep 30 &
wait
"""


class ProviderWrapperTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        t = self.tmp.name
        self.fake = os.path.join(t, "fake-provider")
        self.sleeper = os.path.join(t, "sleeper")
        for p, body in ((self.fake, FAKE), (self.sleeper, SLEEPER)):
            with open(p, "w") as fh:
                fh.write(body)
            os.chmod(p, 0o755)
        self.policy = os.path.join(t, "policy.json")
        with open(self.policy, "w") as fh:
            json.dump({"codex": {"real": self.fake, "sandbox": "workspace-write", "ignore_user_config": True},
                       "claude": {"real": self.fake, "permission_mode": "acceptEdits", "allowed_tools": "Bash Read Edit Write Glob Grep"},
                       "audit": os.path.join(t, "audit.jsonl")}, fh)
        self.out = os.path.join(t, "cap")
        self.env = dict(os.environ, FRIG_POLICY=self.policy, FAKE_OUT=self.out)
        self.env.pop("FRIG_WRAPPER_ACTIVE", None)

    def launch(self, name, args, stdin="PROMPT TEXT\nline two\n", cwd=None, env=None):
        return subprocess.run([os.path.join(SKILL, "bin", name)] + args, input=stdin, capture_output=True, text=True,
                              cwd=cwd or self.tmp.name, env=env or self.env, timeout=30)

    def captured(self):
        with open(self.out + ".args") as fh:
            return fh.read().split("\n")[:-1]

    def read(self, ext):
        with open(self.out + "." + ext) as fh:
            return fh.read()

    def test_codex_bypass_flag_removed_sandbox_and_model_preserved(self):
        wd = os.path.join(self.tmp.name, "wt dir with space")
        os.makedirs(wd)
        p = self.launch("codex", ["exec", "--dangerously-bypass-approvals-and-sandbox", "--skip-git-repo-check", "--json", "--model", "gpt-x"], cwd=wd)
        self.assertEqual(p.returncode, 0, p.stderr)
        args = self.captured()
        self.assertNotIn("--dangerously-bypass-approvals-and-sandbox", args)
        self.assertEqual(args[0], "exec")
        self.assertEqual(args[args.index("-s") + 1], "workspace-write")
        self.assertIn("--ignore-user-config", args)
        self.assertEqual(args[args.index("--model") + 1], "gpt-x")
        self.assertIn("--skip-git-repo-check", args)
        self.assertEqual(self.read("stdin"), "PROMPT TEXT\nline two\n")
        self.assertEqual(os.path.realpath(self.read("cwd").strip()), os.path.realpath(wd))

    def test_extra_args_cannot_restore_a_bypass(self):
        p = self.launch("codex", ["exec", "--json", "--yolo"])
        self.assertEqual(p.returncode, 0)
        self.assertNotIn("--yolo", self.captured())
        p = self.launch("codex", ["exec", "--json", "-s", "danger-full-access"])
        self.assertEqual(p.returncode, 64)
        self.assertIn("not allowed", p.stderr)
        p = self.launch("codex", ["exec", "--sandbox=danger-full-access"])
        self.assertEqual(p.returncode, 64)

    def test_reasoning_effort_follows_the_model_like_agent_run(self):
        with open(self.policy) as fh:
            pol = json.load(fh)
        pol["codex"]["effort_by_model"] = {"gpt-6.1-sol": "high", "gpt-6-luna": "medium"}
        with open(self.policy, "w") as fh:
            json.dump(pol, fh)
        self.launch("codex", ["exec", "--json", "--model", "gpt-6.1-sol"])
        args = self.captured()
        self.assertEqual(args[args.index("-c") + 1], 'model_reasoning_effort="high"')
        self.launch("codex", ["exec", "--json", "--model", "gpt-6-luna"])
        self.assertIn('model_reasoning_effort="medium"', self.captured())
        self.launch("codex", ["exec", "--json", "--model", "unlisted"])
        self.assertNotIn("-c", self.captured())

    def test_claude_bypass_replaced_with_rig_policy(self):
        p = self.launch("claude", ["--input-format", "stream-json", "--output-format", "stream-json", "--verbose",
                                   "--permission-mode", "bypassPermissions", "--model", "m", "--append-system-prompt", "SYS PROMPT; rm -rf x"])
        self.assertEqual(p.returncode, 0, p.stderr)
        args = self.captured()
        self.assertNotIn("bypassPermissions", args)
        self.assertEqual(args[args.index("--permission-mode") + 1], "acceptEdits")
        self.assertEqual(args[args.index("--allowedTools") + 1], "Bash Read Edit Write Glob Grep")
        self.assertEqual(args[args.index("--append-system-prompt") + 1], "SYS PROMPT; rm -rf x")  # one argv element, not split
        self.assertEqual(args[args.index("--model") + 1], "m")

    def test_claude_dangerous_flags_dropped(self):
        self.launch("claude", ["-p", "--dangerously-skip-permissions", "--permission-mode=bypassPermissions"])
        args = self.captured()
        self.assertFalse([a for a in args if "dangerously" in a or "bypass" in a])

    def test_exit_status_and_environment_pass_through(self):
        env = dict(self.env, FAKE_EXIT="7", HOME="/home/someone", CODEX_HOME="/custom/codex")
        p = self.launch("codex", ["exec"], env=env)
        self.assertEqual(p.returncode, 7)
        self.assertEqual(self.read("home"), "/home/someone")
        self.assertEqual(self.read("codexhome"), "/custom/codex")

    def test_unset_codex_home_stays_unset(self):
        env = dict(self.env)
        env.pop("CODEX_HOME", None)
        self.launch("codex", ["exec"], env=env)
        self.assertEqual(self.read("codexhome"), "unset")

    def test_recursion_into_the_wrapper_is_refused(self):
        with open(self.policy) as fh:
            pol = json.load(fh)
        pol["codex"]["real"] = os.path.join(SKILL, "bin", "codex")
        with open(self.policy, "w") as fh:
            json.dump(pol, fh)
        p = self.launch("codex", ["exec"])
        self.assertEqual(p.returncode, 64)
        self.assertIn("recursive", p.stderr)

    def test_signal_reaches_the_real_provider(self):
        with open(self.policy) as fh:
            pol = json.load(fh)
        pol["codex"]["real"] = self.sleeper
        with open(self.policy, "w") as fh:
            json.dump(pol, fh)
        proc = subprocess.Popen([os.path.join(SKILL, "bin", "codex"), "exec"], stdin=subprocess.PIPE, env=self.env, cwd=self.tmp.name)
        for _ in range(100):
            if os.path.exists(self.out + ".started"):
                break
            time.sleep(0.1)
        self.assertTrue(os.path.exists(self.out + ".started"))
        proc.send_signal(signal.SIGTERM)
        self.assertEqual(proc.wait(timeout=10), 143)
        self.assertTrue(os.path.exists(self.out + ".sig"))

    def test_audit_record_written_without_prompt_or_env(self):
        self.launch("codex", ["exec", "--yolo"])
        with open(os.path.join(self.tmp.name, "audit.jsonl")) as fh:
            rec = json.loads(fh.readline())
        self.assertEqual(rec["dropped"], ["--yolo"])
        self.assertNotIn("PROMPT TEXT", json.dumps(rec))
        self.assertNotIn("env", rec)



class DriftTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.clone = os.path.join(self.tmp.name, "up")
        os.makedirs(self.clone)
        def g(*a):
            return subprocess.run(["git", "-C", self.clone] + list(a), capture_output=True, text=True, check=True).stdout.strip()
        g("init", "-q", "-b", "main")
        g("config", "user.email", "t@example.invalid"); g("config", "user.name", "T")
        for f in ("watched.go", "other.go"):
            open(os.path.join(self.clone, f), "w").write("v1")
        g("add", "-A"); g("commit", "-q", "-m", "one")
        self.pin = g("rev-parse", "HEAD")
        self.g = g

    def reg(self):
        return {"components": [{"id": "x", "name": "x", "upstream": "u", "clone": "up", "revision": self.pin, "license": "MIT",
                                "status": "installed-inactive", "responsibility": "r", "paths": [], "verify": ["v"], "update": "u", "rollback": "r",
                                "watch": [{"path": "watched.go", "rerun": ["check-a"]}]}], "overrides": []}

    def test_unchanged_is_pinned_and_unwatched_change_is_not_drift(self):
        from factory_rig import drift as D
        self.assertEqual(D.drift(self.reg(), self.tmp.name)[0]["state"], "pinned")
        open(os.path.join(self.clone, "other.go"), "w").write("v2")
        self.g("add", "-A"); self.g("commit", "-q", "-m", "two")
        self.assertEqual(D.drift(self.reg(), self.tmp.name)[0]["state"], "moved-unwatched")

    def test_watched_change_names_the_checks_to_rerun(self):
        from factory_rig import drift as D
        open(os.path.join(self.clone, "watched.go"), "w").write("v2")
        self.g("add", "-A"); self.g("commit", "-q", "-m", "two")
        r = D.drift(self.reg(), self.tmp.name)[0]
        self.assertEqual((r["state"], r["watched_changed"], r["rerun"]), ("drifted", ["watched.go"], ["check-a"]))

    def test_registry_verify_rejects_unverified_claims(self):
        from factory_rig import drift as D
        reg = self.reg()
        reg["components"][0]["status"] = "installed-and-verified"
        self.assertTrue(any("needs evidence" in e for e in D.verify_registry(reg)))
        reg["components"][0]["status"] = "blocked-platform"
        self.assertTrue(any("needs a blocker" in e for e in D.verify_registry(reg)))
        reg["components"][0]["status"] = "bogus"
        self.assertTrue(any("not one of" in e for e in D.verify_registry(reg)))


class NoodleSetupTests(unittest.TestCase):
    def test_gitignore_pattern_matches_before_the_worktrees_directory_exists(self):
        from factory_rig import noodle_setup
        with tempfile.TemporaryDirectory() as d:
            subprocess.run(["git", "init", "-q", d], check=True)
            with open(os.path.join(d, ".gitignore"), "w") as fh:
                fh.write(".noodle/\n.worktrees/\n")  # the slash form Noodle's check misses
            miss = subprocess.run(["git", "-C", d, "check-ignore", "-q", ".worktrees"]).returncode
            self.assertNotEqual(miss, 0)  # documents the upstream quirk
            noodle_setup.ensure_gitignore(d)
            self.assertEqual(subprocess.run(["git", "-C", d, "check-ignore", "-q", ".worktrees"]).returncode, 0)
            self.assertFalse(noodle_setup.ensure_gitignore(d))  # idempotent

    def test_install_writes_real_directories_and_detects_drift(self):
        from factory_rig import noodle_setup
        with tempfile.TemporaryDirectory() as d:
            subprocess.run(["git", "init", "-q", d], check=True)
            noodle_setup.install(d)
            for name in ("factory-execute", "schedule"):
                p = os.path.join(d, ".agents", "skills", name)
                self.assertTrue(os.path.isdir(p) and not os.path.islink(p))
            self.assertEqual(noodle_setup.drift(d), [])
            with open(os.path.join(d, ".agents", "skills", "schedule", "SKILL.md"), "a") as fh:
                fh.write("tampered")
            self.assertTrue(any("schedule" in x for x in noodle_setup.drift(d)))


class BacklogAdapterTests(unittest.TestCase):
    def test_projection_rejects_items_noodle_would_accept(self):
        from factory_rig import noodle_backlog as nb
        with self.assertRaises(ValueError):
            nb.project([{"id": "1", "title": "only what noodle validates"}])
        ok = {"id": "T", "title": "t", "status": "open", "contract_hash": "h", "spec_revision": "1", "lease_epoch": 1}
        self.assertEqual(len(nb.project([ok])), 1)
        with self.assertRaises(ValueError):
            nb.project([ok, ok])

    def test_done_callback_is_idempotent(self):
        from factory_rig import noodle_backlog as nb
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "cb.jsonl")
            self.assertTrue(nb.record_done(p, "x"))
            self.assertFalse(nb.record_done(p, "x"))
            self.assertEqual(len(open(p).read().strip().split("\n")), 1)

    def test_sync_prints_nothing_so_noodle_scheduler_stays_idle(self):
        p = subprocess.run([os.path.join(SKILL, "bin", "frig-backlog"), "sync"], capture_output=True, text=True)
        self.assertEqual((p.returncode, p.stdout), (0, ""))


if __name__ == "__main__":
    unittest.main()
