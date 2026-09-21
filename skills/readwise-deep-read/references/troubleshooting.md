# Troubleshooting

## Troubleshooting

**`ModuleNotFoundError: No module named 'requests'` (or `anthropic`, `youtube_transcript_api`).**
You used bare `python3`. The pipeline's dependencies live only in
`~/Documents/scripts/.venv`. Re-run with the absolute venv interpreter:
`~/.venvs/readwise-scripts/bin/python3 ~/Documents/scripts/youtube_to_readwise.py <urls>`.
Activating the venv works too, but the absolute path is what this skill documents everywhere
because it survives being copied into a launchd job or a subagent with a bare environment.

**`HTTPError: 429` from `deepread_check.py --ids ...` on a batch.**
Fixed 2026-08-22 — `get()` now retries with exponential backoff (5/10/20/40/60s, honoring
`Retry-After`, six attempts) matching `mirror_notes.api()`. Readwise rate-limits v3/list at
roughly 20 requests/minute and `--ids` fires one request per doc, so a long batch will trip it
legitimately; the script now waits instead of dying. If you still see a 429 escape, the batch
exceeded six consecutive retries — split it, don't remove the gate.

**Phase 2 paragraph index contains a huge blob of SVG coordinates.**
The extraction regex matched `<path>` as if it were `<p>`. Use `<p(?:\s[^>]*)?>.*?</p>`, never
`<p[^>]*>` — see Phase 2 Step 3. Rebuild the index before selecting any highlight by index; a
poisoned index shifts every subsequent index, so highlights anchor to the wrong paragraph.

**`--show-queue` lists docs under "awaiting current-agent deep-read analysis" that are done.**
Those entries were never drained. Run
`~/.venvs/readwise-scripts/bin/python3 ~/Documents/scripts/youtube_to_readwise.py --mark-analyzed <doc_id>`
for each finished doc — see Phase 3 step 4.

**A doc FAILs `deepread_check.py` forever, or `needs_analysis` looks enormous.**
Check whether the id was **superseded** before doing any work on it. A doc whose scrape failed
gets *recreated* at `<original url>#transcript`, not repaired — `html_content` is write-once —
so the real analysis lands on a new doc_id and the original is archived. Everything in this
pipeline is keyed on doc_id, so the dead id fails every check while the finished work sits one
id away. `deepread_check.py` now detects this and reports `⏭ SUPERSEDED by <id>` instead of a
FAIL (superseded does not gate the exit code); drain the stale entry with `--mark-analyzed`.

Measured 2026-08-22: a reconciliation of 166 `needs_analysis` entries reported 4 outstanding
when only 1 was — 162 were complete under their own id, 3 more under successor ids. Two
subagents were dispatched to redo finished work before the pattern was spotted. Nothing in the
pipeline reconciles this list, so it accumulates dead pointers indefinitely.

Two traps when checking successors by hand:

- **The API cannot do the lookup.** `v3/list` silently ignores `source_url=` and `sourceUrl=`
  and returns the whole library (verified: `count=10000` either way). Match through the vault's
  frontmatter `source:` index instead, which is also better evidence — a mirrored successor is
  one whose work actually landed.
