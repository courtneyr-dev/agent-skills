import io
import json
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stdout

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import answer_key as ak  # noqa: E402


def run(doc):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as fh:
        json.dump(doc, fh)
    buf = io.StringIO()
    try:
        with redirect_stdout(buf):
            code = ak.main(["check", fh.name])
    finally:
        os.unlink(fh.name)
    return code, json.loads(buf.getvalue())


def sheet(cells, target, key, **kw):
    return dict({"id": "S", "kind": "spreadsheet", "cells": cells, "target": target, "key": key}, **kw)


class FormulaTests(unittest.TestCase):
    def value(self, formula, cells=None):
        cells = dict(cells or {}, Z1="=" + formula)
        return ak.Sheet(cells).value("Z1")

    def test_precedence_and_left_associative_power(self):
        self.assertEqual(self.value("2+3*4"), 14)
        self.assertEqual(self.value("2^3^2"), 64)
        self.assertEqual(self.value("-2^2"), 4)
        self.assertEqual(self.value("50%*10"), 5)

    def test_ranges_skip_text_and_blanks(self):
        cells = {"A1": "10", "A2": "label", "A3": "", "A4": "=A1*2"}
        self.assertEqual(self.value("SUM(A1:A4)", cells), 30)
        self.assertEqual(self.value("AVERAGE(A1:A4)", cells), 15)
        self.assertEqual(self.value("COUNT(A1:A4)", cells), 2)

    def test_round_half_away_from_zero(self):
        self.assertEqual(self.value("ROUND(2.5,0)"), 3)
        self.assertEqual(self.value("ROUND(-2.5,0)"), -3)
        self.assertEqual(self.value("ROUND(1234.5,-2)"), 1200)

    def test_pmt_and_fv_match_published_formula(self):
        self.assertAlmostEqual(self.value("PMT(0.05/12,60,20000)"), -377.4246, places=3)
        # 100 * ((1 + 0.04/12) ** 24 - 1) / (0.04/12) = 2494.29, worked by hand
        self.assertAlmostEqual(self.value("FV(0.04/12,24,-100)"), 2494.29, places=2)
        self.assertEqual(self.value("PMT(0,10,1000)"), -100)

    def test_if_and_comparison(self):
        self.assertEqual(self.value('IF(A1>=300,"profit","loss")', {"A1": "300"}), "profit")
        self.assertEqual(self.value('IF(A1>=300,"profit","loss")', {"A1": "299"}), "loss")


class CheckTests(unittest.TestCase):
    def test_matching_key_passes(self):
        code, out = run({"items": [sheet({"B2": "450", "B3": "=B2/1.5"}, "B3", 300)]})
        self.assertEqual(code, 0)
        self.assertTrue(out["ok"])

    def test_wrong_key_is_a_mismatch(self):
        code, out = run({"items": [sheet({"B2": "450", "B3": "=B2/2.5"}, "B3", 300)]})
        self.assertEqual(code, 1)
        self.assertEqual(out["items"][0]["key_status"], "mismatch")
        self.assertEqual(out["flagged"], ["S"])

    def test_wrong_submitted_answer_is_flagged_even_when_key_is_right(self):
        item = {"id": "C", "kind": "calc", "expression": "(1200-300)*0.2", "key": 180, "submitted": 240}
        code, out = run({"items": [item]})
        self.assertEqual(code, 1)
        self.assertEqual(out["items"][0]["key_status"], "match")
        self.assertEqual(out["items"][0]["submitted_status"], "mismatch")

    def test_unsupported_function_is_never_passed(self):
        code, out = run({"items": [sheet({"A1": "=VLOOKUP(1,B1:C2,2,FALSE)"}, "A1", 1)]})
        self.assertEqual(code, 1)
        self.assertEqual(out["items"][0]["key_status"], "unsupported")

    def test_circular_reference_and_div_zero_are_errors(self):
        code, out = run({"items": [sheet({"A1": "=A2", "A2": "=A1"}, "A1", 0),
                                   dict(sheet({"A1": "=1/0"}, "A1", 0), id="D")]})
        self.assertEqual(code, 1)
        self.assertEqual([r["key_status"] for r in out["items"]], ["error", "error"])

    def test_sql_unordered_and_ordered(self):
        setup = "CREATE TABLE t (k TEXT, v INT); INSERT INTO t VALUES ('a',1),('b',2);"
        unordered = {"id": "Q", "kind": "sql", "setup": setup, "query": "SELECT k, v FROM t", "key": [["b", 2], ["a", 1]]}
        ordered = dict(unordered, id="O", ordered=True, query="SELECT k, v FROM t ORDER BY k")
        code, out = run({"items": [unordered, ordered]})
        self.assertEqual([r["key_status"] for r in out["items"]], ["match", "mismatch"])
        self.assertEqual(code, 1)

    def test_sql_error_is_reported(self):
        code, out = run({"items": [{"id": "Q", "kind": "sql", "query": "SELECT * FROM missing", "key": []}]})
        self.assertEqual(code, 1)
        self.assertEqual(out["items"][0]["key_status"], "error")

    def test_python_stdout_compared(self):
        good = {"id": "P", "kind": "python", "code": "print(sum(range(1, 4)))", "key": "6"}
        bad = dict(good, id="P2", key="7")
        code, out = run({"items": [good, bad]})
        self.assertEqual([r["key_status"] for r in out["items"]], ["match", "mismatch"])

    def test_python_crash_is_an_error(self):
        code, out = run({"items": [{"id": "P", "kind": "python", "code": "raise SystemExit(3)", "key": ""}]})
        self.assertEqual(out["items"][0]["key_status"], "error")

    def test_calc_cannot_reference_cells(self):
        code, out = run({"items": [{"id": "C", "kind": "calc", "expression": "A1*2", "key": 2}]})
        self.assertEqual(out["items"][0]["key_status"], "error")


class InvalidInputTests(unittest.TestCase):
    def test_rejects_empty_and_malformed(self):
        for doc in ({}, {"items": []}, {"items": "x"}, []):
            code, out = run(doc)
            self.assertEqual(code, 1)
            self.assertEqual(out["status"], "invalid")

    def test_rejects_duplicate_ids_unknown_kind_and_missing_key(self):
        doc = {"items": [{"id": "A", "kind": "calc", "expression": "1", "key": 1},
                         {"id": "A", "kind": "calc", "expression": "1", "key": 1},
                         {"id": "B", "kind": "excel", "key": 1},
                         {"id": "C", "kind": "calc", "expression": "1"},
                         {"id": "D", "kind": "spreadsheet", "cells": [], "target": "A1", "key": 1, "tolerance": -1}]}
        code, out = run(doc)
        self.assertEqual(code, 1)
        text = " ".join(out["errors"])
        for part in ("duplicate item id A", "kind 'excel'", "C has no key", "cells must be an object", "tolerance"):
            self.assertIn(part, text)

    def test_usage_error(self):
        self.assertEqual(ak.main(["run"]), 2)


if __name__ == "__main__":
    unittest.main()
