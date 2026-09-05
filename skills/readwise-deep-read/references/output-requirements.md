# Output requirements: vault landing and Reader notes structure

## Vault landing requirements (MANDATORY, the user 2026-08-16)

Every doc this skill saves — article or YouTube video alike — must, once synced:

1. **Land in `Resources/Readwise/Articles/`**, never `Books`/`Podcasts`/wherever the plugin's own category mapping might otherwise route it.
2. **Show the FULL Document Notes content** — never truncated, whether by the 8191-byte `document_note` limit, the plugin's own native sync, or anything else. See the truncation failure mode documented under Phase 3 step 0.5 below.
3. **Have a featured/cover image** in the frontmatter `cover:` field.

`deepread_check.py` enforces all three automatically as of 2026-08-16 (`wrongfolder`, `truncated`, `nocover` failure states, checked whenever the vault check runs — i.e. whenever `--no-vault` is NOT passed). A doc is not done until this check passes with zero fails, on all three.

4. **Carry all 18 sections.** `deepread_check.py` enforces this as of 2026-08-28 (`INCOMPLETE — missing N/18`). Until then the only completeness test was `"Refactor Appendix" in notes`, so a 2.5KB doc holding Summary + Notes + Conclusion + an appendix stub passed green. Section matching is on the heading NAME with the emoji optional — older notes use plain `## Summary`, and an emoji-required matcher wrongly flagged 1,827 docs.
5. **Put the sections at TOP LEVEL, not inside the callout.** Obsidian Publish and the outline pane index only top-level headings. Measured 2026-08-28: all 9,884 deep-read files had exactly ONE indexed heading — the plugin's `## Highlights` — because the analysis headings sat inside the callout as `> ## ...`, so the published page offered no way to reach any section. `mirror_notes.py` now writes a short provenance callout and emits every `## ` section below it, bracketed by `<!-- deep-read:sections start/end -->` so a re-mirror replaces its own output. `--fix-structure` migrates legacy files offline.


## How completeness is enforced (the ladder, 2026-08-28)

Three rungs, ordered by how well each survives being ignored. Reach for the lowest one
that can hold the rule — a written instruction is the only rung whose enforcement is
probabilistic.

1. **Write gate (architecture).** `push_notes.py` **refuses** to PATCH notes missing any
   required section and exits non-zero. It imports `missing_sections` from
   `deepread_check.py`, so the writer and the checker cannot disagree about what
   "complete" means. `--force` exists for a source where a section genuinely cannot
   apply — say so in the section body rather than deleting the heading.
2. **Nightly regression detector (toolchain).** `~/bin/deepread_sweeper.sh` (launchd
   `com.you.deepread-sweeper`, 06:30) diffs today's failing doc-ids against
   yesterday's and notifies only on **new** failures. It previously reported the total,
   which sat at 600–900 every night for weeks — a constant number is not a signal, and
   drift survived a working alarm because of it. Sundays it also runs the vault-side
   check, since Publish reads the vault and a Reader-only pass cannot see vault damage.
3. **PreToolUse hook (architecture, write-path-independent).**
   `~/.claude/hooks/gate-incomplete-deepread-notes.py`, wired in `~/.claude/settings.json`
   on matcher `mcp__.*Readwise.*(bulk_edit_document_metadata|create_document)`. It **denies**
   any MCP write whose `notes` look like a deep-read (>=3000 chars with a provenance callout
   or Refactor Appendix) but fail the section check, and ignores short notes and tag-only
   edits. Rung 1 only covers `push_notes.py`; on 2026-08-28 a batch of 298 docs was written
   through the MCP tool instead, with 12-22K of analysis and no appendix. A rule enforced on
   one write path is not enforced.

4. **This document (instruction).** Weakest rung. If you find yourself relying on it to
   prevent a recurring, mechanically checkable failure, push the rule down to rung 1 or 2.

## Reader Notes Output Structure (MANDATORY — non-negotiable)

**Every Reader doc saved must include the full 18-section deep-read output in the `notes` field.** Do not abbreviate, condense, or skip sections. The canonical structure lives at `~/.claude/skills/readwise-deep-read/article_template.txt` (also at `~/Documents/scripts/article_template.txt` for the Python script — **note: that path does not exist on the current machine**; the skill-local copy is authoritative here).

