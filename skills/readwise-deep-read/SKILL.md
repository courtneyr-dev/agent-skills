---
name: readwise-deep-read
description: "Use when the user says 'process these URLs', 'deep read', 'morning reading queue', 'save and analyze', pastes several URLs, or asks to add inline highlights to a saved Reader document."
---

# Readwise Deep Read

## Purpose

Take a batch of URLs (YouTube, articles, podcasts) through the full deep-read pipeline: bulk save to Readwise Reader with the full 18-section analytical notes attached (per `article_template.txt`), then Reader-native inline highlights anchored to verbatim transcript/article paragraphs (via `reader_create_highlight`), then confirmation, vault mirroring, and Obsidian sync. Do NOT post classic-Readwise (v2) master-DB highlights via `readwise_create_highlights`.

## When to use

the user pastes multiple URLs, says "process these URLs," "deep read these," "morning reading queue," "save and analyze," references your morning Raycast → Reader → Obsidian workflow, or wants inline highlights added to an already-saved Reader doc. Not for ad-hoc web-search summaries, general topic questions, or a single news headline.

## Workflow

1. Phase 0 — pre-flight check
2. Phase 1 — bulk save via existing Python script
3. Phase 2 — add Reader-native inline highlights
4. Phase 2.5 — topic tags
5. Phase 3 — confirmation + completion check + Obsidian sync
6. Phase 4 — bulk mode (multi-doc inbox processing)

## Reading map

- When deciding whether or why to run this skill, or what it must not do, read references/purpose-and-triggers.md
- Before posting (or being tempted to post) any v2/master-DB highlight, read references/master-db-discontinued.md
- When writing the 18-section notes or checking vault landing (folder, truncation, cover), read references/output-requirements.md
- When checking a fresh save's content (transcript sentinel, empty html_content), read references/phase-0-preflight.md
- When running the bulk-save script (venv path, patches, doc_id capture), read references/phase-1-bulk-save.md
- When adding inline highlights or document-level topic tags, read references/phase-2-inline-highlights.md
- When closing out docs (deepread_check, mirror_notes, synthesis backlog, queue drain), read references/phase-3-confirmation-sync.md
- When batch-processing already-saved inbox docs, read references/phase-4-bulk-mode.md
- When a YouTube doc is missing subtitles or a transcript, read references/youtube-subtitle-fallback.md
- When an API call behaves oddly or Document Notes truncate, read references/reader-api-limitations.md
- When tagging atoms, choosing full vs lean template, or locating scripts/keys/queues, read references/tags-paths-templates.md
- When mapping a user request to phases, read references/examples.md
- When anything fails or looks wrong, read references/troubleshooting.md

Pre-existing skill-root files (do not move): `article_template.txt`, `template_library_reference.md`, `deepread_check.py`, `mirror_notes.py`, `create_video_doc.py`, `push_notes.py`.

**Attaching notes — use `push_notes.py`, not the MCP tool.** `reader_bulk_edit_document_metadata` requires the whole notes body inlined as a tool argument, which costs ~20k output tokens per document to retransmit text already on disk. Instead:

```
python3 ~/.claude/skills/readwise-deep-read/push_notes.py <doc_id> <path-to-md> \
    --tags "tag1,tag2,tag3" --author "Name"
```

It PATCHes `/api/v3/update/<id>/`, warns if the file has fewer than 15 `## ` sections or no `[!info]` provenance callout, and verifies by reading the field back. `--dry-run` checks without writing. A `notes`-only PATCH does not clobber `author` or `tags`. Requires the allow rule `Bash(python3 $HOME/.claude/skills/readwise-deep-read/push_notes.py:*)` in `settings.local.json` — without it the auto-mode classifier blocks the write and you must fall back to the MCP tool. Token is read from `~/.youtube_api_keys`; never print it.

**Check the markup before claiming a source is uncited.** The `<p>`-extraction pattern used throughout this skill strips `<a>` tags, so a linked citation vanishes from the plain-text transcript. Asserting "unnamed, undated, uncited" from stripped text produced **two wrong claims in one 2026-08-26 batch** — the Gates critical-thinking survey (linked to `mdpi.com/2075-4698/15/1/6`) and the Hassabis departure (linked to Axios), both reported in the analysis as unsourced before the markup was checked. Before writing any "no citation" finding:

```
python3 -c "
import json,re
d=json.load(open('<doc>.json')); h=d.get('html_content') or ''
for a in re.findall(r'<a\s[^>]*href=\"([^\"]+)\"[^>]*>(.*?)</a>', h, re.S)[:60]:
    print(re.sub(r'<[^>]+>','',a[1])[:60], '->', a[0][:90])
"
```

An absent link is a real finding; an unchecked one is not.
