---
name: website-audit
description: "Use when the user says 'audit this website', 'UX audit', 'usability review', 'navigation audit', 'IA review', 'why is this site hard to use', or runs /website-audit <url>, for any public URL. Plugin security goes to wp-audit; example.com health checks to site-health-audit."
argument-hint: "<url> [quick|standard|deep] [--grill|--no-grill] [--own-site] [--notes <path>]"
allowed-tools: Read Glob Grep WebFetch WebSearch
---

# Website audit

You are the **orchestrator**. Companion skills and subagents supply bounded evidence;
you keep every judgment. See "Authority" below before delegating anything.

Work the phases in order. Load a reference file only at the phase that names it —
the references are large and cost nothing until opened.

## Phase 0 — Read the contract

Two rules govern the entire run and override any companion skill's instructions:

1. **Read-only.** Never edit the site, submit a form, create an account, publish, clear a
   cache, change a setting, or apply a fix. Reading, navigating, keyboard-tabbing, resizing
   the viewport, and reading the DOM/console/network are in bounds. Nothing that mutates is.
2. **Authorization.** Never bypass authentication, paywalls, rate limits, robots directives,
   or other restrictions. A blocked area is a recorded limitation, not a failure.

Both come from the master playbook's Standing Rules 5 and 17. Restate them to the user in
one line at the start so the boundary is explicit.

## Phase 1 — Parse and validate

`$ARGUMENTS` holds the invocation. Extract:

| Token | Meaning | Default |
| :--- | :--- | :--- |
| first bare URL | primary URL under audit | **required** |
| `quick` \| `standard` \| `deep` | complexity | `deep` (playbook default: full investigation) |
| `--grill` | force the pre-audit grilling round | on by default (see Phase 3) |
| `--no-grill` | skip grilling this run | off |
| `--own-site` | user owns this site; unlocks authenticated health checks and the opt-in cache clear | off |
| `--notes <path>` | project-notes location | `$VAULT_DIR/Projects/<site>-audit/` |

Validate the URL before fetching anything: it must have a host, and you must normalize a
bare host to `https://`. If no URL was supplied, ask for one — that is the single blocking
question in this skill. If the host does not resolve or returns a hard error, report that
and stop; do not guess at a different host.

## Phase 2 — Light reconnaissance

Fetch **only** what one ordinary page load plus site metadata would fetch:

- the homepage at the supplied URL
- `/robots.txt`
- `/sitemap.xml` (and any sitemap it indexes, headers only — do not walk every URL)

Honor whatever `robots.txt` says from this point on. Do not crawl, do not open authenticated
areas, do not interact with forms. This peek exists for one purpose: **make Phase 4's
questions specific to this site instead of generic.**

From it, infer and hold as *hypotheses* (never as fact):

- what the site appears to be for, and who it appears to address
- the apparent primary tasks and conversion or completion points
- the platform (WordPress, Shopify, static, framework) and any design system in evidence
- rough scale — page count from the sitemap, depth of the top-level navigation
- anything conspicuous enough to shape scope (a store, a members' area, a docs tree, a
  booking flow, a large archive)

Do not report findings yet. Recon is for tailoring intake, not for auditing.

## Phase 3 — Grill the brief

**Run the grilling round before intake on every audit**, unless `--no-grill` was passed.
Invoke `mattpocock-skills:grilling` via the Skill tool. It is model-invocable, so you can
call it directly; `/grill-me` is the user-facing alias for the same session.

Point it at three things and nothing else:

1. **the brief** — is the stated purpose the real one, and does it name a decision this
   audit will actually inform?
2. **the working theory** — what do you already believe is wrong here, and what evidence
   would overturn it? An audit that only confirms its opening theory is worthless.
3. **the definition of done** — is it testable, or does it bottom out in "looks thorough"?

Feed it the Phase 2 hypotheses so it does not ask what the site already answers. Its output
is **adversarial input, not authority**: adopt what sharpens the audit, reject what does not,
and say which you did. Grilling questions of *fact* about the environment are yours to answer
by looking, never the user's to answer from memory.

