"""Offline tests for the offer hook and the owner lookup. Run: python3 -m unittest discover skills/skill-retro/tests"""

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS))
import retro_offer_hook as hook  # noqa: E402
import skill_owner as owner  # noqa: E402


def assistant(*blocks, sidechain=False):
    return {"type": "assistant", "isSidechain": sidechain, "message": {"content": list(blocks)}}


def use(name, **inp):
    return {"type": "tool_use", "id": "x", "name": name, "input": inp}


def write_transcript(path, entries):
    path.write_text("".join(json.dumps(e) + "\n" for e in entries))


class HookTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.transcript = self.tmp / "s.jsonl"
        self.config = self.tmp / "config.json"
        self.config.write_text(json.dumps({"threshold": 3, "state_dir": str(self.tmp / "state")}))

    def run_hook(self, payload, env=None):
        e = {**os.environ, "SKILL_RETRO_CONFIG": str(self.config), **(env or {})}
        r = subprocess.run([sys.executable, str(SCRIPTS / "retro_offer_hook.py")], input=json.dumps(payload),
                           capture_output=True, text=True, env=e)
        self.assertEqual(r.returncode, 0, r.stderr)
        return json.loads(r.stdout) if r.stdout.strip() else None

    def payload(self, **extra):
        return {"session_id": "s1", "transcript_path": str(self.transcript), **extra}

    def test_counts_calls_per_skill_until_the_next_skill(self):
        write_transcript(self.transcript, [
            assistant(use("Skill", skill="a"), use("Bash"), use("Read")),
            {"type": "user", "message": {"content": "ok"}},
            assistant(use("Edit")),
            assistant(use("Skill", skill="b"), use("Bash")),
        ])
        self.assertEqual(hook.batches(self.transcript), [["a", 3], ["b", 1]])

    def test_ignores_subagent_lines_and_calls_before_any_skill(self):
        write_transcript(self.transcript, [
            assistant(use("Bash")),
            assistant(use("Skill", skill="a")),
            assistant(use("Bash"), use("Bash"), use("Bash"), sidechain=True),
        ])
        self.assertEqual(hook.batches(self.transcript), [["a", 0]])

    def test_offers_once_then_stays_quiet(self):
        write_transcript(self.transcript, [assistant(use("Skill", skill="a"), use("Bash"), use("Bash"), use("Bash"))])
        out = self.run_hook(self.payload())
        self.assertEqual(out["decision"], "block")
        self.assertIn("a (3 tool calls)", out["reason"])
        self.assertIsNone(self.run_hook(self.payload()))

    def test_below_threshold_excluded_or_guarded_is_silent(self):
        write_transcript(self.transcript, [assistant(use("Skill", skill="a"), use("Bash"), use("Bash"))])
        self.assertIsNone(self.run_hook(self.payload()))
        write_transcript(self.transcript, [assistant(use("Skill", skill="skill-retro"), *[use("Bash")] * 5)])
        self.assertIsNone(self.run_hook(self.payload()))
        write_transcript(self.transcript, [assistant(use("Skill", skill="b"), *[use("Bash")] * 5)])
        self.assertIsNone(self.run_hook(self.payload(stop_hook_active=True)))
        self.assertIsNone(self.run_hook(self.payload(background_tasks=[{"id": "t"}])))
        self.assertIsNone(self.run_hook(self.payload(), env={"SKILL_RETRO_OFF": "1"}))
        self.assertEqual(self.run_hook(self.payload())["decision"], "block")

    def test_glob_exclude_and_three_skill_cap(self):
        write_transcript(self.transcript, [assistant(use("Skill", skill=s), *[use("Bash")] * n)
                                           for s, n in [("a", 3), ("b", 4), ("c", 5), ("d", 6), ("superpowers:x", 9)]])
        got = hook.due(self.transcript, 3, ["superpowers:*"], [])
        self.assertEqual(got, [("d", 6), ("c", 5), ("b", 4)])

    def test_bad_input_never_blocks(self):
        r = subprocess.run([sys.executable, str(SCRIPTS / "retro_offer_hook.py")], input="not json",
                           capture_output=True, text=True, env={**os.environ, "SKILL_RETRO_CONFIG": str(self.config)})
        self.assertEqual((r.returncode, r.stdout), (0, ""))
        self.assertIsNone(self.run_hook({"session_id": "s1", "transcript_path": str(self.tmp / "missing.jsonl")}))


