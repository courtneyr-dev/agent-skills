"""Acceptance runner and override register: drift diagnostics and row status."""
import json
import os
import shutil
import tempfile
import unittest

from support import SKILL

from fleetlib import coverage as cov
from fleetlib.acceptance import _evals, row_status, run_check
from fleetlib.registry import Registry

SKILLS = os.path.dirname(SKILL)


def copy_root():
    """A registry root holding copies of the override register and the sources ledger; nothing is deleted."""
    tmp = tempfile.mkdtemp(prefix="fleet-acceptance-test-")
    for rel in (cov.OVERRIDES, cov.LEDGER):
        os.makedirs(os.path.join(tmp, os.path.dirname(rel)), exist_ok=True)
        shutil.copyfile(os.path.join(SKILL, rel), os.path.join(tmp, rel))
    return Registry(tmp, SKILLS)


class OverrideDrift(unittest.TestCase):
    def test_a_moved_upstream_revision_names_the_override_and_the_action(self):
        reg = copy_root()
        path = reg.path(cov.LEDGER)
        with open(path) as fh:
            ledger = json.load(fh)
        repo = next(r for r in ledger["repos"] if r["id"] == "WordPress/agent-skills")
        repo["revision"] = "0" * 40
        with open(path, "w") as fh:
            json.dump(ledger, fh)
        out = cov.check_overrides(reg)
        self.assertFalse(out["ok"])
        hit = [d for d in out["drift"] if d["repo"] == "WordPress/agent-skills"]
        self.assertEqual([d["override"] for d in hit], ["OVR-CF-14"])
        self.assertIn("rerun the evals", hit[0]["action"])

    def test_an_unrecorded_upstream_is_an_error(self):
        reg = copy_root()
        path = reg.path(cov.OVERRIDES)
        with open(path) as fh:
            doc = json.load(fh)
        doc["overrides"][0]["upstream"].append({"repo": "nobody/unknown", "revision": "x", "path": "y"})
        with open(path, "w") as fh:
            json.dump(doc, fh)
        self.assertIn("OVR-CF-01 cites nobody/unknown, which the sources ledger does not record", cov.check_overrides(reg)["errors"])

    def test_the_shipped_register_has_fourteen_overrides_and_no_drift(self):
        out = cov.check_overrides(Registry(SKILL))
        self.assertEqual(out["overrides"], 14)
        self.assertEqual(out["drift"], [])


class Rows(unittest.TestCase):
    def test_fail_outranks_blocked_outranks_pass(self):
        self.assertEqual(row_status([{"status": "pass"}, {"status": "blocked"}]), "blocked")
        self.assertEqual(row_status([{"status": "blocked"}, {"status": "fail"}]), "fail")
        self.assertEqual(row_status([{"status": "pass"}]), "pass")

    def test_an_honest_unmeasured_eval_satisfies_expect_blocked(self):
        reg = Registry(SKILL)
        out = run_check({"kind": "expect-blocked", "id": "devrel.eval.human-onboarding-usability"}, reg, _evals(reg), {})
        self.assertEqual(out["status"], "pass", out["output"])

    def test_a_missing_eval_fails(self):
        reg = Registry(SKILL)
        out = run_check({"kind": "eval", "id": "agency.eval.no-such-case"}, reg, _evals(reg), {})
        self.assertEqual(out["status"], "fail")


if __name__ == "__main__":
    unittest.main()
