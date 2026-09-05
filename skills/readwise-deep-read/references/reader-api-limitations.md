# Reader API Limitations to Know

## Reader API Limitations to Know

- **No content updates after save.** Once a doc is created, you cannot inject `html_content` or `markdown` into it via the API — and re-saving the same URL is idempotent (returns the existing empty doc, does NOT re-scrape). If Reader's initial scrape failed (subtitles unavailable, paywall, JS-heavy SPA, rate-limited): recover the content (fallback hierarchy for video subtitles; manual paste for paywalled text) and **re-create the doc with the content embedded** (`/api/v3/save/` with `html=`, or `reader_create_document` with `markdown=`; use a unique URL such as the original + `#transcript` since same-URL re-save is idempotent), then archive the empty original. Per the Phase 0 HARD RULE, master-DB-only highlights on a transcript-less doc are not an acceptable end state.
- **html_content is read-only and post-scrape.** Reader generates it after fetching the URL; you can't override it.
- **The `notes` field IS updatable** via `reader_bulk_edit_document_metadata`, but a late update changes the Reader document only. If a v2 highlight book already exists, its `document_note` is a read-only snapshot. A v2 highlight tag toggle, a highlight-note edit, and a new Reader-native highlight were all tested on 2026-07-21; they caused highlight exports but did not hydrate the book's empty `document_note`. `OPTIONS /api/v2/books/<book_id>/` confirms `document_note` is read-only.
- **`document_note` cannot carry a deep read — always mirror locally instead (mandatory).** Obsidian Publish renders the Document Notes dropdown from a `> [!note]+ Document Notes` callout in the local file, which the plugin writes from the v2 book's `document_note`. That field fails two independent ways, measured 2026-07-24 across five docs:

  | How `notes` were set | resulting `document_note` |
  |---|---|
  | `/api/v3/save/` payload at creation | **empty** — no callout ever written |
  | `reader_create_document(notes=...)` | **empty** — no callout ever written |
  | `reader_bulk_edit_document_metadata` (late) | populated but **truncated at 8191 bytes**, cut mid-word |

  An 18-section deep read runs 20–46k chars, so even the "working" path loses roughly three quarters of it — everything from 📊 Methodology onward. `document_note` is read-only (`OPTIONS /api/v2/books/<book_id>/`), so neither failure is fixable through the API.

  **The fix is not an ordering trick.** Run the mirror as a normal Phase 3 step on every processed doc:

  ```bash
  source ~/.youtube_api_keys
  ~/.venvs/readwise-scripts/bin/python3 ~/.claude/skills/readwise-deep-read/mirror_notes.py --ids <doc_id> [<doc_id> ...]
  # repair sweep across ALL locations (always --dry-run first):
  ~/.venvs/readwise-scripts/bin/python3 ~/.claude/skills/readwise-deep-read/mirror_notes.py --since 2026-07-20 --dry-run
  ```

  **Do not sweep with `--location new` — it will miss nearly everything.** Measured 2026-07-24: documents saved through this pipeline are auto-opened and moved to `archive` within 1–7 minutes of creation by an account-side Reader rule (WP2Shell showed `first_opened_at` 15 seconds after `created_at`, `last_moved_at` 97 seconds after). A doc that pre-existed and only received highlights was *not* moved, so the trigger is the save, not the highlighting. Sweep by `--since` instead, which spans every location. The API rejects a bare date on `updatedAfter`; the script appends `T00:00:00Z` for you.

  It fetches the live Reader `notes`, finds the canonical file (exact `source_url` first, then sanitized title, always excluding `Full Document Contents/`), and inserts or replaces the callout between the `🔗 **Source:**` line and `📄 **Full text:**`. It is idempotent — re-running replaces a truncated callout with the full text.

  **Requires a prior sync.** The plugin must have created the local file first; `NO FILE` output means the doc has not synced yet, so sync and re-run. The plugin preserves locally modified files and appends later highlight deltas, so the mirror survives.

  Verify with `rg -F '[!note]+ Document Notes' <file>` **and** confirm the callout reaches the end of the analysis (`rg -F '> ### → Things 3' <file>`) — presence alone does not distinguish a full mirror from an 8 KB truncation. A callout found only under `Full Document Contents/` is not success.

  **Never emit a bare `> ---` under a quoted text line.** Markdown reads it as a setext heading underline, which *terminates the callout*: the dropdown then shows only the lines above it and the entire analysis renders on the page **outside** the dropdown. Because the deep-read template opens with YAML frontmatter, its closing `---` landed under `date created:` and silently truncated the dropdown on **6,025 of 6,068** callout files (measured 2026-07-24). `mirror_notes.py` now drops the frontmatter delimiters (keeping their content) and forces a blank `>` line before any other rule. If you ever hand-write a callout, do the same.

  A file can therefore be byte-perfect against Reader and still render wrong. Check the *published* page, not just the file, when validating a fix:

  ```bash
  rg -n '^> (---|\*\*\*|___)$' <file>   # any hit whose previous line is quoted text is a bug
  ```
- **Notes still belong in the original save payload** — but for the Reader doc itself, not for the callout. Putting them there means the Reader UI and `deepread_check.py` see them immediately; it does nothing for `document_note`, which is what the table above measures.