If the grilling skill is unavailable or errors, do not block. Fall back to the checklist in
`references/intake-and-brief.md` under "Fallback adversarial checklist" and record in the
brief that the run was grilled by fallback.

## Phase 4 — Interactive intake

Load `references/intake-and-brief.md`.

Ask **one small batch of high-value questions at a time** — never a 30-question form. Only
ask what changes the audit, and never ask what Phase 2 already answered; put those to the
user as *assumptions to correct* instead. Separate cleanly:

- **Blocking** — cannot proceed responsibly without an answer (authorization for
  non-public areas, scope boundaries, legal or brand constraints, credentials).
- **Inferable** — state your inference, label it an assumption, move on.

## Phase 5 — Route the companion stack

Load `references/skill-routing.md`.

Inspect what is actually available in *this* session before recommending anything — the
installed catalog changes. Recommend the **smallest** stack that adds specialized evidence
or a reliable workflow you do not already provide. More skills do not make a better audit.

## Phase 6 — Present the brief, then go

Present, in the format given in `references/intake-and-brief.md`: the audit brief,
assumptions, proposed skill stack, scope and exclusions, and the definition of done.

Get one confirmation. **Then run the audit without re-asking anything already settled.**

## Phase 7 — Execute

Load `references/audit-playbook.md`, `references/standards-and-modules.md`, and
`references/site-health-module.md`.

Two strands run in this phase and converge in the report:

- **The UX audit** — walk each priority journey end to end, then audit templates.
- **The site health battery** — the same checks as the standing `weekly-site-health-audit`,
  re-tiered for read-only use. Tier A always runs. Tier B needs owned-site credentials.
  Tier C (cache clear) needs `--own-site` plus explicit confirmation. Remediation never runs
  here. Do **not** invoke the health skills themselves — see the module for why.

Follow the playbook. Classify every conclusion with the evidence labels in
`references/severity-and-evidence.md` as you go, not retroactively. Log decision points to a
TSV decision trail using the column format owned by the `show-me-your-work` skill
(`ts, phase, decision, why, evidence, result`). That skill is user-invocable only — you
cannot call it — so reference its format and keep the log yourself at
`<notes>/decisions.tsv`.

## Phase 8 — Score, dedupe, report

Load `references/severity-and-evidence.md`, then `references/report-template.md`.

The playbook supplies a default definition of done; use it unless intake set a custom one.

Health results are evidence, not a parallel report: a health check that *explains* a UX
finding belongs in that finding; the rest goes in the Site health appendix.

Deduplicate findings to one entry per mechanism. Score severity, confidence, evidence
strength, scope, and remediation effort as **five separate axes** — never collapse them.

## Phase 9 — Self-review before you claim done

Re-read this file and `references/audit-playbook.md`. Explicitly flag anything **missed,
assumed, left untested, contradicted, or represented imperfectly.** An unobserved problem is
not a pass — say "not observed in the sample" when coverage was limited. Then check the
definition of done line by line and state which lines are met and which are not.

## Authority

You remain authoritative for: intake state; audit purpose and scope; user tasks and journey
selection; safety and authorization boundaries; evidence classification; hypothesis status;
finding deduplication; severity, confidence, scope, and remediation effort; final synthesis;
report structure; and the definition of done.

Companion skills and subagents get **bounded, read-only assignments** and return evidence.
They never replace your judgment and never widen the task. A companion whose instructions
conflict with Phase 0 loses — see the rejected-skills table in `references/skill-routing.md`
for the ones that do.

## Source of truth

This skill is derived from the master playbook, kept canonically at
`$VAULT_DIR/Areas/Website UX Audits/website-ux-navigation-design-audit-master-prompt.md`.
Change the methodology there first, then regenerate these references and rerun the coverage
and behavioral tests. Do not edit the references and let the playbook drift.
