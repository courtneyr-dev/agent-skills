"""Installer tests. Every case runs in an isolated fake HOME -- never the real one.

Run: python3 publish/tests/test_install.py
"""
import os, shutil, subprocess, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE)) if os.path.basename(os.path.dirname(HERE)) != "publish" \
       else os.path.dirname(os.path.dirname(HERE))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
INSTALL = os.path.join(ROOT, "install.sh")
SKILLS = os.path.join(ROOT, "skills")
SAMPLE = "lmk"


def run(home, *args):
    env = dict(os.environ, HOME=home)
    env["AGENT_SKILLS_DIR"] = os.path.join(home, ".agents", "skills")
    p = subprocess.run(["bash", INSTALL, *args], capture_output=True, text=True, env=env, cwd=ROOT)
    return p.returncode, p.stdout + p.stderr


class InstallerBase(unittest.TestCase):
    def setUp(self):
        self.home = tempfile.mkdtemp(prefix="fakehome-")
        self.codex = os.path.join(self.home, ".codex", "skills")
        os.makedirs(self.codex)

    def tearDown(self):
        shutil.rmtree(self.home, ignore_errors=True)

    def dest(self, name=SAMPLE):
        return os.path.join(self.codex, name)


class EmptyMachine(InstallerBase):
    def test_dry_run_writes_nothing(self):
        rc, out = run(self.home, "--dry-run", "-a", "codex")
        self.assertEqual(rc, 0)
        self.assertIn("DRY RUN", out)
        self.assertEqual(os.listdir(self.codex), [], "dry-run must not create anything")

    def test_apply_creates_links(self):
        rc, out = run(self.home, "--apply", "-a", "codex")
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.islink(self.dest()))
        self.assertEqual(len(os.listdir(self.codex)), 34, "all 34 public skills install")

    def test_generated_and_public_authored_both_install(self):
        run(self.home, "--apply", "-a", "codex")
        for n in ("lmk", "wiki-cycle", "job-search"):   # generated + public-authored
            self.assertTrue(os.path.islink(os.path.join(self.codex, n)), n)


class Idempotence(InstallerBase):
    def test_second_run_changes_nothing(self):
        run(self.home, "--apply", "-a", "codex")
        before = {n: os.lstat(os.path.join(self.codex, n)).st_mtime_ns for n in os.listdir(self.codex)}
        rc, out = run(self.home, "--apply", "-a", "codex")
        after = {n: os.lstat(os.path.join(self.codex, n)).st_mtime_ns for n in os.listdir(self.codex)}
        self.assertEqual(rc, 0)
        self.assertEqual(before, after, "second run must not relink anything")
        self.assertIn("links created: 0", out)


class ConflictStates(InstallerBase):
    def _apply_and_get(self, name=SAMPLE):
        rc, out = run(self.home, "--apply", "-a", "codex")
        return rc, out

    def test_correct_symlink_is_skipped(self):
        os.symlink(os.path.join(SKILLS, SAMPLE), self.dest())
        rc, out = self._apply_and_get()
        self.assertIn(f"SKIP      codex/{SAMPLE}", out)
        self.assertIn("already correct", out)

    def test_identical_real_copy_reported_not_converted(self):
        shutil.copytree(os.path.join(SKILLS, SAMPLE), self.dest())
        rc, out = self._apply_and_get()
        self.assertIn("identical real copy", out)
        self.assertFalse(os.path.islink(self.dest()), "must not silently convert a real copy")

    def test_customized_copy_is_never_overwritten(self):
        shutil.copytree(os.path.join(SKILLS, SAMPLE), self.dest())
        marker = "MY LOCAL EDIT\n"
        with open(os.path.join(self.dest(), "SKILL.md"), "a") as f:
            f.write(marker)
        rc, out = self._apply_and_get()
        self.assertIn("CONFLICT", out)
        with open(os.path.join(self.dest(), "SKILL.md")) as fh:
            self.assertIn(marker, fh.read(), "customized content must survive")
        self.assertFalse(os.path.islink(self.dest()))

    def test_link_pointing_elsewhere_is_a_conflict(self):
        other = os.path.join(self.home, "elsewhere", SAMPLE)
        os.makedirs(other)
        os.symlink(other, self.dest())
        rc, out = self._apply_and_get()
        self.assertIn("links elsewhere", out)
        self.assertEqual(os.path.realpath(self.dest()), os.path.realpath(other),
                         "must not repoint an existing link")

    def test_dangling_link_is_reported_not_repaired(self):
        os.symlink(os.path.join(self.home, "gone"), self.dest())
        rc, out = self._apply_and_get()
        self.assertIn("dangling link", out)
        self.assertTrue(os.path.islink(self.dest()))
        self.assertFalse(os.path.exists(self.dest()), "left dangling, not silently repaired")

    def test_unknown_file_at_destination_fails_closed(self):
        with open(self.dest(), "w") as f:
            f.write("not a skill")
        rc, out = self._apply_and_get()
        self.assertIn("unrecognized file", out)
        with open(self.dest()) as fh:
            self.assertEqual(fh.read(), "not a skill")

    def test_conflicts_do_not_block_other_skills(self):
        shutil.copytree(os.path.join(SKILLS, SAMPLE), self.dest())
        with open(os.path.join(self.dest(), "SKILL.md"), "a") as f:
            f.write("EDIT\n")
        rc, out = self._apply_and_get()
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.islink(os.path.join(self.codex, "gatherer")))


