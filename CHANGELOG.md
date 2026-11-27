# Changelog

## 1.1.0 — 2026-11-27

### Added
- 40 skills in four new paths: Company fleets (`-p fleets`, 18), Education (`-p education`, 10),
  Hosting operations (`-p hosting`, 10) and Delivery factory (`-p delivery`, 2). The six existing
  paths are unchanged.
- 37 fleet gate skills, generated from canonical with a per-file allowlist; their 1,012 tests run
  from the published copies.
- Public editions of `company-fleets`, `factory-rig` and `factory-execute`. Run output, review
  reports, demo builds, leases and machine paths stay out; machine values are environment
  variables with skill-relative defaults.
- `publish_skills.py --only NAME...` to apply or check named skills while other skills drift, and
  `replace_text` in the policy for declared one-off rewrites that fail closed when stale.
- Seven fleet transforms, each tested, and `.gitleaks.toml` allowing only `idempotency_key` content
  hashes.

### Changed
- The installer test compares installed links with `skills/` on disk instead of a fixed count.

### Notes
- Roles attach 167 upstream skills this repo doesn't contain. They're marked external with their
  source repository and install from there.
- The fleet skills' transform list leaves out `second_person_owner`, which rewrote a pronoun set
  in a claims checker's code while every test passed.
- The hosting benchmark cites public provider documentation, lists providers alphabetically, and
  refuses superiority claims.

## 1.0.0 — 2026-09-05

First public release.

### Added
- 36 skills installable into Claude Code, Cursor, Codex, OpenClaw, or Gemini CLI, grouped into
  six paths: WordPress sites, Reading, PKM, Faith, Writing, Dev workflow.
- `install.sh` with `--guided` (one question per path), `-p <path>`, `--copy` for agents that do
  not follow symlinks, and `--external` for install commands to third-party sources.
- `manifest.json` recording every skill's source, license, redistribution status, and a worked
  example.
- Searchable catalog at <https://courtneyr-dev.github.io/agent-skills/>.
- `docs/CATALOG.md`, `docs/PLATFORMS.md`, `docs/PLUGINS.md`, `docs/WHAT-IS-A-SKILL.md`.

### Provenance
- Every skill was checked against GitHub for an earlier third-party copy by comparing content and
  first-commit dates. Fifteen belonged to other people and became manifest links instead:
  eleven from `readwiseio/readwise-skills`, two wrapping the `counselors` and `librarium` CLIs,
  `explainer` and `deepdive` from `nemock/video-explainer-system` (MIT, Dave Saunders), and four
  WordPress skills withheld because authorship could not be established.
- 44 skills are credited to **pstack by poteto (Lauren Tan)**, MIT. `cursor/plugins` has no root
  LICENSE and licenses each plugin directory, so a repo-root check reports "unlicensed" wrongly.
- Ten skills moved to the companion repos where their tooling lives —
  `wp-release-audit-method` (GPL-2.0) and `wp-dev-prompts` (CC0-1.0) — rather than being
  duplicated here under a third license.

### Notes
- Skills are presented by path, not ranked. How often the author happens to run something says more
  about the last few weeks than about whether it is any good.
- Twelve external skills have no upstream license at all. They are linked, never copied.
