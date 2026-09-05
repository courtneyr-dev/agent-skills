# Purpose, triggers, and boundaries

## Purpose

Take a batch of URLs through the full deep-read pipeline:

1. **Bulk save** to Readwise Reader with the full 18-section analytical notes attached (per `article_template.txt`)
2. **Reader-native inline highlights** anchored to verbatim transcript/article paragraphs (via the Readwise MCP `reader_create_highlight` tool)
3. **Confirmation** + optional Obsidian sync trigger

Do **NOT** post classic-Readwise (v2) master-DB highlights via `readwise_create_highlights` — see "Master-DB highlights — discontinued (2026-08-16)" below.

## When to trigger

Activate when the user:

- Pastes multiple URLs in a message
- Says "process these URLs," "deep read these," "morning reading queue," "save and analyze"
- References your morning Raycast → Reader → Obsidian workflow
- Wants to add inline highlights to an already-saved Reader doc
- Says "highlight the articles I just saved" or similar

Do NOT trigger if:

- The user wants a quick web search summary without saving
- The user asks general questions about a topic (use web_search instead)
- The URL is a single news headline (just answer directly)

## Why this skill exists

The Python script alone posts highlights via the legacy `/api/v2/highlights/` endpoint, which creates highlights in Readwise's master DB but does **NOT** make them appear inline in the Reader UI. Reader-native inline highlights require the Readwise MCP `reader_create_highlight` tool with verbatim HTML fragments from the doc's `html_content`. (Do NOT try a raw `https://readwise.io/api/v3/highlight/` URL — it 404s.)

This skill closes that gap by adding Phase 2 — the mapping step the script can't do, because Claude's analysis paraphrases atoms rather than copying transcript text verbatim. Phase 2 runs in Claude Code (zero marginal API cost) and uses the html_content Reader generates after scraping.

## Boundaries

- Does NOT replace `web_search` or `web_fetch` for ad-hoc research
- Does NOT generate content beyond what the script + Claude Code produce
- Assumes the script is installed, patched, and API keys configured in `~/.youtube_api_keys`
- Defers to the existing Obsidian PARA structure for downstream organization — only ensures highlights are anchored properly in Reader so they sync correctly
- For child-safety, mental-health, or other sensitive content categories, skip Phase 2 entirely if any flag triggers in Phase 1; the analysis notes are sufficient without amplifying potentially harmful content via inline highlights
