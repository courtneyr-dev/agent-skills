# Emoji-Log commit prefixes

Base convention: Emoji-Log (ahmadawais/Emoji-Log). Seven categories,
imperative mood, one emoji at the very start of the subject line only.

| Emoji | Category | Use for |
|---|---|---|
| 📦 | NEW | Something added that didn't exist before |
| 👌 | IMPROVE | Refactor, enhancement, or cleanup of existing code |
| 🐛 | FIX | Bug fix |
| 📖 | DOC | Documentation only |
| 🚀 | RELEASE | Version bump / release commit |
| 🤖 | TEST | Test-only changes |
| ‼️ | BREAKING | Breaking change — call it out explicitly in the body too |

Imperative mood: "Add," "Fix," "Remove" — not "Added," "Fixed," "Removed."

Example: `🐛 FIX: Null check on empty cart response`
[Confirmed by the user 2026-07-04: emoji + CAPS label, canonical Emoji-Log.]

If a project ever wants more granularity than these 7 categories, Gitmoji
(gitmoji.dev) is the standard fallback — but don't default to it. More
categories means more decisions per commit and more inconsistency across
a small team.

# Commit message format
Subject: `<emoji> <LABEL>: <Imperative sentence>`, ~50 characters, no
trailing period.
Body (only if the "why" isn't obvious from the diff): plain sentences after
a blank line — not a bullet-only body unless listing genuinely parallel,
independent changes.

# PR/MR description format
Title: `<emoji> <plain description of what changed>`
Body: no fixed headers required for small/medium PRs. Open with what changed
and why, the way you'd tell a teammate over Slack — not fill out a form. For
larger PRs, use whatever headers actually fit this specific change (e.g.
"## Migration steps" if there's a migration) rather than defaulting to a
generic Summary/Changes/Testing skeleton every time.
If there's something specific you want the reviewer to look at, say so near
the top, not buried at the bottom.
No branding footer in the PR body; commits carry the plain Co-Authored-By
trailer (see SKILL.md).

# Bug report format
Title: plain description of the symptom — not "Bug: various issues" or
"Error in module."
Body:
- What happened (1-2 sentences)
- What you expected instead (1 sentence)
- Repro steps — numbered list only if genuinely sequential, otherwise just
  describe it
- Environment (OS, browser/runtime, version) if relevant
One 🐛 in the title, nowhere else. Skip "please look into this" filler — the
report itself is the ask.

# Code review comment prefixes (Conventional Comments)
Use when reviewing PRs or replying to review feedback:
- `praise:` — something done well, worth calling out
- `nitpick:` — trivial, author can ignore
- `suggestion:` — proposed change, not mandatory
- `issue:` — a problem that should be addressed
- `question:` — asking for clarification, not requesting a change

Format: `<label>: <comment>`. Optional scope in parens:
`issue (security): ...`
