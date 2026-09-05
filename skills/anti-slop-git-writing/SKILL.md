---
name: anti-slop-git-writing
description: "Use when writing a commit message, PR or MR title and body, GitHub or GitLab issue, bug report, or code-review comment, and when a bug found while testing or reviewing needs filing. Makes the text read like a specific person wrote it under normal time pressure."
---

# Anti-Slop Git Writing

## Why this exists
Default AI-written commits, PRs, and bug reports have a recognizable voice:
boilerplate openers ("This PR implements..."), bold-first bullet lists,
em-dash addiction, manufactured rhetorical drama, and a robot footer nobody
asked for. That voice reads as generated, which costs trust with reviewers
and teammates. This skill makes commit/PR/issue output indistinguishable
from what a competent, slightly rushed human would write.

## Before writing anything
1. Run `git log --oneline -30` (and `git log -5 -p` on a couple of commits)
   in the current repo. If an existing pattern is visible — length, tone,
   emoji use or absence — match it. House style beats this skill's defaults.
2. If the repo has PR history, skim the last 5-10 merged PRs
   (`gh pr list --state merged --limit 10`, then `gh pr view <n>` on a few)
   the same way.
3. If there's no established pattern yet (new repo, first commit), fall
   back to the defaults in `references/templates.md`.

## Writing pass
Draft normally, then check the draft against `references/style-guide.md`
before finalizing. If more than one or two of those patterns show up,
rewrite — don't soften the wording, cut the pattern entirely.

## Emoji policy
One emoji, at the very start of the commit subject line or PR/issue title,
chosen from the Emoji-Log set in `references/templates.md`. Never mid-sentence,
never per-bullet, never more than one per line. Emoji-per-bullet is itself a
top AI-slop tell — don't reintroduce it while trying to humanize the rest.

## Attribution
End every commit message with the plain trailer line the harness supplies
(`Co-Authored-By: Claude ... <noreply@anthropic.com>`), in all repos —
personal, employer, and OSS alike. That's the disclosure. Nothing else:
no "Generated with Claude Code" footer or badge in commits, PR
descriptions, or issues. Disclosure yes, branding no.
[Confirmed by the user 2026-07-04: plain trailer everywhere.]

## Structure scales with the change
A one-line fix doesn't get a "## Summary" header. A multi-file feature might.
Don't force every PR into the same skeleton regardless of size — an identical
rigid template every single time is its own tell.

## Autonomous bug filing
When you find a bug while doing something else (testing, reviewing,
debugging) that isn't what you were asked to work on, file it using the bug
report format in `references/templates.md` rather than silently fixing or
ignoring it. Don't inflate severity language — most bugs are not "critical."

## Leaving review comments
If asked to review a PR or respond to review feedback, use Conventional
Comments prefixes (`nit:`, `suggestion:`, `issue:`, `question:`, `praise:`)
so intent is unambiguous — see `references/templates.md`.
