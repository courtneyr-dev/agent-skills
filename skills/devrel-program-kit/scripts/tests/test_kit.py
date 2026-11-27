"""Behavior of check_program.py and check_routes.py. Fixtures are built here so the skill tests stand alone."""
import copy
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import check_program  # noqa: E402
import check_routes  # noqa: E402

import hashlib  # noqa: E402

PROGRAM = {
    "context_record": "tenant/devrel-context.md",
    "goals": ["More first successes"], "non_goals": ["No lead capture"],
    "budget": {"status": "owner-to-provide"}, "staffing": {"status": "owner-to-provide"},
    "metrics": [
        {"id": "first-success", "class": "usefulness", "definition": "keys with a 2xx call in 24h", "instrumentation": "api log", "owner": "analyst"},
        {"id": "visits", "class": "reach", "definition": "unique visitors", "instrumentation": "analytics", "owner": "analyst"},
    ],
    "claims": [], "reports": [{"audience": "exec", "headline_metrics": ["first-success", "visits"]}],
    "chain": [{"type": "quickstart", "artifact": "q.md", "verified_by": "devrel-quickstart-replay",
               "evidence": "evidence/replay.txt", "human_usability": "unverified"}],
}
BASE = None


def put(rel, text):
    path = os.path.join(BASE, rel)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        fh.write(text)


def replay_report(rel_doc, ok=True):
    with open(os.path.join(BASE, rel_doc), "rb") as fh:
        sha = hashlib.sha256(fh.read()).hexdigest()
    return "$ replay.py %s\n" % rel_doc + json.dumps({"tool": "devrel-quickstart-replay", "ok": ok, "doc_sha256": sha}, indent=2)


def setUpModule():
    global BASE
    BASE = tempfile.mkdtemp()
    put("q.md", "# Quickstart v1\n")
    put("evidence/replay.txt", replay_report("q.md"))
    put("records/form-12.json", '{"consent": "publication box ticked"}')
    put("records/crm-export-1.csv", "org,plan\n")
    put("sessions/us-4.md", "Reader session US-4 notes\n")


def tearDownModule():
    shutil.rmtree(BASE, ignore_errors=True)


def rules(fn=None):
    p = copy.deepcopy(PROGRAM)
    if fn:
        fn(p)
    return sorted({v["rule"] for v in check_program.check(check_program.parse(p), BASE)})


class Program(unittest.TestCase):
    def test_clean_plan_passes(self):
        self.assertEqual(rules(), [])

    def test_reach_is_not_success(self):
        self.assertEqual(rules(lambda p: p["reports"][0].update(headline_metrics=["visits"])), ["reach-headline"])
        self.assertIn("no-usefulness-metric", rules(lambda p: p["metrics"].pop(0) and p["reports"][0].update(headline_metrics=["visits"])))

    def test_non_goals_are_required(self):
        self.assertEqual(rules(lambda p: p.update(non_goals=[])), ["no-non-goals"])

    def test_revenue_needs_attribution_and_no_causal_claim(self):
        biz = {"id": "rev", "class": "business", "definition": "paid plans after a workshop", "instrumentation": "billing", "owner": "analyst"}
        self.assertEqual(rules(lambda p: p["metrics"].append(biz)), ["causal-revenue"])
        ok = dict(biz, attribution="Correlational only; it can't show the workshop caused a purchase.")
        self.assertEqual(rules(lambda p: p["metrics"].append(ok)), [])
        self.assertEqual(rules(lambda p: p["claims"].append({"kind": "revenue", "text": "DevRel drove $2M", "source": "records/crm-export-1.csv"})),
                         ["causal-revenue"])

    def test_quotes_and_results_need_sources_and_consent(self):
        self.assertEqual(rules(lambda p: p["claims"].append({"kind": "quote", "text": "x", "source": "records/form-12.json"})), ["fabrication-risk"])
        self.assertEqual(rules(lambda p: p["claims"].append({"kind": "customer-result", "text": "40% faster"})), ["fabrication-risk"])
        self.assertEqual(rules(lambda p: p["claims"].append({"kind": "quote", "text": "x", "source": "records/form-12.json",
                                                              "consent": "records/form-12.json"})), [])

    def test_budget_figures_need_the_owners_source(self):
        self.assertEqual(rules(lambda p: p.update(budget={"status": "provided", "amount": 9000})), ["invented-budget"])
        self.assertEqual(rules(lambda p: p.update(staffing={"status": "owner-to-provide", "headcount": 3})), ["invented-budget"])
        self.assertEqual(rules(lambda p: p.update(budget={"status": "provided", "amount": 9000, "source": "BUD-7"})), [])

    def test_context_stays_in_devrel_context_md(self):
        self.assertEqual(rules(lambda p: p.update(context_record="agent memory")), ["competing-context"])

    def test_runnable_chain_needs_replay_and_usability_needs_humans(self):
        self.assertEqual(rules(lambda p: p["chain"][0].update(verified_by="author")), ["untested-chain"])
        self.assertEqual(rules(lambda p: p["chain"][0].update(human_usability="verified")), ["unmeasured-usability"])
        self.assertEqual(rules(lambda p: p["chain"][0].update(human_usability="verified", human_evidence="sessions/us-4.md")), [])

    def test_invalid_input_is_rejected(self):
        with self.assertRaises(check_program.InputError):
            check_program.parse(dict(PROGRAM, metrics="none"))
        with self.assertRaises(check_program.InputError):
            check_program.parse(dict(PROGRAM, metrics=[{"class": "reach"}]))


