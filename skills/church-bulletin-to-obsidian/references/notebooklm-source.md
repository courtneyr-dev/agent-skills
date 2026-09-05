# NotebookLM source document

### Step 6: Generate NotebookLM Source Document

After writing the sermon note, create a companion file at `Areas/Sermon Notes/YYYY-MM-DD-notebooklm.md` optimized for uploading to NotebookLM as a source. This file helps NotebookLM generate rich visual sketchnotes.

The source document should be a clean, prose-friendly markdown file (no Obsidian wiki-links or Bible Linker syntax) containing:

```markdown
# [Sermon Title] — [Service Date]

## [Church Name] | [Liturgical Season] | [Liturgical Color]

## Scripture Readings

### [Reading Label]: [Reference]

[Full text of each reading — look up and include the actual verse text, not just references. If you included Bible Linker embeds in the sermon note, write out the plain text here instead.]

### Sermon Text: [Reference]

[Full text of the sermon's primary scripture passage]

## Sermon Context

- **Preacher:** [Name]
- **Liturgical Season:** [Season] — [Week]
- **Liturgical Color:** [Color] — [significance]
- **Liturgical Year:** Year [A/B/C] ([Primary Gospel])

## Themes and Imagery

[Write 3-5 sentences describing the key themes, metaphors, and visual imagery from the scripture readings and liturgical context. This guides NotebookLM toward generating relevant visual elements.]

For example: "The Good Shepherd imagery from John 10 — Jesus as shepherd, sheep recognizing his voice, the gate metaphor. Lenten purple as a color of penitence and preparation. The contrast between hired hands who flee and the shepherd who stays."

## Hymns

[List each hymn title and first verse — these provide thematic and tonal context]

## Key Concepts for Visual Representation

- [Concept 1]: [Brief description of what it means and how it connects]
- [Concept 2]: [Brief description]
- [Concept 3]: [Brief description]
```

**Important notes:**

- Write actual scripture text, not Bible Linker embeds — NotebookLM can't parse `![[Book Chapter#Verse]]`
- Include rich descriptive language about imagery and metaphors — this is what drives good visual generation
- Keep it under 5,000 words so NotebookLM processes it efficiently
- After writing the file, tell the user: "NotebookLM source saved to `Sermon Notes/YYYY-MM-DD-notebooklm.md`. Upload this to a new NotebookLM notebook, then ask it to generate a visual summary or sketchnote. Save the result and drop it onto your Excalidraw canvas, then run the Sermon Sketchnote Generator script to add structured scaffolding around it."
