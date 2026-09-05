# Delegation prompt template

Use when handing work to Gemini CLI, OpenClaw, Codex (if installed), a subagent, or any other executor. Fill only the sections that apply — but never skip Goal, Frozen decisions, Non-goals, Verification, or Output format. The point is to make guessing impossible.

```text
Goal:
[Exact outcome. One sentence.]

Target tool:
[Gemini CLI / OpenClaw / Codex / Claude subagent / script]

Why this tool:
[Cheapest safe fit — one line.]

Workspace:
[Repo path, branch, app, or service.]

Inspect first:
- [path]
Do not inspect unless needed:
- [path]

Current state:
[What is true now.]

Frozen decisions:
- [Decision already made — do not revisit.]

Known unknowns:
- [Open questions we already know about.]
Possible blind spots:
- [Likely unknown unknowns; stop and report if one materializes.]

Constraints:
- [constraint]
Non-goals:
- [What not to do / not to touch.]

Implementation steps (if known):
1. [step]

Context budget:
- Read only the listed files first. Don't broaden scope without stating why.
- Stop and report if a new architecture decision appears.
- Max two attempts; then report back with what you learned.

Verification:
- Run: [exact command]
- Also check: [focused manual check]

Expected proof:
- Tests pass; diff limited to expected files; behavior matches spec.

Output format:
- Summary / Files changed / Tests run / Risks / Deviations from plan / Open questions

Implementation notes:
- For non-trivial work, write implementation-notes.md in the workspace: plan summary,
  decisions, deviations + why, conservative choices, open questions, follow-ups not done,
  tests run, evidence of completion, things the reviewer should check closely.
```

After the executor reports done: run the verification checklist (`verification-checklist.md`). Never accept "done" on the executor's word.
