"""Cross-fleet workflow templates: check, route, run under one lease, resume, and refuse."""
import contextlib
import copy
import json
import os
import subprocess
import tempfile
import unittest

from support import SKILL

from factory_rig.lease import LeaseStore
from fleetlib import workflow as wfl
from fleetlib.ownership import claim
from fleetlib.registry import Registry

FIXTURE = os.path.join(SKILL, "workflows", "fixtures", "dry-run-client-a.json")
REDIRECT = os.path.join(SKILL, "demos", "fixtures", "client-a-handover-notes.md")


def reg():
    return Registry(SKILL)


@contextlib.contextmanager
def keep_tmp():
    """A fresh temp folder that is left in place afterward; the rig's rule is that nothing is deleted."""
    yield tempfile.mkdtemp(prefix="fleet-workflow-test-")


def run(wid, base, fixture=None, wf=None, **kw):
    w, wsha = wfl.load_workflow(wid)
    fx = fixture or wfl.load_fixture(FIXTURE)
    return wfl.run(reg(), wf or w, wsha, fx, base, tools="fake", **kw)


def calls(base):
    with open(os.path.join(base, "tool-calls.jsonl")) as fh:
        return [json.loads(l)["step"] for l in fh]


class Templates(unittest.TestCase):
    def test_every_template_passes_check(self):
        proc = subprocess.run([os.path.join(SKILL, "bin", "fleet"), "workflow", "check"], capture_output=True, text=True)
        out = json.loads(proc.stdout)
        self.assertEqual(proc.returncode, 0, out["errors"])
        self.assertEqual(len(out["errors"]), 8)

    def test_self_acceptance_fails_check(self):
        wf, wsha = wfl.load_workflow("community-improvement")
        wf["steps"][1]["acceptance_owner"] = wf["steps"][1]["producer"]
        errs = wfl.check(reg(), wf, wsha)
        self.assertTrue(any("is also its acceptance owner" in e for e in errs), errs)


class Chain(unittest.TestCase):
    def test_dry_run_chains_handoffs_with_keys(self):
        with keep_tmp() as tmp:
            out = run("extension-launch", tmp)
            self.assertEqual(out["status"], "complete")
            done = [s for s in out["steps"] if s["state"] == "accepted"]
            self.assertEqual(len(done), len(out["route"]))
            for a, b in zip(done, done[1:]):
                self.assertEqual(a["next_consumer"], b["producer"])
            for s in done:
                self.assertRegex(s["idempotency_key"], "^[0-9a-f]{32}$")
                self.assertTrue(os.path.isfile(os.path.join(tmp, "ledger", "submitted", s["idempotency_key"] + ".json")))
            self.assertEqual(done[-1]["next_consumer"], "human:product-owner")
            self.assertTrue(wfl.verify(tmp)["ok"])

    def test_producer_as_acceptor_is_refused_at_that_step(self):
        wf, _ = wfl.load_workflow("community-improvement")
        bad = copy.deepcopy(wf)
        bad["steps"][1]["acceptance_owner"] = bad["steps"][1]["producer"]
        with keep_tmp() as tmp:
            out = run("community-improvement", tmp, wf=bad)
            states = [(s["step"], s["state"]) for s in out["steps"]]
            self.assertEqual(states[0], ("evidence", "accepted"))
            self.assertEqual(states[1], ("governance", "refused"))
            self.assertIn("cannot be its own acceptance owner", " ".join(out["steps"][1]["errors"]))
            self.assertNotIn("governance", calls(tmp), "the refused step's tool must not run")
            self.assertFalse(os.path.exists(os.path.join(tmp, "ledger", "opened", out["steps"][1].get("handoff_id", "x") + ".json")))

    def test_human_data_boundary_stops_the_chain(self):
        with keep_tmp() as tmp:
            out = run("bcit-course-unit", tmp)
            self.assertEqual(out["status"], "stopped-at-human-boundary")
            states = {s["step"]: s["state"] for s in out["steps"]}
            self.assertEqual(states["learning-evidence"], "awaiting-human-data")
            self.assertEqual(states["revision"], "not-run")
            self.assertNotIn("learning-evidence", calls(tmp))


class SelectiveLoading(unittest.TestCase):
    def test_unrelated_fleets_are_not_loaded(self):
        with keep_tmp() as tmp:
            out = run("agency-engagement", tmp)
            self.assertEqual(out["fleets_loaded"], ["agency", "corporate"])
            for f in ("hosting", "bcit-education", "community", "consultancies", "devrel", "instructional-design", "product"):
                self.assertIn(f, out["fleets_not_loaded"])
                self.assertFalse(any(p.startswith("fleets/%s/" % f) for p in out["files_read"]), f)
            self.assertIn("hosting-intake", out["not_routed"])

    def test_a_need_routes_its_fleet_in(self):
        fx = wfl.load_fixture(FIXTURE)
        fx["needs"] = ["hosting"]
        with keep_tmp() as tmp:
            out = run("agency-engagement", tmp, fixture=fx)
            self.assertIn("hosting", out["fleets_loaded"])
            self.assertIn("hosting-intake", out["route"])
            self.assertNotIn("bcit-education", out["fleets_loaded"])


