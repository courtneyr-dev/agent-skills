import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import agreement  # noqa: E402

# Test vectors only: in-memory numbers that exercise the arithmetic. They are not observations of any reviewer.


def doc_from_pairs(pairs, scale, source="human-rated", label="test vector", raters=("human:r1", "human:r2")):
    ratings = []
    for n, (a, b) in enumerate(pairs):
        ratings.append({"item": "i%d" % n, "rater": raters[0], "score": a, "source": source})
        ratings.append({"item": "i%d" % n, "rater": raters[1], "score": b, "source": source})
    return {"label": label, "scale": scale, "ratings": ratings}


def disagreement_weighted_kappa(pairs, scale):
    """Independent formula: 1 - sum(v*O) / sum(v*E) with v = (i-j)^2."""
    k, n = len(scale), len(pairs)
    idx = {v: i for i, v in enumerate(scale)}
    obs = [[0] * k for _ in range(k)]
    for a, b in pairs:
        obs[idx[a]][idx[b]] += 1
    row = [sum(obs[i]) for i in range(k)]
    col = [sum(obs[i][j] for i in range(k)) for j in range(k)]
    num = sum((i - j) ** 2 * obs[i][j] for i in range(k) for j in range(k))
    den = sum((i - j) ** 2 * row[i] * col[j] / n for i in range(k) for j in range(k))
    return 1 - num / den


def run_cli(obj):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        fh.write(obj if isinstance(obj, str) else json.dumps(obj))
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            code = agreement.main(["stats", fh.name])
    finally:
        os.unlink(fh.name)
    return code, json.loads(buf.getvalue())


class ComputedTests(unittest.TestCase):
    def test_textbook_binary_example_gives_kappa_0_4(self):
        pairs = [("y", "y")] * 20 + [("y", "n")] * 5 + [("n", "y")] * 10 + [("n", "n")] * 15
        code, out = run_cli(doc_from_pairs(pairs, ["n", "y"]))
        self.assertEqual(code, 0)
        p = out["pairs"][0]
        self.assertEqual(p["n_items"], 50)
        self.assertAlmostEqual(p["exact_agreement"], 0.7)
        self.assertAlmostEqual(p["kappa"], 0.4)
        self.assertAlmostEqual(p["weighted_kappa_quadratic"], 0.4)

    def test_quadratic_weighting_matches_independent_formula(self):
        pairs = [(0, 0), (1, 1), (2, 3), (3, 3), (1, 2), (0, 1), (2, 2), (3, 2), (1, 1), (0, 0), (2, 1), (3, 3)]
        out = agreement.stats(doc_from_pairs(pairs, [0, 1, 2, 3]))
        p = out["pairs"][0]
        self.assertAlmostEqual(p["weighted_kappa_quadratic"], round(disagreement_weighted_kappa(pairs, [0, 1, 2, 3]), 4))
        self.assertAlmostEqual(p["adjacent_agreement"], 1.0)
        self.assertEqual(p["notes"], [])

    def test_perfect_agreement_is_one(self):
        out = agreement.stats(doc_from_pairs([(0, 0), (1, 1), (2, 2)], [0, 1, 2]))
        self.assertEqual(out["pairs"][0]["kappa"], 1.0)
        self.assertIn("fewer than 10", out["pairs"][0]["notes"][0])

    def test_single_level_used_reports_undefined_kappa(self):
        out = agreement.stats(doc_from_pairs([(1, 1), (1, 1)], [0, 1]))
        self.assertIsNone(out["pairs"][0]["kappa"])
        self.assertIn("undefined", out["pairs"][0]["notes"][0])

    def test_three_raters_give_three_pairs(self):
        d = doc_from_pairs([(0, 1), (1, 1)], [0, 1])
        d["ratings"] += [{"item": "i0", "rater": "human:r3", "score": 0, "source": "human-rated"},
                         {"item": "i1", "rater": "human:r3", "score": 1, "source": "human-rated"}]
        self.assertEqual(len(agreement.stats(d)["pairs"]), 3)


class PracticeOnlyTests(unittest.TestCase):
    def test_generated_ratings_claim_no_agreement(self):
        code, out = run_cli(doc_from_pairs([(0, 1), (1, 1), (2, 2)], [0, 1, 2], source="generated"))
        self.assertEqual(code, 1)
        self.assertEqual(out["status"], "practice-only")
        self.assertNotIn("pairs", out)
        self.assertEqual(out["discussion"][0]["item"], "i0")

    def test_synthetic_label_blocks_agreement_even_when_sources_say_human(self):
        out = agreement.stats(doc_from_pairs([(0, 0), (1, 1)], [0, 1], label="SYNTHETIC FIXTURE (Fixture Co)"))
        self.assertEqual(out["status"], "practice-only")

    def test_non_human_rater_blocks_agreement(self):
        out = agreement.stats(doc_from_pairs([(0, 0), (1, 1)], [0, 1], raters=("model:a", "human:r2")))
        self.assertIn("not human", out["reasons"][0])

    def test_anchor_mismatch_is_listed_for_discussion(self):
        d = doc_from_pairs([(1, 1)], [0, 1, 2], source="generated")
        d["anchors"] = {"i0": 2}
        self.assertEqual(agreement.stats(d)["discussion"][0]["anchor"], 2)


class InvalidInputTests(unittest.TestCase):
    def assertInvalid(self, obj):
        code, out = run_cli(obj)
        self.assertEqual(code, 2, out)
        self.assertEqual(out["status"], "invalid-input")

    def test_not_json(self):
        self.assertInvalid("[")

    def test_score_off_scale(self):
        self.assertInvalid(doc_from_pairs([(0, 5)], [0, 1, 2]))

    def test_boolean_and_float_scores_rejected(self):
        self.assertInvalid(doc_from_pairs([(True, 1)], [0, 1]))
        self.assertInvalid(doc_from_pairs([(1.0, 1)], [0, 1]))

    def test_duplicate_rating(self):
        d = doc_from_pairs([(0, 1)], [0, 1])
        d["ratings"].append(dict(d["ratings"][0]))
        self.assertInvalid(d)

    def test_one_rater(self):
        self.assertInvalid({"scale": [0, 1], "ratings": [{"item": "a", "rater": "human:r1", "score": 0, "source": "human-rated"}]})

    def test_duplicate_scale_levels(self):
        self.assertInvalid(doc_from_pairs([(0, 0)], [0, 0, 1]))

    def test_no_shared_items(self):
        self.assertInvalid({"scale": [0, 1], "ratings": [
            {"item": "a", "rater": "human:r1", "score": 0, "source": "human-rated"},
            {"item": "b", "rater": "human:r2", "score": 1, "source": "human-rated"}]})

    def test_usage(self):
        self.assertEqual(agreement.main([]), 2)


if __name__ == "__main__":
    unittest.main()
