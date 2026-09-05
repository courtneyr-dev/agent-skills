---
name: synthesis-backlog
description: "Use when the user says 'triage my backlog', 'what needs synthesis', 'what's outstanding', 'what did I process this week', 'triage my inbox', 'what should I read', or 'reading triage', or after documents are processed and need logging."
---

# Synthesis Backlog

## Why this exists

Osmani's loop-engineering rule: *"the model forgets everything between runs so the memory has to be on disk and not in the context. The agent forgets, the repo doesn't."* Before this skill, the thread of *"what's processed but not yet synthesized"* lived only in the conversation and reset every session — so the user had to manually re-ask "go through today's files." This skill makes that state a **file**: `$VAULT_DIR/_Synthesis Backlog.md`. It is the loop's spine; everything else (triage, the maker/checker pass) rides on it.

This is the discovery/triage half of the loop. The other pieces:
- **readwise-deep-read** — ingests + highlights (the *maker* for pipeline output); logs each doc here.
- **vault-hygiene-checker** — verifies synthesis quality (the *checker*); run for link/dup/orphan checks.

## The backlog file

A normal Obsidian markdown table (the user reads and edits it) at vault root (NOT under `Resources/`, so it isn't published). Hidden `<!-- BACKLOG:ACTIVE:START/END -->` markers make programmatic append/update robust without disturbing the prose.

Columns: **Date · Title · doc_id · Type · Atoms · MOC · Read · Notes**
States: `pending` · `done` · `skip` · `—`
- **Atoms** — did this doc spawn permanent note(s)?
- **MOC** — is it wired into a MOC?
- **Read** — has the user actually read/synthesized it? (the comprehension-debt guard: `read: no` = processed-but-unread)

## Tool: `backlog.py`

```bash
# log a processed doc (idempotent — skips if doc_id already present)
python3 ~/.claude/skills/synthesis-backlog/backlog.py add \
  --doc-id ID --title "T" [--type article|video|tweet|podcast] [--read no] [--notes "..."]

# update status as synthesis happens
python3 ~/.claude/skills/synthesis-backlog/backlog.py set --doc-id ID [--atoms done] [--moc done] [--read yes] [--notes "..."]

# list (optionally only outstanding)
python3 ~/.claude/skills/synthesis-backlog/backlog.py list [--pending]

# triage — the report (add --reader to also scan the Reader inbox for unlogged thin docs)
source ~/.youtube_api_keys   # needed only for --reader inbox discovery
python3 ~/.claude/skills/synthesis-backlog/backlog.py triage [--reader] [--days N]
```

## Tool: `inbox_triage.py` (front of the loop — intake)

The backlog tracks docs *after* processing; this scores NEW inbox docs *before* processing, against the threads the user is actively building (your MOCs), and proposes a deep-read shortlist. **Read-only — it proposes, never processes.**

```bash
source ~/.youtube_api_keys   # needs READWISE_TOKEN
python3 ~/.claude/skills/synthesis-backlog/inbox_triage.py [--top N] [--location new|later|feed] [--min-read N]
```

Scoring signal: each doc's tokens (title + summary + tags + site) vs. each MOC's token set (its title + section headings + the notes it links). The best-matching MOC above threshold = the "thread it hits," named in the report. Docs already in the backlog or already deep-read (notes contain "Refactor Appendix") are excluded. Output buckets: 🔥 deep-read shortlist · 🤔 maybe · ⏭️ low-fit/skip. New-author flagged as a minor signal.

**Triage flow ("triage my inbox"):**
1. Run `inbox_triage.py`. Present the shortlist to the user.
2. You approves which to deep-read (you're the gate — the loop proposes, you decides).
3. Run the **readwise-deep-read** pipeline on the approved IDs; they auto-log to the backlog (Phase 3).
4. Caveat to keep honest: on a homogeneous feed (e.g. daily Twitter-list digests) the scoring discriminates weakly — that's expected; the value is on a diverse `new` inbox. Don't oversell a thread-hit count as a quality judgment; it's a relevance prior, not a verdict.

## Workflow

**Logging (after processing):** when the deep-read pipeline finishes a doc, `add` it. The readwise-deep-read skill's Phase 3 calls this — so every processed doc logs itself. For docs processed outside the pipeline, `add` them manually.

**Triage ("triage my backlog"):**
1. Run `backlog.py triage --reader`. It reports: 🧪 needs atoms · 🗺️ needs a MOC home · 📖 comprehension debt (unread) · 🆕 inbox docs not yet logged + thin (discovery). It also writes a one-line summary into the file's "Last triage" section.
2. Present the report to the user and let your decide what to act on — you're the decision gate (findings come to your). Do NOT auto-synthesize.
3. On your go-ahead, do the maker work (write atoms / wire MOCs), then `set` the affected rows to `done`, then run the **vault-hygiene-checker** to verify the new links/atoms resolve, then re-`triage` to confirm the rows cleared.

**Keep the columns honest:** only mark `atoms done` / `moc done` after verifying the note/MOC link actually exists (that's what the checker is for). A `done` that isn't true is review theater — the exact failure the maker/checker loop guards against. Use `skip` (with a reason in Notes) for docs that deliberately won't get atoms/MOC, so they stop showing up as outstanding.

## Scope boundary

This tracks *state* and surfaces *what's outstanding*. It does not do synthesis (that's the maker), does not verify link quality (that's vault-hygiene-checker), and does not process Reader docs (that's readwise-deep-read). When triage reveals work, route it to the right skill — don't expand scope here.
