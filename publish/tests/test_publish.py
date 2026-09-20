"""Tests for the deterministic publisher. Run: python3 publish/tests/test_publish.py"""
import os, shutil, sys, tempfile, unittest, yaml

HERE = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.dirname(HERE)
ROOT = os.path.dirname(PUB)
sys.path.insert(0, PUB)
import transforms as T
import publish_skills as P

PUBLIC_AUTHORED = ["wiki-cycle", "weekly-site-health-audit", "wiki-memory",
                   "readwise-methods-review", "job-search"]


class Transforms(unittest.TestCase):
    def test_grammar_preserving_pronouns(self):
        for src, want in [("she is done", "you are done"), ("she says hi", "you say hi"),
                          ("she approves it", "you approve it"), ("she decides", "you decide"),
                          ("she tries", "you try"), ("she watches", "you watch"),
                          ("she owns it", "you own it"), ("she stays", "you stay"),
                          ("her vault", "your vault"), ("herself", "yourself")]:
            self.assertEqual(T.second_person_owner(src), want, src)

    def test_no_broken_forms(self):
        import re
        out = T.second_person_owner("she is she says she approves she decides she stays")
        for bad in ["you is", "you says", "you approv", "you decid", "You stays"]:
            self.assertIsNone(re.search(rf"\b{bad}\b", out), f"{bad!r} in {out!r}")

    def test_full_name_before_first_name(self):
        out = T.apply_all("Courtney Robertson's vault", ["full_name_and_agreement", "replace_personal_name"])
        self.assertEqual(out, "the user's vault")
        self.assertNotIn("Robertson", out)

    def test_path_transforms(self):
        self.assertEqual(T.vault_dir_variable("/Users/courtneyrobertson/Documents/2nd Brain/x"), "$VAULT_DIR/x")
        self.assertEqual(T.vault_dir_variable("~/Documents/2nd Brain/x"), "$VAULT_DIR/x")
        self.assertEqual(T.normalize_home_path("/Users/crobertson/x"), "$HOME/x")
        self.assertEqual(T.strip_para_number_prefix("3. Resources/Readwise/"), "Resources/Readwise/")
        self.assertEqual(T.collapse_loop_reports_path("2. Areas/Loop Reports/x"), "Reports/x")

    def test_identifier_transforms(self):
        self.assertEqual(T.genericize_domain("see courtneyr.dev now"), "see example.com now")
        self.assertEqual(T.genericize_identifiers("com.courtneyr.skill-sync"), "com.you.skill-sync")
        self.assertEqual(T.genericize_identifiers("courtneyr-dev/claude-config"), "your-org/claude-config")
        self.assertEqual(T.genericize_personal_site("Robertson's Home"), "a separate personal site")

    def test_unknown_transform_fails_closed(self):
        with self.assertRaises(KeyError):
            T.apply_all("x", ["no_such_transform"])


class PublicAuthoredProtection(unittest.TestCase):
    """The five hand-authored editions must be structurally unreachable by generation."""
    def setUp(self):
        self.pol = P.load_policy()

    def test_all_five_declared_public_authored(self):
        for n in PUBLIC_AUTHORED:
            self.assertEqual(self.pol["skills"][n]["mode"], "public-authored", n)

    def test_never_in_generation_set(self):
        gen = P._generated_names(self.pol)
        for n in PUBLIC_AUTHORED:
            self.assertNotIn(n, gen, f"{n} must never be a generation target")

    def test_assert_writable_refuses_each(self):
        for n in PUBLIC_AUTHORED:
            with self.assertRaises(P.Failure, msg=n):
                P._assert_writable(self.pol, n)

    def test_plan_never_targets_them(self):
        changes, _, _ = P.plan(self.pol)
        for name, *_ in changes:
            self.assertNotIn(name, PUBLIC_AUTHORED)

    def test_job_search_has_no_canonical_and_is_fine(self):
        self.assertEqual(self.pol["skills"]["job-search"]["mode"], "public-authored")
        self.assertFalse(os.path.exists(P.source_path(self.pol, "job-search")))
        _, _, problems = P.plan(self.pol)
        self.assertFalse([p for p in problems if p.startswith("job-search")])

    def test_missing_mode_fails_closed(self):
        with tempfile.NamedTemporaryFile("w", suffix=".yml", delete=False) as f:
            yaml.safe_dump({"version": 1, "canonical_root": "/tmp", "public_root": "skills",
                            "defaults": {"transforms": []},
                            "skills": {"mystery": {}}}, f)
            path = f.name
        with self.assertRaises(P.Failure):
            P.load_policy(path)
        os.unlink(path)


