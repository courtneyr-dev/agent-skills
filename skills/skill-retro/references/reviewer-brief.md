# Reviewer brief

Send this to a fresh general-purpose subagent. Fill the three paths. Don't add your own view of how the run went: the reviewer works from the record so the session's self-assessment gets checked rather than repeated.

---

You're reviewing one session in which an agent ran the skill `<skill>` over a batch of work. Your findings become proposed edits to that skill, read by its maintainer.

- Transcript (JSONL, one entry per line; tool calls are `tool_use` blocks in `assistant` entries, results are `tool_result` blocks in the following `user` entries; skip entries with `"isSidechain": true`): `<transcript path>`. Transcripts run to several MB, so don't read one whole: write a short script that prints each tool call (name and the start of its input) and the start of its result, from the `Skill` call for this skill up to the next `Skill` call, then read the results you need in full.
- The skill as it was installed: `<skill folder>` (read SKILL.md and every file it routes to)
- Optional, the session's own retro notes: `<notes path or none>`; treat them as claims to check.

Find, with evidence from the transcript (quote commands, errors, counts):

1. Where the run followed the skill and it worked.
2. Where the run lost time or produced a wrong result, and the cause: a gap in the skill, an instruction that was wrong or ambiguous, an instruction that was ignored, a tool or environment problem, or the user changing direction.
3. For each cause that the skill could prevent, the smallest edit that would: the file, the exact text, and what the next run should show.
4. Causes the skill can't fix, and where they belong instead (a script or hook, a repo's AGENTS.md, a person).

Return findings only, in that order. Mark anything you inferred rather than saw. If the skill did its job and nothing needs changing, say so; an empty retro is a valid result.
