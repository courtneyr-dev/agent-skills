"""registry/eval-external-needs.json: the public list of eval cases that need upstream skills or local tools."""
import json
import os
import subprocess
import sys
import unittest

from support import SKILL

SCRIPT = os.path.join(SKILL, "scripts", "eval-external-needs.py")


class EvalExternalNeeds(unittest.TestCase):
    def setUp(self):
        with open(os.path.join(SKILL, "registry", "eval-external-needs.json"), encoding="utf-8") as fh:
            self.doc = json.load(fh)

    def test_file_matches_the_registry(self):
        p = subprocess.run([sys.executable, SCRIPT, "--check"], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)

    def test_every_case_names_a_need_and_every_skill_an_owner_repo(self):
        for case_id, need in self.doc["cases"].items():
            self.assertTrue(need["skills"] or need["tools"], case_id)
            for s in need["skills"]:
                self.assertRegex(self.doc["sources"][s], r"^[\w.-]+/[\w.-]+$", s)

if __name__ == "__main__":
    unittest.main()
