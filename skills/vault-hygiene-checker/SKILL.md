---
name: vault-hygiene-checker
description: "Use after any synthesis pass, or when the user says 'check the vault', 'check today's vault work', 'verify my synthesis', 'vault hygiene', or 'did the connections land'. The checker half of the maker/checker split."
---

# Vault Hygiene Checker

## Why this skill exists

This is the **checker** in Osmani's maker/checker loop pattern, applied to the user's Zettelkasten instead of to code. The agent that *writes* permanent notes and MOC links is "too nice grading its own homework" — it claims a note links to 5 atoms without verifying those atoms exist, links resolve, or the note isn't a near-duplicate. Your own vault history has the cautionary tale (the "integration suite was always red — review-theater lesson": 11 PRs merged green that were actually broken). Same failure mode, different domain.

This skill runs a **separate, skeptical pass** whose job is to *refute* the synthesis, then report findings to the user for approval. You stays the decision-maker — findings come to your, fixes happen only on your yes.

It also pairs with the Karpathy "Goal-Driven Execution" principle in your CLAUDE.md: a synthesis pass should have a verifiable stop condition ("every new permanent note links to ≥2 existing atoms, is in exactly one MOC, quotes ≥1 verbatim source"), and this checker is what verifies it.

## Two halves: mechanical (automated) + judgment (read)

**Mechanical checks** — objective, zero judgment, run via the script. These can run unattended:

```bash
python3 ~/.claude/skills/vault-hygiene-checker/check_vault.py --since YYYY-MM-DD
# or:  --days N   |   --files "Note A" "Note B"   |   --scope "Resources/Permanent Notes"
# add --fix-reciprocal to WRITE the missing note→MOC backlinks (see check 6)
```

The script (read-only by default) reports:
1. **🔗 Dead wikilinks** — `[[target]]` whose file doesn't exist anywhere in the vault (resolves by basename or full path; handles `|alias` and `#heading`). Same-file heading anchors (`[[#H1]]`) are valid Obsidian syntax and are never flagged.
2. **⚠️ Fragile links** — the file EXISTS but the wikilink can't reach it: `#` anywhere in the filename (leading `#219 …` or mid-name `… Changelog #133 …` — Obsidian reads from the `#` as a heading anchor), or `[`/`]` in the filename (breaks wikilink parsing). Each finding names the cause. Renaming the file is NOT durable — the Readwise plugin recreates these filenames on every sync (2026-08-24 finding); use a markdown link with the URL, or wait on the mirror-time title-normalization decision.
3. **🧬 Duplicate-import files** — linked source has a `-2`/` 2` sibling (a re-imported Readwise doc). Flag the dup; keep the fuller one.
4. **🗺️ Not registered in any MOC** — orphaned permanent notes referenced by no MOC. Every atom should hang off at least one MOC.
5. **👯 Possible duplicate titles** — token-overlap ≥ threshold against all permanent notes (collision risk grows with the corpus; ~130+ notes today).
6. **♻️ Missing note→MOC reciprocal links** — a MOC references the note but the note doesn't link back. Checked only for files under Literature Notes / Permanent Notes — same-basename Readwise mirrors scooped in by `--files` were the 2026-08-21 false positive. This is the mechanical, note→MOC subset of judgment check 8, the single most-repeated manual repair in the synthesis-pass loop reports. Report-only by default; pass **`--fix-reciprocal`** to insert each missing `[[X MOC]]` backlink into the note's `## Links` section (creating the section if absent). The inserted link carries a `⚠️ … annotate the relationship` placeholder — the checker never invents the semantic relationship; the maker replaces the placeholder with the real one (`extends`/`applies-in`/`contrasts`/…), then re-run to confirm. Bounded by the target set (`--since`/`--files`/`--scope`) and idempotent. **Inserting placeholders is not completing the repair**: any run that uses `--fix-reciprocal` must count outstanding placeholder markers vault-wide and report that count as an open finding until it reaches zero — unannotated placeholders make the vault look more connected than it is.
7. **🎲 Backlog sample audit** — every run spot-checks N random backlog rows marked `atoms: done` (default 10, `--audit-sample N`, 0 disables) and flags any whose title matches no Literature/Permanent note: possible phantom done-rows (2026-08-21 found ~7 marked done with no file behind them). Title matching is fuzzy — verify a flag by hand before acting; a note under a variant title is the known false-positive mode.

**Judgment checks** — need a reading pass; do these for the target notes after the script runs:
6. **Ungrounded claims** — does each major claim in the note trace to a verbatim quote or a cited source highlight? Flag assertions with no source anchor.
7. **Semantic duplicates** — does this note restate an existing atom under a different title? (Token-overlap misses paraphrase.) Check against the strongest atom clusters in [[obsidian-vault-moc-infrastructure]] memory.
8. **Link reciprocity** — if note A says "see [[B]] — *because extends*", does B exist and is the relationship accurate? One-directional or mislabeled links are synthesis debt. The note→MOC subset of this is now mechanized (check 6 + `--fix-reciprocal`); this judgment pass still owns note↔note reciprocity and relationship-label accuracy.

## Workflow

1. Determine the target set. Default: notes from the most recent synthesis batch (`--since` the batch date, or `--days 2`). If unsure which batch, check the `2026-..` dated entries in the `obsidian-vault-moc-infrastructure` memory.
2. Run `check_vault.py` for the mechanical findings.
3. Verify the checker's own flags before reporting — a flag via a parsing quirk is still review theater. (The `#`-filename case is the canonical example: confirm the physical file before calling a link dead vs. fragile.)
4. Read the target notes for the judgment checks (6–8).
5. **Report findings to the user as a prioritized list — do not fix yet.** Group by severity: broken/fragile links first (they break navigation), then orphans, then possible duplicates, then ungrounded claims.
6. On your approval, fix. Plain-language summary of each fix; exact file paths.

## Conventions to respect

- Vault root: `$VAULT_DIR/` (NOT the `Documents/your vault` stale copy).
- Permanent notes: `Resources/Permanent Notes/`; MOCs: `Resources/MOCs/`.
- Permanent-note format and MOC-writing convention live in the [[obsidian-vault-moc-infrastructure]] memory — match them when proposing fixes.
- Read-only by default. This skill verifies; it does not write to the vault without explicit approval.
- Reader tag policy and the deep-read pipeline that feeds the vault: see the `readwise-deep-read` skill.

## Scope boundary

This checks **vault hygiene** (links, registration, duplication, grounding). It does NOT re-do synthesis (that's the maker's job) and does NOT process Readwise docs (that's `readwise-deep-read`). If the check reveals missing synthesis (e.g. an orphan that needs a real MOC home), surface it as a finding for a follow-up maker pass — don't silently expand scope.
