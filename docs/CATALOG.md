# Catalog

Everything, grouped by install path. Back to the [README](../README.md), or use the
[searchable version](https://courtneyr-dev.github.io/agent-skills/).

## WordPress sites — `-p wordpress`

Building and auditing a running WordPress site. Plugin and theme *development* skills live in the wp-dev-prompts companion repo below, and release testing in wp-release-audit-method — both linked with one-line installs.

### [`ollie`](../skills/ollie/)

Build and style sites with the Ollie block theme and Ollie Pro — tokens, patterns, theme.json.

*"build me a pricing page in Ollie" → block markup using the theme's own tokens and patterns, not generic HTML.*

### [`site-health-audit`](../skills/site-health-audit/)

Config-driven site audit: PageSpeed, accessibility, SEO, headers, SSL, email auth, carbon.

*"run the site health audit" → a dated report: PageSpeed numbers, contrast failures, missing headers, SSL and DNS records, each with the check that produced it.*

### [`website-audit`](../skills/website-audit/)

UX and information-architecture audit of any public URL, with findings ranked by severity.

*"audit example.com" → findings ranked by severity, each naming the page and the specific interaction that fails.*

### [`weekly-site-health-audit`](../skills/weekly-site-health-audit/)

Runs the site-health audit weekly and diffs it against last week.

*"weekly site health" → the same report plus a week-over-week diff, so you see what moved rather than re-reading everything.*

## Reading & Readwise — `-p reading`

Turn a read-later queue and highlights into notes you actually reuse.

### [`plaud`](../skills/plaud/)

Pull transcripts, summaries, and follow-ups from Plaud recordings.

*"what did I record yesterday?" → the transcript, a summary, and the follow-ups pulled out.*

### [`readwise-deep-read`](../skills/readwise-deep-read/)

Save, read, and annotate a queue of URLs, adding inline highlights to the saved document.

*paste five URLs → each saved, read, annotated with inline highlights, and written up with the claims separated from the commentary.*

### [`readwise-methods-review`](../skills/readwise-methods-review/)

Weekly pass over what you read that changes how you work, written up as a review.

*"weekly methods review" → what you read that changes how you work, with the rest discarded.*

### [`readwise-synthesis-pass`](../skills/readwise-synthesis-pass/)

Connect new notes to existing ones across a vault — the maker half of maker/checker.

*"run the synthesis pass" → new notes linked to existing ones, with a report of what connected and what stayed orphaned.*

### [`synthesis-backlog`](../skills/synthesis-backlog/)

Triage what is unprocessed: what to read, what needs synthesis, what got done.

*"what needs synthesis?" → a triaged list: what to read, what to process, what to drop.*

### [`transcript-processing`](../skills/transcript-processing/)

Turn meeting transcripts into notes and tracked actions.

*point it at a folder of meeting transcripts → notes plus tracked actions, each attributed to who committed to it.*

## PKM & Obsidian — `-p pkm`

Vault hygiene, wikis as memory, decision records, daily gathering, task sync.

### [`decision-sync`](../skills/decision-sync/)

File a finished decision record into a notes vault with frontmatter and backlinks.

*after a decision is made → the reasoning filed into your vault with frontmatter, backlinks, and an index row.*

### [`gatherer`](../skills/gatherer/)

Pull open issues, PRs, watched tickets, and tasks into today’s daily note.

*"what's on my plate?" → open issues, PRs, watched tickets and tasks pulled into today's note.*

### [`obsid-link-builder`](../skills/obsid-link-builder/)

Build and normalize shareable Obsidian links, with correct URL encoding.

*paste an obsidian:// link → a shareable URL with the vault and file parameters encoded correctly.*

### [`things-obsidian-sync`](../skills/things-obsidian-sync/)

Two-way sync between Things tasks and an Obsidian vault.

*runs on a schedule → tasks and notes stay in step without you reconciling them by hand.*

### [`vault-hygiene-checker`](../skills/vault-hygiene-checker/)

Verify a synthesis pass actually landed — the checker half of maker/checker.

*"check the vault" → whether the last synthesis pass actually landed: broken links, orphans, frontmatter that lies.*

### [`wiki-cycle`](../skills/wiki-cycle/)

One maintenance pass over a registered wiki: scan, ingest, lint, report, record state.

*"run the theology cycle" → one pass: scan what changed, ingest it by that wiki's rules, lint, write a report and run state.*

### [`wiki-memory`](../skills/wiki-memory/)

Staging-and-promotion flow that turns passing signals into durable wiki pages.

*"remember this in the wiki" → the signal staged, deduplicated, and promoted into a durable page with an index entry.*

## Faith & church notes — `-p faith`

Sermon notes, scripture study, and turning a Sunday bulletin into structured notes. Denomination-neutral: the study skill reads multiple translations, and the bulletin skill reads whatever your church actually prints rather than assuming a format.

### [`bible-study`](../skills/bible-study/)

Scholarly multi-translation passage study written into a vault.

*"study Romans 8" → multiple translations, the scholarly reading, and the disagreements named rather than smoothed over.*

### [`church-bulletin-to-obsidian`](../skills/church-bulletin-to-obsidian/)

Turn a church bulletin image or text into a structured sermon-notes file.

*photograph the bulletin → a sermon-notes file with the readings, liturgical date, and scaffolding to write into.*

## Writing — `-p writing`

Drafting and de-slopping prose, docs, commits, and long-form content.

### [`anti-slop-git-writing`](../skills/anti-slop-git-writing/)

Commit messages, PRs, and issues that read like a person wrote them under time pressure.

*before committing → a message that says what changed and why, in the voice of someone who was there.*

### [`email-draft-review`](../skills/email-draft-review/)

Triage an inbox and prepare replies — drafts only, never sends.

*"triage my inbox" → replies prepared for the mail that needs answers. Drafts only; it never sends.*

### [`field-notes-draft`](../skills/field-notes-draft/)

Rank newsletter candidates from recent reading, then draft the issue once you pick a theme.

*"Field Notes" → three ranked themes from the week's reading; pick one and it drafts the issue.*

### [`learning-path`](../skills/learning-path/)

Plan what to learn next, or run a retro on a path you finished.

*"what should I learn next?" → a sequence with milestones, each with a pass/fail check.*

### [`technical-writing`](../skills/technical-writing/)

Turn in-progress code into an article, tutorial, or docs page in your own voice.

*"write this up" → the code you just wrote turned into an article that keeps the reasoning, not just the result.*

## Dev workflow — `-p dev`

Routing work between models, repo hygiene, scheduling, and notifications.

### [`codex-first`](../skills/codex-first/)

Delegate fully-specified mechanical work to Codex instead of doing it inline.

*a fully-specified refactor → handed to Codex with the spec, and the result verified before you see it.*

### [`credit-routing`](../skills/credit-routing/)

Decide what to delegate, to which model, at what effort — before starting the work.

*at the start of anything non-trivial → which model, what effort, and what to delegate, decided before the work starts.*

### [`devrel-engine`](../skills/devrel-engine/)

Turn transcripts and community signals into a prioritized DevRel program.

*paste a month of community signal → a prioritized program, not a summary.*

### [`github-profile`](../skills/github-profile/)

Improve a GitHub profile README, bio, pinned repos, and stats.

*"make my profile look good" → README, bio, pinned repos and stats that say what you actually do.*

### [`github-repo`](../skills/github-repo/)

Prepare a repo for open source: README, CONTRIBUTING, SECURITY, templates, release hygiene.

*"prepare this for open source" → the files a stranger needs before they will trust your repo.*

### [`job-search`](../skills/job-search/)

Repeatable job scan across boards, ATS pages, email, LinkedIn, and chat, diffed each run.

*"run the job scan" → today's roles diffed against yesterday: new, still open, closed, each scored.*

### [`lmk`](../skills/lmk/)

Push a phone notification when long-running work finishes.

*"LMK when you're done" → a phone push when the long job finishes, not a progress feed.*

### [`loop-template`](../skills/loop-template/)

Scaffold a scheduled job so it inherits the maker/checker pattern from the start.

*"add an automation" → a scheduled job that inherits the maker/checker pattern instead of running unchecked.*

### [`prop-for-that`](../skills/prop-for-that/)

React in CSS to runtime state CSS cannot see — checks for a native property first.

*"react to scroll position in CSS" → the native property if one exists, and the minimal JS bridge if not.*

### [`skill-retro`](../skills/skill-retro/)

Mine a session for lessons and route them as edits to the repo that owns the skill.

*a skill drives 15+ tool calls → the Stop hook offers a retro; say yes and get a retro note plus a PR, fork commit or drafted issue in the skill's own repo, sent only after you approve.*

### [`skill-sync`](../skills/skill-sync/)

Keep GitHub-sourced skills updated, and audit which skills are used, dormant, or dead.

*weekly → GitHub-sourced skills updated, plus an audit of which of yours are used, dormant, or dead.*

## Company fleets — `-p fleets`

One registry of roles, workloads and eval cases for agency, consulting, product, DevRel, community and corporate work, plus the deterministic gates those roles call. Every company record is a labeled fixture (Fixture Co). The gate skills read shared code and fixtures from company-fleets and factory-rig, which sit beside them in this repository. Roles also attach upstream skills from other people's repos; those are marked external and install from their own sources.

### [`agency-engagement-gate`](../skills/agency-engagement-gate/)

Gate each stage of an agency engagement on hashed, independently accepted evidence and a sourced margin floor.

*"is this brief ready to price?" → a margin check against the rate card and a stage-by-stage verdict naming the missing evidence.*

### [`agency-i18n-check`](../skills/agency-i18n-check/)

Catch placeholder, plural, untranslated and right-to-left defects in gettext catalogs, templates and CSS.

*"check the PO files" → each defect with its file and line, and linguistic review left as a required human step.*

### [`agency-keyboard-audit`](../skills/agency-keyboard-audit/)

Tab through a page in headless Chromium and report keyboard traps, mouse-only controls and invisible focus.

*"keyboard audit the donate page" → an axe-core baseline plus each WCAG 2.1.1, 2.1.2, 2.4.3 and 2.4.7 failure with steps to reproduce.*

### [`agency-platform-adapters`](../skills/agency-platform-adapters/)

Map a client project's platform and version to the exact platform skills to load, and route legacy versions.

*"which skills for a WooCommerce site on PHP 7.2?" → the legacy route and the skills it needs, or why none apply.*

### [`community-health-measures`](../skills/community-health-measures/)

Lint a community measurement plan and compute its numbers from sourced, consent-aware definitions.

*"what should our community health metrics be?" → each metric with a question, a CHAOSS or local definition, and the computed aggregate.*

### [`community-moderation-review`](../skills/community-moderation-review/)

Check a moderation recommendation against the case record before any human sees it.

*draft a recommendation for a conduct report → a check that nothing is presumed proven, sent or sanctioned, with recusals and the appeal route kept.*

### [`community-operating-kit`](../skills/community-operating-kit/)

Write or complete a community program's operating kit and check every section is present and sourced.

*"we need a charter and an onboarding path" → the eight kit sections mapped to their sources, with the missing ones named.*

### [`company-fleets`](../skills/company-fleets/)

Registry and validator for company fleets: pick the smallest role set for a workload and guard handoffs between fleets.

*"which roles handle a hosting restore?" → the role set, its one coordinator, and the files each role may read.*

### [`consult-compliance-engagement`](../skills/consult-compliance-engagement/)

Gate a compliance engagement through applicability, owners, fresh same-tenant evidence, gaps and reporting.

*"can we issue the SOC 2 readiness report?" → the first stage that fails and why, or a report ready for human sign-off.*

### [`consult-email-send-gate`](../skills/consult-email-send-gate/)

Pre-send gate for one email campaign: suppression, permission, tenant, sender authentication and unsubscribe. Stages, never sends.

*"is this campaign ready to send?" → each blocked recipient with the rule that blocked it, and a staged result for human approval.*

### [`consult-i18n-check`](../skills/consult-i18n-check/)

Check a translated string catalog against its source for placeholder, plural, bidi, length and glossary defects.

*"QA the Arabic catalog" → each defect by key, with translation accuracy left to a human reviewer.*

### [`consult-search-claims-check`](../skills/consult-search-claims-check/)

Reject fabricated citations, edited captures and guaranteed-placement promises in an SEO or AI-search report.

*"check this SEO audit before it goes out" → each claim tied to a captured source, or flagged with the reason.*

### [`corporate-claims-check`](../skills/corporate-claims-check/)

Stop ranking guarantees, uncited statistics and unverifiable quotes in a marketing or comms draft before staging.

*"claims check this blog post" → every number and quote matched to the sources register, or flagged.*

### [`corporate-email-guard`](../skills/corporate-email-guard/)

Send gate that drops suppressed and off-list contacts and refuses any send without a named human's hash-bound approval.

*"send the November newsletter" → refused until an approval names the exact campaign and recipient hashes; delivery goes to a local fake outbox.*

### [`devrel-program-kit`](../skills/devrel-program-kit/)

Keep a DevRel program's routing and claims honest: routed skills installed, program state in one context file.

*"check our DevRel program plan" → routed skills that aren't installed, their fallbacks, and claims without evidence.*

### [`devrel-quickstart-replay`](../skills/devrel-quickstart-replay/)

Prove a quickstart or tutorial works as written by replaying its shell blocks in a clean temp environment.

*"does our quickstart still work?" → each step's output checked against the doc, with the first divergence named.*

### [`product-payment-events`](../skills/product-payment-events/)

Prove duplicate or retried payment webhooks can't capture, fulfill, decrement stock or refund twice.

*replay a webhook log → one capture per order, with replayed and out-of-order events shown converging.*

### [`product-release-gate`](../skills/product-release-gate/)

Gate an extension or SDK release on compatibility, SemVer, changelog, SBOM and review evidence.

*"is v2.0 ready to publish?" → refused before packaging if a host version is untested, otherwise ready for human approval.*

## Education — `-p education`

School and workplace teaching: BCIT and computer science units, assessment and answer-key checks, standards alignment against a verified registry, needs analysis, research review, trainer development, and a student-data guard that refuses reads the school's policy doesn't allow.

### [`bcit-learning-package`](../skills/bcit-learning-package/)

Build and check a complete BCIT course-unit package, from objectives to rubric and accessibility notes.

*"build a unit on spreadsheet budgeting" → objectives, teacher guide, student materials, practice, rubric, and a package check that names gaps.*

### [`cs-classroom-instruction`](../skills/cs-classroom-instruction/)

Build a runnable school computer science lesson or lab, or give feedback on code a learner actually wrote.

*"a grade 9 lab on loops" → a teacher guide, runnable examples with expected output, misconception probes and a rubric.*

### [`edu-answer-key-check`](../skills/edu-answer-key-check/)

Execute an answer key's formulas, SQL, Python and calculations and compare the results with the stated answers.

*"check the quiz answer key" → each answer recomputed, with every mismatch and its executed value.*

### [`edu-assessment-check`](../skills/edu-assessment-check/)

Check that an assessment's tasks, rubric and scoring line up with the objectives they claim to measure.

*"review this rubric" → misaligned criteria, cognitive-level mismatches and barriers outside the intended construct.*

### [`edu-learning-progression`](../skills/edu-learning-progression/)

Check a prerequisite map or course sequence for cycles, gaps and ordering errors.

*"map the CS course sequence" → the progression, with cycles and unreachable topics named.*

### [`edu-needs-analysis`](../skills/edu-needs-analysis/)

Decide whether training fixes a performance problem before anyone builds a course.

*"we need a course on the new process" → a diagnosis that separates knowledge and practice from tools, incentives and access.*

### [`edu-research-review`](../skills/edu-research-review/)

Critique education research and program evaluations with traced citations and bounded claims.

*"does this study show pair programming works?" → the design, its threats to validity, and the claim the evidence supports.*

### [`edu-standards-alignment`](../skills/edu-standards-alignment/)

Check standards alignments and professional references against a verified registry, so nothing claims an unsupported match.

*"align this unit to CSTA" → each cited standard verified, or flagged as a gap.*

### [`edu-student-data-guard`](../skills/edu-student-data-guard/)

Decide whether a workflow may read a student record under tenant rules and the school's verified policy.

*"pull last term's grades for feedback" → allowed or refused, naming the policy clause and the owner grant.*

### [`edu-trainer-development`](../skills/edu-trainer-development/)

Develop trainers and teachers: facilitation guides, modeled examples, observation feedback and rubric calibration.

*"help our facilitators run this workshop" → a guide with design rationale, a modeled example and a plan for transfer evidence.*

## Hosting operations — `-p hosting`

Gates for running a hosting service on synthetic lab data: account lifecycle, DNS and TLS, incident response, restore drills, data migration, tenant isolation, metering and the service catalogue. The benchmark cites public provider documentation and keeps documented claims, targets, configuration, measurements and contracts in separate fields.

### [`hosting-abuse-response`](../skills/hosting-abuse-response/)

Handle an abuse report with hashed evidence, a chain of custody, and only the actions a policy clause authorizes.

*"phishing report against tenant B" → evidence preserved with hashes, embedded instructions flagged as data, and a recorded decision.*

### [`hosting-account-lifecycle`](../skills/hosting-account-lifecycle/)

Run a hosted account from qualify to decommission with idempotent, recoverable panel side effects.

*"provision a reseller account" → each step recorded once, so a retry after a crash does no duplicate work.*

### [`hosting-benchmark-matrix`](../skills/hosting-benchmark-matrix/)

Keep a hosting benchmark honest: documented claim, target, configuration, measurement and contract stay separate.

*"say we're more robust than the big hosts" → refused, with the readiness backlog that would have to close first.*

### [`hosting-data-migration`](../skills/hosting-data-migration/)

Preflight, rehearse and prove a hosted site's data migration, with automatic rollback and a portable export.

*"upgrade the database engine" → a compatibility preflight, a rehearsal with checksum proof, and the rollback result.*

### [`hosting-dns-cert-lifecycle`](../skills/hosting-dns-cert-lifecycle/)

Check DNS zones and TLS certificates through create, change, migrate, renew and decommission.

*"we're decommissioning the old host" → dangling records, takeover risk and certificate problems to fix first.*

### [`hosting-incident-response`](../skills/hosting-incident-response/)

Run a hosting incident from alert to learning handoff, with a tamper-evident record and external messages held as drafts.

*"the API error rate is spiking" → a burn-rate check, a routed page, and a record that won't resolve without recovery evidence.*

### [`hosting-metering-reconcile`](../skills/hosting-metering-reconcile/)

Dedupe meter events, enforce published quotas and reconcile invoices against metered usage.

*"reconcile November invoices" → each invoice line matched to usage, with duplicates and overcharges flagged.*

### [`hosting-restore-exercise`](../skills/hosting-restore-exercise/)

Break a disposable site on purpose, restore it, and measure detection time, RTO and RPO.

*"run a restore drill" → measured detection, recovery and data-loss times from a real restore.*

### [`hosting-service-catalogue`](../skills/hosting-service-catalogue/)

Check a hosting service catalogue and its responsibility matrix against one operating profile.

*"review our reseller catalogue" → duties claimed but not controlled, and duties owed but missing.*

### [`hosting-tenant-isolation`](../skills/hosting-tenant-isolation/)

Test tenant boundaries: record access, a tamper-evident audit trail, secrets in build output, and sandboxed untrusted builds.

*"can this preview be promoted?" → refused, listing the leaked secret, the failed scan and the missing approval.*

## Delivery factory — `-p delivery`

One dispatcher per task, leases, and a merge gate that re-runs verification before anything lands.

### [`factory-execute`](../skills/factory-execute/)

Implement one leased task contract in its worktree, run the verify command, commit, and report.

*the router dispatches one task → a committed candidate and a proof line carrying the commit SHA.*

### [`factory-rig`](../skills/factory-rig/)

Route each software task to one dispatcher, hold its lease, and merge only after a fresh verify and an independent review.

*"what may start next?" → the frontier, with the reason each blocked task can't start.*

## Companion repos

### [wp-release-audit-method](https://github.com/courtneyr-dev/wp-release-audit-method) — GPL-2.0

The full WordPress release-testing method: guides, fixtures, scripts, CI, and the release-day agent skills. The four release skills referenced here live there.

| Skill | What it does |
|---|---|
| [`wordpress-audit-handoff`](https://github.com/courtneyr-dev/wp-release-audit-method/tree/main/skills/wordpress-audit-handoff) | Turn testing results into one self-contained document a colleague can act on. |
| [`wp-release-followup`](https://github.com/courtneyr-dev/wp-release-audit-method/tree/main/skills/wp-release-followup) | After a release: check filed tickets, find what got fixed, log what is still open. |
| [`wp-release-party`](https://github.com/courtneyr-dev/wp-release-audit-method/tree/main/skills/wp-release-party) | Run the release-day checklist against a Beta or RC and produce a shareable report. |
| [`wp-release-prep`](https://github.com/courtneyr-dev/wp-release-audit-method/tree/main/skills/wp-release-prep) | Phase 0 — build fixtures and get test environments ready before a release lands. |

### [wp-dev-prompts](https://github.com/courtneyr-dev/wp-dev-prompts) — CC0-1.0

WordPress development prompts and skills — the canonical home for the WordPress development set, plus security, UI/UX audit, engineering and product prompts.

| Skill | What it does |
|---|---|
| [`prompt-engineering`](https://github.com/courtneyr-dev/wp-dev-prompts/tree/main/skills/prompt-engineering) | Write, improve, and review prompts and system prompts. |
| [`wordpress-accessibility`](https://github.com/courtneyr-dev/wp-dev-prompts/tree/main/skills/wordpress-accessibility) | WCAG 2.2 AA review for themes, plugins, and blocks — keyboard, focus, ARIA, contrast. |
| [`wordpress-dev`](https://github.com/courtneyr-dev/wp-dev-prompts/tree/main/skills/wordpress-dev) | Plugin, block, and theme development — block.json, theme.json, REST, hooks, the Security Trinity. |
| [`wordpress-performance`](https://github.com/courtneyr-dev/wp-dev-prompts/tree/main/skills/wordpress-performance) | Core Web Vitals, caching, object cache, asset loading, slow queries, PHP profiling. |
| [`wordpress-playground`](https://github.com/courtneyr-dev/wp-dev-prompts/tree/main/skills/wordpress-playground) | Browser-based WordPress via WebAssembly for demos, PR previews, and throwaway test sites. |
| [`wordpress-testing`](https://github.com/courtneyr-dev/wp-dev-prompts/tree/main/skills/wordpress-testing) | PHPUnit, WP_Mock, wp-env, PHPCS, Playwright, and a CI matrix for plugins and themes. |
| [`engineering`](https://github.com/courtneyr-dev/wp-dev-prompts/tree/main/skills/engineering) | Engineering practice prompts — architecture, review, debugging. |
| [`product-management`](https://github.com/courtneyr-dev/wp-dev-prompts/tree/main/skills/product-management) | Product management prompts — specs, roadmaps, prioritization. |
| [`ui-ux-audit`](https://github.com/courtneyr-dev/wp-dev-prompts/tree/main/skills/ui-ux-audit) | UI and UX audit prompts for interface review. |
| [`wordpress-security`](https://github.com/courtneyr-dev/wp-dev-prompts/tree/main/skills/wordpress-security) | WordPress security review — the Security Trinity, nonces, capabilities. |
| [`wp-screenshots`](https://github.com/courtneyr-dev/wp-dev-prompts/tree/main/skills/wp-screenshots) | Scripted WordPress admin and front-end screenshots for docs and release posts. |

## External — install from source

These belong to their authors and are never copied here. Each links to the **original** source. Entries added on 2026-11-27 record the upstream commit they were checked against in `source.pinned` in [manifest.json](../manifest.json).

| Skill | Original source | License |
|---|---|---|
| [`woocommerce-finalize`](https://github.com/Automattic/claude-woocommerce-toolkit/tree/main/skills/woocommerce-finalize) | [Automattic/claude-woocommerce-toolkit](https://github.com/Automattic/claude-woocommerce-toolkit) | GPL-2.0-or-later |
| [`woocommerce-plugin-dev`](https://github.com/Automattic/claude-woocommerce-toolkit/tree/main/skills/woocommerce-plugin-dev) | [Automattic/claude-woocommerce-toolkit](https://github.com/Automattic/claude-woocommerce-toolkit) | GPL-2.0-or-later |
| [`woocommerce-upgrade-safety`](https://github.com/Automattic/claude-woocommerce-toolkit/tree/main/skills/woocommerce-upgrade-safety) | [Automattic/claude-woocommerce-toolkit](https://github.com/Automattic/claude-woocommerce-toolkit) | GPL-2.0-or-later |
| [`wp-pinch`](https://github.com/RegionallyFamous/wp-pinch) | [RegionallyFamous/wp-pinch](https://github.com/RegionallyFamous/wp-pinch) | GPL-2.0-or-later<br>Nick Hamze |
| [`blueprint`](https://github.com/WordPress/agent-skills/tree/trunk/skills/blueprint) | [WordPress/agent-skills](https://github.com/WordPress/agent-skills) | GPL-2.0-or-later<br>Copyright (C) 2026 WordPress Contributors |
| [`wordpress-router`](https://github.com/WordPress/agent-skills/tree/trunk/skills/wordpress-router) | [WordPress/agent-skills](https://github.com/WordPress/agent-skills) | GPL-2.0-or-later<br>Copyright (C) 2026 WordPress Contributors |
| [`wp-abilities-api`](https://github.com/WordPress/agent-skills/tree/trunk/skills/wp-abilities-api) | [WordPress/agent-skills](https://github.com/WordPress/agent-skills) | GPL-2.0-or-later<br>Copyright (C) 2026 WordPress Contributors |
| [`wp-abilities-audit`](https://github.com/WordPress/agent-skills/tree/trunk/skills/wp-abilities-audit) | [WordPress/agent-skills](https://github.com/WordPress/agent-skills) | GPL-2.0-or-later<br>Copyright (C) 2026 WordPress Contributors |
| [`wp-abilities-verify`](https://github.com/WordPress/agent-skills/tree/trunk/skills/wp-abilities-verify) | [WordPress/agent-skills](https://github.com/WordPress/agent-skills) | GPL-2.0-or-later<br>Copyright (C) 2026 WordPress Contributors |
| [`wp-ability-development`](https://github.com/WordPress/agent-skills/tree/trunk/skills/wp-ability-development) | [WordPress/agent-skills](https://github.com/WordPress/agent-skills) | GPL-2.0-or-later<br>Copyright (C) 2026 WordPress Contributors |
| [`wp-block-development`](https://github.com/WordPress/agent-skills/tree/trunk/skills/wp-block-development) | [WordPress/agent-skills](https://github.com/WordPress/agent-skills) | GPL-2.0-or-later<br>Copyright (C) 2026 WordPress Contributors |
| [`wp-block-themes`](https://github.com/WordPress/agent-skills/tree/trunk/skills/wp-block-themes) | [WordPress/agent-skills](https://github.com/WordPress/agent-skills) | GPL-2.0-or-later<br>Copyright (C) 2026 WordPress Contributors |
| [`wp-env`](https://github.com/WordPress/agent-skills/tree/trunk/skills/wp-env) | [WordPress/agent-skills](https://github.com/WordPress/agent-skills) | GPL-2.0-or-later<br>Copyright (C) 2026 WordPress Contributors |
| [`wp-interactivity-api`](https://github.com/WordPress/agent-skills/tree/trunk/skills/wp-interactivity-api) | [WordPress/agent-skills](https://github.com/WordPress/agent-skills) | GPL-2.0-or-later<br>Copyright (C) 2026 WordPress Contributors |
| [`wp-patterns`](https://github.com/WordPress/agent-skills/tree/trunk/skills/wp-patterns) | [WordPress/agent-skills](https://github.com/WordPress/agent-skills) | GPL-2.0-or-later<br>Copyright (C) 2026 WordPress Contributors |
| [`wp-performance`](https://github.com/WordPress/agent-skills/tree/trunk/skills/wp-performance) | [WordPress/agent-skills](https://github.com/WordPress/agent-skills) | GPL-2.0-or-later<br>Copyright (C) 2026 WordPress Contributors |
| [`wp-phpstan`](https://github.com/WordPress/agent-skills/tree/trunk/skills/wp-phpstan) | [WordPress/agent-skills](https://github.com/WordPress/agent-skills) | GPL-2.0-or-later<br>Copyright (C) 2026 WordPress Contributors |
| [`wp-playground`](https://github.com/WordPress/agent-skills/tree/trunk/skills/wp-playground) | [WordPress/agent-skills](https://github.com/WordPress/agent-skills) | GPL-2.0-or-later<br>Copyright (C) 2026 WordPress Contributors |
| [`wp-plugin-development`](https://github.com/WordPress/agent-skills/tree/trunk/skills/wp-plugin-development) | [WordPress/agent-skills](https://github.com/WordPress/agent-skills) | GPL-2.0-or-later<br>Copyright (C) 2026 WordPress Contributors |
| [`wp-plugin-directory-guidelines`](https://github.com/WordPress/agent-skills/tree/trunk/skills/wp-plugin-directory-guidelines) | [WordPress/agent-skills](https://github.com/WordPress/agent-skills) | GPL-2.0-or-later<br>Copyright (C) 2026 WordPress Contributors |
| [`wp-project-triage`](https://github.com/WordPress/agent-skills/tree/trunk/skills/wp-project-triage) | [WordPress/agent-skills](https://github.com/WordPress/agent-skills) | GPL-2.0-or-later<br>Copyright (C) 2026 WordPress Contributors |
| [`wp-rest-api`](https://github.com/WordPress/agent-skills/tree/trunk/skills/wp-rest-api) | [WordPress/agent-skills](https://github.com/WordPress/agent-skills) | GPL-2.0-or-later<br>Copyright (C) 2026 WordPress Contributors |
| [`wp-wpcli-and-ops`](https://github.com/WordPress/agent-skills/tree/trunk/skills/wp-wpcli-and-ops) | [WordPress/agent-skills](https://github.com/WordPress/agent-skills) | GPL-2.0-or-later<br>Copyright (C) 2026 WordPress Contributors |
| [`wpds`](https://github.com/WordPress/agent-skills/tree/trunk/skills/wpds) | [WordPress/agent-skills](https://github.com/WordPress/agent-skills) | GPL-2.0-or-later<br>Copyright (C) 2026 WordPress Contributors |
| [`counselors`](https://github.com/aarondfrancis/counselors) | [aarondfrancis/counselors](https://github.com/aarondfrancis/counselors) | MIT |
| [`access-lifecycle`](https://github.com/alirezarezvani/claude-skills/tree/main/ra-qm-team/skills/access-lifecycle) | [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | MIT<br>Copyright (c) 2025 Alireza Rezvani |
| [`capacity-planner`](https://github.com/alirezarezvani/claude-skills/tree/main/business-operations/skills/capacity-planner) | [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | MIT<br>Copyright (c) 2025 Alireza Rezvani |
| [`ceo-advisor`](https://github.com/alirezarezvani/claude-skills/tree/main/c-level-advisor/skills/ceo-advisor) | [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | MIT<br>Copyright (c) 2025 Alireza Rezvani |
| [`cfo-advisor`](https://github.com/alirezarezvani/claude-skills/tree/main/c-level-advisor/skills/cfo-advisor) | [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | MIT<br>Copyright (c) 2025 Alireza Rezvani |
| [`channel-economics`](https://github.com/alirezarezvani/claude-skills/tree/main/commercial/skills/channel-economics) | [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | MIT<br>Copyright (c) 2025 Alireza Rezvani |
| [`chro-advisor`](https://github.com/alirezarezvani/claude-skills/tree/main/c-level-advisor/skills/chro-advisor) | [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | MIT<br>Copyright (c) 2025 Alireza Rezvani |
| [`ciso-advisor`](https://github.com/alirezarezvani/claude-skills/tree/main/c-level-advisor/skills/ciso-advisor) | [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | MIT<br>Copyright (c) 2025 Alireza Rezvani |
| [`compliance-os`](https://github.com/alirezarezvani/claude-skills/tree/main/compliance-os/skills/compliance-os) | [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | MIT<br>Copyright (c) 2025 Alireza Rezvani |
| [`coo-advisor`](https://github.com/alirezarezvani/claude-skills/tree/main/c-level-advisor/skills/coo-advisor) | [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | MIT<br>Copyright (c) 2025 Alireza Rezvani |
| [`cpo-advisor`](https://github.com/alirezarezvani/claude-skills/tree/main/c-level-advisor/skills/cpo-advisor) | [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | MIT<br>Copyright (c) 2025 Alireza Rezvani |
| [`cro-advisor`](https://github.com/alirezarezvani/claude-skills/tree/main/c-level-advisor/skills/cro-advisor) | [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | MIT<br>Copyright (c) 2025 Alireza Rezvani |
| [`cto-advisor`](https://github.com/alirezarezvani/claude-skills/tree/main/c-level-advisor/skills/cto-advisor) | [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | MIT<br>Copyright (c) 2025 Alireza Rezvani |
| [`customer-success-manager`](https://github.com/alirezarezvani/claude-skills/tree/main/business-growth/skills/customer-success-manager) | [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | MIT<br>Copyright (c) 2025 Alireza Rezvani |
| [`deal-desk`](https://github.com/alirezarezvani/claude-skills/tree/main/commercial/skills/deal-desk) | [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | MIT<br>Copyright (c) 2025 Alireza Rezvani |
| [`financial-analyst`](https://github.com/alirezarezvani/claude-skills/tree/main/finance/skills/financial-analyst) | [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | MIT<br>Copyright (c) 2025 Alireza Rezvani |
| [`gdpr-dsgvo-expert`](https://github.com/alirezarezvani/claude-skills/tree/main/ra-qm-team/skills/gdpr-dsgvo-expert) | [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | MIT<br>Copyright (c) 2025 Alireza Rezvani |
| [`general-counsel-advisor`](https://github.com/alirezarezvani/claude-skills/tree/main/c-level-advisor/skills/general-counsel-advisor) | [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | MIT<br>Copyright (c) 2025 Alireza Rezvani |
| [`isms-audit-expert`](https://github.com/alirezarezvani/claude-skills/tree/main/ra-qm-team/skills/isms-audit-expert) | [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | MIT<br>Copyright (c) 2025 Alireza Rezvani |
| [`month-end-close`](https://github.com/alirezarezvani/claude-skills/tree/main/finance/skills/month-end-close) | [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | MIT<br>Copyright (c) 2025 Alireza Rezvani |
| [`partnerships-architect`](https://github.com/alirezarezvani/claude-skills/tree/main/commercial/skills/partnerships-architect) | [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | MIT<br>Copyright (c) 2025 Alireza Rezvani |
| [`pricing-strategist`](https://github.com/alirezarezvani/claude-skills/tree/main/commercial/skills/pricing-strategist) | [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | MIT<br>Copyright (c) 2025 Alireza Rezvani |
| [`process-mapper`](https://github.com/alirezarezvani/claude-skills/tree/main/business-operations/skills/process-mapper) | [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | MIT<br>Copyright (c) 2025 Alireza Rezvani |
| [`procurement-optimizer`](https://github.com/alirezarezvani/claude-skills/tree/main/business-operations/skills/procurement-optimizer) | [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | MIT<br>Copyright (c) 2025 Alireza Rezvani |
| [`product-analytics`](https://github.com/alirezarezvani/claude-skills/tree/main/product-team/skills/product-analytics) | [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | MIT<br>Copyright (c) 2025 Alireza Rezvani |
| [`revenue-operations`](https://github.com/alirezarezvani/claude-skills/tree/main/business-growth/skills/revenue-operations) | [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | MIT<br>Copyright (c) 2025 Alireza Rezvani |
| [`rfp-responder`](https://github.com/alirezarezvani/claude-skills/tree/main/commercial/skills/rfp-responder) | [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | MIT<br>Copyright (c) 2025 Alireza Rezvani |
| [`sales-engineer`](https://github.com/alirezarezvani/claude-skills/tree/main/business-growth/skills/sales-engineer) | [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | MIT<br>Copyright (c) 2025 Alireza Rezvani |
| [`soc2-compliance`](https://github.com/alirezarezvani/claude-skills/tree/main/ra-qm-team/skills/soc2-compliance) | [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | MIT<br>Copyright (c) 2025 Alireza Rezvani |
| [`support-ops`](https://github.com/alirezarezvani/claude-skills/tree/main/business-growth/skills/support-ops) | [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | MIT<br>Copyright (c) 2025 Alireza Rezvani |
| [`vendor-management`](https://github.com/alirezarezvani/claude-skills/tree/main/business-operations/skills/vendor-management) | [alirezarezvani/claude-skills](https://github.com/alirezarezvani/claude-skills) | MIT<br>Copyright (c) 2025 Alireza Rezvani |
| [`aim`](https://github.com/borkweb/discernment-skills/tree/main/plugins/discernment/skills/aim) | [borkweb/discernment-skills](https://github.com/borkweb/discernment-skills) | MIT |
| [`cross-check`](https://github.com/borkweb/discernment-skills/tree/main/plugins/discernment/skills/cross-check) | [borkweb/discernment-skills](https://github.com/borkweb/discernment-skills) | MIT |
| [`own`](https://github.com/borkweb/discernment-skills/tree/main/plugins/discernment/skills/own) | [borkweb/discernment-skills](https://github.com/borkweb/discernment-skills) | MIT |
| [`skill-patterns`](https://github.com/borkweb/skill-patterns/tree/main/skills/skill-patterns) | [borkweb/skill-patterns](https://github.com/borkweb/skill-patterns) | MIT |
| [`agents-md-lint`](https://github.com/borkweb/skills/tree/main/skills/core/agents-md-lint) | [borkweb/skills](https://github.com/borkweb/skills) | MIT |
| [`review-security`](https://github.com/borkweb/skills/tree/main/skills/core/review-security) | [borkweb/skills](https://github.com/borkweb/skills) | MIT |
| [`writing-sql`](https://github.com/borkweb/skills/tree/main/skills/core/writing-sql) | [borkweb/skills](https://github.com/borkweb/skills) | MIT |
| [`cloudflare-one`](https://github.com/cloudflare/skills/tree/main/skills/cloudflare-one) | [cloudflare/skills](https://github.com/cloudflare/skills) | Apache-2.0 |
| [`gateway-workers`](https://github.com/cloudflare/skills/tree/main/skills/gateway-workers) | [cloudflare/skills](https://github.com/cloudflare/skills) | Apache-2.0 |
| [`workers-best-practices`](https://github.com/cloudflare/skills/tree/main/skills/workers-best-practices) | [cloudflare/skills](https://github.com/cloudflare/skills) | Apache-2.0 |
| [`wrangler`](https://github.com/cloudflare/skills/tree/main/skills/wrangler) | [cloudflare/skills](https://github.com/cloudflare/skills) | Apache-2.0 |
| [`ab-testing`](https://github.com/coreyhaines31/marketingskills/tree/main/skills/ab-testing) | [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | MIT<br>Copyright (c) 2025 Corey Haines |
| [`ad-creative`](https://github.com/coreyhaines31/marketingskills/tree/main/skills/ad-creative) | [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | MIT<br>Copyright (c) 2025 Corey Haines |
| [`ads`](https://github.com/coreyhaines31/marketingskills/tree/main/skills/ads) | [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | MIT<br>Copyright (c) 2025 Corey Haines |
| [`ai-seo`](https://github.com/coreyhaines31/marketingskills/tree/main/skills/ai-seo) | [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | MIT<br>Copyright (c) 2025 Corey Haines |
| [`analytics`](https://github.com/coreyhaines31/marketingskills/tree/main/skills/analytics) | [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | MIT<br>Copyright (c) 2025 Corey Haines |
| [`attribution`](https://github.com/coreyhaines31/marketingskills/tree/main/skills/attribution) | [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | MIT<br>Copyright (c) 2025 Corey Haines |
| [`competitor-profiling`](https://github.com/coreyhaines31/marketingskills/tree/main/skills/competitor-profiling) | [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | MIT<br>Copyright (c) 2025 Corey Haines |
| [`content-strategy`](https://github.com/coreyhaines31/marketingskills/tree/main/skills/content-strategy) | [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | MIT<br>Copyright (c) 2025 Corey Haines |
| [`conversion-tracking`](https://github.com/coreyhaines31/marketingskills/tree/main/skills/conversion-tracking) | [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | MIT<br>Copyright (c) 2025 Corey Haines |
| [`customer-research`](https://github.com/coreyhaines31/marketingskills/tree/main/skills/customer-research) | [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | MIT<br>Copyright (c) 2025 Corey Haines |
| [`emails`](https://github.com/coreyhaines31/marketingskills/tree/main/skills/emails) | [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | MIT<br>Copyright (c) 2025 Corey Haines |
| [`launch`](https://github.com/coreyhaines31/marketingskills/tree/main/skills/launch) | [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | MIT<br>Copyright (c) 2025 Corey Haines |
| [`marketing-loops`](https://github.com/coreyhaines31/marketingskills/tree/main/skills/marketing-loops) | [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | MIT<br>Copyright (c) 2025 Corey Haines |
| [`marketing-plan`](https://github.com/coreyhaines31/marketingskills/tree/main/skills/marketing-plan) | [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | MIT<br>Copyright (c) 2025 Corey Haines |
| [`product-marketing`](https://github.com/coreyhaines31/marketingskills/tree/main/skills/product-marketing) | [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | MIT<br>Copyright (c) 2025 Corey Haines |
| [`prospecting`](https://github.com/coreyhaines31/marketingskills/tree/main/skills/prospecting) | [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | MIT<br>Copyright (c) 2025 Corey Haines |
| [`public-relations`](https://github.com/coreyhaines31/marketingskills/tree/main/skills/public-relations) | [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | MIT<br>Copyright (c) 2025 Corey Haines |
| [`referrals`](https://github.com/coreyhaines31/marketingskills/tree/main/skills/referrals) | [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | MIT<br>Copyright (c) 2025 Corey Haines |
| [`sales-enablement`](https://github.com/coreyhaines31/marketingskills/tree/main/skills/sales-enablement) | [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | MIT<br>Copyright (c) 2025 Corey Haines |
| [`schema`](https://github.com/coreyhaines31/marketingskills/tree/main/skills/schema) | [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | MIT<br>Copyright (c) 2025 Corey Haines |
| [`seo-audit`](https://github.com/coreyhaines31/marketingskills/tree/main/skills/seo-audit) | [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | MIT<br>Copyright (c) 2025 Corey Haines |
| [`site-architecture`](https://github.com/coreyhaines31/marketingskills/tree/main/skills/site-architecture) | [coreyhaines31/marketingskills](https://github.com/coreyhaines31/marketingskills) | MIT<br>Copyright (c) 2025 Corey Haines |
| [`architect`](https://github.com/cursor/plugins/tree/main/pstack/skills/architect) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`arena`](https://github.com/cursor/plugins/tree/main/pstack/skills/arena) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`automate-me`](https://github.com/cursor/plugins/tree/main/pstack/skills/automate-me) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`blast-radius`](https://github.com/cursor/plugins/tree/main/pstack/skills/blast-radius) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`bro`](https://github.com/cursor/plugins/tree/main/pstack/skills/bro) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`create-verification-skill`](https://github.com/cursor/plugins/tree/main/pstack/skills/create-verification-skill) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`figure-it-out`](https://github.com/cursor/plugins/tree/main/pstack/skills/figure-it-out) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`how`](https://github.com/cursor/plugins/tree/main/pstack/skills/how) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`interrogate`](https://github.com/cursor/plugins/tree/main/pstack/skills/interrogate) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`maintain-verification-skill`](https://github.com/cursor/plugins/tree/main/pstack/skills/maintain-verification-skill) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`no-comments`](https://github.com/cursor/plugins/tree/main/pstack/skills/no-comments) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`poteto-mode`](https://github.com/cursor/plugins/tree/main/pstack/skills/poteto-mode) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`principle-boundary-discipline`](https://github.com/cursor/plugins/tree/main/pstack/skills/principle-boundary-discipline) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`principle-build-the-lever`](https://github.com/cursor/plugins/tree/main/pstack/skills/principle-build-the-lever) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`principle-encode-lessons-in-structure`](https://github.com/cursor/plugins/tree/main/pstack/skills/principle-encode-lessons-in-structure) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`principle-exhaust-the-design-space`](https://github.com/cursor/plugins/tree/main/pstack/skills/principle-exhaust-the-design-space) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`principle-experience-first`](https://github.com/cursor/plugins/tree/main/pstack/skills/principle-experience-first) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`principle-fix-root-causes`](https://github.com/cursor/plugins/tree/main/pstack/skills/principle-fix-root-causes) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`principle-foundational-thinking`](https://github.com/cursor/plugins/tree/main/pstack/skills/principle-foundational-thinking) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`principle-guard-the-context-window`](https://github.com/cursor/plugins/tree/main/pstack/skills/principle-guard-the-context-window) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`principle-laziness-protocol`](https://github.com/cursor/plugins/tree/main/pstack/skills/principle-laziness-protocol) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`principle-make-operations-idempotent`](https://github.com/cursor/plugins/tree/main/pstack/skills/principle-make-operations-idempotent) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`principle-migrate-callers-then-delete-legacy-apis`](https://github.com/cursor/plugins/tree/main/pstack/skills/principle-migrate-callers-then-delete-legacy-apis) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`principle-minimize-reader-load`](https://github.com/cursor/plugins/tree/main/pstack/skills/principle-minimize-reader-load) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`principle-model-the-domain`](https://github.com/cursor/plugins/tree/main/pstack/skills/principle-model-the-domain) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`principle-never-block-on-the-human`](https://github.com/cursor/plugins/tree/main/pstack/skills/principle-never-block-on-the-human) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`principle-outcome-oriented-execution`](https://github.com/cursor/plugins/tree/main/pstack/skills/principle-outcome-oriented-execution) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`principle-prove-it-works`](https://github.com/cursor/plugins/tree/main/pstack/skills/principle-prove-it-works) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`principle-redesign-from-first-principles`](https://github.com/cursor/plugins/tree/main/pstack/skills/principle-redesign-from-first-principles) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`principle-separate-before-serializing-shared-state`](https://github.com/cursor/plugins/tree/main/pstack/skills/principle-separate-before-serializing-shared-state) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`principle-sequence-verifiable-units`](https://github.com/cursor/plugins/tree/main/pstack/skills/principle-sequence-verifiable-units) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`principle-subtract-before-you-add`](https://github.com/cursor/plugins/tree/main/pstack/skills/principle-subtract-before-you-add) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`principle-type-system-discipline`](https://github.com/cursor/plugins/tree/main/pstack/skills/principle-type-system-discipline) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`recall`](https://github.com/cursor/plugins/tree/main/pstack/skills/recall) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`reflect`](https://github.com/cursor/plugins/tree/main/pstack/skills/reflect) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`setup-pstack`](https://github.com/cursor/plugins/tree/main/pstack/skills/setup-pstack) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`show-me-your-work`](https://github.com/cursor/plugins/tree/main/pstack/skills/show-me-your-work) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`swarm`](https://github.com/cursor/plugins/tree/main/pstack/skills/swarm) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`tdd`](https://github.com/cursor/plugins/tree/main/pstack/skills/tdd) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`teach`](https://github.com/cursor/plugins/tree/main/pstack/skills/teach) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`technical-writing-standard`](https://github.com/cursor/plugins/tree/main/pstack/skills/technical-writing-standard) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`typescript-best-practices`](https://github.com/cursor/plugins/tree/main/pstack/skills/typescript-best-practices) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`unslop`](https://github.com/cursor/plugins/tree/main/pstack/skills/unslop) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`why`](https://github.com/cursor/plugins/tree/main/pstack/skills/why) | [cursor/plugins](https://github.com/cursor/plugins)<br><sub>via courtneyr-dev/plugins (fork)</sub> | MIT<br>Copyright (c) 2026 Lauren Tan (poteto) |
| [`terraform-style-guide`](https://github.com/hashicorp/agent-skills/tree/main/plugins/terraform/skills/terraform-style-guide) | [hashicorp/agent-skills](https://github.com/hashicorp/agent-skills) | MPL-2.0 |
| [`terraform-test`](https://github.com/hashicorp/agent-skills/tree/main/plugins/terraform/skills/terraform-test) | [hashicorp/agent-skills](https://github.com/hashicorp/agent-skills) | MPL-2.0<br>Copyright IBM Corp. 2026 |
| [`librarium`](https://github.com/jkudish/librarium) | [jkudish/librarium](https://github.com/jkudish/librarium) | MIT |
| [`code-standards-checker`](https://github.com/kanopi/cms-cultivator/tree/main/skills/code-standards-checker) | [kanopi/cms-cultivator](https://github.com/kanopi/cms-cultivator) | GPL-2.0-or-later |
| [`composer-security-update`](https://github.com/kanopi/cms-cultivator/tree/main/skills/composer-security-update) | [kanopi/cms-cultivator](https://github.com/kanopi/cms-cultivator) | GPL-2.0-or-later |
| [`pr-quality-report`](https://github.com/kanopi/cms-cultivator/tree/main/skills/pr-quality-report) | [kanopi/cms-cultivator](https://github.com/kanopi/cms-cultivator) | GPL-2.0-or-later |
| [`k12-check-for-understanding`](https://github.com/learning-commons-org/agent-skills/tree/main/skills/k12-check-for-understanding) | [learning-commons-org/agent-skills](https://github.com/learning-commons-org/agent-skills) | Apache-2.0<br>Copyright 2026 Anthropic, PBC; Copyright 2026 Learning Commons |
| [`k12-fixing-lesson-plans`](https://github.com/learning-commons-org/agent-skills/tree/main/skills/k12-fixing-lesson-plans) | [learning-commons-org/agent-skills](https://github.com/learning-commons-org/agent-skills) | Apache-2.0<br>Copyright 2026 Learning Commons |
| [`k12-lesson-differentiation`](https://github.com/learning-commons-org/agent-skills/tree/main/skills/k12-lesson-differentiation) | [learning-commons-org/agent-skills](https://github.com/learning-commons-org/agent-skills) | Apache-2.0<br>Copyright 2026 Anthropic, PBC; Copyright 2026 Learning Commons |
| [`k12-lesson-plan-creation`](https://github.com/learning-commons-org/agent-skills/tree/main/skills/k12-lesson-plan-creation) | [learning-commons-org/agent-skills](https://github.com/learning-commons-org/agent-skills) | Apache-2.0<br>Copyright 2026 Anthropic, PBC; Copyright 2026 Learning Commons |
| [`k12-lesson-prep`](https://github.com/learning-commons-org/agent-skills/tree/main/skills/k12-lesson-prep) | [learning-commons-org/agent-skills](https://github.com/learning-commons-org/agent-skills) | Apache-2.0<br>Copyright 2026 Anthropic, PBC; Copyright 2026 Learning Commons |
| [`agent-evals-and-observability`](https://github.com/magnus919/agent-skills/tree/main/agent-evals-and-observability) | [magnus919/agent-skills](https://github.com/magnus919/agent-skills) | MIT<br>Copyright (c) 2026 Magnus Hedemark |
| [`implementation-planning`](https://github.com/magnus919/agent-skills/tree/main/implementation-planning) | [magnus919/agent-skills](https://github.com/magnus919/agent-skills) | MIT<br>Copyright (c) 2026 Magnus Hedemark |
| [`incident-learning`](https://github.com/magnus919/agent-skills/tree/main/incident-learning) | [magnus919/agent-skills](https://github.com/magnus919/agent-skills) | MIT<br>Copyright (c) 2026 Magnus Hedemark |
| [`kanban-guru`](https://github.com/magnus919/agent-skills/tree/main/kanban-guru) | [magnus919/agent-skills](https://github.com/magnus919/agent-skills) | MIT<br>Copyright (c) 2026 Magnus Hedemark |
| [`multi-agent-coordination`](https://github.com/magnus919/agent-skills/tree/main/multi-agent-coordination) | [magnus919/agent-skills](https://github.com/magnus919/agent-skills) | MIT<br>Copyright (c) 2026 Magnus Hedemark |
| [`production-readiness`](https://github.com/magnus919/agent-skills/tree/main/production-readiness) | [magnus919/agent-skills](https://github.com/magnus919/agent-skills) | MIT<br>Copyright (c) 2026 Magnus Hedemark |
| [`release-engineering`](https://github.com/magnus919/agent-skills/tree/main/release-engineering) | [magnus919/agent-skills](https://github.com/magnus919/agent-skills) | MIT<br>Copyright (c) 2026 Magnus Hedemark |
| [`technical-program-management`](https://github.com/magnus919/agent-skills/tree/main/technical-program-management) | [magnus919/agent-skills](https://github.com/magnus919/agent-skills) | MIT<br>Copyright (c) 2026 Magnus Hedemark |
| [`technical-project-management`](https://github.com/magnus919/agent-skills/tree/main/technical-project-management) | [magnus919/agent-skills](https://github.com/magnus919/agent-skills) | MIT<br>Copyright (c) 2026 Magnus Hedemark |
| [`verification-methodology`](https://github.com/magnus919/agent-skills/tree/main/verification-methodology) | [magnus919/agent-skills](https://github.com/magnus919/agent-skills) | MIT<br>Copyright (c) 2026 Magnus Hedemark |
| [`web-accessibility`](https://github.com/magnus919/agent-skills/tree/main/web-accessibility) | [magnus919/agent-skills](https://github.com/magnus919/agent-skills) | MIT<br>Copyright (c) 2026 Magnus Hedemark |
| [`ask-matt`](https://github.com/mattpocock/skills/tree/main/skills/engineering/ask-matt) | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT<br>Copyright (c) 2026 Matt Pocock |
| [`chief-of-staff`](https://github.com/mattpocock/skills/tree/main/skills/in-progress/chief-of-staff) | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT<br>Copyright (c) 2026 Matt Pocock |
| [`claude-handoff`](https://github.com/mattpocock/skills/tree/main/skills/in-progress/claude-handoff) | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT<br>Copyright (c) 2026 Matt Pocock |
| [`code-review`](https://github.com/mattpocock/skills/tree/main/skills/engineering/code-review) | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT<br>Copyright (c) 2026 Matt Pocock |
| [`codebase-design`](https://github.com/mattpocock/skills/tree/main/skills/engineering/codebase-design) | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT<br>Copyright (c) 2026 Matt Pocock |
| [`diagnosing-bugs`](https://github.com/mattpocock/skills/tree/main/skills/engineering/diagnosing-bugs) | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT<br>Copyright (c) 2026 Matt Pocock |
| [`domain-modeling`](https://github.com/mattpocock/skills/tree/main/skills/engineering/domain-modeling) | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT<br>Copyright (c) 2026 Matt Pocock |
| [`git-guardrails-claude-code`](https://github.com/mattpocock/skills/tree/main/skills/misc/git-guardrails-claude-code) | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT<br>Copyright (c) 2026 Matt Pocock |
| [`grill-me`](https://github.com/mattpocock/skills/tree/main/skills/productivity/grill-me) | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT<br>Copyright (c) 2026 Matt Pocock |
| [`grill-with-docs`](https://github.com/mattpocock/skills/tree/main/skills/engineering/grill-with-docs) | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT<br>Copyright (c) 2026 Matt Pocock |
| [`grilling`](https://github.com/mattpocock/skills/tree/main/skills/productivity/grilling) | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT<br>Copyright (c) 2026 Matt Pocock |
| [`handoff`](https://github.com/mattpocock/skills/tree/main/skills/productivity/handoff) | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT<br>Copyright (c) 2026 Matt Pocock |
| [`implement`](https://github.com/mattpocock/skills/tree/main/skills/engineering/implement) | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT<br>Copyright (c) 2026 Matt Pocock |
| [`implement-spec`](https://github.com/mattpocock/skills/tree/main/skills/engineering/implement-spec) | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT<br>Copyright (c) 2026 Matt Pocock |
| [`improve-codebase-architecture`](https://github.com/mattpocock/skills/tree/main/skills/engineering/improve-codebase-architecture) | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT<br>Copyright (c) 2026 Matt Pocock |
| [`loop-me`](https://github.com/mattpocock/skills/tree/main/skills/in-progress/loop-me) | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT<br>Copyright (c) 2026 Matt Pocock |
| [`migrate-to-shoehorn`](https://github.com/mattpocock/skills/tree/main/skills/misc/migrate-to-shoehorn) | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT<br>Copyright (c) 2026 Matt Pocock |
| [`pr`](https://github.com/mattpocock/skills/tree/main/skills/engineering/pr) | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT<br>Copyright (c) 2026 Matt Pocock |
| [`prototype`](https://github.com/mattpocock/skills/tree/main/skills/engineering/prototype) | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT<br>Copyright (c) 2026 Matt Pocock |
| [`research`](https://github.com/mattpocock/skills/tree/main/skills/engineering/research) | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT<br>Copyright (c) 2026 Matt Pocock |
| [`scaffold-exercises`](https://github.com/mattpocock/skills/tree/main/skills/misc/scaffold-exercises) | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT<br>Copyright (c) 2026 Matt Pocock |
| [`setup-matt-pocock-skills`](https://github.com/mattpocock/skills/tree/main/skills/engineering/setup-matt-pocock-skills) | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT<br>Copyright (c) 2026 Matt Pocock |
| [`setup-pre-commit`](https://github.com/mattpocock/skills/tree/main/skills/misc/setup-pre-commit) | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT<br>Copyright (c) 2026 Matt Pocock |
| [`setup-ts-deep-modules`](https://github.com/mattpocock/skills/tree/main/skills/in-progress/setup-ts-deep-modules) | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT<br>Copyright (c) 2026 Matt Pocock |
| [`software-factory`](https://github.com/mattpocock/skills/tree/main/skills/in-progress/software-factory) | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT<br>Copyright (c) 2026 Matt Pocock |
| [`to-questionnaire`](https://github.com/mattpocock/skills/tree/main/skills/productivity/to-questionnaire) | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT<br>Copyright (c) 2026 Matt Pocock |
| [`to-spec`](https://github.com/mattpocock/skills/tree/main/skills/engineering/to-spec) | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT<br>Copyright (c) 2026 Matt Pocock |
| [`to-tickets`](https://github.com/mattpocock/skills/tree/main/skills/engineering/to-tickets) | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT<br>Copyright (c) 2026 Matt Pocock |
| [`wait-what`](https://github.com/mattpocock/skills/tree/main/skills/productivity/wait-what) | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT<br>Copyright (c) 2026 Matt Pocock |
| [`wayfinder`](https://github.com/mattpocock/skills/tree/main/skills/engineering/wayfinder) | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT<br>Copyright (c) 2026 Matt Pocock |
| [`wizard`](https://github.com/mattpocock/skills/tree/main/skills/engineering/wizard) | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT<br>Copyright (c) 2026 Matt Pocock |
| [`writing-beats`](https://github.com/mattpocock/skills/tree/main/skills/in-progress/writing-beats) | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT<br>Copyright (c) 2026 Matt Pocock |
| [`writing-for-agents`](https://github.com/mattpocock/skills/tree/main/skills/productivity/writing-for-agents) | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT<br>Copyright (c) 2026 Matt Pocock |
| [`writing-fragments`](https://github.com/mattpocock/skills/tree/main/skills/in-progress/writing-fragments) | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT<br>Copyright (c) 2026 Matt Pocock |
| [`writing-shape`](https://github.com/mattpocock/skills/tree/main/skills/in-progress/writing-shape) | [mattpocock/skills](https://github.com/mattpocock/skills) | MIT<br>Copyright (c) 2026 Matt Pocock |
| [`deepdive`](https://github.com/nemock/video-explainer-system/tree/main/skills/deepdive) | [nemock/video-explainer-system](https://github.com/nemock/video-explainer-system) | MIT<br>Copyright (c) 2026 Dave Saunders |
| [`explainer`](https://github.com/nemock/video-explainer-system/tree/main/skills/explainer) | [nemock/video-explainer-system](https://github.com/nemock/video-explainer-system) | MIT<br>Copyright (c) 2026 Dave Saunders |
| [`defuddle`](https://github.com/obsidianmd/obsidian-skills/tree/main/plugins/obsidian/skills/defuddle) | [obsidianmd/obsidian-skills](https://github.com/obsidianmd/obsidian-skills) | MIT<br>Copyright (c) 2026 Steph Ango (@kepano) |
| [`json-canvas`](https://github.com/obsidianmd/obsidian-skills/tree/main/plugins/obsidian/skills/json-canvas) | [obsidianmd/obsidian-skills](https://github.com/obsidianmd/obsidian-skills) | MIT<br>Copyright (c) 2026 Steph Ango (@kepano) |
| [`knap`](https://github.com/obsidianmd/obsidian-skills/tree/main/plugins/obsidian/skills/knap) | [obsidianmd/obsidian-skills](https://github.com/obsidianmd/obsidian-skills) | MIT<br>Copyright (c) 2026 Steph Ango (@kepano) |
| [`obsidian-bases`](https://github.com/obsidianmd/obsidian-skills/tree/main/plugins/obsidian/skills/obsidian-bases) | [obsidianmd/obsidian-skills](https://github.com/obsidianmd/obsidian-skills) | MIT<br>Copyright (c) 2026 Steph Ango (@kepano) |
| [`obsidian-cli`](https://github.com/obsidianmd/obsidian-skills/tree/main/plugins/obsidian/skills/obsidian-cli) | [obsidianmd/obsidian-skills](https://github.com/obsidianmd/obsidian-skills) | MIT<br>Copyright (c) 2026 Steph Ango (@kepano) |
| [`obsidian-headless`](https://github.com/obsidianmd/obsidian-skills/tree/main/plugins/obsidian/skills/obsidian-headless) | [obsidianmd/obsidian-skills](https://github.com/obsidianmd/obsidian-skills) | MIT<br>Copyright (c) 2026 Steph Ango (@kepano) |
| [`obsidian-markdown`](https://github.com/obsidianmd/obsidian-skills/tree/main/plugins/obsidian/skills/obsidian-markdown) | [obsidianmd/obsidian-skills](https://github.com/obsidianmd/obsidian-skills) | MIT<br>Copyright (c) 2026 Steph Ango (@kepano) |
| [`noodle`](https://github.com/poteto/noodle/tree/main/.agents/skills/noodle) | [poteto/noodle](https://github.com/poteto/noodle) | MIT<br>Copyright (c) 2026 Lauren Tan |
| [`book-review`](https://github.com/readwiseio/readwise-skills/tree/main/skills/book-review) | [readwiseio/readwise-skills](https://github.com/readwiseio/readwise-skills) | NONE — no redistribution |
| [`build-persona`](https://github.com/readwiseio/readwise-skills/tree/main/skills/build-persona) | [readwiseio/readwise-skills](https://github.com/readwiseio/readwise-skills) | NONE — no redistribution |
| [`feed-catchup`](https://github.com/readwiseio/readwise-skills/tree/main/skills/feed-catchup) | [readwiseio/readwise-skills](https://github.com/readwiseio/readwise-skills) | NONE — no redistribution |
| [`highlight-graph`](https://github.com/readwiseio/readwise-skills/tree/main/skills/highlight-graph) | [readwiseio/readwise-skills](https://github.com/readwiseio/readwise-skills) | NONE — no redistribution |
| [`now-reading-page`](https://github.com/readwiseio/readwise-skills/tree/main/skills/now-reading-page) | [readwiseio/readwise-skills](https://github.com/readwiseio/readwise-skills) | NONE — no redistribution |
| [`quiz`](https://github.com/readwiseio/readwise-skills/tree/main/skills/quiz) | [readwiseio/readwise-skills](https://github.com/readwiseio/readwise-skills) | NONE — no redistribution |
| [`reader-recap`](https://github.com/readwiseio/readwise-skills/tree/main/skills/reader-recap) | [readwiseio/readwise-skills](https://github.com/readwiseio/readwise-skills) | NONE — no redistribution |
| [`readwise-cli`](https://github.com/readwiseio/readwise-skills/tree/main/skills/readwise-cli) | [readwiseio/readwise-skills](https://github.com/readwiseio/readwise-skills) | NONE — no redistribution |
| [`readwise-mcp`](https://github.com/readwiseio/readwise-skills/tree/main/skills/readwise-mcp) | [readwiseio/readwise-skills](https://github.com/readwiseio/readwise-skills) | NONE — no redistribution |
| [`surprise-me`](https://github.com/readwiseio/readwise-skills/tree/main/skills/surprise-me) | [readwiseio/readwise-skills](https://github.com/readwiseio/readwise-skills) | NONE — no redistribution |
| [`triage`](https://github.com/readwiseio/readwise-skills/tree/main/skills/triage) | [readwiseio/readwise-skills](https://github.com/readwiseio/readwise-skills) | NONE — no redistribution |
| [`add-expert`](https://github.com/remotion-dev/remotion/tree/main/.agents/skills/add-expert) | [remotion-dev/remotion](https://github.com/remotion-dev/remotion) | Other — no redistribution |
| [`gh-fetch`](https://github.com/retlehs/gh-fetch) | [retlehs/gh-fetch](https://github.com/retlehs/gh-fetch) | NONE — no redistribution |
| [`bluesky-dev-playbook`](https://github.com/samber/developer-relations-skills/tree/main/skills/bluesky-dev-playbook) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`build-in-public`](https://github.com/samber/developer-relations-skills/tree/main/skills/build-in-public) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`changelog-writing`](https://github.com/samber/developer-relations-skills/tree/main/skills/changelog-writing) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`coding-agent-docs-optimization`](https://github.com/samber/developer-relations-skills/tree/main/skills/coding-agent-docs-optimization) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`conference-cfp-submission`](https://github.com/samber/developer-relations-skills/tree/main/skills/conference-cfp-submission) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`dailydev-playbook`](https://github.com/samber/developer-relations-skills/tree/main/skills/dailydev-playbook) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`developer-booth-playbook`](https://github.com/samber/developer-relations-skills/tree/main/skills/developer-booth-playbook) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`developer-case-study`](https://github.com/samber/developer-relations-skills/tree/main/skills/developer-case-study) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`developer-certification-program`](https://github.com/samber/developer-relations-skills/tree/main/skills/developer-certification-program) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`developer-champions`](https://github.com/samber/developer-relations-skills/tree/main/skills/developer-champions) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`developer-community-health`](https://github.com/samber/developer-relations-skills/tree/main/skills/developer-community-health) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`developer-community-launch`](https://github.com/samber/developer-relations-skills/tree/main/skills/developer-community-launch) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`developer-community-moderation`](https://github.com/samber/developer-relations-skills/tree/main/skills/developer-community-moderation) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`developer-docs-ai-visibility`](https://github.com/samber/developer-relations-skills/tree/main/skills/developer-docs-ai-visibility) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`developer-docs-structure-audit`](https://github.com/samber/developer-relations-skills/tree/main/skills/developer-docs-structure-audit) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`developer-ecosystem-strategy`](https://github.com/samber/developer-relations-skills/tree/main/skills/developer-ecosystem-strategy) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`developer-education-strategy`](https://github.com/samber/developer-relations-skills/tree/main/skills/developer-education-strategy) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`developer-event-followup`](https://github.com/samber/developer-relations-skills/tree/main/skills/developer-event-followup) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`developer-event-sponsorship`](https://github.com/samber/developer-relations-skills/tree/main/skills/developer-event-sponsorship) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`developer-feedback-loop`](https://github.com/samber/developer-relations-skills/tree/main/skills/developer-feedback-loop) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`developer-first-gtm`](https://github.com/samber/developer-relations-skills/tree/main/skills/developer-first-gtm) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`developer-how-to-guide`](https://github.com/samber/developer-relations-skills/tree/main/skills/developer-how-to-guide) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`developer-journey-map`](https://github.com/samber/developer-relations-skills/tree/main/skills/developer-journey-map) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`developer-keyword-research`](https://github.com/samber/developer-relations-skills/tree/main/skills/developer-keyword-research) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`developer-live-demo-design`](https://github.com/samber/developer-relations-skills/tree/main/skills/developer-live-demo-design) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`developer-meetup-program`](https://github.com/samber/developer-relations-skills/tree/main/skills/developer-meetup-program) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`developer-office-hours-program`](https://github.com/samber/developer-relations-skills/tree/main/skills/developer-office-hours-program) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`developer-quickstart-guide`](https://github.com/samber/developer-relations-skills/tree/main/skills/developer-quickstart-guide) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`developer-relations-kickoff`](https://github.com/samber/developer-relations-skills/tree/main/skills/developer-relations-kickoff) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`developer-segmentation`](https://github.com/samber/developer-relations-skills/tree/main/skills/developer-segmentation) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`developer-survey-design`](https://github.com/samber/developer-relations-skills/tree/main/skills/developer-survey-design) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`developer-troubleshooting-docs`](https://github.com/samber/developer-relations-skills/tree/main/skills/developer-troubleshooting-docs) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`developer-tutorial`](https://github.com/samber/developer-relations-skills/tree/main/skills/developer-tutorial) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`developer-workshop-program`](https://github.com/samber/developer-relations-skills/tree/main/skills/developer-workshop-program) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`devrel-analytics`](https://github.com/samber/developer-relations-skills/tree/main/skills/devrel-analytics) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`devrel-budget-allocation`](https://github.com/samber/developer-relations-skills/tree/main/skills/devrel-budget-allocation) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`devrel-career`](https://github.com/samber/developer-relations-skills/tree/main/skills/devrel-career) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`devrel-competitor-analysis`](https://github.com/samber/developer-relations-skills/tree/main/skills/devrel-competitor-analysis) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`devrel-content-calendar`](https://github.com/samber/developer-relations-skills/tree/main/skills/devrel-content-calendar) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`devrel-exec-reporting`](https://github.com/samber/developer-relations-skills/tree/main/skills/devrel-exec-reporting) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`devrel-field-events`](https://github.com/samber/developer-relations-skills/tree/main/skills/devrel-field-events) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`devrel-hiring`](https://github.com/samber/developer-relations-skills/tree/main/skills/devrel-hiring) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`devrel-live-streaming`](https://github.com/samber/developer-relations-skills/tree/main/skills/devrel-live-streaming) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`devrel-metrics`](https://github.com/samber/developer-relations-skills/tree/main/skills/devrel-metrics) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`devrel-newsletter-deliverability`](https://github.com/samber/developer-relations-skills/tree/main/skills/devrel-newsletter-deliverability) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`devrel-newsletter-growth`](https://github.com/samber/developer-relations-skills/tree/main/skills/devrel-newsletter-growth) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`devrel-newsletter-issue`](https://github.com/samber/developer-relations-skills/tree/main/skills/devrel-newsletter-issue) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`devrel-newsletter-program`](https://github.com/samber/developer-relations-skills/tree/main/skills/devrel-newsletter-program) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`devrel-newsletter-sourcing`](https://github.com/samber/developer-relations-skills/tree/main/skills/devrel-newsletter-sourcing) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`devrel-newsletter-sponsorship`](https://github.com/samber/developer-relations-skills/tree/main/skills/devrel-newsletter-sponsorship) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`devrel-radar`](https://github.com/samber/developer-relations-skills/tree/main/skills/devrel-radar) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`devrel-strategy`](https://github.com/samber/developer-relations-skills/tree/main/skills/devrel-strategy) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`devrel-team-structure`](https://github.com/samber/developer-relations-skills/tree/main/skills/devrel-team-structure) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`devrel-webinar-program`](https://github.com/samber/developer-relations-skills/tree/main/skills/devrel-webinar-program) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`devrel-youtube-channel`](https://github.com/samber/developer-relations-skills/tree/main/skills/devrel-youtube-channel) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`devto-playbook`](https://github.com/samber/developer-relations-skills/tree/main/skills/devto-playbook) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`devtools-business-model`](https://github.com/samber/developer-relations-skills/tree/main/skills/devtools-business-model) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`devtools-pricing-strategy`](https://github.com/samber/developer-relations-skills/tree/main/skills/devtools-pricing-strategy) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`discord-community-playbook`](https://github.com/samber/developer-relations-skills/tree/main/skills/discord-community-playbook) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`discourse-forums-playbook`](https://github.com/samber/developer-relations-skills/tree/main/skills/discourse-forums-playbook) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`docs-code-sample-standards`](https://github.com/samber/developer-relations-skills/tree/main/skills/docs-code-sample-standards) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`docs-localization-strategy`](https://github.com/samber/developer-relations-skills/tree/main/skills/docs-localization-strategy) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`docs-seo`](https://github.com/samber/developer-relations-skills/tree/main/skills/docs-seo) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`docs-site-platform-selection`](https://github.com/samber/developer-relations-skills/tree/main/skills/docs-site-platform-selection) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`docs-versioning-strategy`](https://github.com/samber/developer-relations-skills/tree/main/skills/docs-versioning-strategy) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`engineering-blog-post`](https://github.com/samber/developer-relations-skills/tree/main/skills/engineering-blog-post) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`github-profile-optimization`](https://github.com/samber/developer-relations-skills/tree/main/skills/github-profile-optimization) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`hackernews-playbook`](https://github.com/samber/developer-relations-skills/tree/main/skills/hackernews-playbook) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`kaggle-playbook`](https://github.com/samber/developer-relations-skills/tree/main/skills/kaggle-playbook) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`medium-playbook`](https://github.com/samber/developer-relations-skills/tree/main/skills/medium-playbook) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`open-source-company-strategy`](https://github.com/samber/developer-relations-skills/tree/main/skills/open-source-company-strategy) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`open-standards-strategy`](https://github.com/samber/developer-relations-skills/tree/main/skills/open-standards-strategy) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`oss-contributor-onboarding`](https://github.com/samber/developer-relations-skills/tree/main/skills/oss-contributor-onboarding) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`oss-distribution-strategy`](https://github.com/samber/developer-relations-skills/tree/main/skills/oss-distribution-strategy) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`oss-governance`](https://github.com/samber/developer-relations-skills/tree/main/skills/oss-governance) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`oss-issue-triage`](https://github.com/samber/developer-relations-skills/tree/main/skills/oss-issue-triage) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`oss-launch`](https://github.com/samber/developer-relations-skills/tree/main/skills/oss-launch) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`oss-license-strategy`](https://github.com/samber/developer-relations-skills/tree/main/skills/oss-license-strategy) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`oss-maintainer-sustainability`](https://github.com/samber/developer-relations-skills/tree/main/skills/oss-maintainer-sustainability) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`oss-monetization`](https://github.com/samber/developer-relations-skills/tree/main/skills/oss-monetization) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`oss-release-policy`](https://github.com/samber/developer-relations-skills/tree/main/skills/oss-release-policy) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`oss-security-disclosure`](https://github.com/samber/developer-relations-skills/tree/main/skills/oss-security-disclosure) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`oss-sponsors-brand-strategy`](https://github.com/samber/developer-relations-skills/tree/main/skills/oss-sponsors-brand-strategy) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`oss-sponsors-fundraising`](https://github.com/samber/developer-relations-skills/tree/main/skills/oss-sponsors-fundraising) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`producthunt-playbook`](https://github.com/samber/developer-relations-skills/tree/main/skills/producthunt-playbook) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`readme-optimization`](https://github.com/samber/developer-relations-skills/tree/main/skills/readme-optimization) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`student-developer-programs`](https://github.com/samber/developer-relations-skills/tree/main/skills/student-developer-programs) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`tech-employer-branding`](https://github.com/samber/developer-relations-skills/tree/main/skills/tech-employer-branding) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`tech-podcast-interview-prep`](https://github.com/samber/developer-relations-skills/tree/main/skills/tech-podcast-interview-prep) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`tech-press-relations`](https://github.com/samber/developer-relations-skills/tree/main/skills/tech-press-relations) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`tech-talk-outline`](https://github.com/samber/developer-relations-skills/tree/main/skills/tech-talk-outline) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`technical-video-script`](https://github.com/samber/developer-relations-skills/tree/main/skills/technical-video-script) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`version-migration-guide`](https://github.com/samber/developer-relations-skills/tree/main/skills/version-migration-guide) | [samber/developer-relations-skills](https://github.com/samber/developer-relations-skills) | MIT<br>Copyright (c) 2026 Samuel Berthe |
| [`babysit-pr`](https://github.com/t3dotgg/tstack/tree/main/skills/babysit-pr) | [t3dotgg/tstack](https://github.com/t3dotgg/tstack) | MIT<br>Copyright (c) 2026 Theo Browne |
| [`council`](https://github.com/t3dotgg/tstack/tree/main/skills/council) | [t3dotgg/tstack](https://github.com/t3dotgg/tstack) | MIT<br>Copyright (c) 2026 Theo Browne |
| [`file-pr`](https://github.com/t3dotgg/tstack/tree/main/skills/file-pr) | [t3dotgg/tstack](https://github.com/t3dotgg/tstack) | MIT<br>Copyright (c) 2026 Theo Browne |
| [`full-send`](https://github.com/t3dotgg/tstack/tree/main/skills/full-send) | [t3dotgg/tstack](https://github.com/t3dotgg/tstack) | MIT<br>Copyright (c) 2026 Theo Browne |
| [`full-stop`](https://github.com/t3dotgg/tstack/tree/main/skills/full-stop) | [t3dotgg/tstack](https://github.com/t3dotgg/tstack) | MIT<br>Copyright (c) 2026 Theo Browne |
| [`leaving-pr-comments`](https://github.com/t3dotgg/tstack/tree/main/skills/leaving-pr-comments) | [t3dotgg/tstack](https://github.com/t3dotgg/tstack) | MIT<br>Copyright (c) 2026 Theo Browne |
| [`sol-loop`](https://github.com/t3dotgg/tstack/tree/main/skills/sol-loop) | [t3dotgg/tstack](https://github.com/t3dotgg/tstack) | MIT<br>Copyright (c) 2026 Theo Browne |
| [`takeover`](https://github.com/t3dotgg/tstack/tree/main/skills/takeover) | [t3dotgg/tstack](https://github.com/t3dotgg/tstack) | MIT<br>Copyright (c) 2026 Theo Browne |
| [`differential-review`](https://github.com/trailofbits/skills/tree/main/plugins/differential-review/skills/differential-review) | [trailofbits/skills](https://github.com/trailofbits/skills) | CC-BY-SA-4.0 |
| [`fp-check`](https://github.com/trailofbits/skills/tree/main/plugins/fp-check/skills/fp-check) | [trailofbits/skills](https://github.com/trailofbits/skills) | CC-BY-SA-4.0 |
| [`supply-chain-risk-auditor`](https://github.com/trailofbits/skills/tree/main/plugins/supply-chain-risk-auditor/skills/supply-chain-risk-auditor) | [trailofbits/skills](https://github.com/trailofbits/skills) | CC-BY-SA-4.0 |
| [`brd-writer`](https://github.com/yysun/project-manager/tree/main/skills/brd-writer) | [yysun/project-manager](https://github.com/yysun/project-manager) | NONE — no redistribution |
| [`project-manager`](https://github.com/yysun/project-manager/tree/main/skills/project-manager) | [yysun/project-manager](https://github.com/yysun/project-manager) | NONE — no redistribution |
| [`test-manager`](https://github.com/yysun/project-manager/tree/main/skills/test-manager) | [yysun/project-manager](https://github.com/yysun/project-manager) | NONE — no redistribution |
| [`art-direction`](https://github.com/zstvns/design-skills/tree/main/skills/art-direction) | [zstvns/design-skills](https://github.com/zstvns/design-skills) | MIT<br>Copyright (c) 2026 Zach Stevens |
| [`brand`](https://github.com/zstvns/design-skills/tree/main/skills/brand) | [zstvns/design-skills](https://github.com/zstvns/design-skills) | MIT<br>Copyright (c) 2026 Zach Stevens |
| [`brand-strategy`](https://github.com/zstvns/design-skills/tree/main/skills/brand-strategy) | [zstvns/design-skills](https://github.com/zstvns/design-skills) | MIT<br>Copyright (c) 2026 Zach Stevens |
| [`collateral-design`](https://github.com/zstvns/design-skills/tree/main/skills/collateral-design) | [zstvns/design-skills](https://github.com/zstvns/design-skills) | MIT<br>Copyright (c) 2026 Zach Stevens |
| [`creative-direction`](https://github.com/zstvns/design-skills/tree/main/skills/creative-direction) | [zstvns/design-skills](https://github.com/zstvns/design-skills) | MIT<br>Copyright (c) 2026 Zach Stevens |
| [`design-principles`](https://github.com/zstvns/design-skills/tree/main/skills/design-principles) | [zstvns/design-skills](https://github.com/zstvns/design-skills) | MIT<br>Copyright (c) 2026 Zach Stevens |
| [`design-system`](https://github.com/zstvns/design-skills/tree/main/skills/design-system) | [zstvns/design-skills](https://github.com/zstvns/design-skills) | MIT<br>Copyright (c) 2026 Zach Stevens |
| [`logo-design`](https://github.com/zstvns/design-skills/tree/main/skills/logo-design) | [zstvns/design-skills](https://github.com/zstvns/design-skills) | MIT<br>Copyright (c) 2026 Zach Stevens |
| [`motion-design`](https://github.com/zstvns/design-skills/tree/main/skills/motion-design) | [zstvns/design-skills](https://github.com/zstvns/design-skills) | MIT<br>Copyright (c) 2026 Zach Stevens |
| [`product-film`](https://github.com/zstvns/design-skills/tree/main/skills/product-film) | [zstvns/design-skills](https://github.com/zstvns/design-skills) | MIT<br>Copyright (c) 2026 Zach Stevens |
| [`web-design`](https://github.com/zstvns/design-skills/tree/main/skills/web-design) | [zstvns/design-skills](https://github.com/zstvns/design-skills) | MIT<br>Copyright (c) 2026 Zach Stevens |

## gstack suite (58)

Installed by [gstack](https://github.com/garrytan/gstack) itself (MIT). Members: `_gstack-command`, `autoplan`, `benchmark`, `benchmark-models`, `better-documents`, `browse`, `canary`, `careful`, `codex`, `comprehensive-documentation-engineering`, `connect-chrome`, `context-restore`, `context-save`, `cso`, `design-consultation`, `design-html`, `design-review`, `design-shotgun`, `devex-review`, `diagram`, `document-generate`, `document-release`, `freeze`, `gstack`, `gstack-upgrade`, `guard`, `health`, `investigate`, `ios-clean`, `ios-design-review`, `ios-fix`, `ios-qa`, `ios-sync`, `land-and-deploy`, `landing-report`, `learn`, `make-pdf`, `office-hours`, `open-gstack-browser`, `pair-agent`, `plan-ceo-review`, `plan-design-review`, `plan-devex-review`, `plan-eng-review`, `plan-tune`, `qa`, `qa-only`, `retro`, `review`, `scrape`, `setup-browser-cookies`, `setup-deploy`, `setup-gbrain`, `ship`, `skillify`, `spec`, `sync-gbrain`, `unfreeze`

## PMO Platform suite (55)

Installed by [PMO Platform](https://github.com/cody-hutson/pmo-platform)'s own installer into a Claude Code workspace. Business Source License 1.1: source-available, not open source, so it is never redistributed here. The license allows non-production, personal, educational and internal business use and becomes Apache-2.0 on 2030-05-27. Members: `adr-helper`, `artifact-generator`, `artifact-lint`, `build-reviewer`, `change-management`, `comms-writer`, `context-budget-auditor`, `daily-status`, `delivery-engine`, `eval-writer`, `file-router`, `finops-usage-extractor`, `generated-cleanup`, `health-check`, `implementation-planner`, `intake-desk`, `pipeline-triage`, `pmo-architect`, `pmo-business-analyst`, `pmo-data-engineer`, `pmo-devops-sre`, `pmo-knowledge-manager`, `pmo-ocm-lead`, `pmo-portfolio-manager`, `pmo-principal-engineer`, `pmo-process-designer`, `pmo-product-owner`, `pmo-program-coordinator`, `pmo-program-manager`, `pmo-project-manager`, `pmo-qa-auditor`, `pmo-qa-lead`, `pmo-release-manager`, `pmo-release-train-engineer`, `pmo-scrum-master`, `pmo-skill-editor`, `pmo-skill-refiner`, `pmo-skill-router`, `pmo-software-engineer`, `pmo-technical-analyst`, `pmo-technical-program-manager`, `pmo-tier-1-support`, `pmo-tier-2-support`, `pmo-wms-specialist`, `ppm-agent`, `project-initiator`, `prompt-builder`, `release-executor`, `release-hub`, `release-planner`, `roadmap-curator`, `session-retro`, `skill-compliance-auditor`, `tracker-manager`, `weekly-status-rollup`

## Withheld — provenance unresolved (4)

An earlier third-party copy exists and authorship could not be established.

| Skill | Earlier copy | License |
|---|---|---|
| `wp-audit` | [linchpin/skills](https://github.com/linchpin/skills) | GPL-2.0 |
| `wp-github-actions` | [jdevalk/joost-blog](https://github.com/jdevalk/joost-blog) | GPL-3.0 |
| `wp-readme-optimizer` | [jdevalk/joost-blog](https://github.com/jdevalk/joost-blog) | GPL-3.0 |
| `wp-screenshots` | [flintfromthebasement/skills](https://github.com/flintfromthebasement/skills) | NONE |

