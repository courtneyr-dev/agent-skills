---
name: codex-first
description: "Use when a task is mechanical enough to specify completely (implementation from a settled design, refactor, migration, tests, coverage, CI fix, dependency bump, script) and bigger than a tiny edit, or when the user says 'have Codex build this', 'delegate the implementation', or 'codex-first'. Not for reviews or stuck-recovery."
---

# Codex-first: delegate implementation, keep judgment

Adapted from steipete's codex-first skill. Claude is the orchestrator; Codex is the implementation worker. Economics: move generation tokens to Codex — Claude spends tokens only on the spec and the review.

## Step 0 — should this be delegated at all?

Do it directly in Claude when ANY of these hold:

- **Tiny edit**: ~<20 changed lines with a single obvious change. Delegation overhead costs more than the work.
- **The spec IS the work**: ambiguity means design; design stays with Claude. If you can't write FROZEN DECISIONS, resolve the design first — don't delegate the ambiguity.
- **Session-bound tools needed**: MCP, browser, computer use, credentials, interactive auth.
- **Sensitive surface**: secrets, security-critical logic, destructive operations, releases/pushes/production/GitHub mutations.

Otherwise delegate: implementation from a frozen spec, refactors, mechanical migrations, test writing, coverage fills, CI fixes, dependency bumps, scripts/tooling, bulk mechanical exploration.

## Step 1 — preflight

```bash
command -v codex >/dev/null || echo "MISSING: npm install -g @openai/codex"
```

If missing or unauthenticated (`codex login`), tell the user and do the work directly rather than blocking.

Confirm the working tree state first (`git status -sb`) so you can attribute the diff to Codex afterward. If the tree is dirty with unrelated changes, note which files were already modified.

## Step 2 — write the frozen spec

Use the template at `~/.claude/skills/credit-routing/references/delegation-template.md`. Required fields: GOAL, REPO, RELEVANT FILES, CURRENT STATE, FROZEN DECISIONS, CONSTRAINTS, NON-GOALS, IMPLEMENTATION STEPS (if known), EXPECTED PROOF, TEST COMMAND, OUTPUT FORMAT. Spec quality decides success — a blank field means Codex guesses.

Always append this guard:

```
Do not read or modify anything under ~/.claude/, .claude/, agents/, or AGENTS.md files.
Do not make product, architecture, or naming decisions beyond the frozen ones.
If the spec is ambiguous, stop and report the ambiguity instead of guessing.
```

## Step 3 — delegate

Spec goes in a temp file, never inline:

```bash
P=$(mktemp)
cat >"$P" <<'EOF'
<the filled spec>
EOF
command codex exec -C <repo-root> -s workspace-write \
  -c model_reasoning_effort="high" \
  - <"$P" > /tmp/codex-last.md 2>&1
```

- Capture output by redirecting (`> /tmp/codex-last.md 2>&1`) — `codex exec` has no `-o` flag (exits 2 at 0.31.0), and stderr must be kept: startup failures are only diagnosable from it.
- A malformed `[mcp_servers.*]` entry in `~/.codex/config.toml` blocks every `codex exec` at startup. Bypass per-run with `-c 'mcp_servers={}'` — don't edit the user's config. Full failure catalog: `~/.claude/knowledge/wiki/tools/codex-cli.md`.
- Default sandbox is `workspace-write` (Codex can edit files and run tests inside the repo, nothing outside).
- Escalate to `--dangerously-bypass-approvals-and-sandbox` (`--yolo`) ONLY when the sandbox demonstrably blocks a needed command (network installs, global tooling) — say so when you do.
- Long tasks: run in the background (`run_in_background`) and continue orchestrating.

## Step 4 — verify (never skip)

Codex's report is advisory. Run the checklist at `~/.claude/skills/credit-routing/references/verification-checklist.md`:
`git status -sb` → read the full diff → compare against the spec (frozen decisions honored, non-goals untouched) → run the exact TEST COMMAND yourself → re-decide any assumption that was really a design call → scan for scope creep and secrets.

If the main context is hot, dispatch the `verification-reviewer` agent instead of reading the diff inline — but the final judgment stays with the main session.

## Step 5 — iterate or take over

Corrections go through resume, not a fresh session:

```bash
P2=$(mktemp); cat >"$P2" <<'EOF'
<what failed, exactly; what to change; same guard lines>
EOF
(cd <repo-root> && command codex exec resume --last \
  -s workspace-write -c model_reasoning_effort="high" \
  - <"$P2" > /tmp/codex-last.md 2>&1)
```

**After two failed rounds, take over and implement directly.** Note why the delegation failed.

## Step 6 — record

If the task produced durable learning: project code facts → gstack `/learn`; agent-ops rules (routing, template fixes, recurring delegation shapes) → `~/.claude/knowledge/wiki/` (+ index and log lines). Skip recording session-only details.

## Related

- gstack `/codex` — read-only review/challenge/consult (the advisor channel). Never modifies files.
- `codex:rescue` (openai-codex plugin) — stuck-recovery and second diagnosis pass.
- Credit routing policy — `~/.claude/CLAUDE.md` § Credit routing; full model in `~/.claude/knowledge/wiki/decisions/2026-07-08-credit-operating-model.md`.
