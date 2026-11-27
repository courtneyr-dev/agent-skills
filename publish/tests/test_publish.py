"""Tests for the deterministic publisher. Run: python3 publish/tests/test_publish.py"""
import os, shutil, sys, tempfile, unittest, yaml

HERE = os.path.dirname(os.path.abspath(__file__))
PUB = os.path.dirname(HERE)
ROOT = os.path.dirname(PUB)
sys.path.insert(0, PUB)
import transforms as T
import publish_skills as P

PUBLIC_AUTHORED = ["wiki-cycle", "weekly-site-health-audit", "wiki-memory",
                   "readwise-methods-review", "job-search",
                   "company-fleets", "factory-rig", "factory-execute"]


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

    def test_fleet_skill_transforms(self):
        self.assertEqual(T.public_license_frontmatter(
            '---\nlicense: "Private rig (courtneyr-dev/claude-config)"\n---\n'), "---\nlicense: MIT\n---\n")
        self.assertEqual(T.public_license_frontmatter(
            "license: Private rig (x). Original skill; no upstream code copied."), "license: MIT")
        self.assertEqual(T.public_rig_rights("| 2026-11-25 | Private rig; original |"),
                         "| 2026-11-25 | agent-skills (MIT); original |")
        for path in ("/Users/courtneyrobertson/Downloads/brief.md", "~/Downloads/brief.md", "$HOME/Downloads/brief.md"):
            for tail in ("", " line 3", ", line 778", " lines 310-320", " lines 419 to 450"):
                self.assertEqual(T.private_prompt_reference(f"| `{path}`{tail} | x |"),
                                 "| project requirements (not published) | x |", path + tail)
        self.assertEqual(T.private_prompt_reference("Location: `fleet-task-prompt.md`, lines 242-267"),
                         "Location: project requirements (not published)")
        self.assertEqual(T.private_prompt_reference("see prompt.md and prompts/"), "see prompt.md and prompts/")
        self.assertEqual(T.private_branch_reference("rig branch claude/factory-rig, read 2026-11-25"),
                         "agent-skills, read 2026-11-25")
        self.assertEqual(T.private_branch_reference("Rig branch claude/factory-rig; claude/factory-rig branch"),
                         "agent-skills; agent-skills")
        self.assertEqual(T.credit_pstack_upstream("installed from courtneyr-dev/plugins"),
                         "installed from cursor/plugins")
        self.assertEqual(T.rig_mount_paths('"rig": "~/.claude/claude-config/skills", ~/Developer/rig-upstream/x'),
                         '"rig": "~/.claude/skills", $FRIG_UPSTREAM_ROOT/x')
        self.assertEqual(T.synthetic_token_prefix('("fxs-synthetic-token", rb"\\bfxs_[A-Za-z0-9]{16,}\\b")'),
                         '("fx-demo-synthetic-token", rb"\\bfx_demo_[A-Za-z0-9]{16,}\\b")')

    def test_fleet_transform_list_leaves_pronoun_word_lists_alone(self):
        """second_person_owner rewrote a claims checker's pronoun set ("she" -> "you"); the fleet
        skills' list must not include it."""
        pol = P.load_policy()
        fleet = pol["skills"]["corporate-claims-check"]["transforms"]
        self.assertNotIn("second_person_owner", fleet)
        line = 'THIRD = {"he", "she", "they"}  # in (?:its|their|his|her) words'
        self.assertEqual(T.apply_all(line, fleet), line)

    def test_unknown_transform_fails_closed(self):
        with self.assertRaises(KeyError):
            T.apply_all("x", ["no_such_transform"])


