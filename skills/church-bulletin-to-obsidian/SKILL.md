---
name: church-bulletin-to-obsidian
description: "Use when the user shares a church bulletin (image or text) or says 'church bulletin' and wants the sermon-notes file for the vault."
---

# Church Bulletin to Obsidian Sermon Notes

Transform a church bulletin (photographed, scanned, or pasted text) into a complete Obsidian Excalidraw hybrid note — visual canvas (front) + full sermon notes (back), toggled with hotkey — with all scripture as Bible Linker `![[Book Chapter#Verse]]` embeds, liturgical calendar context (season, week, color, Jewish calendar, NL + RCL readings — St. John's UCC follows the Narrative Lectionary), full hymn lyrics with attribution, empty sermon-note scaffolding, complete YAML front matter, and every piece of bulletin content preserved (announcements, calendar, leadership, mission, contact info). A companion NotebookLM source doc is generated alongside.

## When to use

- User says "convert this bulletin", "create sermon notes", "here's this week's bulletin"
- User provides a church bulletin image or text
- User asks to process a worship service program

## Workflow

1. Read the bulletin (image or text) and extract all content
2. Calculate liturgical calendar context for the service date
3. Convert every scripture reference to Bible Linker embed syntax
4. Look up full hymn lyrics (placed inline in the Order of Worship — see overrides)
5. Generate the complete markdown file from the document structure
6. Write it to the Obsidian vault
7. Generate the NotebookLM source document
8. Update the Faith & Theology MOC cross-link
9. Run the quality checklist, offer browser staging, confirm to user

## File Locations

| Item              | Path                                                                                   |
| ----------------- | -------------------------------------------------------------------------------------- |
| Output file       | `$VAULT_DIR/Areas/Sermon Notes/YYYY-MM-DD.md`            |
| NotebookLM source | `$VAULT_DIR/Areas/Sermon Notes/YYYY-MM-DD-notebooklm.md` |
| Example output    | `~/.claude/skills/church-bulletin-to-obsidian/examples/sample-output.md`               |

Create the `Sermon Notes` directory if it doesn't exist.

## Reading map

- ALWAYS read references/user-preference-overrides.md before generating anything — authoritative preferences (PARA `2. ` vault-path prefix, hymn lyrics inline in the Order of Worship, MOC cross-linking, browser staging offer) that supersede the other references.
- When extracting content from the bulletin, read references/bulletin-extraction.md
- When calculating liturgical context (RCL cycle, season/color, NL readings, Hebrew calendar, ecumenical observances), read references/liturgical-calendar.md
- When converting scripture to Bible Linker embeds (book names, verse-range expansion, responsive readings), read references/bible-linker-syntax.md
- When the bulletin abbreviates book names, read references/abbreviation-mappings.md
- When looking up hymn lyrics and attribution, read references/hymn-lyrics.md
- When generating the markdown file (YAML front matter schema + Excalidraw hybrid body template), read references/document-structure.md
- When generating the NotebookLM source doc, read references/notebooklm-source.md
- Before delivering the file, read references/quality-checklist.md
- When something unusual comes up (lyrics not found, unreadable image, multiple services, non-standard elements), read references/edge-cases.md
