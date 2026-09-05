<!-- ===================================================================
REFERENCE LIBRARY — DO NOT EMIT BELOW THIS MARKER

Three target shapes for the Note Refactor / QuickAdd-Zettelizer plugins
when splitting atoms out of the appendix. The Python atomizer matches
these structures. Stop emitting after the → Things 3 section above.
=================================================================== -->

## 🧰 Template Library — Spun-Out Note Shapes (reference only)

### 📝 Fleeting note

```markdown
---
type: fleeting
status: inbox
created: {{date:YYYY-MM-DD HH:mm}}
source_link:
tags: [fleeting, inbox]
---

# {{title}}

**One-liner**:

**Why now**: {one line — what triggered the capture}

## Claim bridge
### [H1] {≤10-word present-tense claim header — Konik style}
> [!quote]
> {optional ≤25-word verbatim if available}

## → Things 3
- [ ] {next physical action, if any} #things

## Process by
{{date+2d}} — promote to Literature, draft Permanent, or park as question
```

### 📚 Literature note (Konik triage + Ahrens structure)

```markdown
---
type: literature
status: draft
created: {{date:YYYY-MM-DD}}
source_title:
author:
citekey:
source_link:
tags: [literature]
---

# {{source_title}} — {{author}}

## 🗂️ Triage — annotated highlights surfaced

> [!help]+ Lingering Questions
> - **id12345 — claim header** — Question or research prompt.

> [!info]+ Article Ideas
> - **id12345 — claim header** — Direction. #articleseed / #addendum

> [!note]- Cross Reference
> - **id12345 — claim header** — Connects to [[note]]. #xref

> [!tip]- Fiction & Worldbuilding
> - **id12345 — claim header** — Story potential. #bmf / #storystem

> [!info] Vocabulary
> - id12345 **term**: definition.

## → Things 3
- [ ] {action} #things

## 🧭 Bib capsule
{1-line citation; year and publisher only if not derivable from citekey}

## 🧠 Author's thesis (Adler Q1+Q2)
{2–4 sentences}

## 🧩 Key arguments
- {arg 1}
- {arg 2}
- {arg 3}

## 🧪 Evaluation (Adler Q3+Q4) — *only if reading_stage is analytical/syntopical*
- **Is it true?** {…}
- **So what?** {…}
- **Bias & reliability**: {…}

## 🗒️ Notes — Literature atoms (claim header → quote → annotation)

### [H1] {≤10-word present-tense claim header}
> [!quote] ID:rw_{id}
> {≤25 words verbatim}

- **Where**: {page / timestamp}
- **Why**: {one-line takeaway — mirrors inline annotation if present}

[view highlight](readwise://...)

### [H2] …

## 🔖 Permanent candidates
- [[P1 — concept handle title]]
- [[P2 — …]]

## ✅ Processing checklist
- [ ] All H3 atoms have claim header + quote + atomicity check
- [ ] Triage callouts populated (or explicitly empty) for every tagged highlight
- [ ] ≥1 Permanent candidate identified (or "none worth promoting")
- [ ] Version History Diff check passed (no [view highlight] stripped, no quotes rewritten)
```

### 🧠 Permanent note

```markdown
---
type: permanent
id: {{date:YYYYMMDDHHmm}}
status: seedling   # seedling | budding | evergreen
created: {{date:YYYY-MM-DD}}
origin: {{citekey}}
tags: [permanent]
# proof_state: working   # OPT-IN: working | supported | refuted (empirical only)
---

# {{Concept handle — declarative title, present tense}}

## Claim
{One sentence, the user's voice, present tense. If "and" or "also" is needed, split.}

## Evidence
**Source**: [[Literature note]] §[H1]
> [!quote]
> {OPTIONAL ≤25 words verbatim — only if aphoristic or load-bearing}

## Scope & conditions
- Holds when: {…}
- Breaks when: {…}

## Links
- [[Broader concept]] — because extends
- [[Sibling claim]] — because contrasts on {dimension}
- [[Application]] — because applies-in {context}
- [[Evidence/case]] — because evidence-for

## Implications
- {open question or writing prompt — not yet a Thing}

## Tests / falsifiers — *only if `proof_state: working`*
- {what would change my mind}

## Maintenance
- Last tended: {{date}}
- Next review: {{date+90d}}
```

## 📖 References (for future Claude instances training on this prompt)

- Ahrens, *How to Take Smart Notes* — atomicity, "in your own words"
- Konik, eleanorkonik.com — claim-header rules, triage callouts, Version History Diff verification, seven-tag taxonomy
- Matuschak, notes.andymatuschak.org — concept-handle titles, "one thing but the entirety of that thing"
- Forte, *Building a Second Brain* — Progressive Summarization L1→L5, "design for the laziest version of yourself"
- Allen, *Getting Things Done* — 2-minute rule applies at clarify, not capture
- Adler, *How to Read a Book* — Q1/Q2 inspectional, Q3/Q4 analytical
- Abdaal, *Feel-Good Productivity* — friction reduction
- Appleton, maggieappleton.com — seedling/budding/evergreen growth-stages