- **Match on the `readwise_doc_id:` stamp, never the filename.** Near-duplicate titles ("You
  Ask, I Answer …") resolve to the wrong sibling, and a recreate can leave two complete docs
  sharing one `source_url`. That happened in the same session: `reader_create_document` mints a
  new id regardless of URL, so it does **not** inherit the idempotency that `POST /api/v3/save/`
  has. If you find two, keep the one the vault file is stamped to and delete the other — two
  docs with highlights and one `source_url` become two published pages.

**Reader notes are condensed / missing sections.**
The `notes` field must contain the full 18-section template output. If sections are missing, the Python script likely truncated mid-generation (apply the `max_tokens=16384` patch) OR a manual save bypassed the template (route all saves through the script, not direct API calls).

**Phase 1 script truncates analysis mid-section.**
Apply the `max_tokens=16384` patch. Symptom is the Refactor Appendix being cut off or DEIB/Accessibility sections being incomplete.

**Fallacy highlights don't get the right tag.**
Apply the whitespace-normalization patch — "Straw man" with the space won't match "Strawman" in `KNOWN_FALLACIES`.

**Phase 2 can't find matching passages in html_content.**
Run Phase 0 pre-flight check first. If html_content is the "no subtitles" sentinel, cascade through the YouTube fallback hierarchy. For paywalled articles, you may need to manually paste the article text into a `markdown=<text>` save.

**YouTube doc has empty html_content.**
Cascade through the YouTube Subtitle Fallback Hierarchy above. The most common cause is that YouTube hasn't generated auto-captions yet for a recently-uploaded video; retry in 24 hours via the queue.

**Inline highlights appear in Reader but don't sync to Obsidian.**
Confirm the Readwise Official Obsidian plugin is set to sync Reader highlights (not just master Readwise highlights). The plugin's sync settings differentiate these. If highlights sync but the canonical file still lacks `> [!note]+ Document Notes`, do **not** try to coax the v2 book into emitting it — `document_note` is empty for anything saved with notes at creation time and cannot be written. Run `mirror_notes.py --ids <doc_id>` instead. A callout found only in `Full Document Contents/` does not repair the highlight file used by Obsidian Publish.

**The dropdown exists but stops after the metadata.**
The callout is being terminated by a setext heading underline — see the `document_note` entry under Reader API Limitations. Repair the whole vault offline with `mirror_notes.py --fix-structure` (no API calls), or a single file with `--ids`. Verify on the *published* page, not just the file: a file can be byte-identical to Reader and still render wrong.

**The doc was saved with short notes; how do I add the full template now?**
Run the template against the article text again and use `reader_bulk_edit_document_metadata` to update the Reader `notes` field — that field IS updatable post-save (unlike `html_content`). Then run `mirror_notes.py --ids <doc_id>` to push the full text into the vault file. Do not expect the v2 book's `document_note` to follow; it is read-only and caps at 8191 bytes even when it does populate.

**Documents appear already analyzed, tagged `public_api`, and no MCP call wrote them.**
That is this pipeline. `youtube_to_readwise.py` (the save, via `/api/v3/save/`) and `push_notes.py` (the notes and tags, via `/api/v3/update/`) both call the REST API with `READWISE_TOKEN` from `~/.youtube_api_keys`, so Reader records them as `public_api`; only `reader_create_highlight` and other MCP tools go through the MCP server. They run from Bash inside the Claude Code session that invoked the skill, which keeps working after the person steps away. Verified 2026-09-21: every "unknown writer" timestamp (2026-09-20 23:26:39–44Z, then 12:13, 12:25, 12:37Z the next morning) matched this session's script calls to within a minute, and document ULIDs decode to the same instants. The ~12-minute "cadence" was the gap between three `/readwise-deep-read` invocations, not a scheduler.

Before assuming a second writer, decode the document id — Reader ids are ULIDs and the first 10 characters are the creation time — and compare it with the session transcript's Bash calls.

What is and is not scheduled, as of 2026-09-21:
- `com.you.deepread-sweeper` (06:30 daily) — **read-only**; runs `deepread_check.py --no-vault` and writes a local report.
- `com.you.youtube-queue-retry` — described in phase-0 and phase-1 as the daily retry writer. **Not installed**: no plist, not loaded, and `~/bin/retry_youtube_queue.sh` is absent. Nothing currently retries `pending_transcript` (44 items on 2026-09-21).

There is no write lock. `push_notes.py` overwrites `notes` wholesale and, with `--tags`, replaces the tag list; the save script's duplicate check is the local `processed` list, keyed by URL. Two sessions working the same document concurrently would race, last write wins. With a single human-invoked writer and no scheduled one, that is a theoretical risk today, not an observed one.
