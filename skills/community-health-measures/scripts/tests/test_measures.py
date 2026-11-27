"""Behavior of measures.py. Fixtures are built here so the skill tests stand alone."""
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
import measures  # noqa: E402

GOOD = {
    "id": "first-response", "question": "How long do newcomers wait for a reply?",
    "definition": "Median hours from a newcomer's first thread to the first reply by someone else.",
    "source": {"kind": "chaoss", "url": "https://chaoss.community/kb/metric-time-to-first-response/"},
    "compute": {"kind": "median-hours", "record_type": "thread", "start": "opened_at", "end": "first_reply_at"},
    "level": "community", "min_group_size": 5, "consent_basis": "Public posts, aggregated only.", "publish": "public",
}
PEOPLE = ["alice-x", "bob-y", "carol-z", "dan-w", "erin-v"]


def plan(*metrics):
    return {"community": "c", "metrics": [dict(copy.deepcopy(GOOD), **m) for m in metrics] or [copy.deepcopy(GOOD)]}


def rules(p):
    return sorted({v["rule"] for v in measures.lint(p)})


def thread(person, h, **extra):
    return dict({"type": "thread", "person": person, "opened_at": "2026-10-01T00:00:00Z",
                 "first_reply_at": "2026-10-01T%02d:00:00Z" % h, "consent": "public"}, **extra)


class Lint(unittest.TestCase):
    def test_defined_sourced_aggregated_metric_passes(self):
        self.assertEqual(rules(plan()), [])

    def test_volunteer_rankings_are_refused(self):
        self.assertIn("ranking", rules(plan({"id": "top-10-contributors"})))
        self.assertIn("ranking", rules(plan({"definition": "A leaderboard of members by commit count each month."})))
        self.assertEqual(rules(plan({"level": "person"})), ["individual-level"])

    def test_inferred_burnout_and_protected_traits_are_refused(self):
        self.assertIn("inference", rules(plan({"question": "Which maintainers show burnout?"})))
        self.assertIn("inference", rules(plan({"definition": "Reply times broken down by gender of the poster."})))
        self.assertEqual(rules(plan({"definition": "Average hours to first reply, per channel, per quarter."})), [])

    def test_undefined_health_score_is_refused_and_a_defined_one_passes(self):
        score = {"id": "health-score", "question": "How healthy is the community?", "compute": None,
                 "definition": "One number from 0 to 100 for the board each quarter."}
        self.assertIn("undefined-composite", rules(plan({}, score)))
        defined = dict(score, components=["first-response"], weights={"first-response": 1.0})
        self.assertEqual(rules(plan({}, defined)), [])

    def test_sales_leads_are_refused_but_leadership_is_not(self):
        self.assertIn("sales-leads", rules(plan({"definition": "Attendees passed to sales as prospects after each meetup."})))
        self.assertEqual(rules(plan({"definition": "Members who stepped into leadership roles this year, counted."})), [])

    def test_moderation_cases_never_feed_metrics(self):
        self.assertIn("confidential-source", rules(plan({"compute": {"kind": "count", "record_type": "moderation-case"}})))

    def test_group_floor_consent_and_source_are_required(self):
        self.assertEqual(rules(plan({"min_group_size": 4})), ["small-groups"])
        self.assertEqual(rules(plan({"consent_basis": ""})), ["no-consent"])
        self.assertEqual(rules(plan({"source": {"kind": "chaoss", "url": "https://example.com/metric"}})), ["unsourced"])
        self.assertEqual(rules(plan({"source": {"kind": "local"}})), ["unsourced"])
        self.assertEqual(rules(plan({"definition": "speed"})), ["undefined-metric"])


