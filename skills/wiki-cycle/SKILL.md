---
name: wiki-cycle
description: Use for "update the X wiki", "run the X cycle", or "ingest X content" for any wiki registered in references/wikis.yml. Runs one maintenance pass over one wiki — scan your notes for what changed in the window, ingest it by that wiki's own rules, lint, then write a report and run state.
---

# Wiki cycle

One maintenance pass over one registered wiki. Unattended: finish the run. The only stops are a name
matching two registry entries (ask which) and a registry that fails to load.

Writes go to three places: the wiki directory, the report file, and `state/<slug>.json` beside this
file. The wiki's own `CLAUDE.md` (or `AGENTS.md`) governs its content and wins inside the wiki; the
report and state files are this skill's outputs and are always allowed.

**Setup:** copy `references/wikis.example.yml` to `references/wikis.yml` and register your wikis.
Both `wikis.yml` and `state/` are gitignored — they describe your machine, not this skill.

## 1. Resolve the wiki

Read `references/wikis.yml`. Lowercase the phrase, drop "the", "wiki", "cycle", and "content", then
match the rest against each entry's `slug` and `aliases` (prefix or substring counts: "neuro"
matches `neuro-parenting`). One match: continue. Two or more: ask which. None: list the slugs and
end. Done when `slug` and `dir` are stated.

## 2. Load the rules and the window

Read `<dir>/CLAUDE.md` in full (plus `AGENTS.md` when present); it defines page format, lint checks,
and boundaries. No `CLAUDE.md`: run steps d and e only, and say so.

Read `state/<slug>.json`; `last_run` is the window start. No state: the window starts `cadence` days
before the run start (weekly = 7, monthly = 30), counted from the run's own timestamp, not midnight.
Done when the window is stated.

## 3. The cycle

**a. Note scan.** For each `source_folders` path:
`find "<path>" -type f -name '*.md' -newermt "<window start>"`. Missing paths are named in the
report and skipped.

Watch for **bulk-write artifacts**: folders synced from an external service (a read-later app, a
notes exporter) rewrite whole files on every sync, so every file looks new. For those folders a hit
counts only if its `updated` frontmatter or its body actually changed in the window. Mark them with
`bulk_synced: true` in the registry. Without this the scan returns the entire folder every run and
buries the real changes.

Read the first 40 lines of at most 60 hits, non-bulk-synced folders first; hits past 60 are listed
as `not read` in the report. Keep those inside the domain the wiki's `CLAUDE.md` Purpose states.
Done when the report lists found, read, and kept counts plus the kept paths.

**b. Chat scan** (when `chat_channels` is non-empty). Optional, and skipped entirely when no chat
integration is connected.

Confirm each channel id once before searching, then search each channel from the window start.
Treat a thread as substantive when at least three messages from at least two people, excluding join
and leave notices, discuss one topic. Each substantive thread gets a source page at
`wiki/sources/chat-YYYY-MM-DD-<topic>.md`: channel, date, participants, paraphrase, links to related
pages. Chat unavailable: record it and continue. Done when the report shows a message count per
channel and the pages written.

> **Worked example — Beeper Desktop.** Confirm ids with `get_chat` first: a wrong id and an empty
> window both return "No matching chats found" from search, so an unconfirmed id looks exactly like
> a quiet week. Then `search_messages` with `chatIDs`, `dateAfter` = window start,
> `chatType: group`, `excludeLowPriority: false`, and **no** `limit` — passing `limit` returns
> `400 Invalid input`, and `dateAfter` already bounds the result, so no cursor loop is needed.
> Other clients page differently; check whether yours caps results per page, or a busy channel will
> silently under-scan.

**c. Ingest** each kept item by the wiki's own ingest workflow — this run stands in for that
workflow's "wait for confirmation" step. Read fully, create or update pages, update `index.md`,
append to `log.md`. Existing pages get surgical edits to the sections the source actually changes,
not a rewrite. Done when every kept item has a `log.md` line.

**d. Lint** with the checks the wiki's `CLAUDE.md` names. Default set: orphans, dead links, missing
pages, contradictions, stale content, incomplete frontmatter.

Report everything found. Fix frontmatter and dead links **only** in pages created or updated this
run; list every other finding as open, with its page. A cycle that silently repairs pages it did not
otherwise touch makes its own report untrustworthy — you can no longer tell what the sources
changed from what the linter did.

Verify the linter before trusting a dramatic number. A dead-link check that resolves links the wrong
way will report hundreds of failures that do not exist, and a count nobody spot-checks becomes a
fact. Done when the lint entry is in `log.md`.

**e. Report and state.** Write `<report_dir>/wiki-cycle-<slug>-YYYY-MM-DD.md`: outcome first, then
sources ingested, threads captured, pages created and updated (paths), contradictions, gaps, skipped
folders, open lint items.

Write `state/<slug>.json`:

```json
{"slug": "example", "last_run": "<run start, ISO 8601>",
 "counts": {"found": 31, "read": 31, "kept": 4, "chat_messages": 120, "threads": 2,
            "pages_created": 3, "pages_updated": 5, "lint_open": 2},
 "skipped_folders": []}
```

`found` = files the scan matched, `read` = files opened, `kept` = files ingested, `chat_messages` =
messages returned across all channels, `threads` = source pages written from chat, `pages_created`
and `pages_updated` = content pages only (lint-only edits are not counted), `lint_open` = findings
left open. If the entry's `first_clean_run` is null and all five steps finished, say so — a human
sets that date after reading the report. Done when both files exist.

## Quoting

Paraphrase by default. Copied words sit inside quotation marks with the author's display name, the
channel or file, and the date; everything else on the page is your own wording.

<example>
Two contributors in #training discussed batching facilitator-guide reviews every two weeks; one
counted 14 open drafts. Kept verbatim because the phrasing is the point: "one guide at a time is why
the queue never clears" — @maple_dev, #training, 2026-09-03.
(Source: [[chat-2026-09-03-facilitator-review-cadence]])
</example>

## If context compacts

Keep `slug`, `dir`, the window start, kept items, pages written, lint findings, and the open step;
resume there.
