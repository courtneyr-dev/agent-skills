# Tag scheme, required paths, template selection, cost notes

## Hierarchical tag scheme

Apply these consistently across atoms in analysis files AND inline highlights:

| Tag | Meaning |
|---|---|
| `#atom/literature/h1` | Strongest evidence-based claim |
| `#atom/literature/h2` | Secondary evidence claim |
| `#atom/literature/h3` | Supporting context |
| `#atom/zettel/z1` | Atomic concept worth memorizing |
| `#atom/fleeting/f1` | Loose connection or hunch |
| `#action/h1` | High-priority action item |
| `#action/h2` | Medium priority |
| `#action/h3` | Low priority |
| `#fallacy/<slug>` | Identified logical fallacy (e.g., `#fallacy/strawman`, `#fallacy/tu-quoque`, `#fallacy/appeal-to-tradition`) |
| `#darvo/deny` `#darvo/attack` `#darvo/reverse` | DARVO components when identified |

## Required files & paths

- **Interpreter:** `~/.venvs/readwise-scripts/bin/python3` — **required**, never bare `python3` (see Phase 1)
- **Script:** `~/Documents/scripts/youtube_to_readwise.py`
- **Templates:**
  - `~/Documents/scripts/article_template.txt` (full 18-section deep-read — canonical, used by Python script)
  - `~/.claude/skills/readwise-deep-read/article_template.txt` (skill-local copy for Claude Code reference)
  - `~/Documents/scripts/article_template_lean.txt` (WP Tavern archive style — short news only)
- **Queue state:** `~/.youtube_processing_queue.json` — keys `pending_transcript`, `failed_permanent`, `processed`, `needs_analysis`. Drain `needs_analysis` with `--mark-analyzed <doc_id>` after writing an analysis; nothing else removes entries (see Phase 3 step 4).
- **Analysis output:** `~/.youtube_analyses/`
- **API keys:** `~/.youtube_api_keys` (sourced for `READWISE_TOKEN`, `ANTHROPIC_API_KEY`, `YOUTUBE_API_KEY`, optional `OPENAI_API_KEY` for Whisper)
- **Pre-patch backup:** `~/Documents/scripts/youtube_to_readwise.py.backup-pre-highlights`

## Template selection

`youtube_to_readwise.py` accepts only `--external-analysis`, `--no-analysis`, `--mark-analyzed`, `--retry-queue`, `--show-queue`. There is no `--full` or `--lean` flag (verified 2026-09-02: `--full` was parsed as a URL and errored). Template choice happens when you write the notes:

- `article_template.txt` (18-section deep-read) — **default for everything substantive**
- `<!-- deep-read: light-touch -->` marker in the notes — thin sources (short reviews, announcements); both `push_notes.py` and `deepread_check.py` accept it
- `~/Documents/scripts/article_template_lean.txt` (Summary + Comments, WP Tavern archive style) — legacy, gives less than light-touch; rarely the right call

## Cost notes

- **Phase 1** (Python script) uses Claude Sonnet 4 via Anthropic API — burns tokens proportional to transcript length × template output (full template generates 8-15k tokens per source)
- **Phase 2** (this skill in Claude Code) uses Claude Code's bundled credits — **zero marginal API cost** for the analysis-to-highlight mapping work
- **Phase 0 fallback** — vidIQ watch is bundled with vidIQ subscription; Whisper local is free; OpenAI Whisper API is ~$0.006/min (so a 60-min podcast costs ~$0.36)

The major efficiency case for using this skill in Claude Code vs. running everything in chat with the Python script alone: for a daily 8-URL queue, the savings are substantial.
