"""Behavior tests for resolve_adapter.py. A temporary home holds fake skill mounts, so presence is deterministic."""
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.normpath(os.path.join(HERE, "..", "resolve_adapter.py"))
SKILL = os.path.normpath(os.path.join(HERE, "..", ".."))
FIX = os.path.join(SKILL, "fixtures")
REGISTER = os.path.join(SKILL, "references", "adapters.json")


def run(*args):
    p = subprocess.run([sys.executable, SCRIPT] + list(args), capture_output=True, text=True)
    return p.returncode, json.loads(p.stdout)


class ResolveTests(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp(prefix="adapters-home-")
        with open(REGISTER, encoding="utf-8") as fh:
            reg = json.load(fh)
        for plat in reg["platforms"]:
            for s in plat.get("skills", []) + plat.get("legacy", {}).get("skills", []):
                d = os.path.join(reg["mounts"][s["mount"]].replace("~", self.home, 1), s["id"])
                os.makedirs(d, exist_ok=True)
                open(os.path.join(d, "SKILL.md"), "w").close()

    def tearDown(self):
        shutil.rmtree(self.home)

    def resolve(self, fixture):
        return run("--project", os.path.join(FIX, fixture), "--home", self.home)

    def test_current_wordpress_gets_the_official_skills(self):
        code, out = self.resolve("project-wordpress-current.json")
        self.assertEqual((code, out["decision"]), (0, "supported"))
        ids = [s["id"] for s in out["skills"]]
        self.assertIn("wordpress-router", ids)
        self.assertIn("code-standards-checker", ids)
        self.assertIn("WordPress Coding Standards", out["standards"])

    def test_legacy_wordpress_is_routed_not_assumed(self):
        code, out = self.resolve("project-wordpress-legacy.json")
        self.assertEqual((code, out["decision"]), (1, "legacy"))
        self.assertIn("6.8.3 is below 7.0", out["reason"])
        self.assertEqual([s["id"] for s in out["skills"]], ["wp-project-triage", "code-standards-checker"])

    def test_old_php_alone_triggers_the_legacy_route(self):
        code, out = self.resolve("project-wordpress-old-php.json")
        self.assertEqual((code, out["decision"]), (1, "legacy"))
        self.assertIn("PHP 7.3 is below 7.4.0", out["reason"])

    def test_unstated_range_passes_with_a_warning(self):
        code, out = self.resolve("project-drupal.json")
        self.assertEqual((code, out["decision"]), (0, "range-unstated"))
        self.assertTrue(out["warnings"])

    def test_blocked_platform_names_its_reason(self):
        code, out = self.resolve("project-headless.json")
        self.assertEqual((code, out["decision"]), (1, "blocked"))
        self.assertIn("human CMS specialist", out["reason"])

    def test_unknown_platform_is_not_given_a_generic_adapter(self):
        code, out = self.resolve("project-unknown.json")
        self.assertEqual((code, out["decision"], out["skills"]), (1, "unknown", []))

    def test_missing_adapter_skill_is_reported(self):
        shutil.rmtree(os.path.join(self.home, ".agents", "skills", "wordpress-router"))
        code, out = self.resolve("project-wordpress-current.json")
        self.assertEqual((code, out["decision"]), (1, "adapter-missing"))
        self.assertIn("wordpress-router", out["reason"])

    def test_invalid_version_is_rejected(self):
        code, out = self.resolve("project-invalid.json")
        self.assertEqual(code, 2)
        self.assertIn("version", out["error"])

    def test_register_without_legacy_route_is_rejected(self):
        with open(REGISTER, encoding="utf-8") as fh:
            reg = json.load(fh)
        del reg["platforms"][0]["legacy"]
        bad = os.path.join(self.home, "register.json")
        with open(bad, "w", encoding="utf-8") as fh:
            json.dump(reg, fh)
        code, out = run("--project", os.path.join(FIX, "project-wordpress-current.json"), "--register", bad, "--home", self.home)
        self.assertEqual(code, 2)
        self.assertIn("legacy route", out["error"])


    def test_woocommerce_on_old_wordpress_or_php_takes_the_legacy_route(self):
        code, out = self.resolve("project-woocommerce-legacy-host.json")
        self.assertEqual((code, out["decision"]), (1, "legacy"))
        self.assertIn("wordpress_version 6.1 is below 7.0", out["reason"])
        self.assertIn("PHP 7.0 is below 7.4.0", out["reason"])

    def test_woocommerce_needs_its_wordpress_and_php_versions(self):
        code, out = self.resolve("project-woocommerce-no-host.json")
        self.assertEqual(code, 2)
        self.assertIn("wordpress_version", out["error"])

    def test_woocommerce_on_current_wordpress_keeps_its_own_range_warning(self):
        code, out = self.resolve("project-woocommerce-current.json")
        self.assertEqual((code, out["decision"]), (0, "range-unstated"))

    def test_wordpress_must_report_every_fact_its_minimums_need(self):
        """Re-review finding 12: WordPress with php_version and no version resolved supported."""
        for project, missing in (({"platform": "wordpress", "php_version": "8.2"}, "needs version"),
                                 ({"platform": "wordpress", "version": "7.0"}, "needs php_version")):
            with self.subTest(project=project):
                path = os.path.join(self.home, "p.json")
                with open(path, "w", encoding="utf-8") as fh:
                    json.dump(project, fh)
                code, out = run("--project", path, "--home", self.home)
                self.assertEqual(code, 2)
                self.assertIn(missing, out["error"])

if __name__ == "__main__":
    unittest.main()
