# Plaud MCP reference

Loaded by the `plaud` skill. Server `plaud` (`mcp__plaud__*`), seven tools. When a second Plaud server without `login` and `logout` is also loaded, use `plaud`: it is the one that can re-authenticate.

## Auth and session

| Tool | Behavior |
|---|---|
| `login` | Opens the browser for OAuth; returns on the callback or after a 2-minute timeout |
| `logout` | Revokes and clears the cached tokens |
| `get_current_user` | Returns the signed-in account; call it when a result looks like someone else's library |

Tokens cache in `~/.plaud/tokens-mcp.json`: access token 24h, refresh token 7d, refreshed by the server on its own. A `401` means the cached pair is dead and `login` replaces it.

## Errors

| Error text | Meaning | Response |
|---|---|---|
| `401`, `Not authenticated` | Token missing or expired | `login`, then retry the call once |
| `404` | No recording with that ID | Report the ID as wrong; a retry returns the same |
| `500` | Backend error, often an invalid ID | Retry once; a second `500` means not found |
| `fetch failed`, `ECONNREFUSED` | Network | Stop; report the connection problem |

## `list_files`

| Param | Default | Notes |
|---|---|---|
| `page` | 1 | Ignored when any filter is set |
| `page_size` | 20 | Ignored when any filter is set |
| `query` | — | Case-insensitive substring match on `name` |
| `date_from`, `date_to` | — | `YYYY-MM-DD`, inclusive, interpreted in the server's timezone |

The underlying API returns pages in `created_at` descending order and ignores every filter param. With any filter set, the MCP tool scans up to 5 pages × 100 recordings (the newest 500) and returns all matches in one response, so a filtered search cannot reach a recording older than the 500th. Without filters, a page shorter than `page_size` is the last page.

Each row carries `id`, `name`, `created_at` (and `start_at`), and `duration` in milliseconds. The developer API returns timestamps as ISO strings without a timezone suffix, and they are UTC: convert before showing a local date. A recording near midnight local time can sit on the neighboring UTC date, so widen a date filter by one day when a recording the user knows exists is missing.

### Relative dates

Resolve against today's date from the conversation context.

| Phrase | `date_from` | `date_to` |
|---|---|---|
| today | today | today |
| yesterday | yesterday | yesterday |
| this week | Monday of this week | today |
| last week | Monday of last week | Sunday of last week |
| this month | 1st of this month | today |
| last month | 1st of last month | last day of last month |
| from Monday | most recent Monday | omit |

## `get_file(file_id)`

Full record for one recording.

- `presigned_url` — audio download link; expires 24h after the call, and a fresh `get_file` mints a new one.
- `source_list` — array; the item with `data_type: "transaction"` holds the transcript segments as a JSON-encoded string in `data_content` (or behind a `data_link`).
- `note_list` — array; the item with `data_type: "auto_sum_note"` holds the AI summary as Markdown in `data_content`.
- `duration` — milliseconds.

Empty `note_list` means Plaud has not summarized the recording; empty `source_list` means there is no transcript. Check both before reporting that content exists.

## `get_note(file_id)`

Returns one entry per tab in the Plaud app: the AI summary (action items, key topics), any template tab, a saved Ask Plaud answer, and the highlights note when the highlight button was pressed during recording. Markdown. Render it as-is under a `Plaud summary:` label when the user asked for the summary itself.

## `get_transcript(file_id, block, cursor, limit)`

| Param | Default | Notes |
|---|---|---|
| `block` | `transaction` | Raw transcript with speaker names and timestamps. `transaction_polish`: AI-cleaned, same per-utterance shape. `outline`: section outline. `mark_memo`: moments flagged with the device button, returned under `marks`, present only when the button was pressed |
| `cursor` | — | The previous response's `next_cursor`; omit to start at the first utterance |
| `limit` | 50 | 1–500 items per page; list-shaped blocks only |

Paging: call once, read `next_cursor`, call again with `cursor` until `next_cursor` is absent. Past three pages, save each page to the scratchpad and extract per page instead of holding the whole transcript in context. Pair `mark_memo` with `transaction` to map each flagged moment onto what was said there.

## Digest procedure

- Cap: 50 `get_note` calls per digest, newest first. When the window holds more, digest the newest 50 and state the count left out; narrowing the window is the user's call after you sees the number.
- Skip recordings with an empty `note_list` and list them at the end under "unsummarized".
- Scratch file: append `name | date | duration | takeaway` as each note returns, then build the digest from the file, so a compaction mid-run loses nothing.
- Shape: headline (one line for the window); by recording (one line each, as in the SKILL.md example); recurring themes (two or more recordings); open action items (deduplicated, each naming its recording); unsummarized.
- Scope is the window the user asked for. A transcript enters a digest only when one recording's note is empty and the user asked about that recording.

## Structured extraction

When the user supplies a schema such as `{"action_items": [], "decisions": [], "attendees": []}`: `get_note` first (it usually holds these fields), `get_transcript` only for a field the note lacks, then return JSON matching the schema with `null` plus a one-phrase reason for anything missing.

## Output formats

| Content | Format |
|---|---|
| Recording list | Table: ID, name, date `YYYY-MM-DD` (local), duration |
| Duration | `23s`, `5m23s`, `1h05m`; milliseconds stay in logs |
| Transcript | `[MM:SS - MM:SS] Speaker: content`, timestamps untouched |
| Plaud summary | Blockquote under a `Plaud summary:` label, Markdown as returned |
| Own synthesis | Paraphrase; copied wording in quotation marks with `[MM:SS] Speaker` or `(Plaud summary)` |
| Audio | The `presigned_url` plus "expires in 24h" |

## Follow-up templates

- Follow-up email: `To:` attendees from the note, or `?`; `Subject: Follow-up — {recording name}, {date}`; one-line thanks plus meeting summary; 3–5 key-point bullets; numbered action items with owner and due date (`TBD` when unstated); closing "Let me know if I missed anything."
- Thank-you note: one paragraph with one concrete thing learned or appreciated from the call.
- Action-item list: `- [ ] {owner}: {item} (due {date})`, owner `?` when the note doesn't say.
- Meeting brief: attendees, date, duration, decisions, risks, next steps.

## Export destinations

Plaud has no push tool; delivery uses whichever MCP tool is loaded for the destination. Credentials stay with the MCP host. Convert format (Slack mrkdwn, Notion blocks) without changing meaning.

| Destination | Identifier to confirm |
|---|---|
| Notion | page ID or database ID |
| Slack | channel name or ID |
| HubSpot / Salesforce | deal, contact, or company ID |
| Linear | team or project ID |
| Gmail | recipient address(es), from the note or from the user |
| Webhook | full URL |

Report back the Notion page URL, Slack permalink, message ID, or webhook HTTP status.