class PublicAuthoredProtection(unittest.TestCase):
    """The hand-authored editions must be structurally unreachable by generation."""
    def setUp(self):
        self.pol = P.load_policy()

    def test_each_declared_public_authored(self):
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
        with open(pp, encoding="utf-8") as fh:
            original = fh.read()
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
        self.assertEqual(sorted(k for k in lock if k.endswith("/SKILL.md") and k.count("/") == 1),
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
        with open(pp, encoding="utf-8") as fh:
            original = fh.read()
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
        with open(P.LOCK) as fh:
            self.assertIn("demo/scripts/run.py", fh.read())

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
        with open(P.LOCK) as fh:
            self.assertNotIn("demo/cfg.yml", fh.read())

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
        with open(P.LOCK) as fh:
            lock = fh.read()
        self.assertIn("demo/scripts/run.sh", lock)
        self.assertTrue(any(l.endswith(" x") for l in lock.splitlines()
                            if l.startswith("demo/scripts/run.sh")))

    def test_symlink_supporting_file_is_rejected_not_dereferenced(self):
        self.write(self.canon, "demo", "SKILL.md", "---\nname: demo\ndescription: d\n---\n")
        target = self.write(self.canon, "demo", "real.md", "content\n")
        os.symlink(target, os.path.join(self.canon, "demo", "link.md"))
        v, probs = self.verbs(self.policy({"link.md": "generated"}))
        self.assertEqual(v["demo/link.md"], "BLOCK")
        self.assertTrue(any("symlink" in p for p in probs))

    def test_replace_text_rewrites_and_fails_closed_when_stale(self):
        self.write(self.canon, "demo", "SKILL.md", "---\nname: demo\ndescription: d\n---\nruns on this Mac\n")
        self.write(self.canon, "demo", "references/r.md", "built by the sources workstream\n")
        pol = self.policy({"references/r.md": "generated"})
        pol["skills"]["demo"]["replace_text"] = [
            {"file": "SKILL.md", "old": "on this Mac", "new": "on macOS"},
            {"file": "references/r.md", "old": "the sources workstream", "new": "you"}]
        self.assertEqual(P.cmd_apply(pol), 0)
        with open(os.path.join(self.pub, "demo/SKILL.md")) as fh:
            self.assertIn("runs on macOS", fh.read())
        with open(os.path.join(self.pub, "demo/references/r.md")) as fh:
            self.assertEqual(fh.read(), "built by you\n")
        self.write(self.canon, "demo", "references/r.md", "reworded upstream\n")
        _, probs = self.verbs(pol)
        self.assertTrue(any("replace_text no longer matches" in p for p in probs), probs)

    def test_scoped_apply_keeps_other_skills_in_the_lock(self):
        for skill in ("demo", "other"):
            self.write(self.canon, skill, "SKILL.md", f"---\nname: {skill}\ndescription: d\n---\n")
            self.write(self.canon, skill, "scripts/run.py", "print(1)\n")
        pol = self.policy({"scripts/run.py": "generated"})
        pol["skills"]["other"] = {"mode": "generated", "source": "other", "files": {"scripts/run.py": "generated"}}
        self.assertEqual(P.cmd_apply(pol), 0)
        os.remove(os.path.join(self.canon, "other", "scripts/run.py"))   # a full apply now refuses
        self.assertEqual(P.cmd_apply(pol), 1)
        self.write(self.canon, "demo", "scripts/run.py", "print(2)\n")
        self.assertEqual(P.cmd_apply(P.only_skills(pol, ["demo"]), scoped=True), 0)
        lock = P.read_lock()
        self.assertIn("other/SKILL.md", lock)
        self.assertIn("other/scripts/run.py", lock)
        self.assertEqual(lock["demo/scripts/run.py"][0], P.sha("print(2)\n"))
        with self.assertRaises(P.Failure):
            P.only_skills(pol, ["ghost"])

    def test_privacy_scan_covers_supporting_files(self):
        self.write(self.canon, "demo", "SKILL.md", "---\nname: demo\ndescription: d\n---\n")
        self.write(self.canon, "demo", "scripts/leak.py", 'KEY = "sk-abcdefghijklmnopqrstuvwx"\n')
        v, probs = self.verbs(self.policy({"scripts/leak.py": "generated"}))
        self.assertEqual(v["demo/scripts/leak.py"], "BLOCK")
        self.assertTrue(probs)



class PublicAuthoredFiles(unittest.TestCase):
    """Public-authored skills are hand-written here, so no lock hashes them. They still fail closed:
    every file is declared in the list the policy names, and every file passes the privacy gate."""

    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="pa-")
        self._root = P.ROOT
        P.ROOT = self.tmp
        self.write("public/pa/SKILL.md", "---\nname: pa\ndescription: d\n---\n")
        self.write("public/pa/references/notes.md", "Run it from the skill folder.\n")
        self.write("publish/public-authored.files", "# one path per line\npa/references/notes.md\n")
        self.pol = {"version": 1, "canonical_root": "/nonexistent", "public_root": "public",
                    "defaults": {"transforms": [], "supporting_files": {
                        "undeclared_canonical": "excluded", "undeclared_public": "blocked",
                        "public_authored_list": "publish/public-authored.files"}},
                    "skills": {"pa": {"mode": "public-authored", "reason": "test"}}, "retired": {}}

    def tearDown(self):
        P.ROOT = self._root
        shutil.rmtree(self.tmp, ignore_errors=True)

    def write(self, rel, body):
        p = os.path.join(self.tmp, rel)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as fh:
            fh.write(body)

    def test_declared_clean_files_pass(self):
        problems, n = P.public_authored_problems(self.pol)
        self.assertEqual((problems, n), ([], 2))

    def test_stray_file_fails(self):
        self.write("public/pa/references/stray.md", "nobody declared me\n")
        problems, _ = P.public_authored_problems(self.pol)
        self.assertTrue(any("pa/references/stray.md" in p and "not declared" in p for p in problems), problems)

    def test_declared_file_that_is_gone_fails(self):
        os.remove(os.path.join(self.tmp, "public/pa/references/notes.md"))
        problems, _ = P.public_authored_problems(self.pol)
        self.assertTrue(any("declared public-authored but missing" in p for p in problems), problems)

    def test_home_path_and_private_marker_fail(self):
        self.write("public/pa/references/notes.md", "cd /Users/x/projects first\n")
        self.write("public/pa/SKILL.md", "---\nname: pa\n---\n<!-- private -->\n")
        problems = " ".join(P.public_authored_problems(self.pol)[0])
        self.assertIn("pa/references/notes.md: private absolute home path", problems)
        self.assertIn("pa/SKILL.md: explicit private marker", problems)

    def test_placeholder_home_paths_pass(self):
        self.write("public/pa/references/notes.md", 'HOME="/home/someone" and a regex r"/Users/[a-z]"\n')
        self.assertEqual(P.public_authored_problems(self.pol)[0], [])

    def test_missing_list_fails_closed(self):
        os.remove(os.path.join(self.tmp, "publish/public-authored.files"))
        problems, _ = P.public_authored_problems(self.pol)
        self.assertTrue(problems)


