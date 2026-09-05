---
name: transcript-processing
description: "Use when the user says 'process transcripts', 'transcript sweep', or 'what came out of my meetings', or when Zoom, Spellar, or Drive-folder meeting transcripts need turning into notes and Things actions. Plaud recordings go to plaud."
---

# Transcript Processing (v3)

## Transcript sources

the user has four active transcript sources. The plugin treats them uniformly.

| Source | Drive folder name | Folder ID | Format | Notes |
| --- | --- | --- | --- | --- |
| Plaud.ai (current) | `_meetings` | `1myldke5cEDWhBqssE0ZvZXRZiaZ2F02v` | Markdown files named `YYYY-MM-DD — Title.md` | Primary source as of ~Feb 2026 |
| Plaud.ai (summaries) | `Meetings` | `15K9x_-sK_DPZ1Ch_gd3ItfNm8zvBhVpa` | Contains `Daily Summaries` and `2026/` subfolders | Secondary Plaud outputs |
| Spellar AI | `Spellar Meetings` | `1Q1-tmJnRe_WkxrPsQVpHM-jDGncrbh6b` | Google Docs grouped by date-bracketed subfolders | Legacy; use until cutover date |
| Zoom Cloud | `YYYY-MM-DD HH.mm.ss the user's Zoom Meeting` | varies per meeting | VTT + M4A + summary | Only process if a transcript file is present |

The inventory doc at `docs/transcript-inventory.md` keeps the current folder IDs.

## Processing flow

```
1. Discover → list new files in each source since last run watermark [USES: Zapier MCP]
2. Fetch    → export/download to local cache [USES: Direct OAuth MCP]
3. Parse    → detect format (Plaud md / Spellar doc / Zoom vtt)
4. Classify → meeting type (1:1, team, customer, community, internal review)
5. Route    → Obsidian path by meeting type
6. Write    → structured note (see template)
7. Extract  → action items, decisions, risks, entities
8. Stage    → Things for tasks, wiki inbox for entities, draft for Jira
9. Record   → update watermark + hash so re-runs are idempotent
```

## MCP hybrid pattern

**Discovery (step 1):** Use Zapier MCP (`mcp__5de407c6-…`) to list folder children. Cheap; no quota cost.

**Fetch (step 2):** Use Direct OAuth MCP (`mcp__87feeec4-…`) to download/export files. Expensive ops bypass Zapier's task ledger.

See `docs/drive-mcp-migration.md` for full rationale and gotchas (e.g., direct MCP doesn't support `parents` queries).

## Routing rules

| Meeting type | Obsidian path |
| --- | --- |
| 1:1 with manager or report | `Resources/Meetings/1-on-1s/YYYY/` |
| Internal team (standup, review) | `Resources/Meetings/Team/YYYY/` |
| Customer or partner | `Resources/Meetings/External/YYYY/` |
| DevRel community (Discord, Slack groups) | `Resources/Meetings/Community/YYYY/` |
| Event debrief | `Resources/Meetings/Events/YYYY/` |
| Unknown / ambiguous | `Inbox/meetings/YYYY/` — route on review |

## Action item handling (hard rule)

Action items are **always** created in Things 3 under the project that matches
the meeting owner. They are **never** written to Jira. When a Jira ticket is
implied, the action is created in Things with the tag `waiting:jira-approval`
and a pointer to the transcript. the user approves Jira creation explicitly.

For each action item extract:
- Owner (map to Things contact or `@self`)
- Due date (if stated; else none)
- Context line (verbatim quote with timestamp)
- Source transcript wikilink
- Proposed Jira project + summary (only as a draft in the note, not created)

## Entity extraction

Pull the following into the staging area at
`Projects/<your-wiki>/wiki/entities/_staging/`:

- People (name, role, affiliation)
- Projects, products, features
- Tools, plugins, MCP servers
- Repos (`org/repo`)
- External companies
- Decisions (one line, with rationale)

The `wiki-memory` skill promotes staged entities into the right wiki on nightly
ingest.

## Idempotency

Each processed transcript gets:

```yaml
transcript_hash: sha256-of-body
source: plaud | spellar | zoom
source_id: <drive file id>
processed_at: ISO timestamp
processor_version: 3.0.0
```

On re-run, matching `source_id` + identical `transcript_hash` is skipped.
When the hash changes (e.g. Plaud re-summarized), the note is re-processed and
a diff comment is appended.

## Failure mode

If a transcript can't be fetched or parsed, append an entry to the daily note
under `## Transcript errors` and retry on the next run. Never silently drop.

## See also

- `templates/transcript-note.md` — the note format
- `agents/entity-extract.md` — the extraction sub-agent
- `skills/wiki-memory/SKILL.md` — promotion into wiki
- `docs/transcript-inventory.md` — current source IDs and counts
