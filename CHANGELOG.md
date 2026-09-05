# Changelog

## 1.0.0 — 2026-09-05

First public release.

### Added
- 36 skills installable into Claude Code, Cursor, Codex, OpenClaw, or Gemini CLI, grouped into
  six paths: WordPress sites, Reading, PKM, Faith, Writing, Dev workflow.
- `install.sh` with `--guided` (one question per path), `-p <path>`, `--copy` for agents that do
  not follow symlinks, and `--external` for install commands to third-party sources.
- `manifest.json` recording every skill's source, license, redistribution status, usage count and
  a worked example.
- Searchable catalog at <https://courtneyr-dev.github.io/agent-skills/>.
- `docs/CATALOG.md`, `docs/PLATFORMS.md`, `docs/PLUGINS.md`, `docs/WHAT-IS-A-SKILL.md`.

### Provenance
- Every skill was checked against GitHub for an earlier third-party copy by comparing content and
  first-commit dates. Fifteen belonged to other people and became manifest links instead:
  eleven from `readwiseio/readwise-skills`, two wrapping the `counselors` and `librarium` CLIs,
  and four WordPress skills withheld because authorship could not be established.
- 44 skills are credited to **pstack by poteto (Lauren Tan)**, MIT. `cursor/plugins` has no root
  LICENSE and licenses each plugin directory, so a repo-root check reports "unlicensed" wrongly.
- Ten skills moved to the companion repos where their tooling lives —
  `wp-release-audit-method` (GPL-2.0) and `wp-dev-prompts` (CC0-1.0) — rather than being
  duplicated here under a third license.

### Notes
- Run counts are a snapshot over 2026-07-24 → 2026-09-05, not a live feed.
- Twelve external skills have no upstream license at all. They are linked, never copied.
