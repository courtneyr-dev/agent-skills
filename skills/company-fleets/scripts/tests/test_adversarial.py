"""The shared adversarial pack: probes hold on a sound gate and name each hole cut into a copy."""
import json
import os
import shutil
import subprocess
import tempfile
import unittest

from support import FIXTURES, SKILL

from factory_rig.canon import sha_file
from fleetlib import adversarial
from fleetlib.adversarial import TransformError, address_variant, apply
from fleetlib.handoff import evidence_errors, key_for, validate_handoff

TOY = os.path.join(FIXTURES, "adversarial", "toy-gate")
RIG_SKILLS = os.path.dirname(SKILL)


def holes(result):
    return {p["name"] for p in result["probes"] if p["result"] == "hole"}


class ToyGate(unittest.TestCase):
    def copy_with(self, tmp, *cuts):
        dst = os.path.join(tmp, "toy-gate")
        shutil.copytree(TOY, dst)
        path = os.path.join(dst, "gate.py")
        src = open(path).read()
        for old, new in cuts:
            self.assertIn(old, src, "the toy gate no longer contains the line this test cuts")
            src = src.replace(old, new, 1)
        open(path, "w").write(src)
        return dst

    def test_every_probe_holds_on_the_sound_gate(self):
        r = adversarial.run(TOY)
        self.assertTrue(r["ok"], r)
        self.assertEqual(r["counts"]["held"], 10)

    def test_each_known_hole_is_named_and_nothing_else_moves(self):
        cuts = {
            "approval binding removed": ([('if approval.get("subject_sha256") != canon(bound):', "if False:")],
                                         {"relabel-kind-after-approval", "grow-audience-after-approval"}),
            "zero-width folding and row validation removed": ([('addr = addr.replace("\\u200b", "")', "addr = addr"),
                                                              ("if not EMAIL.match(addr):", "if False:")], {"suppression-zero-width"}),
            "path confinement removed": ([("if not path.startswith(base + os.sep):", "if False:")], {"evidence-outside-base"}),
            "owner threshold removed": ([('not policy["min_amount"] <= amount <= policy["max_amount"]', "False")], {"negative-amount"}),
            "principal anchor removed": ([('(?:-[a-z]+)*)$")', '(?:-[a-z]+)*)")')], {"pad-acceptor"}),
        }
        for label, (cut, expected) in cuts.items():
            with self.subTest(label), tempfile.TemporaryDirectory() as tmp:
                r = adversarial.run(self.copy_with(tmp, *cut))
                self.assertFalse(r["ok"])
                self.assertEqual(holes(r), expected)

    def test_a_probe_cannot_pass_by_testing_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            dst = os.path.join(tmp, "toy-gate")
            shutil.copytree(TOY, dst)
            decl = json.load(open(os.path.join(dst, "evals", "adversarial.json")))
            decl["accepted_when"] = {"exit": [0], "contains": ["text the gate never prints"]}
            json.dump(decl, open(os.path.join(dst, "evals", "adversarial.json"), "w"))
            r = adversarial.run(dst)
        self.assertFalse(r["ok"])
        self.assertEqual(r["counts"]["bad-baseline"], 10)

    def test_declarations_are_checked_before_anything_runs(self):
        with tempfile.TemporaryDirectory() as tmp:
            dst = os.path.join(tmp, "toy-gate")
            shutil.copytree(TOY, dst)
            path = os.path.join(dst, "evals", "adversarial.json")
            decl = json.load(open(path))
            decl["probes"][0]["transforms"] = [{"op": "teleport", "file": "inputs/request.json"}]
            decl["probes"][1]["transforms"] = [{"op": "relabel", "file": "inputs/request.json", "pointer": "/kind"}]
            json.dump(decl, open(path, "w"))
            r = adversarial.run(dst)
        self.assertFalse(r["ok"])
        self.assertTrue(any("teleport" in e or "must be one of" in e for e in r["errors"]), r["errors"])
        self.assertTrue(any("relabel needs value" in e for e in r["errors"]), r["errors"])

    def test_cli_exit_codes(self):
        base = [os.path.join(SKILL, "bin", "fleet"), "--skills-root", os.path.join(FIXTURES, "adversarial")]
        self.assertEqual(subprocess.run(base + ["adversarial", "--skill", "toy-gate"], capture_output=True, timeout=300).returncode, 0)
        with tempfile.TemporaryDirectory() as tmp:
            self.copy_with(tmp, ("if not path.startswith(base + os.sep):", "if False:"))
            p = subprocess.run([base[0], "--skills-root", tmp, "adversarial", "--skill", "toy-gate"], capture_output=True, text=True, timeout=300)
        self.assertEqual(p.returncode, 1)
        self.assertEqual(holes(json.loads(p.stdout)), {"evidence-outside-base"})


