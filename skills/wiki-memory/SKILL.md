---
name: wiki-memory
description: "Use when the user says 'remember this in the wiki', 'stage entities', or 'ingest sources' — the staging-and-promotion flow that turns passing signals into durable wiki pages. Routine maintenance passes go to wiki-cycle."
---

# Wiki Memory

The wiki is the plugin's long-term memory. Daily notes come and go; wikis
compound.

## Your wikis

Each wiki is a directory with its own `CLAUDE.md` defining its schema, and each is registered in
`wiki-cycle`'s `references/wikis.yml`. Read that registry to learn which wikis exist, where they
live, and what each one covers — this skill deliberately hardcodes no list, so the two skills can
never disagree about what is registered.

A wiki earns its place by having a subject narrow enough that a page clearly belongs or clearly does
not. "Everything interesting" is not a wiki; it is a notes folder with extra steps.

> **Never touch files outside a wiki's own folder.** Read across wikis freely,
> write only inside the destination wiki.

## Staging → promotion flow

1. Transcript processor or discover agent drops new items into a wiki's
   `wiki/entities/_staging/` or `wiki/sources/_staging/`.
2. Nightly ingest (`/cos:wiki-ingest`) reviews staging, deduplicates, and
   promotes into the proper section.
3. Each promotion updates `wiki/index.md` and appends an entry to `wiki/log.md`.
4. Stale entries (>7 days in staging with no new signal) are auto-closed with a
   `status: deferred` note.

## Cross-wiki linking

When an entity is found in multiple wikis:

- Other wikis link to it via full-path wikilink:
- The cross-wiki backlink index (`wiki/cross-wiki.md`) is rebuilt on nightly
  ingest.

## Lint rules (per-wiki, as declared in its CLAUDE.md)

Each wiki's `CLAUDE.md` declares a lint profile. Default:

- No orphan pages (every page linked from `index.md`)
- Summary paragraph under 50 words
- At least one source cited
- YAML frontmatter complete
- No forbidden words (per the style list in CLAUDE.md)

Lint output lives at `wiki/analysis/Lint YYYY-MM-DD.md` — a new one per run.

## Source ingest

Daily automations drop raw materials into `wiki/raw/` (immutable). The LLM
reads from `raw/`, summarizes, and files into `wiki/sources/`, `wiki/entities/`,
`wiki/concepts/`. Raw remains untouched.

## OKR touchpoint

When an entity relates to a Key Result from
`Meta/Strategy-Config-2025-H2.md`, the promotion step adds an `okr_touchpoints`
entry to the entity's YAML and a bullet to
`Meta/Rollups/YYYY-Q#-rollup.md`.

## Tools

- Obsidian MCP (`read_note`, `write_note`, `patch_note`, `search_notes`,
  `list_directory`)
- `scripts/wiki_lint.py` — reusable lint runner
- `scripts/cross_wiki_index.py` — rebuilds cross-wiki backlinks

## See also

- `skills/vault-intelligence/SKILL.md` — vault navigation (inherited from v2)
- `skills/transcript-processing/SKILL.md` — upstream of entity staging
- `commands/wiki-ingest.md` — nightly promotion runner

The authoritative list of wikis, their directories, sources, and cadences is `~/.claude/skills/wiki-cycle/references/wikis.yml` (18 entries as of 2026-09-04); this table is illustrative.
