---
name: loop-template
description: "Use when creating any new automated loop, scheduled task, or launchd job, or when the user says 'new loop', 'build a loop', 'add an automation', or 'scaffold a scheduled task', so the loop inherits the maker/checker pattern."
allowed-tools:
  - Read
  - Write
  - Bash
---

# Loop template

How to build a loop that's honest. A loop is a recurring task that finds its own work, does it, and verifies it — without you being the cron or the only checker.

## Step 0: the "when NOT to loop" gate (run this first)

Do not build the loop if any of these is true:

- **High slop-risk AND low verification confidence.** If the output is hard to auto-verify and a bad run pollutes a vault/repo/channel, keep it manual.
- **The follow-up is a <5-minute UI click, or it needs the user's eyes anyway.** Automating a thing you still has to review by hand just adds a step.
- **The output is taste, not facts.** Prose, atom-writing, social copy, design — loops can *draft* these into a "NEEDS REVIEW" file, but never auto-publish and never treat them as done.

If it passes the gate, continue.

## Step 1: name the five blocks

Write these down before any code:

1. **Automation** — what fires it? (cron schedule, launchd, hook, or manual)
2. **Maker** — the produce step. What does it create or change?
3. **Checker** — the verify step. See the rule below. This is the part that makes "done" mean something.
4. **Memory spine** — the file on disk that holds state between runs. Without it the loop can't tell "broken once" from "broken three weeks running."
5. **Connectors** — which MCP tools / CLIs it touches (gh, wp-cli, Jira, Beeper, Obsidian).

## Step 2: the blind-checker rule (non-negotiable)

**The checker re-derives findings from source. It does NOT re-read the maker's output.**

- Real checker: re-runs the test suite, re-fetches the live URL from outside the origin, re-queries the Jira JQL, re-pulls the API.
- Theater (don't do this): the maker writes a temp file of findings, then "Pass 2" re-reads that same file and grades it. That's self-grading with extra steps.

**Exception — deterministic facts need no second agent.** A git commit count, a file timestamp, an HTTP status code: the script that computes it IS the verification. Don't spawn a token-burning agent to "independently re-confirm" arithmetic. Use a second agent only when the thing being checked involves judgment or could plausibly be wrong on re-derivation.

## Step 3: the memory-spine convention

- Loop reports live in `$VAULT_DIR/Reports/` or a domain folder (`Site Health/`, `Plugin Health/`).
- State files (JSON, last-run pins, streak counters) live next to the task or in the report folder, named `_<loop>-state.json` or `<loop>/state.json`.
- Add a row to `_loop-registry.md` so the dashboard knows the loop exists.
- Write a dated report AND let the loop-of-loops meta-review update `_dashboard.md`.

## Step 4: the standard SKILL.md skeleton

```markdown
---
name: <loop-id>
description: <one line — what + cadence>
---

This is a <cadence> <domain> loop. You are a scheduled agent with no prior context.

**Paths:** vault `$VAULT_DIR/` (always absolute; `$HOME/...` paths are from the old laptop and don't exist here).
Report: `Reports/<loop>-YYYY-MM-DD.md`. State: `<path>/state.json`.

## Pass 1 — Maker: produce
[the work. Write raw findings to a temp file.]

## Pass 2 — Checker: re-derive from source
[re-run / re-fetch / re-query the SOURCE, independent of Pass 1's output.
Deterministic facts: assert inline, no second agent. Judgment calls: spawn a
blind Task that doesn't see Pass 1's reasoning.]

## Write report + update spine
[dated report; update state.json; update _dashboard.md row.]

**Rules:**
- Operate autonomously: never ask the user questions mid-run. Choose sensible defaults; if genuinely blocked, write the blocker into the report and end the run.
- On source failure: write a failure note, do NOT overwrite a good baseline/state.
- A read-only loop that errors must look DIFFERENT from a quiet day — always emit a heartbeat line so silent failure is visible.
- notifyOnCompletion: false unless the loop's whole job is to alert.
```

## Step 5: register it

After creating the task, add its row to `_loop-registry.md` and a `⚪ not yet run` row to `_dashboard.md`. Permissions persist via `permissions.allow` in `~/.claude/settings.json`, NOT via run-time approvals — each scheduled run is a fresh session, so "allow once" never carries over. If the loop needs a tool not already allowlisted, show the user the exact proposed rule and get your explicit yes before adding it (the auto-mode classifier blocks agent-written allow rules you hasn't specifically named).

## The three caveats to honor every time (Addy Osmani)

- **Verification is still on your.** A loop running unattended is a loop making mistakes unattended. The checker is what lets your walk away.
- **Comprehension debt.** The faster a loop ships work you didn't write, the bigger the gap. Reports are plain language, scannable, with exact commands — never an essay.
- **Token cost / slop.** Spend a second blind agent only where the second opinion is worth paying for. A cheap single deterministic pass beats a maker/checker when the fact isn't in dispute.
