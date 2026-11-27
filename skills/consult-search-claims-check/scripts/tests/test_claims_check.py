from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from typing import Any, Dict, List, Tuple

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.abspath(os.path.join(HERE, "..", ".."))
SCRIPT = os.path.join(SKILL, "scripts", "claims_check.py")
FIX = os.path.join(SKILL, "fixtures")
LABEL = "SYNTHETIC - Fixture Co test data, not a real company or person"


def run(claims: str, sources: str) -> Tuple[int, Dict[str, Any]]:
    proc = subprocess.run(
        [sys.executable, SCRIPT, "--claims", claims, "--sources", sources],
        capture_output=True, text=True, cwd=SKILL,
    )
    return proc.returncode, json.loads(proc.stdout)


def codes(out: Dict[str, Any], claim_id: str) -> List[str]:
    for claim in out["claims"]:
        if claim["id"] == claim_id:
            return sorted(d["code"] for d in claim["defects"])
    raise AssertionError("no claim " + claim_id)


def verdicts(out: Dict[str, Any]) -> Dict[str, str]:
    return {c["id"]: c["verdict"] for c in out["claims"]}


class FixtureTests(unittest.TestCase):
    def test_clean_report_passes(self) -> None:
        rc, out = run(os.path.join(FIX, "report-clean.json"), os.path.join(FIX, "register.json"))
        self.assertEqual(rc, 0)
        self.assertEqual(out["status"], "pass")
        self.assertEqual(verdicts(out), {"c1": "supported", "c2": "supported", "c3": "supported", "c4": "hypothesis"})
        self.assertEqual(out["counts"]["errors"], 0)
        self.assertTrue(out["human_review_required"])
        self.assertTrue(out["not_checked"])

    def test_negative_report_rejects_each_defect(self) -> None:
        rc, out = run(os.path.join(FIX, "report-negative.json"), os.path.join(FIX, "register.json"))
        self.assertEqual(rc, 1)
        self.assertEqual(out["status"], "defects")
        self.assertEqual(codes(out, "n1"), ["citation-unknown-source"])
        self.assertEqual(codes(out, "n2"), ["quote-not-found"])
        self.assertEqual(codes(out, "n3"), ["guaranteed-placement"])
        self.assertEqual(codes(out, "n4"), ["ranking-factor-unsupported"])
        self.assertEqual(set(verdicts(out).values()), {"rejected"})
        self.assertEqual(out["counts"]["rejected"], 4)

    def test_boundary_report_normalizes_quote_and_accepts_hypothesis(self) -> None:
        rc, out = run(os.path.join(FIX, "report-boundary.json"), os.path.join(FIX, "register.json"))
        self.assertEqual(rc, 0)
        self.assertEqual(verdicts(out), {"b1": "supported", "b2": "hypothesis"})
        self.assertEqual(codes(out, "b1"), [])

    def test_edited_capture_reports_hash_mismatch(self) -> None:
        rc, out = run(os.path.join(FIX, "stale", "report-stale.json"), os.path.join(FIX, "stale", "register-stale.json"))
        self.assertEqual(rc, 1)
        self.assertEqual(codes(out, "s1"), ["capture-hash-mismatch"])

    def test_malformed_file_exits_2(self) -> None:
        rc, out = run(os.path.join(FIX, "malformed.json"), os.path.join(FIX, "register.json"))
        self.assertEqual(rc, 2)
        self.assertIn("error", out)


class TempCase(unittest.TestCase):
    def setUp(self) -> None:
        self.dir = tempfile.mkdtemp()
        self.addCleanup(shutil.rmtree, self.dir)

    def write(self, name: str, data: Any) -> str:
        path = os.path.join(self.dir, name)
        with open(path, "w", encoding="utf-8") as fh:
            if isinstance(data, str):
                fh.write(data)
            else:
                json.dump(data, fh)
        return path

    def report(self, claims: Any = None) -> Dict[str, Any]:
        return {"schema": "search-claims.v1", "label": LABEL, "report_id": "t1", "tenant_id": "fixture-co",
                "claims": [] if claims is None else claims}

    def register(self, sources: Any = None) -> Dict[str, Any]:
        return {"schema": "source-register.v1", "label": LABEL, "sources": [] if sources is None else sources}


