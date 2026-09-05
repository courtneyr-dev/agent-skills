---
name: credit-routing
description: "Use at the start of any non-trivial task, when deciding whether to delegate, when a task has failed twice, before escalating model or effort, or when the user mentions credits, cost, tokens, routing, or 'which model'."
---

# Credit routing

Claude Code is the orchestrator, reviewer, and final judge — not the typist. Spend expensive tokens on judgment; route mechanical work to cheaper executors; make knowledge compound instead of re-deriving it.

Canonical references (read just in time, not preemptively):

- Routing matrix + examples: `~/.claude/knowledge/wiki/tools/tool-routing.md`
- Model/effort policy + failure diagnosis: `~/.claude/knowledge/wiki/tools/model-effort-policy.md`
- Delegation prompt template: `references/delegation-template.md`
- Verification, explainers, compaction: `references/verification-checklist.md`
- Unknowns mapping + context rules: `references/unknowns-and-context.md`
- Benchmark log + scorecard: `~/.claude/knowledge/wiki/tools/benchmark-log.md`

## The loop (every non-trivial task)

1. **Observe** — inspect only the needed files and current state. Grep/glob/index before opening files; Explore subagent for bulk sweeps.
2. **Orient** — check the wiki index (`~/.claude/knowledge/wiki/index.md`) and project instructions before re-deriving anything. For unfamiliar high-impact work, run a blind spot pass first (see unknowns-and-context.md).
3. **Decide** — route per tool-routing.md: Claude keeps judgment; subagents take bounded analysis; Gemini takes second-pass reading/critique; OpenClaw takes bounded personal automation; scripts take anything deterministic; ask the user only when the answer changes the architecture.
4. **Act** — smallest effective unit of work. Delegations use the template; specs are frozen before implementation starts.
5. **Verify** — diffs, tests, spec comparison. Delegated claims are advisory. Two failed delegation rounds → take over.
6. **Record** — durable learnings go to the wiki; routing lessons get a benchmark row; scratch notes get deleted. Only when the learning is durable.

## Hard rules

- Judgment stays with Claude: architecture, product decisions, API/UX design, naming, security, secrets, risk analysis, final review. Never delegated.
- Diagnose failures in order: context → effort → model. Never reach for a bigger model or more effort to compensate for a vague prompt, missing files, or bad scoping.
- Advisor/second-opinion cap: two per substantial task (one planning, one completion). Cheap verification for "does the patch match the spec?"; stronger model only for "is this the right approach?"
- Don't delegate tiny edits — overhead costs more than the work.
- Repeated deterministic work becomes a script, hook, or cron job, not another model call. A workflow that has run the same way three times is a loop to engineer, not a task to redo.
- **Freeze the session, not just the lesson.** When an exploratory session has *just produced* a procedure worth repeating, the last prompt of that session should be "write this as a script" — while the agent still holds the context that built it. Reconstructing it next week costs more and loses the details. Two reasons beyond credit: the script runs when every model is down, and it lives in git where it can be improved. Trigger on the second successful run, not the first.
- Destructive ops, production/GitHub mutations, releases, spend: explicit approval first, always.
- Soft budgets, stated up front: "read only these files first", "stop at the first decision point", "max two delegation rounds" — not token caps.
