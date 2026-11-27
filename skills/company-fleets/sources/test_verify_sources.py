import contextlib
import io
import json
import subprocess
import tempfile
import unittest
from pathlib import Path

import verify_sources as v

PIN = {"disable-model-invocation": "disable-model-invocation: true"}
UPSTREAM_MD = "---\nname: demo-skill\ndescription: Synthetic fixture skill.\n---\nSee [ref](references/a.md).\n"


def git(cwd, *args):
    subprocess.run(["git", "-c", "user.name=Fixture", "-c", "user.email=fixture@example.invalid", *args],
                   cwd=cwd, check=True, capture_output=True)


class Fixture:
    """A pinned clone, a hidden install rendered from it with skill-sync's pin, and a matching ledger and matrix."""

    def __init__(self, tmp):
        self.root = Path(tmp)
        self.clone = self.root / "clone"
        src = self.clone / "skills/demo-skill"
        (src / "references").mkdir(parents=True)
        (src / "SKILL.md").write_text(UPSTREAM_MD)
        (src / "references/a.md").write_text("synthetic reference\n")
        git(self.clone, "init", "-q")
        git(self.clone, "add", ".")
        git(self.clone, "commit", "-q", "-m", "fixture")
        sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=self.clone, capture_output=True, text=True).stdout.strip()
        self.skills = self.root / "skills"
        skill = self.skills / "demo-skill"
        (skill / "references").mkdir(parents=True)
        (skill / "SKILL.md").write_text(v.sync_skills.apply_pins(UPSTREAM_MD, PIN))
        (skill / "references/a.md").write_text("synthetic reference\n")
        (self.skills / "local-skill").mkdir()
        (self.skills / "local-skill/SKILL.md").write_text("---\nname: local-skill\n---\n")
        self.ledger = {"repos": [{"id": "fixture/repo", "url": "https://example.invalid/fixture/repo", "revision": sha,
                                  "revision_date": "2026-11-26", "license": {"spdx": "MIT"}, "clone": str(self.clone),
                                  "status": "installed-inactive"}],
                       "items": [{"name": "demo-skill", "repo": "fixture/repo", "path": "skills/demo-skill",
                                  "status": "installed-inactive", "model_invocation": "disabled", "tree_sha256": v.tree_hash(skill)},
                                 {"name": "seed-only", "repo": "fixture/repo", "status": "source-only"}]}
        self.registry = {"demo-skill": {"repo": "fixture/repo", "path": "skills/demo-skill", "ref": "main", "frontmatter": dict(PIN)}}
        self.requirements = {"rows": [{"id": "S03-001"}, {"id": "S03-002"}]}
        self.matrix = {"rows": [
            {"requirement": "S03-001", "fleet": "corporate", "disposition": "upstream-skill", "skills": ["demo-skill"],
             "adapter": "load by path", "verification": "hash"},
            {"requirement": "S03-002", "fleet": "corporate", "disposition": "original-local", "local_skill": "local-skill",
             "builder": "corporate-and-agency", "verification": "fleet evals"}]}

    def run(self, *extra):
        paths = {}
        for name in ("ledger", "registry", "matrix", "requirements"):
            paths[name] = self.root / f"{name}.json"
            paths[name].write_text(json.dumps(getattr(self, name)))
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = v.main(["--ledger", str(paths["ledger"]), "--matrix", str(paths["matrix"]), "--registry", str(paths["registry"]),
                           "--requirements", str(paths["requirements"]), "--skills-root", str(self.skills),
                           "--existing-root", str(self.skills), *extra])
        return code, out.getvalue()


