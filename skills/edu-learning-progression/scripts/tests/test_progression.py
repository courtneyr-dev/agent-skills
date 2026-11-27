import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "progression.py")
sys.path.insert(0, os.path.join(HERE, ".."))
import progression  # noqa: E402

GRAPH = {
    "label": "SYNTHETIC test graph",
    "concepts": [
        {"id": "variables", "band": "6-8", "prior": True, "prereqs": []},
        {"id": "loops", "band": "6-8", "prereqs": ["variables"], "assessed_by": ["a"]},
        {"id": "lists", "band": "9-10", "prereqs": ["variables"], "assessed_by": ["b"]},
        {"id": "traversal", "band": "9-10", "prereqs": ["loops", "lists"], "assessed_by": ["c"]},
        {"id": "big-o", "band": "university", "prereqs": ["traversal"], "assessed_by": ["d"],
         "bridge": "optional grade 12 extension comparing step counts"},
    ],
    "sequence": [
        {"unit": "U1", "grade": 9, "concepts": ["loops", "lists", "traversal"]},
        {"unit": "U2", "grade": 12, "concepts": ["big-o"]},
    ],
}


def run_cli(*args):
    proc = subprocess.run([sys.executable, SCRIPT] + list(args), capture_output=True, text=True, timeout=60)
    return proc.returncode, proc.stdout


class CheckTests(unittest.TestCase):
    def test_valid_graph_has_prerequisite_order(self):
        r = progression.check(copy.deepcopy(GRAPH))
        self.assertTrue(r["ok"], r["errors"])
        order = r["order"]
        for c in GRAPH["concepts"]:
            for p in c["prereqs"]:
                self.assertLess(order.index(p), order.index(c["id"]))

    def test_cycle_is_an_error_and_no_order(self):
        g = copy.deepcopy(GRAPH)
        g["concepts"][1]["prereqs"] = ["variables", "traversal"]
        r = progression.check(g)
        self.assertFalse(r["ok"])
        self.assertIsNone(r["order"])
        self.assertTrue(any("cycle" in e and "loops" in e for e in r["errors"]))

    def test_university_concept_in_k12_without_bridge(self):
        g = copy.deepcopy(GRAPH)
        del g["concepts"][4]["bridge"]
        r = progression.check(g)
        self.assertTrue(any("big-o (band university)" in e and "without a bridge" in e for e in r["errors"]))

    def test_upper_band_concept_in_lower_grade_without_bridge(self):
        g = copy.deepcopy(GRAPH)
        g["concepts"][3]["band"] = "11-12"
        r = progression.check(g)
        self.assertTrue(any("traversal (band 11-12)" in e for e in r["errors"]))

    def test_sequenced_before_prerequisite(self):
        g = copy.deepcopy(GRAPH)
        g["sequence"][0]["concepts"] = ["traversal", "loops", "lists"]
        r = progression.check(g)
        self.assertIn("traversal comes before its prerequisite loops in the sequence", r["errors"])

    def test_unassessed_is_flagged_as_warning_only(self):
        g = copy.deepcopy(GRAPH)
        g["concepts"][2]["assessed_by"] = []
        r = progression.check(g)
        self.assertTrue(r["ok"])
        self.assertEqual(r["unassessed"], ["lists"])

    def test_unknown_duplicate_and_unsequenced(self):
        g = copy.deepcopy(GRAPH)
        g["concepts"][2]["prereqs"] = ["ghost"]
        g["concepts"].append({"id": "loops", "band": "6-8", "prereqs": []})
        g["concepts"].append({"id": "orphan", "band": "9-10", "prereqs": [], "assessed_by": ["e"]})
        g["sequence"][1]["concepts"].append("loops")
        errors = progression.check(g)["errors"]
        self.assertIn("lists names unknown prerequisite ghost", errors)
        self.assertIn("duplicate concept loops", errors)
        self.assertIn("concept orphan is neither sequenced nor marked prior", errors)
        self.assertIn("concept loops is placed twice", errors)


class InvalidInputTests(unittest.TestCase):
    def test_invalid_shapes_raise(self):
        for bad in ([], {"concepts": []}, {"concepts": [{"band": "9-10"}], "sequence": []},
                    {"concepts": [{"id": "a", "band": "high school"}], "sequence": []},
                    {"concepts": [{"id": "a", "band": "9-10"}], "sequence": [{"unit": "U1", "grade": "ninth", "concepts": ["a"]}]}):
            with self.assertRaises(progression.Invalid):
                progression.check(bad)

    def test_cli_exit_codes(self):
        with tempfile.TemporaryDirectory() as tmp:
            ok = os.path.join(tmp, "ok.json")
            with open(ok, "w") as fh:
                json.dump(GRAPH, fh)
            bad = os.path.join(tmp, "bad.json")
            with open(bad, "w") as fh:
                fh.write("{oops")
            self.assertEqual(run_cli("check", ok)[0], 0)
            self.assertEqual(run_cli("check", bad)[0], 2)
            self.assertEqual(run_cli("check")[0], 2)
            self.assertEqual(run_cli("lint", ok)[0], 2)
            broken = copy.deepcopy(GRAPH)
            del broken["concepts"][4]["bridge"]
            with open(ok, "w") as fh:
                json.dump(broken, fh)
            self.assertEqual(run_cli("check", ok)[0], 1)


if __name__ == "__main__":
    unittest.main()
