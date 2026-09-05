---
name: field-notes-draft
description: "Use when the user says 'Field Notes', asks for the Thursday or Friday Field Notes review, wants newsletter candidates ranked, or wants the Saturday issue drafted after picking a theme. Never sends or schedules."
---

# Field Notes draft

Run the human reviewed newsletter workflow for example.com. The script provides conservative intake triage. the user chooses the theme, supplies or approves the point of view, voices the draft, and approves scheduling and sending.

## Authoritative paths

- Vault: `$VAULT_DIR/`
- Newsletter spec: `Areas/Content Strategy/Newsletter — Field Notes.md`
- Backlog: `_Synthesis Backlog.md`
- Intake reports: `Areas/Content Strategy/Content Intake/YYYY/`
- Drafts: `Areas/Content Strategy/Field Notes Drafts/Field Notes — DRAFT YYYY-MM-DD.md`
- Script and state: this skill directory, `assemble.py` and `state.json`

## Schedule

- **Thursday evening:** review the delta, present three ranked themes, and let the user select one.
- **Friday:** draft, complete the user's voice pass, approve, and schedule.
- **Saturday:** send only after approval, then record the issue and public or administrative receipt.

## Thursday review

For the initial accepted scan, run:

```bash
python3 $HOME/.agents/skills/field-notes-draft/assemble.py \
  --since 2026-08-01 --through 2026-08-28
```

Later runs default to the last recorded issue date. `--days N` remains available after a gap.

The script reads the synthesis backlog, removes already featured document IDs, routes explicit faith or family titles out, and groups professional candidates. It does not decide that an item is publication ready.

Review every section:

- `groups`: professional candidates grouped by topic.
- `review_scope`: ambiguous titles or records with several scope signals. Read them in context.
- `review_other`: professional candidates outside the standard groups.
- `excluded_explicit`: explicit faith or family titles kept out of Field Notes and available for a separate personal site routing.

Do not classify from one keyword buried in notes. A title such as “Parenting Claude” may be professional. A community article that mentions NAR once may still be a professional source.

Present three ranked issue themes. Each option must show:

- the theme and why it is timely;
- one or two items that support it;
- other strong items that could complete a hybrid issue;
- source readiness and evidence limits;
- any `needs full read`, `needs the user's take`, `freshness check`, `high review`, or `employer-adjacent` flags;
- optional Build log, book, One to try, and From the blog material.

the user selects or overrides the theme before drafting.

## Friday draft

Read the newsletter spec and the personal content engine voice reference.

1. **From my desk:** 100 to 200 words based on the user's direct input or a clearly the user-authored Permanent Note, project decision, review, or synthesis. End with a real reply question.
2. **What I read this week:** three to five curated items total. A hybrid issue usually uses one or two theme items and fills the other slots with the strongest professional reading.
3. Resolve original source URLs. Never link to Reader as a substitute for the original.
4. Use one or two sentences for why each item matters. Do not invent the user's take from an imported summary.
5. Include Build log, book, One to try, or From the blog only when current evidence supports it.
6. Mark the draft `STATUS: NEEDS REVIEW — the user edits + voices before send`.
7. Run the personal content engine voice lint and fix all errors before approval.

## Saturday receipt and state

After the approved issue is sent, record only the document IDs that appeared:

```bash
python3 $HOME/.agents/skills/field-notes-draft/assemble.py \
  --record YYYY-MM-DD doc_id,doc_id
```

Do not advance state for an abandoned draft.

## Boundaries

- Professional scope only. All faith writing routes to a separate personal site.
- Read only during intake. Do not move or tag vault or Reader records.
- Three to five curated items total, not per theme.
- Drafting does not authorize scheduling or sending.
- Report the draft path, triage counts, missing the user input, and the next approval gate.