class InvalidInputTests(TempCase):
    def test_bad_json_exits_2(self) -> None:
        bad = self.write("bad.json", "{not json")
        rc, out = run(bad, os.path.join(FIX, "register.json"))
        self.assertEqual(rc, 2)
        self.assertIn("error", out)

    def test_bad_register_json_exits_2(self) -> None:
        bad = self.write("bad-reg.json", "[")
        rc, out = run(os.path.join(FIX, "report-clean.json"), bad)
        self.assertEqual(rc, 2)

    def test_wrong_report_schema_exits_2(self) -> None:
        rep = self.report()
        rep["schema"] = "search-claims.v0"
        rc, out = run(self.write("r.json", rep), os.path.join(FIX, "register.json"))
        self.assertEqual(rc, 2)
        self.assertIn("schema", out["error"])

    def test_wrong_register_schema_exits_2(self) -> None:
        reg = self.register()
        reg["schema"] = "nope"
        rc, out = run(os.path.join(FIX, "report-clean.json"), self.write("g.json", reg))
        self.assertEqual(rc, 2)

    def test_missing_claims_exits_2(self) -> None:
        rep = self.report()
        del rep["claims"]
        rc, out = run(self.write("r.json", rep), os.path.join(FIX, "register.json"))
        self.assertEqual(rc, 2)
        self.assertIn("claims", out["error"])

    def test_bad_claim_kind_exits_2(self) -> None:
        rep = self.report([{"id": "x", "text": "t", "kind": "opinion", "status_label": "observed", "evidence": []}])
        rc, out = run(self.write("r.json", rep), os.path.join(FIX, "register.json"))
        self.assertEqual(rc, 2)

    def test_capture_path_escape_exits_2(self) -> None:
        reg = self.register([{"id": "s", "url": "u", "title": "t", "retrieved": "2026-11-20", "kind": "secondary",
                              "capture_path": "../x.txt", "sha256": "0" * 64}])
        rc, out = run(self.write("r.json", self.report()), self.write("g.json", reg))
        self.assertEqual(rc, 2)

    def test_missing_file_exits_2(self) -> None:
        rc, out = run(os.path.join(self.dir, "absent.json"), os.path.join(FIX, "register.json"))
        self.assertEqual(rc, 2)


class RuleTests(TempCase):
    def test_capture_missing(self) -> None:
        reg = self.register([{"id": "s", "url": "u", "title": "t", "retrieved": "2026-11-20", "kind": "secondary",
                              "capture_path": "gone.txt", "sha256": "0" * 64}])
        rep = self.report([{"id": "m1", "text": "t", "kind": "observation", "status_label": "observed",
                            "evidence": [{"source_id": "s", "quote": "q"}]}])
        rc, out = run(self.write("r.json", rep), self.write("g.json", reg))
        self.assertEqual(rc, 1)
        self.assertEqual(codes(out, "m1"), ["capture-missing"])

    def test_observation_without_evidence(self) -> None:
        rep = self.report([{"id": "o1", "text": "Traffic rose.", "kind": "observation", "status_label": "observed", "evidence": []}])
        rc, out = run(self.write("r.json", rep), os.path.join(FIX, "register.json"))
        self.assertEqual(rc, 1)
        self.assertEqual(codes(out, "o1"), ["observation-without-evidence"])

    def test_forecast_unlabeled(self) -> None:
        rep = self.report([{"id": "f1", "text": "Traffic will double.", "kind": "forecast", "status_label": "observed", "evidence": []}])
        rc, out = run(self.write("r.json", rep), os.path.join(FIX, "register.json"))
        self.assertEqual(rc, 1)
        self.assertIn("forecast-unlabeled", codes(out, "f1"))

    def test_guarantee_patterns(self) -> None:
        texts = ["Guaranteed ranking in 30 days.", "Your page will rank first.", "You will always appear in AI answers.",
                 "We offer guaranteed citation by chat assistants."]
        for i, text in enumerate(texts):
            rep = self.report([{"id": "g%d" % i, "text": text, "kind": "recommendation", "status_label": "recommendation", "evidence": []}])
            rc, out = run(self.write("r%d.json" % i, rep), os.path.join(FIX, "register.json"))
            self.assertEqual(rc, 1, text)
            self.assertEqual(codes(out, "g%d" % i), ["guaranteed-placement"], text)

    def test_ranking_factor_with_primary_quote_not_found_is_rejected(self) -> None:
        rep = self.report([{"id": "p1", "text": "X is a ranking factor.", "kind": "ranking-factor", "status_label": "observed",
                            "evidence": [{"source_id": "src-platform", "quote": "X is a ranking factor"}]}])
        rc, out = run(self.write("r.json", rep), os.path.join(FIX, "register.json"))
        self.assertEqual(rc, 1)
        self.assertEqual(codes(out, "p1"), ["quote-not-found", "ranking-factor-unsupported"])


