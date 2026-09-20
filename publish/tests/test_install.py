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
        self.assertIn(marker, open(os.path.join(self.dest(), "SKILL.md")).read(),
                      "customized content must survive")
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
        self.assertEqual(open(self.dest()).read(), "not a skill")

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