class ReviewProbes(unittest.TestCase):
    """Review defect 6: evidence, sessions, sources and consent must be retained files, and claim kinds known."""

    def test_chain_evidence_must_exist(self):
        self.assertEqual(rules(lambda p: p["chain"][0].update(evidence="evidence/never-ran.txt")), ["untested-chain"])

    def test_chain_evidence_must_be_a_passing_replay_of_this_artifact(self):
        put("evidence/failed.txt", replay_report("q.md", ok=False))
        self.assertEqual(rules(lambda p: p["chain"][0].update(evidence="evidence/failed.txt")), ["untested-chain"])
        put("q2.md", "# Quickstart v2, edited after its replay\n")
        self.assertEqual(rules(lambda p: p["chain"][0].update(artifact="q2.md")), ["untested-chain"])

    def test_usability_needs_a_session_record_file(self):
        self.assertEqual(rules(lambda p: p["chain"][0].update(human_usability="verified", human_evidence="session-notes")),
                         ["unmeasured-usability"])

    def test_unknown_claim_kinds_are_refused(self):
        claim = {"kind": "endorsement", "text": "\"This API saved our team 40 hours a week\" - CTO, Acme Corp"}
        self.assertEqual(rules(lambda p: p["claims"].append(claim)), ["unknown-claim"])

    def test_sources_and_consent_must_be_retained_records(self):
        claim = {"kind": "testimonial", "text": "\"Great docs\"", "source": "slack", "consent": "given"}
        self.assertEqual(rules(lambda p: p["claims"].append(claim)), ["fabrication-risk"])


class Routes(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.root, True)
        for s in ("devrel-metrics", "developer-workshop-program"):
            os.makedirs(os.path.join(self.root, s))
            open(os.path.join(self.root, s, "SKILL.md"), "w").write("---\nname: %s\n---\n" % s)
        self.router = os.path.join(self.root, "router")
        os.makedirs(self.router)
        open(os.path.join(self.router, "SKILL.md"), "w").write(
            "Route to `samber/developer-relations-skills@devrel-metrics`, "
            "`samber/developer-relations-skills@renamed-skill` and "
            "`samber/dev-event-organizer-skills@workshop-program-design`.\n")

    def cli(self, *argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = check_routes.main(["--skills-root", self.root] + list(argv))
        return code, json.loads(buf.getvalue())

    def test_scan_separates_drift_from_missing_siblings_and_offers_installed_fallbacks(self):
        code, out = self.cli("scan", self.router)
        self.assertEqual(code, 1)
        self.assertEqual(out["counts"], {"installed": 1, "drift": 1, "sibling-not-installed": 1})
        sib = next(u for u in out["unresolved"] if u["status"] == "sibling-not-installed")
        self.assertEqual(sib["fallback"], ["developer-workshop-program"])

    def test_routes_that_all_resolve_pass(self):
        path = os.path.join(self.root, "r.json")
        json.dump({"routes": [{"skill": "devrel-metrics"}, {"skill": "samber/developer-relations-skills@developer-workshop-program"}]}, open(path, "w"))
        self.assertEqual(self.cli("routes", path)[0], 0)

    def test_invalid_input_is_rejected(self):
        path = os.path.join(self.root, "bad.json")
        json.dump({"routes": [{"skill": "Not A Name!"}]}, open(path, "w"))
        self.assertEqual(self.cli("routes", path)[0], 2)
        json.dump({"routes": []}, open(path, "w"))
        self.assertEqual(self.cli("routes", path)[0], 2)
        self.assertEqual(self.cli("scan", os.path.join(self.root, "missing"))[0], 2)


if __name__ == "__main__":
    unittest.main()
