# Phase 3 — Confirmation, completion check, Obsidian sync

### Phase 3 — Confirmation + completion check + Obsidian sync

0. **Completion check (MANDATORY maker/checker gate — do not skip).** A deep-read is NOT done
   until an independent check confirms it. The maker (you) must not grade its own homework
   from memory — re-derive completion from Reader's actual state:

   ```bash
   source ~/.youtube_api_keys
   ~/.venvs/readwise-scripts/bin/python3 ~/.claude/skills/readwise-deep-read/deepread_check.py --ids <doc_id> [<doc_id> ...]
   # or, after a session/batch:  --since YYYY-MM-DD   |   --location new
   ```

   The script (read-only) FAILs any deep-read doc missing: topic tags, policy-compliant tags,
   notes containing the Refactor Appendix (the full-18-section marker), **or a vault file
   carrying the Document Notes callout**. Fix every FAIL, then re-run until it passes. (It skips
   RSS/feed items and un-processed saves; it cannot verify inline-highlight presence via API, so
   still confirm Phase 2 ran.) This gate exists because a long manual run silently skipped
   article tags — the comprehension-debt failure the `loop-engineering` note (`The Maker Should
   Not Grade Its Own Homework`) names directly.

   **The vault half was added 2026-07-31 after a second, worse instance of the same failure:**
   the 2026-07-29 batch passed green with 12 docs complete in Reader and *zero* mirrored, because
   the checker only ever looked at Reader. Reader-complete is not done — the published page reads
   from the vault. The header now states its scope, `(Reader+vault)` or `(Reader only)`; if it
   says Reader only, the vault check did not run and the gate is the weaker pre-2026-07-31 one.
   `--no-vault` skips it deliberately (e.g. off-machine). Ordering: the vault check can only pass
   after step 0.5, so run the gate, mirror, then run the gate again.

0.5. **Mirror notes into the vault (MANDATORY — the published page depends on it).** After the Readwise Official sync has created the local file:

   ```bash
   source ~/.youtube_api_keys
   ~/.venvs/readwise-scripts/bin/python3 ~/.claude/skills/readwise-deep-read/mirror_notes.py --ids <doc_id> [<doc_id> ...]
   ```

   Without this, the Obsidian Publish page has **no Document Notes dropdown at all** when notes were set at creation time, or a dropdown truncated at 8 KB when they were set late. See the `document_note` entry under Reader API Limitations for the measured behavior. If the script reports `NO FILE`, the doc has not synced yet — sync, then re-run.

   **`NO FILE` is not a stopping point — it is an open task.** Diagnosed 2026-08-16: reporting
   a doc as "done, vault mirror pending sync" and moving on, without ever re-checking, is a
   real failure mode that happened repeatedly in one session (one doc out of 17 that session
   touched was left silently un-mirrored — caught only because the user manually compared two
   published pages days later). If `mirror_notes.py` returns `NO FILE`, do not close out the
   doc or the session/turn until you have re-run it and gotten `REPLACED`/`ADDED`/`unchanged` —
   either wait and retry within the same turn, or explicitly tell the user "still open, will
   need a re-check" rather than phrasing it as handled.

   **The plugin's own native sync can independently (re)write a truncated Document Notes
   callout, even after `mirror_notes.py` already fixed it.** Also diagnosed 2026-08-16: a doc
   whose notes were set via `reader_bulk_edit_document_metadata` got picked up by the Readwise
   Official plugin's own sync before `mirror_notes.py` ever ran on it, and the plugin wrote its
   *own* truncated callout (stopped mid-section, well short of the full analysis) directly into
   the local file — independent of, and not fixed by, anything `mirror_notes.py` had or hadn't
   done. This means a single successful mirror is not permanent proof of correctness if any
   sync could plausibly have happened since. **Before treating a batch as closed, re-run
   `mirror_notes.py --ids <all doc_ids in the batch>` one more time** (even ones already
   verified earlier in the session) — `unchanged`/`OK (already current)` confirms nothing
   regressed; anything that comes back `REPLACED` was silently broken and just got fixed.

   **File-level correctness is not proof of what's live.** The published page is a separate,
   cached artifact — a local file can be byte-perfect and the public page still shows stale/
   truncated content until the user runs an actual Publish sync in the Obsidian app. When
   validating a fix (not just after a normal batch), spot-check the real
   `publish.obsidian.md` URL via WebFetch for at least one doc, not just the local file —
   `grep`-ing the file confirms the fix is *ready*, not that it's *visible*.

1. Print the inbox URL (`https://read.readwise.io/new`) and the saved doc titles. **Do NOT hand the user the direct `/read/<doc_id>` URL for freshly-saved docs** — Reader's UI 404s on direct deep links for several minutes after creation while the doc-body service catches up, even though their own API returns that URL as canonical. The inbox-list path renders from a faster-warming cache, so "open inbox → click card" works immediately. After ~10 min the direct URL works too and is fine to share for reference.
2. Suggest manually triggering the Readwise Official Obsidian plugin sync (or auto-trigger if `obsidian-cli` is available)
3. **Log each processed doc to the synthesis backlog** (the loop's memory spine) so "what still needs synthesis" survives the session:

   ```bash
   ~/.venvs/readwise-scripts/bin/python3 ~/.claude/skills/synthesis-backlog/backlog.py add \
     --doc-id <doc_id> --title "<title>" --type <article|video|tweet|podcast> --read no \
     --notes "<author / strongest atom candidate / cross-link, optional>"
   ```

   `add` is idempotent (skips if already logged). Set `--read yes` only if the user has actually read/synthesized it, not just had it processed. See the **synthesis-backlog** skill; surface outstanding items later with "triage my backlog".

4. **If the doc came from the `needs_analysis` queue, drain it.** Check with
   `--show-queue`; if the doc_id is listed there, run this once its analysis is written:

   ```bash
   ~/.venvs/readwise-scripts/bin/python3 ~/Documents/scripts/youtube_to_readwise.py --mark-analyzed <doc_id> [<doc_id> ...]
   ```

   **Nothing else removes entries from this list.** `needs_analysis` in
   `~/.youtube_processing_queue.json` is written by `mark_needs_analysis()` when a source is
   saved transcript-only (both analysis backends down, or the unattended daily retry running
   without a key) — and until `--mark-analyzed` existed it was **write-only**: no code path
   ever removed an entry. Every doc an agent finished stayed listed forever, so the
   `--show-queue` count reported completed work as outstanding and drifted further from
   reality with each run. The flag is a purely local queue edit — it needs no API tokens, it
   touches only `needs_analysis` (`processed` and `pending_transcript` are left alone), and it
   is safe to re-run: an unknown or already-drained doc_id prints a warning and changes
   nothing. If you inherit a stale queue, reconcile it by passing every doc_id whose Reader
   notes already contain the Refactor Appendix.
