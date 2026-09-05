# Quality checklist

## Quality Checklist

Before delivering the file, verify:

- [ ] **YAML front matter** is valid — no unescaped colons in values, all strings properly quoted
- [ ] **Every scripture reference** uses Bible Linker embed syntax `![[Book Chapter#Verse]]`
- [ ] **Every verse in every range** is individually expanded (no skipped verses)
- [ ] **Book names are full** — not abbreviated (Genesis, not Gen; Matthew, not Matt)
- [ ] **Psalm is singular** — `Psalm`, not `Psalms`
- [ ] **Numbered books have a space** — `1 Samuel`, not `1Samuel`
- [ ] **Responsive readings** preserve Leader/People format AND include Bible Linker embeds
- [ ] **All hymns** have full lyrics, author, tune name, composer, copyright status
- [ ] **Hymns in YAML** use nested arrays with quoted strings
- [ ] **Liturgical context** is fully calculated — season, year, color, week, Hebrew date
- [ ] **RCL readings** are looked up for the specific date
- [ ] **All bulletin content** is preserved — nothing from the original bulletin is omitted
- [ ] **Scaffolding sections** are present but empty — sermon notes, reflections, applications
- [ ] **Narrative Lectionary** reading is looked up for the specific date and 4-year cycle
- [ ] **Excalidraw frontmatter** includes `excalidraw-plugin: parsed`, `excalidraw-open-md: true`, `excalidraw-embed-md: true`, `excalidraw-autoexport: svg`
- [ ] **`# Back of Card`** section present — all sermon content lives under this heading
- [ ] **`# Excalidraw Data`** section present at end with `## Text Elements`, `## Embedded Files`, and `%% ## Drawing {JSON} %%`
- [ ] **File heading** is `# [[YYYY-MM-DD]]` followed by `![[YYYY-MM-DD.svg]]` before `# Back of Card`
- [ ] **File is written** to `Areas/Sermon Notes/YYYY-MM-DD.md` (not `.excalidraw.md`)
- [ ] **NotebookLM source** written to `Areas/Sermon Notes/YYYY-MM-DD-notebooklm.md` with plain scripture text (no Bible Linker syntax), imagery descriptions, and key concepts
- [ ] **No AI-sounding prose** — natural, direct language throughout
- [ ] **No placeholders** — no `{{}}`, `[insert]`, or `[fill in]` markers remain (scaffolding sections use HTML comments for guidance instead)