### Provenance stamp (required)

The `notes` field is machine-written analysis, not the author's words — and several of its
sections (Permanent Candidates, Paraphrase, Newsletter) are written *in the user's voice*,
while Action Items attribute work to teams no source mentions. Anything reading these notes
downstream can misattribute a machine's synthesis to a named human.

Every generated `notes` block must open with this line, immediately under the YAML:

```
> [!info] Generated analysis — not the author's words. Sections below are machine-written
> from the captured source. Only text inside `> [!quote]` blocks is verbatim from the author.
> Do not quote or attribute any other line to the named author.
```

Two related defects to fix on sight while writing notes:

- **Unrendered template literals.** `date created: {{date:YYYY-MM-DD}} {{time:HH:mm}}` has been
  shipping into the YAML. Substitute the real date or drop the key.
- **WPOCC naming.** Always "The WPOCC" / "The WP Open Community Collective." Never "The WPCC" —
  the organization rebranded 2026-07-24. The Action Items boilerplate still carries the old name
  in places; fix it as you go.

Required sections in this exact order:

1. **YAML frontmatter** — tags, author, source, reference, date created
2. **🏷️ Title**
3. **🧭 Table of Contents**
4. **🔗 References** (in-page)
5. **📝 Summary** — what happened, why it matters, stakeholders, risks, bottom line
6. **📖 Main Content** — with **🗒️ Notes** subheading (timestamped segments for transcripts)
7. **📚 References** — primary sources preferred
8. **🗣️ Paraphrase** — paragraph-by-paragraph
9. **📰 Newsletter** — WordPress-focused, witty, with links
10. **✅ Action Items** — DevRel / OSPO / Community / WordPress (all 21+ subteams: Core, Core Performance, Core AI, Core Program Team, Mobile, Playground, Community, Training, Marketing, Support, Design, Documentation, Photos, TV, Polyglots, Accessibility, Meta, CLI, Hosting, Tide, Openverse, Themes, Plugins) / The WPCC / FAIR
11. **🧪 Hypotheses** — 3–6 testable, derived from article
12. **📊 Methodology** — study designs, data sources
13. **❓ Questions** — sharp, forward-looking
14. **🔮 Future Research** — gaps and directions
15. **💡 Implications** — practice, policy, security, education, funding
16. **🧠 Learning Styles Assessment** — all 8 learner types (Visual, Aural, Verbal, Kinesthetic, Logical, Social, Solitary, Naturalistic) with reading level estimate
17. **📊 Accessibility Assessment** — all 7 subcategories mapped to WCAG 2.2 AA
18. **🌍 DEIB Assessment** — Cultural breadth, Inclusive language, Neurodiversity support, Representation, Psychological safety
19. **✅ Logical Validity** — Strong reasoning + Fallacies (named, located, explained, fix proposed) + Tone of voice
20. **🛡️ DARVO Analysis** — Deny / Attack / Reverse victim-offender
21. **🎯 Conclusion** — bottom line + next steps
22. **🧱 Refactor Appendix** — Literature Split Pad (H3) + Atomic Split Pad (H4) + Fleeting Queue
23. **🧰 Template Library** — Fleeting, Literature, Atomic refactor templates

**If any section would be empty or N/A, write "Not applicable to this source" with a one-line reason rather than omitting the heading.** the user's PARA/Zettelkasten workflow depends on consistent structure across all docs.

### Backfilling what already drifted

`backfill_tags.py --since YYYY-MM-DD [--limit N] [--dry-run]` repairs docs that got the full
analysis but never got Phase 2.5's document-level tags — the tags are already declared in the
notes YAML, so it reads them, drops anything the tag policy forbids, and applies the rest. It
invents nothing and skips any doc whose notes declare no usable tag. 621 docs needed this in a
7-day window on 2026-08-28.

`mirror_notes.py --since YYYY-MM-DD` repairs vault copies that landed truncated while Reader
holds the full notes. `--fix-structure` migrates legacy files to the top-level-headings layout
offline. Neither can help a doc whose Reader notes are themselves incomplete — that needs
re-analysis, and the write gates above are what stop new ones from being created.
