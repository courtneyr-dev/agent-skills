# Companion skill routing

Load at Phase 5. Recommend the **smallest** stack that adds specialized evidence or a
reliable workflow the orchestrator does not already provide. More skills do not make a
better audit — they make a longer one with more duplicated output.

## Route by discovery, never by this list alone

The installed catalog changes. **Before recommending anything, look at what this session
actually has** — the available-skills listing and the available MCP tools — and treat the
tables below as priors to check, not as a hardcoded roster.

For any skill you have not routed to before, **read its `SKILL.md` before assigning work.**
Names lie. The rejections below were all discovered by reading, not by guessing.

Three questions decide every candidate:

1. **Does it add evidence or a workflow I lack?** If it only restates what you would do
   anyway, it costs context and returns nothing. Reject.
2. **Is every action it takes read-only?** A skill that clears a cache, edits content, or
   "auto-fixes" violates Phase 0 and is disqualified regardless of how useful the rest is.
3. **Can Claude actually invoke it?** `disable-model-invocation: true` means you cannot.
   Either tell the user the exact command to run, or use the skill's format without calling it.

## Browser and evidence channels are MCP, not skills

Live-site inspection comes from MCP tools. Pick one channel and stay on it:

| Channel | Use when |
| :--- | :--- |
| `mcp__Claude_Browser__*` | **Default.** In-app browser, isolated from the user's real sessions. Read-only inspection, `read_page` accessibility tree, console, network, `resize_window` for responsive passes. |
| `playwright` plugin | Scripted multi-viewport sweeps, or repeatable evidence you want to re-run. |
| `mcp__claude-in-chrome__*` | Only when the task genuinely needs the user's existing logged-in sessions. Ask first — it touches their real browser. |
| `mcp__Control_Chrome__*` | Fallback when the above are unavailable. |

`read_page` beats `screenshot` for verifying text, structure, heading order, landmarks, and
link names. Reach for screenshots when the finding is genuinely visual — layout, contrast,
spacing, visual hierarchy, focus-indicator visibility.

**`specification-website` MCP** is a strong, non-obvious fit: a read-only server for The
Website Specification with `get_checklist`, `list_topics`, and `search`. Items carry
`required` / `recommended` / `optional` / `avoid` status, which maps directly onto the
playbook's **Standards-based** evidence label. Use it to source standards claims instead of
asserting them from memory.

## Recommended stack

| Skill | Assignment | Why |
| :--- | :--- | :--- |
| `mattpocock-skills:grilling` | Phase 3 only — grill brief, working theory, definition of done. | Model-invocable. Round-based design-tree interview that stops when the frontier is empty. Directly serves the "is the definition of done testable" gate. `/grill-me` is the user-facing alias for the same session. |
| `unslop` | Final pass over report prose. | Its own description says it must always apply. Cheap, and audit reports are exactly where hedge-words and filler creep in. |

That is the default stack. Everything else is conditional on what intake surfaced.

## Conditional — route only when intake triggers it

| Skill | Trigger | Bounded assignment |
| :--- | :--- | :--- |
| `wordpress-accessibility` | Site is WordPress **and** accessibility is in scope | WCAG 2.1/2.2 AA patterns, ARIA, keyboard, contrast. Evidence only — never apply its remediation guidance to the site. |
| `wordpress-performance` | Site is WordPress **and** performance/Core Web Vitals in scope | LCP/INP/CLS interpretation and asset-loading analysis. Reject its server-side profiling steps — those need admin access. |
| `ui-ux-audit` | Interaction, motion, or design-system consistency in scope | Use `checklist.yaml` rows for `interaction_patterns`, `responsive_behavior`, `motion_design`. **Skip its `wordpress_admin` section** — that audits wp-admin, not a public site. |
| `wp-screenshots` | Authenticated journeys in scope **and** the user owns the site **and** credentials came through an authorized channel | Capture only. Its own docs say do not point it at production sites you do not own. |
| `better-documents` | Report goes to a non-technical or executive audience | Structure and framing of the deliverable. Never let it soften a finding's severity. |

## Absorbed, rejected, and why

Recorded so a future run does not re-litigate these. Re-open one only if the skill changes.

| Skill | Verdict | Reason |
| :--- | :--- | :--- |
| `site-health-audit` | **Not invoked — absorbed instead** | Its Phase 1 clears the site's caches and its Phase 15 auto-fixes post content and plugin settings. You cannot opt out of a skill's phases once you call it, so calling it would break Phase 0. Its **Phases 2–14 are reproduced in `site-health-module.md`**, re-tiered by what each check requires. Read its `config.example.yml` for the stack fields Tier B needs. |
| `site-health-audit` | Not invoked — absorbed instead | Same two write phases, plus hardcoded to example.com. Same battery, same module. Its dated reports in `Areas/Site Health/` are the **baseline for week-over-week diffs** when auditing that site. |
| `interrogate` | Rejected | `disable-model-invocation: true`, and it is scoped to reviewing *code changes and diffs*, not a live site. Grilling already covers adversarial input at the right layer. |
| `counselors` | Rejected by default | Dispatches external agents; its own header warns of 10–20+ minutes wall time. Offer it only if the user explicitly wants a multi-model second opinion on the finished report. |
| `wp-audit` | Rejected | Its site pass is a pre-launch security/health checklist and its plugin pass audits source for vulnerabilities. Different question from UX. Recommend it as *adjacent work* rather than routing to it. |
| `figure-it-out` | Rejected | Designs a playbook when none exists. One exists. It would also compete with this skill for orchestration authority. |
| `how` / `why` / `blast-radius` | Rejected | Codebase-oriented. `why` is worth mentioning only when the user has repo access and a finding turns on *why* something was built that way. |

## Cannot be invoked by Claude

| Skill | Constraint | What to do |
| :--- | :--- | :--- |
| `show-me-your-work` | `disable-model-invocation: true` | You cannot call it. Adopt its TSV column format — `ts, phase, decision, why, evidence, result` — and keep the log yourself. It explicitly invites this: *"Other skills route their audit trail here instead of inventing one."* Its mandatory cross-model subagent review and its Cursor-specific transcript path do not transfer; do not try to follow them. |
| `mattpocock-skills:grill-me` | `disable-model-invocation: true` | User-only alias. Its entire body is "Run a `/grilling` session." Call `mattpocock-skills:grilling` instead — same session, and you *can* invoke it. |

## Subagents

Fan out **bounded, read-only** evidence assignments — one per audit dimension (accessibility,
performance, responsive, IA and navigation, content design, forms and journeys). Each returns
evidence with the playbook's evidence labels already attached.

You keep every judgment: deduplication, severity, confidence, scope, effort, synthesis, and
the definition of done. A subagent's claim is **advisory until you verify it** — re-derive by
execution (reproduce the interaction, re-read the page) rather than by re-reading its
reasoning. Never let a subagent widen its own assignment.