class PublicAuthoredFilesInThisRepo(unittest.TestCase):
    """The CLI, on this repository: a stray file or a planted home path in a public-authored skill
    makes --verify-public exit non-zero."""

    def verify(self):
        import subprocess
        env = dict(os.environ, CLAUDE_SKILLS="/nonexistent")
        return subprocess.run([sys.executable, os.path.join(PUB, "publish_skills.py"), "--verify-public"],
                              capture_output=True, text=True, env=env)

    def test_stray_file_in_company_fleets_fails(self):
        stray = os.path.join(ROOT, "skills", "company-fleets", "references", "stray.md")
        with open(stray, "w") as fh:
            fh.write("hand-added\n")
        try:
            p = self.verify()
        finally:
            os.remove(stray)
        self.assertEqual(p.returncode, 1, p.stdout)
        self.assertIn("company-fleets/references/stray.md", p.stdout)

    def test_planted_home_path_in_skill_md_fails(self):
        path = os.path.join(ROOT, "skills", "company-fleets", "SKILL.md")
        with open(path, encoding="utf-8") as fh:
            original = fh.read()
        try:
            with open(path, "a", encoding="utf-8") as fh:
                fh.write("\nSee /Users/someoneelse/Developer for the rig.\n")
            p = self.verify()
        finally:
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(original)
        self.assertEqual(p.returncode, 1, p.stdout)
        self.assertIn("company-fleets/SKILL.md: private absolute home path", p.stdout)

if __name__ == "__main__":
    print(f"canonical sources available: {CANONICAL} "
          f"({'full local suite' if CANONICAL else 'CI-safe subset; canonical tests skipped'})\n")
    unittest.main(verbosity=2)