@unittest.skipIf(v.MISSING, "skill-sync beside company-fleets lacks %s" % ", ".join(v.MISSING))
class VerifySources(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.f = Fixture(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def test_consistent_fixture_passes_with_the_pin_rendered_into_the_clone_check(self):
        code, out = self.f.run()
        self.assertEqual(code, 0, out)
        self.assertIn("OK: 1 repos, 2 items (1 installed, 1 hidden), 2 of 2 requirements mapped, 0 original skills planned, 0 findings", out)

    def test_unknown_status_is_invalid(self):
        self.f.ledger["items"][1]["status"] = "reference-only"
        code, out = self.f.run()
        self.assertEqual(code, 2)
        self.assertIn("status 'reference-only'", out)

    def test_short_revision_is_invalid(self):
        self.f.ledger["repos"][0]["revision"] = "abc1234"
        self.assertEqual(self.f.run()[0], 2)

    def test_edited_install_reports_drift_with_resume_step(self):
        (self.f.skills / "demo-skill/references/a.md").write_text("locally edited\n")
        code, out = self.f.run("--no-clones")
        self.assertEqual(code, 1)
        self.assertIn("differs from pinned", out)
        self.assertIn("sync_skills.py check demo-skill", out)

    def test_upstream_change_past_the_pin_is_a_finding(self):
        (self.f.clone / "skills/demo-skill/references/a.md").write_text("upstream changed\n")
        git(self.f.clone, "commit", "-qam", "upstream change")
        code, out = self.f.run()
        self.assertEqual(code, 1)
        self.assertIn("is not the pinned", out)

    def test_hidden_skill_that_loses_its_field_or_pin_is_a_finding(self):
        (self.f.skills / "demo-skill/SKILL.md").write_text(UPSTREAM_MD)
        self.f.ledger["items"][0]["tree_sha256"] = v.tree_hash(self.f.skills / "demo-skill")
        self.f.registry["demo-skill"].pop("frontmatter")
        code, out = self.f.run("--no-clones")
        self.assertEqual(code, 1)
        self.assertIn("SKILL.md lost disable-model-invocation: true", out)
        self.assertIn("registry does not pin disable-model-invocation", out)

    def test_new_dangling_link_is_a_finding_until_listed(self):
        md = self.f.skills / "demo-skill/SKILL.md"
        md.write_text(md.read_text() + "Uses `../missing-sibling/SKILL.md`.\n")
        self.f.ledger["items"][0]["tree_sha256"] = v.tree_hash(self.f.skills / "demo-skill")
        code, out = self.f.run("--no-clones")
        self.assertEqual(code, 1)
        self.assertIn("../missing-sibling/SKILL.md", out)
        self.f.ledger["items"][0]["dangling_links"] = [{"from": "SKILL.md", "link": "../missing-sibling/SKILL.md", "reason": "excluded"}]
        self.assertEqual(self.f.run("--no-clones")[0], 0)

    def test_source_only_item_must_not_be_registered(self):
        self.f.registry["seed-only"] = {"repo": "fixture/repo", "path": "x"}
        code, out = self.f.run()
        self.assertEqual(code, 1)
        self.assertIn("seed-only: status source-only but skill-sync registers it", out)

    def test_upstream_row_naming_uninstalled_skill_is_a_finding(self):
        self.f.matrix["rows"][0]["skills"] = ["seed-only"]
        code, out = self.f.run()
        self.assertEqual(code, 1)
        self.assertIn("upstream skill seed-only is not installed", out)

    def test_original_local_row_needs_a_known_builder(self):
        self.f.matrix["rows"][1]["builder"] = "someone-else"
        code, out = self.f.run()
        self.assertEqual(code, 2)
        self.assertIn("builder 'someone-else'", out)

    def test_unbuilt_original_skill_is_planned_and_fails_only_under_strict(self):
        self.f.matrix["rows"][1]["local_skill"] = "not-built-yet"
        code, out = self.f.run()
        self.assertEqual(code, 0, out)
        self.assertIn("1 original skills planned", out)
        code, out = self.f.run("--strict")
        self.assertEqual(code, 1)
        self.assertIn("original skill not-built-yet has no SKILL.md yet", out)

    def test_unmapped_requirement_is_a_finding(self):
        self.f.requirements["rows"].append({"id": "ED-001"})
        code, out = self.f.run()
        self.assertEqual(code, 1)
        self.assertIn("maps no row for requirement(s) ED-001", out)

    def test_requirement_mapped_twice_is_invalid(self):
        self.f.matrix["rows"].append(dict(self.f.matrix["rows"][0]))
        code, out = self.f.run()
        self.assertEqual(code, 2)
        self.assertIn("S03-001: requirement mapped twice", out)


if __name__ == "__main__":
    unittest.main()
