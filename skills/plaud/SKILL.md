---
name: plaud
description: "Use when the user says 'Plaud', 'my recordings', 'what did I record', or wants a Plaud transcript, summary, digest, follow-up, or export. Meeting transcripts from other sources go to transcript-processing."
---

# plaud

Server: `plaud` (`mcp__plaud__*`). Reference: [references/plaud-api.md](references/plaud-api.md).

## Before any call

- On `401`/`Not authenticated`, call `login`, wait for it to return, retry once; never ask the user for a token.
- The Plaud API ignores `query`/`date_from`/`date_to`; the MCP `list_files` tool filters client-side over the newest 500 (`page`/`page_size` apply only unfiltered).
- `get_transcript` is the largest payload: only where a mode names it, one page per call via `next_cursor` (scratchpad past three pages).
- Relative dates resolve against today's date (reference table).
- Show recordings as name, `YYYY-MM-DD`, `5m23s`, file ID.

## Quoting

Paraphrase by default; copied wording goes in quotation marks with its source: `[MM:SS] Speaker` for a transcript line, `(Plaud summary)` for the note. A requested summary renders whole as a blockquote labeled `Plaud summary:`, synthesis kept separate. Facts come from the notes or transcript; unknowns are `?` or `TBD`.

<example>
- Weekly Sync (2026-09-01, 32m10s) — Launch moved to the 15th; Sam owns the migration checklist. Open question in the note: "who signs off on the DNS cutover" (Plaud summary).
</example>

## browse — "what recordings do I have", "next page"

`list_files(page=1, page_size=20)`; next page is `page+1`. Done: one page as a table, noting whether more exist (short page: no).

## find — "find the Weekly Sync", "the meeting from Monday", "the call about Q2"

`list_files(query=, date_from=, date_to=)` with only the criteria given (none: page 1 of recents). Zero matches: widen once (shorter keyword, ±7 days). Over 10: top 10 by date plus the total. Find never auto-loads a transcript. Done: match list on screen; the user picks one to read.

## read — "show the transcript", "summarize this", "get audio"

`get_note(file_id)` first (summary, action items, highlights); `get_transcript(file_id)`, paged, for verbatim lines or speaker attribution; `get_file(file_id)` for metadata or the audio `presigned_url` (expires in 24h; say so). Content exists only when `note_list`/`source_list` is populated. Done: rendered as the reference specifies.

## digest — "weekly report", "recap of last quarter"

`list_files(date_from=, date_to=)` for the window, then `get_note` per recording, newest first, up to 50, reporting the rest. Append each takeaway line to a scratch file and assemble from it (survives compaction). Shape: headline; one line per recording as in the example; themes in two or more recordings; deduplicated open action items; "unsummarized" for empty notes. Done: every claim names its recording.

## follow-up — "draft follow-up", "what were the action items"

Find or browse if unnamed; `get_note`, then `get_transcript` only for quotes or who-said-what; templates in the reference. Never invent email recipients: `To: ?` when attendees weren't captured. Done: draft in chat, unsent; sending is export.

## export — "save to Notion", "post to Slack"

Plaud has no push tool: list the loaded MCP tools; if none matches the destination, say so and stop. Confirm the payload when more than one candidate exists, and the exact destination (channel, page, recipient, URL) before every send; no defaults. Content goes unchanged apart from format conversion. Done: delivery URL or HTTP status reported.