class RealGateCopy(unittest.TestCase):
    """corporate-email-guard with its plus-tag folding reverted: the pack must name the reopened hole. The suppression
    list itself comes from the owner ledger, so the probes vary only what the caller supplies."""

    CUTS = (('    local = local.split("+", 1)[0]\n', ''),)

    def test_pack_finds_the_reverted_fix(self):
        src = os.path.join(RIG_SKILLS, "corporate-email-guard")
        if not os.path.isfile(os.path.join(src, "evals", "adversarial.json")):
            self.skipTest("corporate-email-guard has no adversarial.json")
        code = open(os.path.join(src, "scripts", "email_guard.py")).read()
        if not all(old in code for old, _ in self.CUTS):
            self.skipTest("email_guard.py changed; update the lines this test reverts")
        for old, new in self.CUTS:
            code = code.replace(old, new, 1)
        with tempfile.TemporaryDirectory() as tmp:
            dst = os.path.join(tmp, "corporate-email-guard")
            shutil.copytree(src, dst, ignore=shutil.ignore_patterns("__pycache__"))
            for sibling in ("company-fleets", "factory-rig"):  # the guard reads its owner ledger through company-fleets
                os.symlink(os.path.join(RIG_SKILLS, sibling), os.path.join(tmp, sibling))
            open(os.path.join(dst, "scripts", "email_guard.py"), "w").write(code)
            r = adversarial.run(dst)
        self.assertFalse(r["ok"])
        self.assertEqual(holes(r), {"contact-plus-tag"})


class Transforms(unittest.TestCase):
    def test_address_variants(self):
        self.assertEqual(address_variant("dee@example.com", "plus-tag"), "dee+probe@example.com")
        self.assertEqual(address_variant("dee@example.com", "trailing-dot"), "dee@example.com.")
        self.assertEqual(address_variant("dee@example.com", "zero-width"), "dee@example.com​")
        self.assertEqual(address_variant("dee@example.com", "gmail-dot"), "d.ee@example.com")

    def test_header_flip_number_edges_and_missing_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            open(os.path.join(tmp, "ar.po"), "w").write('msgid ""\nmsgstr ""\n"Language: ar\\n"\n"Plural-Forms: nplurals=6;\\n"\n')
            apply(tmp, {"op": "header-flip", "file": "ar.po", "header": "Language", "value": "en"})
            self.assertIn('"Language: en\\n"', open(os.path.join(tmp, "ar.po")).read())
            json.dump({"hours": 40, "floor": 0.35}, open(os.path.join(tmp, "b.json"), "w"))
            for variant, want in (("negative", -40), ("zero", 0), ("empty", ""), ("null", None)):
                json.dump({"hours": 40}, open(os.path.join(tmp, "b.json"), "w"))
                apply(tmp, {"op": "number-edge", "file": "b.json", "pointer": "/hours", "variant": variant})
                self.assertEqual(json.load(open(os.path.join(tmp, "b.json")))["hours"], want)
            with self.assertRaises(TransformError):
                apply(tmp, {"op": "header-flip", "file": "ar.po", "header": "Content-Type", "value": "x"})
            with self.assertRaises(TransformError):
                apply(tmp, {"op": "json-delete", "file": "b.json", "pointer": "/missing/deeper"})

    def test_rehash_handoff_is_the_review_attack_and_the_gate_still_refuses(self):
        with tempfile.TemporaryDirectory() as tmp:
            shutil.copytree(os.path.join(FIXTURES, "handoff"), os.path.join(tmp, "h"))
            ws = os.path.join(tmp, "h", "workspace")
            owner = json.load(open(os.path.join(tmp, "h", "owner.json")))
            out = "out/accessibility-findings.md"
            from fleetlib.handoff import apply_worker_update, open_handoff
            h, _ = apply_worker_update(open_handoff(owner), {
                "outputs": [{"path": out, "sha256": sha_file(os.path.join(ws, out)), "artifact_type": "defect-list"}],
                "evidence": [{"path": "evidence/review.txt", "sha256": sha_file(os.path.join(ws, "evidence/review.txt")), "about": out,
                              "about_sha256": sha_file(os.path.join(ws, out)), "contract_hash": owner["contract_hash"]}]})
            json.dump(h, open(os.path.join(tmp, "h", "handoff.json"), "w"))
            open(os.path.join(ws, out), "w").write("No defects found.\n")
            apply(os.path.join(tmp, "h"), {"op": "rehash-handoff", "file": "handoff.json", "base": "workspace", "outputs": [out]})
            forged = json.load(open(os.path.join(tmp, "h", "handoff.json")))
            contract = json.load(open(os.path.join(tmp, "h", "contract.json")))
            self.assertEqual(forged["idempotency_key"], key_for(forged))
            self.assertEqual(validate_handoff(forged), [])
            self.assertTrue(any("does not name the output hash it reviewed" in e for e in evidence_errors(forged, contract, ws)))


if __name__ == "__main__":
    unittest.main()
