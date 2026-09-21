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


def _canonical_available():
    """The private canonical sources exist only on the maintainer's machine.
    Tests that genuinely need them are skipped elsewhere rather than weakened."""
    pol = P.load_policy()
    root = P.canonical_root(pol)
    return os.path.isdir(root) and any(
        os.path.exists(P.source_path(pol, n)) for n in P._generated_names(pol))


CANONICAL = _canonical_available()
needs_canonical = unittest.skipUnless(
    CANONICAL, "requires the private canonical skill sources (local-only)")


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

    @needs_canonical
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


@needs_canonical
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

    @needs_canonical
    def test_check_still_requires_canonical(self):
        """The strong local check must NOT silently pass when sources are gone."""
        self.assertEqual(P.cmd_check(self.pol), 1)

    def test_lock_excludes_public_authored(self):
        lock = P.read_lock()
        self.assertIsNotNone(lock)
        for n in PUBLIC_AUTHORED:
            self.assertNotIn(n, lock, f"{n} must never be locked as generated output")

    def test_lock_covers_every_generated(self):
        """The lock now keys complete artifacts: <skill>/SKILL.md plus each generated
        supporting file. Public-authored and excluded files must stay absent."""
        lock = P.read_lock()
        self.assertEqual(sorted(k for k in lock if k.endswith("/SKILL.md")),
                         [f"{n}/SKILL.md" for n in P._generated_names(self.pol)])
        for name in P._public_authored_names(self.pol):
            self.assertNotIn(f"{name}/SKILL.md", lock)
        for name in P._generated_names(self.pol):
            for rel, mode in P.supporting_modes(self.pol, name).items():
                key = f"{name}/{rel}"
                if mode == "generated":
                    self.assertIn(key, lock, f"{key} is generated but unlocked")
                else:
                    self.assertNotIn(key, lock, f"{key} is {mode} but hashed in the lock")

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


@needs_canonical
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