class Gates(unittest.TestCase):
    def setUp(self):
        self.pol = P.load_policy()

    def test_privacy_scan_catches_injected_values(self):
        for bad, _ in [("/Users/courtneyrobertson/x", 1), ("Courtney wrote this", 1),
                       ("api_key: sk-abcdefghijklmnopqrstuvwx", 1),
                       ("-----BEGIN RSA PRIVATE KEY-----", 1), ("2nd Brain", 1)]:
            self.assertTrue(P.privacy_scan(bad, "t"), bad)

    def test_clean_text_passes(self):
        self.assertEqual(P.privacy_scan("Use $VAULT_DIR/Reports/ for output.", "t"), [])

    def test_missing_source_reports_and_does_not_delete(self):
        pol = P.load_policy()
        pol["skills"]["ghost"] = {"mode": "generated", "source": "definitely-not-here"}
        _, _, problems = P.plan(pol)
        self.assertTrue(any(p.startswith("ghost:") for p in problems))
        # the public tree is untouched by planning
        self.assertTrue(os.path.isdir(os.path.join(ROOT, "skills")))

    def test_retirement_is_explicit_not_inferred(self):
        self.assertIn("retired", self.pol)
        self.assertIsInstance(self.pol["retired"], dict)


class DriftDetection(unittest.TestCase):
    def test_check_fails_on_manual_edit(self):
        pol = P.load_policy()
        gen = P._generated_names(pol)
        changes, current, _ = P.plan(pol)
        target = current[0] if current else gen[0]
        pp = P.public_path(pol, target)
        original = open(pp, encoding="utf-8").read()
        try:
            with open(pp, "a", encoding="utf-8") as f:
                f.write("\nMANUALLY EDITED LINE\n")
            changes2, _, _ = P.plan(pol)
            self.assertIn(target, [c[0] for c in changes2], "check must notice a hand edit")
        finally:
            with open(pp, "w", encoding="utf-8") as f:
                f.write(original)
        changes3, _, _ = P.plan(pol)
        self.assertNotIn(target, [c[0] for c in changes3], "restore must clear the drift")


class CISafeVerification(unittest.TestCase):
    """--verify-public must work with NO private canonical sources (the GitHub Actions case)."""
    def setUp(self):
        self.pol = P.load_policy()
        self._orig = os.environ.get("CLAUDE_SKILLS")
        os.environ["CLAUDE_SKILLS"] = "/nonexistent-canonical-root"

    def tearDown(self):
        if self._orig is None:
            os.environ.pop("CLAUDE_SKILLS", None)
        else:
            os.environ["CLAUDE_SKILLS"] = self._orig

    def test_passes_without_canonical_sources(self):
        self.assertEqual(P.cmd_verify_public(self.pol), 0)

    def test_check_still_requires_canonical(self):
        """The strong local check must NOT silently pass when sources are gone."""
        self.assertEqual(P.cmd_check(self.pol), 1)

    def test_lock_excludes_public_authored(self):
        lock = P.read_lock()
        self.assertIsNotNone(lock)
        for n in PUBLIC_AUTHORED:
            self.assertNotIn(n, lock, f"{n} must never be locked as generated output")

    def test_lock_covers_every_generated(self):
        lock = P.read_lock()
        self.assertEqual(sorted(lock), P._generated_names(self.pol))

    def test_detects_hand_edited_generated_file(self):
        target = P._generated_names(self.pol)[0]
        pp = P.public_path(self.pol, target)
        original = open(pp, encoding="utf-8").read()
        try:
            with open(pp, "a", encoding="utf-8") as f:
                f.write("\nHAND EDIT\n")
            self.assertEqual(P.cmd_verify_public(self.pol), 1)
        finally:
            with open(pp, "w", encoding="utf-8") as f:
                f.write(original)
        self.assertEqual(P.cmd_verify_public(self.pol), 0)


class Determinism(unittest.TestCase):
    def test_render_is_stable(self):
        pol = P.load_policy()
        n = P._generated_names(pol)[0]
        self.assertEqual(P.render(pol, n), P.render(pol, n))

    def test_no_timestamps_in_output(self):
        import re
        pol = P.load_policy()
        for n in P._generated_names(pol)[:6]:
            out = P.render(pol, n)
            self.assertIsNone(re.search(r"\b2026-\d\d-\d\d \d\d:\d\d:\d\d\b", out))


if __name__ == "__main__":
    unittest.main(verbosity=2)