class ViaMount(InstallerBase):
    def test_two_hop_only_when_requested(self):
        run(self.home, "--apply", "-a", "codex")
        self.assertFalse(os.path.exists(os.path.join(self.home, ".agents", "skills")),
                         "default install must not create the mount")

    def test_via_mount_builds_the_chain(self):
        rc, out = run(self.home, "--apply", "--via-mount", "-a", "codex")
        mount = os.path.join(self.home, ".agents", "skills", SAMPLE)
        self.assertTrue(os.path.islink(mount))
        self.assertEqual(os.readlink(self.dest()), mount)


class NoPrivateOrExternalInstall(InstallerBase):
    def test_only_repo_skills_are_installable(self):
        rc, out = run(self.home, "--list")
        names = set(out.split())
        on_disk = set(os.listdir(SKILLS))
        self.assertEqual(names, on_disk, "installer must offer exactly the repo's public skills")

    def test_external_mode_installs_nothing(self):
        rc, out = run(self.home, "--external")
        self.assertIn("owned by their upstreams", out)
        self.assertEqual(os.listdir(self.codex), [])

class SupportGrades(InstallerBase):
    """The write gate is a safety mechanism: agents below L3 must not be written by a plain
    --apply. If this inverted, an unverified harness would be bulk-installed silently."""

    def setUp(self):
        super().setUp()
        self.cursor = os.path.join(self.home, ".cursor", "skills")
        os.makedirs(self.cursor)

    def test_grades_come_from_the_manifest(self):
        rc, out = run(self.home, "--grades")
        self.assertEqual(rc, 0)
        import json
        with open(os.path.join(ROOT, "manifest.json")) as fh:
            roots = json.load(fh)["skill_roots"]
        for agent, v in roots.items():
            if isinstance(v, dict) and "grade" in v:
                self.assertIn(agent, out)
                self.assertIn(v["grade"], out)

    def test_l3_agent_is_linked_and_labelled_proven(self):
        rc, out = run(self.home, "--dry-run", "-a", "codex")
        self.assertEqual(rc, 0)
        self.assertIn("L3 runtime-proven", out)
        self.assertIn("LINK", out)
        self.assertNotIn("PLAN", out)

    def test_sub_l3_agent_is_planned_not_linked(self):
        rc, out = run(self.home, "--dry-run", "-a", "cursor")
        self.assertEqual(rc, 0)
        self.assertIn("PLAN", out)
        self.assertIn("L2 runtime-unverified", out)

    def test_apply_refuses_to_write_sub_l3_by_default(self):
        rc, out = run(self.home, "--apply", "-a", "cursor")
        self.assertEqual(rc, 0)
        self.assertEqual(os.listdir(self.cursor), [],
                         "--apply must not write for an agent below L3 without --include-unverified")

    def test_include_unverified_is_an_explicit_opt_in(self):
        rc, out = run(self.home, "--apply", "--include-unverified", "-a", "cursor")
        self.assertEqual(rc, 0)
        self.assertTrue(os.path.islink(os.path.join(self.cursor, SAMPLE)))

    def test_never_claims_fully_supported(self):
        _, out = run(self.home, "--dry-run", "-a", "cursor")
        self.assertNotIn("fully supported", out.lower())



