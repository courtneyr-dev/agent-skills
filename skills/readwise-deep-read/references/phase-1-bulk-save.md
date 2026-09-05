# Phase 1 — Bulk save via existing Python script

### Phase 1 — Bulk save via existing Python script

```bash
~/.venvs/readwise-scripts/bin/python3 ~/Documents/scripts/youtube_to_readwise.py <urls>
```

**Always call the venv interpreter by absolute path — never bare `python3`.** The pipeline's
third-party dependencies (`requests`, `anthropic`, `youtube_transcript_api`) are installed only
in `~/Documents/scripts/.venv`, never in the system interpreter. Bare `python3` dies instantly
with `ModuleNotFoundError: No module named 'requests'`. Every Python invocation in this skill
uses the venv path for that reason; copy the full path rather than shortening it, and don't
"simplify" it back to `python3` in a later edit. (Strictly, only `youtube_to_readwise.py` needs
the third-party packages — `deepread_check.py`, `mirror_notes.py`, and `backlog.py` are
stdlib-only and would survive bare `python3`. The path is kept uniform anyway so no invocation
in this file models the pattern that breaks Phase 1.) `source ~/.youtube_api_keys` is still
required for the token env vars; the venv supplies packages, not credentials.

The script handles:

- **Title normalization at save time** (added 2026-08-24, the user's call): `normalize_reader_title()`
  drops `#` and turns `[`/`]` into parens before every `/api/v3/save/` payload (same rule in
  `create_video_doc.py`). Reader titles become vault filenames via the Obsidian plugin, and those
  characters break wikilinks to the mirrored file. The backfill for pre-existing docs is
  `~/Documents/scripts/normalize_titles.py` (`scan` / `apply`); after an apply, the next Obsidian
  sync writes each changed doc to a NEW clean-named file — re-run `mirror_notes.py` for those docs
  (the Document Notes callout lives in the old file) and delete the stale `#`-named mirrors.
  Plugin `[doc-id]` suffixes on same-title collisions are unaffected — those brackets come from the
  plugin, not the title.
- yt-dlp transcript fetching with retry and queue-based dedup (`~/.youtube_processing_queue.json`)
- Article scraping
- Claude Sonnet 4 analysis using `~/Documents/scripts/article_template.txt` (the full 18-section template above)
- Save to Reader via `/api/v3/save/` with the full template output in the `notes` field
- v2 Master-DB highlights for each extracted atom
- Analysis output to `~/.youtube_analyses/<video_id>_<title>.md`

**Script patches** (all applied 2026-05-20; pre-patch backup at `~/Documents/scripts/youtube_to_readwise.py.backup-pre-patches-2026-05-19`):

1. ✅ **max_tokens=16384** in `process_with_claude()` (line 518) — prevents Refactor Appendix truncation on full-template output (8–15k tokens)
2. ✅ **Fallacy-name whitespace normalize** in `extract_highlights_from_analysis()` — both sides use `.lower().replace(' ', '')` so "Straw man" matches "Strawman" in `KNOWN_FALLACIES`
3. ✅ **Doc_id capture in `send_to_readwise()`** (NOT `save_to_reader()` — that function never existed) — extracts `id` from response JSON, returns `Optional[str]`; `process_video` and `process_article` print `📋 doc_id=<id>` to stdout on success
4. ✅ **Pre-flight subtitle regex** — `Unfortunately,?\s+Youtube\s+does\s+not\s+provide\s+subtitles` matches the no-subtitles sentinel before queueing for Phase 2
5. ✅ **Claude Code CLI fallback + hardened daily job** (added 2026-07-19; backup `youtube_to_readwise.py.backup-pre-claudecli-fallback-2026-07-19`) — when the paid Anthropic API errors (out of credits / dead key / outage), `process_with_claude()` catches the exception and re-runs the same template prompt through `claude -p --model sonnet` (`_claude_cli_analysis()`), using bundled Claude Code credits at zero marginal API cost. Trims any preamble before the YAML `---`; returns `"Processing failed"` only if the CLI is missing or also errors.
   - **Daily launchd hardened to use it:** `~/bin/retry_youtube_queue.sh` now runs `--retry-queue` (dropped `--no-analysis`), so the unattended job produces full 18-section notes via the API→CLI fallback. `--retry-queue` no longer requires `ANTHROPIC_API_KEY` (the fallback covers it). New `process_video(degrade_on_failure=True)` in the retry path saves **transcript-only** (needs_analysis) if BOTH backends are down — the old floor is preserved, never a total loss. Shared helper `_save_transcript_only()`.
   - **Headless auth:** the CLI's auth is in the macOS Keychain (`Claude Code-credentials-*`), which a sparse launchd env can't reach ("run /login"). Fix: the wrapper `source`s `~/.youtube_api_keys` (600 perms), which exports `CLAUDE_CODE_OAUTH_TOKEN` (from `claude setup-token`) — verified the CLI honors that env var and bypasses the keychain (dummy token → `401 Invalid bearer token`, not "not logged in"). Token lives ONLY in that 600-perm file, never in the plist or transcript. Plist unchanged (wrapper handles the token).

Capture stdout for the saved doc_ids — grep for lines matching `📋 doc_id=([a-z0-9]+)`. They're the input to Phase 2.
