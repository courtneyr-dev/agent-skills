---
name: learning-path
description: "Use when the user says 'learning path', 'what should I learn next', 'plan my learning', 'learning retro', or 'what did I learn this week'; plans a path or, in retro mode, reviews a finished one."
---

# Learning path

One plan note per topic; plan mode writes it, retro mode edits it. No note for the topic (frontmatter `type: learning-path`) → plan. Note exists and the user names a milestone, says "retro", or asks what you learned → retro (no note: say so, then plan). Two or more matching notes → ask which (the one mid-task question).

## Folder

Folder: unset. Agree it with the user in the first intake question and record it here (one-line edit).

## Plan mode

Inputs: topic, baseline (known or built), target outcome (what you will ship or do), hours per week, deadline. Missing ones: one batched question, then finish without further check-ins.

Resources: reuse your Reader library (`readwise-mcp`) and `Resources/Readwise/` first; cap at 3 primary. Confirm each by search (URL, edition, version) even when the title is familiar.
2. Sequence fundamentals → applied practice. Each milestone: date, deliverable, pass/fail check, one practice exercise with feedback criteria; `quiz` is the understanding check.
3. Write the note (≤1 page): frontmatter (`type`, `topic`, `status`, `created`, `hours_per_week`, `deadline`), milestone table, one paragraph per milestone, empty `## Retros` section.

Done: note in the agreed folder; every milestone dated with deliverable and check; milestone hours ≤ hours per week × weeks to deadline.

## Retro mode

Inputs: the plan note; evidence since the last retro entry (or `created`): commits, vault notes, quiz results, daily notes, and what the user says you did.

Preconditions — four open blockers from the 2026-08-08 weekly-retro design (`Projects/weekly-learning-retro/`, a separate unbuilt session). Check each; record its state in the entry:

1. chief-of-staff paths unrepaired (no `Review/Weekly/` file in 14 days) → orient from the plan note and evidence only; say so.
3. Things AppleScript write unverified → list next actions in the entry for your to add by hand; create nothing in Things.
4. No session day picked → runs only when asked; no schedule, no cron.

Steps:

1. Score each due milestone pass, partial, or miss against its check, citing the file or commit.
2. Name blockers and weak concepts recurring across 2+ milestones; mark each reinforce or defer.
3. Re-date remaining milestones to the hours left; give the next one a date and a measurable checkpoint.
4. Surgical edit, not a whole-file rewrite: append a dated entry under `## Retros`; update the milestone rows.

Done, all in the plan note: each due milestone scored with evidence; next milestone dated with a checkpoint; four precondition states recorded.