class Aggregate(unittest.TestCase):
    def test_output_names_no_one_and_drops_confidential_and_withdrawn_records(self):
        recs = [thread(p, h) for p, h in zip(PEOPLE, [1, 2, 3, 4, 5])]
        recs += [thread("frank-u", 20, consent="withdrawn"), thread("gina-t", 20, classification="confidential"),
                 {"type": "moderation-case", "person": "hal-s", "classification": "confidential"}]
        out = measures.aggregate(plan(), {"records": recs})
        self.assertEqual(out["metrics"][0]["value"], 3.0)
        self.assertEqual(out["excluded_records"], {"confidential-or-case": 2, "consent-withdrawn": 1})
        text = json.dumps(out)
        for person in PEOPLE + ["frank-u", "gina-t", "hal-s"]:
            self.assertNotIn(person, text)

    def test_groups_below_the_minimum_are_suppressed_not_estimated(self):
        out = measures.aggregate(plan(), {"records": [thread(p, 1) for p in PEOPLE[:4]]})
        self.assertTrue(out["metrics"][0]["suppressed"])
        self.assertNotIn("value", out["metrics"][0])

    def test_repeat_records_from_one_person_do_not_reach_the_floor(self):
        out = measures.aggregate(plan(), {"records": [thread("alice-x", h) for h in range(1, 9)]})
        self.assertTrue(out["metrics"][0]["suppressed"])


class CaseRecordsNeverFeedMetrics(unittest.TestCase):
    """Review defect 5: a metric over conduct cases is refused however it's named, and case records never count."""

    def test_a_case_metric_is_refused_from_its_words(self):
        m = {"compute": None, "definition": "Number of moderation cases opened per month, by category, from the case log."}
        self.assertIn("confidential-source", rules(plan(m)))

    def test_a_case_like_record_type_is_refused(self):
        self.assertIn("confidential-source", rules(plan({"compute": {"kind": "count", "record_type": "coc-complaint"}})))

    def test_records_marked_as_cases_are_dropped(self):
        recs = [thread(p, h) for p, h in zip(PEOPLE, [1, 2, 3, 4, 5])]
        recs.append(thread("ivan-r", 20, category="moderation-case"))
        out = measures.aggregate(plan(), {"records": recs})
        self.assertEqual(out["excluded_records"]["confidential-or-case"], 1)
        self.assertEqual(out["metrics"][0]["value"], 3.0)


class Cli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.tmp, True)

    def write(self, name, obj):
        p = os.path.join(self.tmp, name)
        with open(p, "w") as fh:
            fh.write(obj if isinstance(obj, str) else json.dumps(obj))
        return p

    def run_cli(self, *argv):
        buf = io.StringIO()
        with redirect_stdout(buf):
            code = measures.main(list(argv))
        return code, json.loads(buf.getvalue())

    def test_aggregate_refuses_a_plan_that_fails_lint(self):
        bad = self.write("bad.json", plan({"level": "person"}))
        act = self.write("act.json", {"records": [thread(p, 1) for p in PEOPLE]})
        code, out = self.run_cli("aggregate", "--plan", bad, "--activity", act)
        self.assertEqual(code, 1)
        self.assertFalse(out["ok"])
        self.assertNotIn("excluded_records", out)
        self.assertEqual(out["violations"][0]["rule"], "individual-level")

    def test_aggregate_refuses_to_publish_a_case_count(self):
        p = self.write("p.json", plan({"compute": {"kind": "count", "record_type": "coc-complaint"}}))
        a = self.write("a.json", {"records": [{"type": "coc-complaint", "person": "p%02d" % i} for i in range(6)]})
        code, out = self.run_cli("aggregate", "--plan", p, "--activity", a)
        self.assertEqual(code, 1)
        self.assertNotIn("excluded_records", out)

    def test_invalid_input_is_rejected(self):
        self.assertEqual(self.run_cli("lint", self.write("x.json", "{broken"))[0], 2)
        self.assertEqual(self.run_cli("lint", self.write("y.json", {"metrics": "none"}))[0], 2)
        self.assertEqual(self.run_cli("lint", self.write("z.json", {"metrics": [{"question": "no id"}]}))[0], 2)
        good = self.write("g.json", plan())
        self.assertEqual(self.run_cli("aggregate", "--plan", good, "--activity", self.write("a.json", {"rows": []}))[0], 2)


if __name__ == "__main__":
    unittest.main()
