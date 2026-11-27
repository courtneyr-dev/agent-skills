"""Offline tests for research_check. Run: python3 -m unittest discover -s scripts/tests -p 'test_*.py'"""
import contextlib
import io
import json
import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import research_check as rc  # noqa: E402


def study(**over):
    doc = {"design": "matched-random", "evidence_type": "peer-reviewed-study", "comparison_group": True,
           "random_assignment": True, "confound_controls": ["pretest match"],
           "sample": {"n": 120, "sites": 3, "level": "k12", "setting": "classroom", "selection": "random-sample"},
           "measures": [{"name": "post", "kind": "performance"}, {"name": "survey", "kind": "self-report"}],
           "analysis": {"equivalence_test": False, "subgroup_post_hoc": False},
           "claims": [{"id": "C1", "text": "The treatment group scored higher on the post-test.", "basis": ["post"]}]}
    doc.update(over)
    return doc


def rules(out):
    return {f["rule"] for f in out["findings"]}


def run_cli(args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        code = rc.main(args)
    return code, buf.getvalue()


class ClaimsTest(unittest.TestCase):
    def test_scoped_experimental_claim_passes(self):
        out = rc.check_claims(study())
        self.assertTrue(out["ok"])
        self.assertEqual(out["findings"], [])

    def test_causal_universal_small_selfreport_overclaim_is_rejected(self):
        doc = study(design="descriptive", comparison_group=False, random_assignment=False, confound_controls=[],
                    sample={"n": 24, "sites": 1, "level": "k12", "setting": "classroom", "selection": "convenience"},
                    claims=[{"id": "S1", "text": "The tutor causes all K-12 students to learn faster.", "basis": ["survey"]}])
        out = rc.check_claims(doc)
        self.assertFalse(out["ok"])
        self.assertTrue({"causal-from-nonexperimental", "universal-from-narrow-sample",
                         "small-single-site", "self-report-learning"} <= rules(out))

    def test_higher_ed_sample_applied_to_k12_is_an_error(self):
        doc = study(sample={"n": 300, "sites": 1, "level": "higher-ed", "setting": "university-course", "selection": "census"},
                    claims=[{"id": "T1", "text": "Students score higher.", "scope": {"level": "k12"}, "basis": ["post"]}])
        out = rc.check_claims(doc)
        self.assertIn("higher-ed-to-other-level", rules(out))
        self.assertFalse(out["ok"])

    def test_transfer_argument_lifts_the_level_finding(self):
        doc = study(sample={"n": 300, "sites": 1, "level": "higher-ed", "setting": "university-course", "selection": "census"},
                    claims=[{"id": "T1", "text": "Students score higher.", "scope": {"level": "k12"}, "basis": ["post"],
                             "transfer_argument": "replicated in two grade 10 classes"}])
        self.assertNotIn("higher-ed-to-other-level", rules(rc.check_claims(doc)))

    def test_hedged_generalization_warns_instead_of_failing(self):
        doc = study(claims=[{"id": "C", "text": "This may help novices in general.", "scope": {"level": "general"}}])
        out = rc.check_claims(doc)
        self.assertTrue(out["ok"])
        self.assertIn("transfer-beyond-sample", rules(out))

    def test_quasi_experiment_without_controls_is_an_error(self):
        doc = study(design="quasi-experimental", random_assignment=False, confound_controls=[])
        self.assertIn("no-confound-controls", rules(rc.check_claims(doc)))

    def test_controlled_quasi_causal_wording_warns(self):
        doc = study(design="quasi-experimental", random_assignment=False,
                    claims=[{"id": "Q", "text": "The unit improved scores.", "basis": ["post"]}])
        out = rc.check_claims(doc)
        self.assertTrue(out["ok"])
        self.assertIn("causal-from-nonexperimental", rules(out))

    def test_null_result_and_post_hoc_subgroup_warn(self):
        doc = study(analysis={"equivalence_test": False, "subgroup_post_hoc": True},
                    claims=[{"id": "N", "text": "Access does not impede learning gains.", "basis": ["post"]},
                            {"id": "G", "text": "High scorers gained more.", "subgroup": True, "basis": ["post"]}])
        self.assertTrue({"null-as-equivalence", "post-hoc-subgroup"} <= rules(rc.check_claims(doc)))

    def test_nonsignificant_directional_claim_warns_unless_acknowledged(self):
        flagged = study(claims=[{"id": "A", "text": "The tool reduced stress.", "result_significant": False}])
        honest = study(claims=[{"id": "B", "text": "The tool reduced stress, but this did not reach statistical significance.",
                                "result_significant": False}])
        self.assertIn("nonsignificant-as-effect", rules(rc.check_claims(flagged)))
        self.assertNotIn("nonsignificant-as-effect", rules(rc.check_claims(honest)))

    def test_conference_talk_as_established_finding_is_an_error(self):
        doc = study(evidence_type="conference-talk",
                    claims=[{"id": "W", "text": "Students scored higher.", "strength": "established"}])
        self.assertIn("weak-evidence-type", rules(rc.check_claims(doc)))

    def test_invalid_study_input_is_rejected(self):
        for bad in (study(design="vibes"), study(claims=[]), study(sample={"n": "many", "sites": 1, "level": "k12"}),
                    study(sample={"n": 5, "sites": 1, "level": "general"}), study(evidence_type="blog")):
            with self.assertRaises(rc.InputError):
                rc.check_claims(bad)
        doc = study()
        del doc["design"]
        with self.assertRaises(rc.InputError):
            rc.check_claims(doc)


def plan(**over):
    doc = {"question": "Q?", "question_type": "causal", "rationale": {"theory": "t"},
           "method": {"approach": "quasi-experimental", "justification": "intact classes", "confound_controls": ["pretest"]},
           "participants": {"population": "p", "minors": True},
           "instruments": [{"name": "i", "construct": "c", "validity_plan": "pilot"}],
           "analysis": {"plan": "ANCOVA"},
           "ethics": {"status": "not-submitted", "consent_assent": "consent and assent"},
           "data_management": {"storage": "s", "retention": "r", "access": "a", "deidentification": "d"},
           "participant_data": []}
    doc.update(over)
    return doc


class DesignTest(unittest.TestCase):
    def test_complete_plan_passes(self):
        self.assertTrue(rc.check_design(plan())["ok"])

    def test_claimed_approval_without_evidence_is_rejected(self):
        out = rc.check_design(plan(ethics={"status": "approved", "consent_assent": "x"}))
        self.assertIn("approval-claimed-without-evidence", rules(out))
        self.assertFalse(out["ok"])

    def test_recorded_approval_still_needs_a_human_check(self):
        out = rc.check_design(plan(ethics={"status": "approved", "approval_evidence": "REB-123", "consent_assent": "x"}))
        self.assertTrue(out["ok"])
        self.assertIn("approval-unconfirmed", rules(out))

    def test_plan_holding_participant_data_is_rejected(self):
        self.assertIn("participant-data-present", rules(rc.check_design(plan(participant_data=[{"id": 1}]))))

    def test_method_must_fit_question(self):
        out = rc.check_design(plan(method={"approach": "qualitative", "justification": "j"}))
        self.assertIn("method-question-mismatch", rules(out))

    def test_missing_sections_and_minors_without_assent(self):
        doc = plan(ethics={"status": "not-submitted"})
        del doc["data_management"]
        found = rules(rc.check_design(doc))
        self.assertTrue({"missing-section", "minors-without-assent"} <= found)

    def test_invalid_design_values_are_rejected(self):
        for bad in (plan(question_type="hunch"), plan(method={"approach": "astrology", "justification": "j"}),
                    plan(ethics={"status": "pending-ish", "consent_assent": "x"})):
            with self.assertRaises(rc.InputError):
                rc.check_design(bad)


def program(**over):
    doc = {"evaluation_foci": sorted(rc.FOCI),
           "evidence": [{"id": "E1", "kind": "scored-student-work", "dimensions": ["business-subject-mastery"]},
                        {"id": "E2", "kind": "satisfaction-survey", "dimensions": []}],
           "conclusions": [{"id": "K1", "dimension": "business-subject-mastery", "about_learning": True, "evidence": ["E1"]}]}
    doc.update(over)
    return doc


class ProgramTest(unittest.TestCase):
    def test_matched_dimension_passes(self):
        self.assertTrue(rc.check_program(program())["ok"])

    def test_evidence_for_one_dimension_does_not_establish_another(self):
        out = rc.check_program(program(conclusions=[{"id": "K", "dimension": "occupational-assessment-readiness", "evidence": ["E1"]}]))
        self.assertIn("cross-dimension", rules(out))

    def test_survey_is_not_learning_evidence(self):
        out = rc.check_program(program(conclusions=[{"id": "K", "dimension": "business-subject-mastery",
                                                     "about_learning": True, "evidence": ["E2"]}]))
        self.assertIn("not-learning-evidence", rules(out))

    def test_missing_focus_and_unchecked_standards(self):
        out = rc.check_program(program(evaluation_foci=["coherence"], standards_mapping="x"))
        self.assertTrue({"focus-missing", "standards-unchecked"} <= rules(out))

    def test_invalid_program_input_is_rejected(self):
        for bad in (program(conclusions=[{"id": "K", "dimension": "vibes", "evidence": ["E1"]}]),
                    program(evidence=[{"id": "E9", "kind": "gut-feeling"}])):
            with self.assertRaises(rc.InputError):
                rc.check_program(bad)


RESOLVER = {"entries": {
    "doi:10.1/good": {"titles": ["Computational Thinking in K–12"], "years": [2013], "authors": ["Grover", "Pea"], "doi": "10.1/good", "source": "crossref"},
    "arxiv:2101.00001": {"titles": ["A Preprint Title"], "years": [2021], "authors": ["Ada Lovelace"], "doi": "", "source": "arxiv"},
    "search:" + rc._norm("Scratch programming for all Resnick Maloney 2009"): {"source": "crossref-search", "candidates": [
        {"titles": ["Scratch: programming for all"], "years": [2009], "authors": ["Resnick"], "doi": "10.1/s", "source": "crossref"}]}}}


def refs(*entries):
    return {"references": list(entries)}


class CitationsTest(unittest.TestCase):
    def setUp(self):
        self.resolve = lambda key: RESOLVER["entries"].get(key)

    def test_doi_arxiv_and_search_verify(self):
        out = rc.check_citations(refs(
            {"id": "a", "doi": "10.1/GOOD", "cited": {"title": "Computational thinking in K-12", "year": 2013, "authors": ["Grover"]}},
            {"id": "b", "arxiv": "2101.00001", "cited": {"title": "A preprint title", "year": 2021, "authors": ["Lovelace"]}},
            {"id": "c", "cited": {"title": "Scratch programming for all", "year": 2009, "authors": ["Resnick", "Maloney"]}}),
            self.resolve)
        self.assertEqual(out["counts"], {"verified": 3, "mismatch": 0, "unresolved": 0})
        self.assertTrue(out["ok"])

    def test_wrong_year_and_author_are_mismatches(self):
        out = rc.check_citations(refs({"id": "a", "doi": "10.1/good",
                                       "cited": {"title": "Computational thinking in K-12", "year": 2010, "authors": ["Smith"]}}),
                                 self.resolve)
        self.assertEqual(out["results"][0]["status"], "mismatch")
        self.assertEqual(set(out["results"][0]["mismatched"]), {"year", "first_author"})
        self.assertFalse(out["ok"])

    def test_corporate_author_is_unchecked_not_wrong(self):
        resolve = lambda key: {"titles": ["Standards for Reporting"], "years": [2006], "authors": [], "doi": "10.1/aera"}
        out = rc.check_citations(refs({"id": "a", "doi": "10.1/aera", "cited": {"title": "Standards for reporting", "year": 2006,
                                                                               "authors": ["American Educational Research Association"]}}), resolve)
        self.assertEqual(out["results"][0]["status"], "verified")
        self.assertEqual(out["results"][0]["unchecked"], ["first_author"])

    def test_corporate_name_matches_as_phrase_and_surname_as_token(self):
        resolve = lambda key: {"titles": ["DBR"], "years": [2003], "authors": ["The Design-Based Research Collective"], "doi": ""}
        ok = rc.check_citations(refs({"id": "a", "doi": "10.1/d", "cited": {"title": "DBR", "year": 2003,
                                                                           "authors": ["Design-Based Research Collective"]}}), resolve)
        self.assertEqual(ok["results"][0]["status"], "verified")
        partial = rc.check_citations(refs({"id": "b", "doi": "10.1/d", "cited": {"title": "DBR", "year": 2003, "authors": ["Collect"]}}),
                                     resolve)
        self.assertEqual(partial["results"][0]["mismatched"], ["first_author"])

    def test_editors_stand_in_for_missing_authors(self):
        meta = rc._crossref_meta({"title": ["Handbook"], "editor": [{"family": "Fincher"}], "issued": {"date-parts": [[2019]]}})
        self.assertEqual(meta["authors"], ["Fincher"])

    def test_fabricated_identifier_is_unresolved(self):
        out = rc.check_citations(refs({"id": "x", "doi": "10.9999/none", "cited": {"title": "Made up", "year": 2024}}), self.resolve)
        self.assertEqual(out["results"][0]["status"], "unresolved")

    def test_network_failure_is_reported_not_raised(self):
        def boom(key):
            raise OSError("offline")
        out = rc.check_citations(refs({"id": "x", "doi": "10.1/good", "cited": {"title": "t", "year": 2000}}), boom)
        self.assertEqual(out["results"][0]["status"], "unresolved")
        self.assertIn("lookup failed", out["results"][0]["reason"])

    def test_invalid_refs_are_rejected(self):
        for bad in ({"references": []}, {"references": [{"id": "a"}]},
                    {"references": [{"id": "a", "cited": {"title": "t", "year": "2020"}}]}, {}):
            with self.assertRaises(rc.InputError):
                rc.check_citations(bad, self.resolve)

    def test_offline_cli_and_record_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            res, ref, rec = (os.path.join(d, n) for n in ("res.json", "refs.json", "rec.json"))
            json.dump(RESOLVER, open(res, "w"))
            json.dump(refs({"id": "a", "doi": "10.1/good", "cited": {"title": "Computational thinking in K-12", "year": 2013,
                                                                       "authors": ["Grover"]}}), open(ref, "w"))
            code, out = run_cli(["citations", ref, "--offline", res, "--record", rec])
            self.assertEqual(code, 0, out)
            self.assertIn("doi:10.1/good", json.load(open(rec))["entries"])
            code2, _ = run_cli(["citations", ref, "--offline", rec])
            self.assertEqual(code2, 0)


class CliTest(unittest.TestCase):
    def test_unreadable_and_non_object_input_exit_2(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, "x.json")
            open(p, "w").write("[1, 2]")
            self.assertEqual(run_cli(["claims", p])[0], 2)
            self.assertEqual(run_cli(["claims", os.path.join(d, "missing.json")])[0], 2)
            open(p, "w").write("{not json")
            self.assertEqual(run_cli(["design", p])[0], 2)

    def test_usage_error_exit_2(self):
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(run_cli(["nonsense"])[0], 2)

    def test_bad_offline_resolver_shape_exit_2(self):
        with tempfile.TemporaryDirectory() as d:
            res, ref = os.path.join(d, "r.json"), os.path.join(d, "f.json")
            json.dump({"nope": 1}, open(res, "w"))
            json.dump(refs({"id": "a", "doi": "10.1/x", "cited": {"title": "t", "year": 2000}}), open(ref, "w"))
            self.assertEqual(run_cli(["citations", ref, "--offline", res])[0], 2)


if __name__ == "__main__":
    unittest.main()