class MountTargetSafety(InstallerBase):
    """--via-mount composes two safe operations into an unsafe one.

    The installer classifies the DESTINATION (~/.codex/skills/foo) and, finding it missing,
    links it at the mount. Nothing classified the TARGET (~/.agents/skills/foo). So a mount
    copy the same run just reported as CONFLICT could become the content a consumer resolves
    to. Target safety and destination safety are separate invariants.
    """

    def mount(self, name=SAMPLE):
        return os.path.join(self.home, ".agents", "skills", name)

    def put_mount_dir(self, body, name=SAMPLE):
        m = self.mount(name)
        os.makedirs(m)
        with open(os.path.join(m, "SKILL.md"), "w") as fh:
            fh.write(body)
        return m

    def source_body(self, name=SAMPLE):
        with open(os.path.join(SKILLS, name, "SKILL.md")) as fh:
            return fh.read()

    # --- unsafe targets: must never be linked ---

    def test_divergent_real_copy_blocks_the_consumer_link(self):
        self.put_mount_dir("---\nname: lmk\ndescription: DIVERGENT\n---\nlocal\n")
        rc, out = run(self.home, "--dry-run", "--via-mount", "-a", "codex")
        self.assertIn("BLOCK", out)
        self.assertNotRegex(out, r"LINK\s+codex/%s\b" % SAMPLE,
                            "must not propose linking a consumer at a conflicted mount copy")

    def test_apply_does_not_create_the_link_or_touch_the_target(self):
        m = self.put_mount_dir("---\nname: lmk\ndescription: DIVERGENT\n---\nlocal\n")
        run(self.home, "--apply", "--via-mount", "-a", "codex")
        self.assertFalse(os.path.lexists(self.dest()), "consumer link must not be created")
        with open(os.path.join(m, "SKILL.md")) as fh:
            self.assertIn("DIVERGENT", fh.read(), "the divergent target must not be repaired")

    def test_wrong_symlink_target_blocks(self):
        elsewhere = os.path.join(self.home, "elsewhere"); os.makedirs(elsewhere)
        os.makedirs(os.path.dirname(self.mount()), exist_ok=True)
        os.symlink(elsewhere, self.mount())
        rc, out = run(self.home, "--dry-run", "--via-mount", "-a", "codex")
        self.assertIn("BLOCK", out)
        self.assertNotRegex(out, r"LINK\s+codex/%s\b" % SAMPLE)

    def test_dangling_symlink_target_blocks(self):
        os.makedirs(os.path.dirname(self.mount()), exist_ok=True)
        os.symlink(os.path.join(self.home, "gone"), self.mount())
        rc, out = run(self.home, "--dry-run", "--via-mount", "-a", "codex")
        self.assertIn("BLOCK", out)
        self.assertNotRegex(out, r"LINK\s+codex/%s\b" % SAMPLE)

    def test_non_skill_file_target_blocks(self):
        os.makedirs(os.path.dirname(self.mount()), exist_ok=True)
        with open(self.mount(), "w") as fh:
            fh.write("not a skill")
        rc, out = run(self.home, "--dry-run", "--via-mount", "-a", "codex")
        self.assertIn("BLOCK", out)
        self.assertNotRegex(out, r"LINK\s+codex/%s\b" % SAMPLE)

    # --- safe targets: must still link ---

    def test_missing_target_is_safe_and_still_links(self):
        rc, out = run(self.home, "--apply", "--via-mount", "-a", "codex")
        self.assertTrue(os.path.islink(self.mount()))
        self.assertEqual(os.readlink(self.dest()), self.mount())

    def test_already_correct_mount_link_is_safe(self):
        run(self.home, "--apply", "--via-mount", "-a", "codex")
        rc, out = run(self.home, "--apply", "--via-mount", "-a", "codex")
        self.assertNotIn("BLOCK", out)
        self.assertEqual(os.readlink(self.dest()), self.mount())

    def test_identical_real_copy_is_consumable_but_named(self):
        """Content is correct today, so refusing would break a working install. It is
        reported explicitly rather than blessed silently."""
        self.put_mount_dir(self.source_body())
        rc, out = run(self.home, "--dry-run", "--via-mount", "-a", "codex")
        self.assertNotIn("BLOCK", out)
        self.assertRegex(out, r"LINK\s+codex/%s\b" % SAMPLE)
        self.assertIn("identical copy", out)

    # --- grade gating stays independent of target safety ---

    def test_include_unverified_cannot_override_an_unsafe_target(self):
        """--include-unverified is permission to use an unproven harness, not permission
        to consume conflicted content."""
        cursor = os.path.join(self.home, ".cursor", "skills"); os.makedirs(cursor)
        self.put_mount_dir("---\nname: lmk\ndescription: DIVERGENT\n---\nlocal\n")
        run(self.home, "--apply", "--include-unverified", "--via-mount", "-a", "cursor")
        self.assertFalse(os.path.lexists(os.path.join(cursor, SAMPLE)),
                         "opting into an unproven harness must not opt into unsafe content")

    def test_default_mode_is_unaffected_by_mount_state(self):
        self.put_mount_dir("---\nname: lmk\ndescription: DIVERGENT\n---\nlocal\n")
        rc, out = run(self.home, "--apply", "-a", "codex")
        self.assertNotIn("BLOCK", out, "target validation applies only to --via-mount")
        self.assertEqual(os.readlink(self.dest()), os.path.join(SKILLS, SAMPLE))


if __name__ == "__main__":
    unittest.main(verbosity=2)
