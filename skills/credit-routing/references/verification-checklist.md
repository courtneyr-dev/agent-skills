# Verification, explainers, and compaction

## Verifying delegated work (always, no exceptions)

Delegated claims are advisory. Verify by:

1. `git status -sb`, then read the full diff.
2. Read implementation-notes.md if present; check deviations against the frozen spec.
3. Run focused tests (the exact command from the delegation prompt) when practical.
4. Check the diff touches only expected files.
5. Iterate via follow-up instructions rather than restarting from scratch.
6. Take over directly after two failed delegation rounds — a third identical attempt costs more than doing it.
7. If the task taught something durable: update the wiki (`~/.claude/knowledge/wiki/`), and add a benchmark row if it changes routing.

## Post-implementation explainer (substantial changes)

Give the user: what changed, why, which decisions mattered, remaining risks, what to inspect, which tests prove it, what was intentionally not done, and whether the route (tool/model/effort) was right.

Merge-readiness checklist for complex work — the user should be able to answer yes to:

- I understand the behavior that changed.
- I know which files were touched and which tests prove the change.
- I know what was not tested.
- I understand deviations from the plan and remaining risk.
- I agree this route should be used again for similar work.

## Compaction (long-horizon tasks)

Compact before context degrades, not after. Preserve: goal, constraints, architecture decisions, files touched, tests run, bugs found, open questions, risks, next action, deviations, unresolved unknowns, tool/model/effort route, anything to benchmark later.

Discard: raw tool output already distilled, repeated command output, dead-end exploration, redundant summaries, stale context that no longer affects decisions.

Durable state goes in notes or wiki pages, not chat history. Resume from notes, not by re-reading everything.