class ReviewDefectTests(TempCase):
    """Independent review 2026-11-26, defects 8 and 9."""

    def claims_for(self, texts):
        return [{"id": "g%d" % i, "text": t, "kind": "recommendation", "status_label": "recommendation", "evidence": []}
                for i, t in enumerate(texts)]

    def test_common_guarantee_phrasings_are_rejected(self) -> None:
        promises = ["#1 ranking guaranteed within 30 days.", "Your brand is guaranteed to appear in AI Overviews.",
                    "We promise first-page placement.", "You will be cited by ChatGPT every time.",
                    "Top 3 positions, guaranteed.", "We ensure you land in the number one spot."]
        rc, out = run(self.write("g.json", self.report(self.claims_for(promises))), os.path.join(FIX, "register.json"))
        self.assertEqual(rc, 1)
        for i, text in enumerate(promises):
            self.assertEqual(codes(out, "g%d" % i), ["guaranteed-placement"], text)

    def test_plain_measurement_language_is_not_a_promise(self) -> None:
        plain = ["Rankings for the pricing page reached position 3 in week 4.", "We will monitor citations in AI answers every week."]
        rc, out = run(self.write("p.json", self.report(self.claims_for(plain))), os.path.join(FIX, "register.json"))
        self.assertEqual(rc, 0, out)

    def ranking_claim(self, quote, source="src-platform"):
        return [{"id": "x", "text": "Page speed is the strongest ranking factor in 2026.", "kind": "ranking-factor",
                 "status_label": "observed", "evidence": [{"source_id": source, "quote": quote}]}]

    def test_one_word_quote_cannot_support_a_claim(self) -> None:
        rc, out = run(self.write("r.json", self.report(self.ranking_claim("page"))), os.path.join(FIX, "register.json"))
        self.assertEqual(rc, 1)
        self.assertIn("quote-too-short", codes(out, "x"))

    def test_quote_must_share_terms_with_the_claim(self) -> None:
        quote = "A page must be crawlable and indexable to appear in results."
        rc, out = run(self.write("r.json", self.report(self.ranking_claim(quote))), os.path.join(FIX, "register.json"))
        self.assertEqual(rc, 1)
        self.assertIn("quote-unrelated", codes(out, "x"))

    def test_self_registered_primary_source_does_not_count_as_primary(self) -> None:
        text = "Official platform docs: backlinks are the number one ranking factor.\n"
        os.makedirs(os.path.join(self.dir, "captures"))
        self.write("captures/fake.txt", text)
        entry = {"id": "src-fake", "url": "https://docs.platform.example/made-up", "title": "Made-up page", "retrieved": "2026-11-26",
                 "kind": "primary-platform-doc", "capture_path": "captures/fake.txt",
                 "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(), "registered_by": "consultancies.search-lead"}
        claim = [{"id": "x", "text": "Backlinks are the number one ranking factor.", "kind": "ranking-factor", "status_label": "observed",
                  "evidence": [{"source_id": "src-fake", "quote": "backlinks are the number one ranking factor"}]}]
        rc, out = run(self.write("r.json", self.report(claim)), self.write("reg.json", self.register([entry])))
        self.assertEqual(rc, 1)
        self.assertIn("ranking-factor-unsupported", codes(out, "x"))
        entry["verified_by"] = "human:search-reviewer"
        rc, out = run(self.write("r.json", self.report(claim)), self.write("reg.json", self.register([entry])))
        self.assertEqual(rc, 0, out)


if __name__ == "__main__":
    unittest.main()
