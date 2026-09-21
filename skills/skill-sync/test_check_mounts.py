"""Tests for check_mounts.repair(). Every case runs in a temporary tree, never the real mount.

Run: python3 test_check_mounts.py

Why these exist: until 2026-09-20 repair() refused only when the mount copy held files
existing nowhere else. A copy whose content merely DIFFERED was relinked and that version
discarded into a backup. A blind --fix that day would have rewritten 43 diverging copies.
"""
import importlib.util, os, shutil, tempfile, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("cm", os.path.join(HERE, "check_mounts.py"))
cm = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cm)


class RepairGate(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="cmtest-")
        self.mount = os.path.join(self.tmp, "mount")
        self.canon = os.path.join(self.tmp, "canon")
        os.makedirs(self.mount); os.makedirs(self.canon)
        self._m, self._c, self._b = cm.MOUNT, cm.CANON, cm.BACKUP
        cm.MOUNT, cm.CANON = self.mount, self.canon
        cm.BACKUP = os.path.join(self.tmp, "backup")

    def tearDown(self):
        cm.MOUNT, cm.CANON, cm.BACKUP = self._m, self._c, self._b
        shutil.rmtree(self.tmp, ignore_errors=True)

    def make(self, name, mount_files, canon_files, canon_is_link_to_mount=False):
        m = os.path.join(self.mount, name); os.makedirs(m)
        for f, body in mount_files.items():
            os.makedirs(os.path.dirname(os.path.join(m, f)), exist_ok=True)
            with open(os.path.join(m, f), "w") as fh:
                fh.write(body)
        c = os.path.join(self.canon, name)
        if canon_is_link_to_mount:
            os.symlink(m, c)
            return
        os.makedirs(c)
        for f, body in canon_files.items():
            os.makedirs(os.path.dirname(os.path.join(c, f)), exist_ok=True)
            with open(os.path.join(c, f), "w") as fh:
                fh.write(body)

    def test_identical_copy_is_repaired(self):
        self.make("same", {"SKILL.md": "x\n"}, {"SKILL.md": "x\n"})
        ok, msg = cm.repair("same", [])
        self.assertTrue(ok, msg)
        self.assertTrue(os.path.islink(os.path.join(self.mount, "same")))

    def test_differing_copy_is_refused_and_preserved(self):
        """The defect this suite exists for: differing content must never be discarded."""
        self.make("drift", {"SKILL.md": "MINE\n"}, {"SKILL.md": "THEIRS\n"})
        ok, msg = cm.repair("drift", [])
        self.assertFalse(ok)
        self.assertIn("differ", msg)
        p = os.path.join(self.mount, "drift", "SKILL.md")
        self.assertFalse(os.path.islink(os.path.join(self.mount, "drift")))
        with open(p) as fh:
            self.assertEqual(fh.read(), "MINE\n", "the divergent copy must survive untouched")

    def test_unique_files_still_refused(self):
        self.make("uniq", {"SKILL.md": "x\n", "logs/run.log": "live\n"}, {"SKILL.md": "x\n"})
        ok, msg = cm.repair("uniq", ["logs/run.log"])
        self.assertFalse(ok)
        self.assertIn("only here", msg)

    def test_canonical_that_links_into_the_mount_is_refused(self):
        """find-skills and wp-playground: the mount IS canonical. Relinking makes a cycle."""
        self.make("inverted", {"SKILL.md": "x\n"}, {}, canon_is_link_to_mount=True)
        ok, msg = cm.repair("inverted", [])
        self.assertFalse(ok)
        self.assertIn("cycle", msg)
        self.assertFalse(os.path.islink(os.path.join(self.mount, "inverted")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