class OwnerTests(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.skills = self.tmp / "skills"
        self.skills.mkdir()
        self.cfg = {**owner.DEFAULTS, "skills_dirs": [str(self.skills)], "plugins_dir": str(self.tmp / "plugins"),
                    "own_orgs": ["me"], "fork_repos": ["me/pack"], "employer_orgs": ["acme"],
                    "rfc_repos": ["acme/team-skills"], "rfc_process_skill": "team-skills:skill-rfc-process",
                    "commit_styles": {"acme": "conventional, signed"}}

    def git_repo(self, name, origin, upstream=None):
        repo = self.tmp / name
        (repo / "skills" / "s").mkdir(parents=True)
        (repo / "skills" / "s" / "SKILL.md").write_text("---\nname: s\n---\n")
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        subprocess.run(["git", "-C", str(repo), "remote", "add", "origin", f"https://github.com/{origin}.git"], check=True)
        if upstream:
            subprocess.run(["git", "-C", str(repo), "remote", "add", "upstream", f"git@github.com:{upstream}.git"], check=True)
        (self.skills / "s").symlink_to(repo / "skills" / "s")
        return repo

    def test_employer_repo_gets_a_pr_in_its_configured_commit_style(self):
        self.git_repo("devrel", "acme/team-tools")
        out = owner.lookup("s", self.cfg)
        self.assertEqual((out["flow"], out["repo"], out["path"]), ("pr", "acme/team-tools", "skills/s"))
        self.assertEqual((out["employer"], out["commit_style"]), (True, "conventional, signed"))

    def test_defaults_name_no_employer(self):
        self.assertEqual((owner.DEFAULTS["employer_orgs"], owner.DEFAULTS["rfc_repos"], owner.DEFAULTS["commit_styles"]),
                         ([], [], {}))
        self.git_repo("devrel", "acme/team-tools")
        out = owner.lookup("s", {**owner.DEFAULTS, "skills_dirs": [str(self.skills)]})
        self.assertEqual((out["flow"], out["employer"], out["commit_style"]),
                         ("upstream-issue", False, "match the repo's git log"))

    def test_fork_with_upstream_remote_prs_upstream(self):
        self.git_repo("writer", "me/writer", upstream="someone/writer")
        out = owner.lookup("s", self.cfg)
        self.assertEqual((out["flow"], out["repo"], out["fork"]), ("pr", "someone/writer", "me/writer"))

    def test_manifest_routes_third_party_forks_and_reports_overlays(self):
        manifest = self.tmp / "sources.json"
        manifest.write_text(json.dumps({
            "t": {"repo": "vendor/skills", "path": "t", "frontmatter": {"description": "description: x"}},
            "p": {"repo": "me/pack", "path": "pack/p"},
        }))
        cfg = {**self.cfg, "sync_manifest": str(manifest)}
        t, p = owner.lookup("t", cfg), owner.lookup("p", cfg)
        self.assertEqual((t["flow"], t["overlay"]), ("upstream-issue", ["description"]))
        self.assertEqual(p["flow"], "fork-commit")

    def test_plugin_skill_from_synced_meta_and_rfc_repo(self):
        synced = self.tmp / "plugins" / "synced" / "org"
        (synced / "team-skills" / "skills" / "writing-skills").mkdir(parents=True)
        (synced / "team-skills.meta.json").write_text(json.dumps({"marketplace_name": "acme/team-skills"}))
        (synced / "design~g2.meta.json").write_text(json.dumps({"marketplace_name": "knowledge-work-plugins"}))
        rfc = owner.lookup("team-skills:writing-skills", self.cfg)
        self.assertEqual((rfc["flow"], rfc["rfc_process_skill"]), ("rfc-pr", "team-skills:skill-rfc-process"))
        self.assertEqual(owner.lookup("design:ux-copy", self.cfg)["repo"], "anthropics/knowledge-work-plugins")

    def test_override_wins_and_unknown_is_reported(self):
        cfg = {**self.cfg, "owners": {"q": {"repo": "acme/team-tools", "path": "skills/q"}}}
        self.assertEqual(owner.lookup("q", cfg)["path"], "skills/q")
        self.assertEqual(owner.lookup("nope", self.cfg)["flow"], "unknown")


if __name__ == "__main__":
    unittest.main()