class CompleteArtifact(unittest.TestCase):
    """Supporting-file publication, entirely on fixtures -- no private canonical sources.

    A generated skill is a DIRECTORY. Before this, only SKILL.md was deterministic, so a
    supporting script could drift or a private file could appear next to it unnoticed.
    """

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="artifact-")
        self.canon = os.path.join(self.tmp, "canonical")
        self.pub = os.path.join(self.tmp, "public")
        os.makedirs(self.canon); os.makedirs(self.pub)
        self._root = P.ROOT; self._lock = P.LOCK
        P.ROOT = self.tmp
        P.LOCK = os.path.join(self.tmp, "generated.lock")

    def tearDown(self):
        P.ROOT = self._root; P.LOCK = self._lock
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, base, skill, rel, body, ex=False):
        p = os.path.join(base, skill, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as fh:
            fh.write(body)
        if ex:
            os.chmod(p, os.stat(p).st_mode | 0o111)
        return p

    def policy(self, files, skill="demo"):
        return {"version": 1, "canonical_root": self.canon, "public_root": "public",
                "defaults": {"transforms": [], "supporting_files":
                             {"undeclared_canonical": "excluded", "undeclared_public": "blocked"}},
                "skills": {skill: {"mode": "generated", "source": skill, "files": files}},
                "retired": {}}

    def verbs(self, pol):
        facts, problems = P.file_plan(pol)
        return {f"{n}/{rel}": v for v, n, rel, *_ in facts}, problems

    # 1 + 12
    def test_generated_supporting_file_publishes_and_locks(self):
        self.write(self.canon, "demo", "SKILL.md", "---\nname: demo\ndescription: d\n---\n")
        self.write(self.canon, "demo", "scripts/run.py", "print(1)\n")
        pol = self.policy({"scripts/run.py": "generated"})
        v, probs = self.verbs(pol)
        self.assertEqual(v["demo/scripts/run.py"], "ADD"); self.assertEqual(probs, [])
        P.cmd_apply(pol)
        self.assertTrue(os.path.exists(os.path.join(self.pub, "demo/scripts/run.py")))
        self.assertIn("demo/scripts/run.py", open(P.LOCK).read())

    # 2
    def test_supporting_file_uses_the_same_transforms(self):
        self.write(self.canon, "demo", "SKILL.md", "---\nname: demo\ndescription: d\n---\n")
        self.write(self.canon, "demo", "references/g.md", "Ask Courtney first.\n")
        pol = self.policy({"references/g.md": "generated"})
        pol["defaults"]["transforms"] = ["replace_personal_name"]
        P.cmd_apply(pol)
        with open(os.path.join(self.pub, "demo/references/g.md")) as fh:
            self.assertNotIn("Courtney", fh.read())

    # 3 + 8
    def test_public_authored_supporting_file_is_never_written(self):
        self.write(self.canon, "demo", "SKILL.md", "---\nname: demo\ndescription: d\n---\n")
        self.write(self.canon, "demo", "cfg.yml", "CANONICAL\n")
        self.write(self.pub, "demo", "cfg.yml", "HAND WRITTEN FOR PUBLIC\n")
        pol = self.policy({"cfg.yml": "public-authored"})
        v, probs = self.verbs(pol)
        self.assertEqual(v["demo/cfg.yml"], "PROTECT"); self.assertEqual(probs, [])
        P.cmd_apply(pol)
        with open(os.path.join(self.pub, "demo/cfg.yml")) as fh:
            self.assertEqual(fh.read(), "HAND WRITTEN FOR PUBLIC\n")
        self.assertNotIn("demo/cfg.yml", open(P.LOCK).read())

    # 4
    def test_excluded_canonical_file_never_publishes(self):
        self.write(self.canon, "demo", "SKILL.md", "---\nname: demo\ndescription: d\n---\n")
        self.write(self.canon, "demo", "state.json", '{"secret":"local"}\n')
        pol = self.policy({"state.json": "excluded"})
        v, probs = self.verbs(pol)
        self.assertEqual(v["demo/state.json"], "EXCLUDE"); self.assertEqual(probs, [])
        P.cmd_apply(pol)
        self.assertFalse(os.path.exists(os.path.join(self.pub, "demo/state.json")))

    def test_excluded_file_appearing_publicly_is_a_problem(self):
        self.write(self.canon, "demo", "SKILL.md", "---\nname: demo\ndescription: d\n---\n")
        self.write(self.canon, "demo", "state.json", "x\n")
        self.write(self.pub, "demo", "state.json", "x\n")
        _, probs = self.verbs(self.policy({"state.json": "excluded"}))
        self.assertTrue(any("excluded but present" in p for p in probs))

    # 6 — fail closed
    def test_undeclared_canonical_file_does_not_publish_silently(self):
        self.write(self.canon, "demo", "SKILL.md", "---\nname: demo\ndescription: d\n---\n")
        self.write(self.canon, "demo", "NEW-private.py", "token = 'x'\n")
        pol = self.policy({})
        v, probs = self.verbs(pol)
        self.assertNotIn("demo/NEW-private.py", v)
        P.cmd_apply(pol)
        self.assertFalse(os.path.exists(os.path.join(self.pub, "demo/NEW-private.py")),
                         "a new canonical file must never publish without a policy entry")

    def test_undeclared_public_file_blocks(self):
        self.write(self.canon, "demo", "SKILL.md", "---\nname: demo\ndescription: d\n---\n")
        self.write(self.pub, "demo", "mystery.md", "where did this come from\n")
        v, probs = self.verbs(self.policy({}))
        self.assertEqual(v["demo/mystery.md"], "BLOCK")
        self.assertTrue(any("not declared in policy" in p for p in probs))

    # 7
    def test_missing_generated_public_file_is_republished(self):
        self.write(self.canon, "demo", "SKILL.md", "---\nname: demo\ndescription: d\n---\n")
        self.write(self.canon, "demo", "scripts/run.py", "print(1)\n")
        pol = self.policy({"scripts/run.py": "generated"})
        P.cmd_apply(pol)
        os.remove(os.path.join(self.pub, "demo/scripts/run.py"))
        v, _ = self.verbs(pol)
        self.assertEqual(v["demo/scripts/run.py"], "ADD")

    # 8
    def test_hand_edited_generated_file_is_detected_and_restored(self):
        self.write(self.canon, "demo", "SKILL.md", "---\nname: demo\ndescription: d\n---\n")
        self.write(self.canon, "demo", "scripts/run.py", "print(1)\n")
        pol = self.policy({"scripts/run.py": "generated"})
        P.cmd_apply(pol)
        self.write(self.pub, "demo", "scripts/run.py", "print('tampered')\n")
        v, _ = self.verbs(pol)
        self.assertEqual(v["demo/scripts/run.py"], "CHANGE")

    # 9 + 11
    def test_missing_canonical_source_does_not_delete_public_output(self):
        self.write(self.canon, "demo", "SKILL.md", "---\nname: demo\ndescription: d\n---\n")
        self.write(self.canon, "demo", "scripts/run.py", "print(1)\n")
        pol = self.policy({"scripts/run.py": "generated"})
        P.cmd_apply(pol)
        os.remove(os.path.join(self.canon, "demo/scripts/run.py"))
        v, probs = self.verbs(pol)
        self.assertEqual(v["demo/scripts/run.py"], "BLOCK")
        self.assertTrue(any("canonical source is missing" in p for p in probs))
        rc = P.cmd_apply(pol)
        self.assertEqual(rc, 1, "apply must refuse while a declared source is missing")
        self.assertTrue(os.path.exists(os.path.join(self.pub, "demo/scripts/run.py")),
                        "a missing source must never delete published output")

    # 10
    def test_executable_bit_is_preserved(self):
        self.write(self.canon, "demo", "SKILL.md", "---\nname: demo\ndescription: d\n---\n")
        self.write(self.canon, "demo", "scripts/run.sh", "#!/bin/sh\necho hi\n", ex=True)
        pol = self.policy({"scripts/run.sh": "generated"})
        P.cmd_apply(pol)
        out = os.path.join(self.pub, "demo/scripts/run.sh")
        self.assertTrue(os.access(out, os.X_OK), "a published script must stay executable")
        self.assertIn("demo/scripts/run.sh", open(P.LOCK).read())
        self.assertTrue(any(l.endswith(" x") for l in open(P.LOCK).read().splitlines()
                            if l.startswith("demo/scripts/run.sh")))

    def test_symlink_supporting_file_is_rejected_not_dereferenced(self):
        self.write(self.canon, "demo", "SKILL.md", "---\nname: demo\ndescription: d\n---\n")
        target = self.write(self.canon, "demo", "real.md", "content\n")
        os.symlink(target, os.path.join(self.canon, "demo", "link.md"))
        v, probs = self.verbs(self.policy({"link.md": "generated"}))
        self.assertEqual(v["demo/link.md"], "BLOCK")
        self.assertTrue(any("symlink" in p for p in probs))

    def test_privacy_scan_covers_supporting_files(self):
        self.write(self.canon, "demo", "SKILL.md", "---\nname: demo\ndescription: d\n---\n")
        self.write(self.canon, "demo", "scripts/leak.py", 'KEY = "sk-abcdefghijklmnopqrstuvwx"\n')
        v, probs = self.verbs(self.policy({"scripts/leak.py": "generated"}))
        self.assertEqual(v["demo/scripts/leak.py"], "BLOCK")
        self.assertTrue(probs)


if __name__ == "__main__":
    print(f"canonical sources available: {CANONICAL} "
          f"({'full local suite' if CANONICAL else 'CI-safe subset; canonical tests skipped'})\n")
    unittest.main(verbosity=2)