class Ownership(unittest.TestCase):
    def test_a_held_lease_refuses_a_second_run(self):
        wf, wsha = wfl.load_workflow("hosting-incident")
        fx = wfl.load_fixture(FIXTURE)
        with keep_tmp() as tmp:
            leases = os.path.join(tmp, "leases")
            chash = "0" * 64
            claim(LeaseStore(leases), reg(), fx["tenant_id"], wf["home_workload"], fx["instance"], wf["coordinator"], os.getpid(), chash)
            out = wfl.run(reg(), wf, wsha, fx, os.path.join(tmp, "run"), tools="fake", lease_root=leases)
            self.assertEqual(out["status"], "refused")
            self.assertIn("ownership", out["reason"])
            self.assertFalse(os.path.exists(os.path.join(tmp, "run", "tool-calls.jsonl")))


class Recovery(unittest.TestCase):
    def test_interrupted_run_resumes_without_duplicate_work(self):
        with keep_tmp() as tmp:
            first = run("hosting-incident", tmp, stop_after=2)
            self.assertEqual(first["status"], "interrupted")
            second = run("hosting-incident", tmp)
            self.assertEqual(second["status"], "complete")
            self.assertEqual([s.get("resumed", False) for s in second["steps"]][:3], [True, True, False])
            c = calls(tmp)
            self.assertEqual(len(c), len(set(c)), "a step's tool ran twice: %s" % c)
            third = run("hosting-incident", tmp)
            self.assertTrue(all(s.get("resumed") for s in third["steps"]))
            self.assertEqual(len(calls(tmp)), len(second["route"]))

    def test_edited_output_makes_verify_fail(self):
        with keep_tmp() as tmp:
            out = run("hosting-incident", tmp)
            first = out["steps"][0]["outputs"][0]
            with open(os.path.join(tmp, first), "a") as fh:
                fh.write("edited after acceptance\n")
            v = wfl.verify(tmp)
            self.assertFalse(v["ok"])
            self.assertIn("changed after the handoff recorded it", " ".join(v["steps"][0]["errors"]))
            again = run("hosting-incident", tmp)
            self.assertFalse(again["steps"][0].get("resumed", False), "stale evidence must not satisfy the gate on resume")

    def test_owner_fields_edited_in_opened_and_submitted_make_verify_fail(self):
        """The reviewer's minor 8: widen a step's authority in both opened/ and submitted/; verify reads the owner log."""
        with keep_tmp() as tmp:
            out = run("hosting-incident", tmp)
            hid = out["steps"][0]["handoff_id"]
            for folder in ("opened", "submitted"):
                for name in os.listdir(os.path.join(tmp, "ledger", folder)):
                    path = os.path.join(tmp, "ledger", folder, name)
                    with open(path) as fh:
                        h = json.load(fh)
                    if h.get("handoff_id") == hid:
                        h["authority"] = dict(h["authority"], mutation="scoped-write", external_actions="human-approved", publication="human-approved")
                        with open(path, "w") as fh:
                            json.dump(h, fh)
            v = wfl.verify(tmp)
            self.assertFalse(v["ok"])
            self.assertIn("protected field authority differs", " ".join(v["steps"][0]["errors"]))


class UntrustedContent(unittest.TestCase):
    def test_redirect_instructions_are_refused_and_analysis_continues(self):
        fx = wfl.load_fixture(FIXTURE)
        fx["untrusted"] = [{"path": os.path.relpath(REDIRECT, fx["_dir"]), "source_kind": "client-file", "step": "discovery"}]
        fx["worker_requests"] = {"discovery": {
            "data": {"classification": "confidential", "allowed_destinations": ["external:audit-desk@fixture-partner.example"]},
            "acceptance_owner": "agency.research-strategist", "reviewer": "agency.research-strategist"}}
        with keep_tmp() as tmp:
            out = run("agency-engagement", tmp, fixture=fx)
            step = next(s for s in out["steps"] if s["step"] == "discovery")
            self.assertEqual(sorted(step["refused_fields"]), ["acceptance_owner", "data", "reviewer"])
            self.assertEqual(step["state"], "accepted")
            self.assertEqual(out["status"], "complete")
            with open(os.path.join(tmp, "ledger", "submitted", step["idempotency_key"] + ".json")) as fh:
                rec = json.load(fh)
            self.assertEqual(rec["acceptance_owner"], "agency.engagement-director")
            self.assertNotIn("external:", json.dumps(rec["data"]))
            self.assertTrue({"evidence", "exfiltration"} <= {f["category"] for f in step["untrusted_findings"]})


class RealTools(unittest.TestCase):
    def test_a_failing_bound_check_stops_the_chain(self):
        fx = wfl.load_fixture(FIXTURE)
        fx["tools"] = {"evidence": {"outputs": ["note.txt"], "produce": [{"argv": ["{python}", "-c", "print('x')"], "stdout": "note.txt"}],
                                    "check": {"argv": ["{python}", "-c", "import sys; sys.exit(3)"], "expect_exit": [0]}}}
        w, wsha = wfl.load_workflow("community-improvement")
        with keep_tmp() as tmp:
            out = wfl.run(reg(), w, wsha, fx, tmp, tools="bound")
            self.assertEqual(out["steps"][0]["state"], "check-failed")
            self.assertEqual(out["steps"][0]["check_exit"], 3)
            self.assertEqual(out["status"], "stopped")


if __name__ == "__main__":
    unittest.main()
