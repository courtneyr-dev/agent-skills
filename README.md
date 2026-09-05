# agent-skills

Portable skills for coding agents — Claude Code, Cursor, Codex, OpenClaw, Gemini CLI, or anything
else that reads a `SKILL.md`. 36 skills you can install directly, plus a manifest of 77 more that
live in other people's repos and install from their own upstreams.

Nothing here is tied to one vendor. A skill is a directory with a `SKILL.md`; the only thing that
varies between agents is where they look for it, and `install.sh` handles that.

## Install

```bash
git clone https://github.com/YOUR-ORG/agent-skills.git
cd agent-skills
./install.sh
```

With no arguments it installs every skill into `~/.agents/skills` and symlinks them into each agent
directory it finds. Restart your agent afterwards.

```bash
./install.sh --list              # show what would happen, change nothing
./install.sh -a cursor -a codex  # only these agents
./install.sh --copy              # real directories instead of symlinks
./install.sh --external          # install commands for the third-party skills
```

One canonical copy, symlinked everywhere, so `git pull` updates every agent at once. See
[docs/PLATFORMS.md](docs/PLATFORMS.md) for directory locations and the skill-listing budget, which
matters more than people expect once you pass a few dozen skills.

## What is here

| | Count | |
|---|---:|---|
| **[Included in this repo](skills/)** | 36 | MIT, install directly |
| **[External, manifest only](manifest.json)** | 77 | Install from their own upstreams |
| **[gstack suite](https://github.com/garrytan/gstack)** | 58 | Install via gstack |
| **[Plugin marketplaces](docs/PLUGINS.md)** | 31 | Install with `/plugin` |

### Install a slice

You probably do not want all of them. Pick by what you actually do:

```bash
./install.sh --guided              # one question per path
./install.sh -p pkm -p writing      # or name them
./install.sh --paths               # see the options
```

#### WordPress sites — `-p wordpress` (4 skills)

Building and auditing a running WordPress site. Plugin and theme *development* skills live in the wp-dev-prompts companion repo below, and release testing in wp-release-audit-method — both linked with one-line installs.

| Skill | What it does |
|---|---|
| [`ollie`](skills/ollie/) | Build and style sites with the Ollie block theme and Ollie Pro — tokens, patterns, theme.json. |
| [`site-health-audit`](skills/site-health-audit/) | Config-driven site audit: PageSpeed, accessibility, SEO, headers, SSL, email auth, carbon. |
| [`website-audit`](skills/website-audit/) | UX and information-architecture audit of any public URL, with findings ranked by severity. |
| [`weekly-site-health-audit`](skills/weekly-site-health-audit/) | Runs the site-health audit weekly and diffs it against last week. |

#### Reading & Readwise — `-p reading` (6 skills)

Turn a read-later queue and highlights into notes you actually reuse.

| Skill | What it does |
|---|---|
| [`plaud`](skills/plaud/) | Pull transcripts, summaries, and follow-ups from Plaud recordings. |
| [`readwise-deep-read`](skills/readwise-deep-read/) | Save, read, and annotate a queue of URLs, adding inline highlights to the saved document. |
| [`readwise-methods-review`](skills/readwise-methods-review/) | Weekly pass over what you read that changes how you work, written up as a review. |
| [`readwise-synthesis-pass`](skills/readwise-synthesis-pass/) | Connect new notes to existing ones across a vault — the maker half of maker/checker. |
| [`synthesis-backlog`](skills/synthesis-backlog/) | Triage what is unprocessed: what to read, what needs synthesis, what got done. |
| [`transcript-processing`](skills/transcript-processing/) | Turn meeting transcripts into notes and tracked actions. |

#### PKM & Obsidian — `-p pkm` (7 skills)

Vault hygiene, wikis as memory, decision records, daily gathering, task sync.

| Skill | What it does |
|---|---|
| [`decision-sync`](skills/decision-sync/) | File a finished decision record into a notes vault with frontmatter and backlinks. |
| [`gatherer`](skills/gatherer/) | Pull open issues, PRs, watched tickets, and tasks into today’s daily note. |
| [`obsid-link-builder`](skills/obsid-link-builder/) | Build and normalize shareable Obsidian links, with correct URL encoding. |
| [`things-obsidian-sync`](skills/things-obsidian-sync/) | Two-way sync between Things tasks and an Obsidian vault. |
| [`vault-hygiene-checker`](skills/vault-hygiene-checker/) | Verify a synthesis pass actually landed — the checker half of maker/checker. |
| [`wiki-cycle`](skills/wiki-cycle/) | One maintenance pass over a registered wiki: scan, ingest, lint, report, record state. |
| [`wiki-memory`](skills/wiki-memory/) | Staging-and-promotion flow that turns passing signals into durable wiki pages. |

#### Faith & church notes — `-p faith` (2 skills)

Sermon notes, scripture study, and turning a Sunday bulletin into structured notes. Denomination-neutral: the study skill reads multiple translations, and the bulletin skill reads whatever your church actually prints rather than assuming a format.

| Skill | What it does |
|---|---|
| [`bible-study`](skills/bible-study/) | Scholarly multi-translation passage study written into a vault. |
| [`church-bulletin-to-obsidian`](skills/church-bulletin-to-obsidian/) | Turn a church bulletin image or text into a structured sermon-notes file. |

#### Writing — `-p writing` (7 skills)

Drafting and de-slopping prose, docs, commits, and long-form content.

| Skill | What it does |
|---|---|
| [`anti-slop-git-writing`](skills/anti-slop-git-writing/) | Commit messages, PRs, and issues that read like a person wrote them under time pressure. |
| [`deepdive`](skills/deepdive/) | Generate a long-form explainer or tutorial script on a topic. |
| [`email-draft-review`](skills/email-draft-review/) | Triage an inbox and prepare replies — drafts only, never sends. |
| [`explainer`](skills/explainer/) | Turn a topic or source document into a short explainer video or deck. |
| [`field-notes-draft`](skills/field-notes-draft/) | Rank newsletter candidates from recent reading, then draft the issue once you pick a theme. |
| [`learning-path`](skills/learning-path/) | Plan what to learn next, or run a retro on a path you finished. |
| [`technical-writing`](skills/technical-writing/) | Turn in-progress code into an article, tutorial, or docs page in your own voice. |

#### Dev workflow — `-p dev` (10 skills)

Routing work between models, repo hygiene, scheduling, and notifications.

| Skill | What it does |
|---|---|
| [`codex-first`](skills/codex-first/) | Delegate fully-specified mechanical work to Codex instead of doing it inline. |
| [`credit-routing`](skills/credit-routing/) | Decide what to delegate, to which model, at what effort — before starting the work. |
| [`devrel-engine`](skills/devrel-engine/) | Turn transcripts and community signals into a prioritized DevRel program. |
| [`github-profile`](skills/github-profile/) | Improve a GitHub profile README, bio, pinned repos, and stats. |
| [`github-repo`](skills/github-repo/) | Prepare a repo for open source: README, CONTRIBUTING, SECURITY, templates, release hygiene. |
| [`job-search`](skills/job-search/) | Repeatable job scan across boards, ATS pages, email, LinkedIn, and chat, diffed each run. |
| [`lmk`](skills/lmk/) | Push a phone notification when long-running work finishes. |
| [`loop-template`](skills/loop-template/) | Scaffold a scheduled job so it inherits the maker/checker pattern from the start. |
| [`prop-for-that`](skills/prop-for-that/) | React in CSS to runtime state CSS cannot see — checks for a native property first. |
| [`skill-sync`](skills/skill-sync/) | Keep GitHub-sourced skills updated, and audit which skills are used, dormant, or dead. |

## Companion repos

Some sets are better kept where their tooling lives. These are separate repos, linked rather
than copied, each with a one-line install.

### [wp-release-audit-method](https://github.com/courtneyr-dev/wp-release-audit-method) — GPL-2.0

The full WordPress release-testing method: guides, fixtures, scripts, CI, and the release-day agent skills. The four release skills referenced here live there.

```bash
npx skills@latest add courtneyr-dev/wp-release-audit-method --path skills/wordpress-audit-handoff -s wordpress-audit-handoff
npx skills@latest add courtneyr-dev/wp-release-audit-method --path skills/wp-release-followup -s wp-release-followup
npx skills@latest add courtneyr-dev/wp-release-audit-method --path skills/wp-release-party -s wp-release-party
npx skills@latest add courtneyr-dev/wp-release-audit-method --path skills/wp-release-prep -s wp-release-prep
```

| Skill | What it does |
|---|---|
| [`wordpress-audit-handoff`](https://github.com/courtneyr-dev/wp-release-audit-method/tree/main/skills/wordpress-audit-handoff) | Turn testing results into one self-contained document a colleague can act on. |
| [`wp-release-followup`](https://github.com/courtneyr-dev/wp-release-audit-method/tree/main/skills/wp-release-followup) | After a release: check filed tickets, find what got fixed, log what is still open. |
| [`wp-release-party`](https://github.com/courtneyr-dev/wp-release-audit-method/tree/main/skills/wp-release-party) | Run the release-day checklist against a Beta or RC and produce a shareable report. |
| [`wp-release-prep`](https://github.com/courtneyr-dev/wp-release-audit-method/tree/main/skills/wp-release-prep) | Phase 0 — build fixtures and get test environments ready before a release lands. |

The skills alone are the small part. The repo also carries the fixtures, the release-day
playbook, direct-jump matrices, and CI — which is what makes a Beta or RC test mean
something. Clone it if you are actually testing a release:

```bash
git clone https://github.com/courtneyr-dev/wp-release-audit-method.git
```

### [wp-dev-prompts](https://github.com/courtneyr-dev/wp-dev-prompts) — CC0-1.0

WordPress development prompts and skills — the canonical home for the WordPress development set, plus security, UI/UX audit, engineering and product prompts.

```bash
npx skills@latest add courtneyr-dev/wp-dev-prompts --path skills/prompt-engineering -s prompt-engineering
npx skills@latest add courtneyr-dev/wp-dev-prompts --path skills/wordpress-accessibility -s wordpress-accessibility
npx skills@latest add courtneyr-dev/wp-dev-prompts --path skills/wordpress-dev -s wordpress-dev
npx skills@latest add courtneyr-dev/wp-dev-prompts --path skills/wordpress-performance -s wordpress-performance
npx skills@latest add courtneyr-dev/wp-dev-prompts --path skills/wordpress-playground -s wordpress-playground
npx skills@latest add courtneyr-dev/wp-dev-prompts --path skills/wordpress-testing -s wordpress-testing
```

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

### External — install from source

These belong to their authors and are never copied here. Each row links to the **original**
source. `no redistribution` means the upstream ships no license at all, so it is all rights
reserved however freely it is shared — install it from source.

| Skill | Original source | License |
|---|---|---|
| [`wp-pinch`](https://github.com/RegionallyFamous/wp-pinch) | [RegionallyFamous/wp-pinch](https://github.com/RegionallyFamous/wp-pinch) | GPL-2.0-or-later<br>Nick Hamze |
| [`counselors`](https://github.com/aarondfrancis/counselors) | [aarondfrancis/counselors](https://github.com/aarondfrancis/counselors) | MIT |
| [`aim`](https://github.com/borkweb/discernment-skills/tree/main/plugins/discernment/skills/aim) | [borkweb/discernment-skills](https://github.com/borkweb/discernment-skills) | MIT |
| [`cross-check`](https://github.com/borkweb/discernment-skills/tree/main/plugins/discernment/skills/cross-check) | [borkweb/discernment-skills](https://github.com/borkweb/discernment-skills) | MIT |
| [`own`](https://github.com/borkweb/discernment-skills/tree/main/plugins/discernment/skills/own) | [borkweb/discernment-skills](https://github.com/borkweb/discernment-skills) | MIT |
| [`skill-patterns`](https://github.com/borkweb/skill-patterns/tree/main/skills/skill-patterns) | [borkweb/skill-patterns](https://github.com/borkweb/skill-patterns) | MIT |
| [`agents-md-lint`](https://github.com/borkweb/skills/tree/main/skills/core/agents-md-lint) | [borkweb/skills](https://github.com/borkweb/skills) | MIT |
| [`review-security`](https://github.com/borkweb/skills/tree/main/skills/core/review-security) | [borkweb/skills](https://github.com/borkweb/skills) | MIT |
| [`writing-sql`](https://github.com/borkweb/skills/tree/main/skills/core/writing-sql) | [borkweb/skills](https://github.com/borkweb/skills) | MIT |
| [`prompt-engineering`](https://github.com/courtneyr-dev/wp-dev-prompts/tree/main/skills/prompt-engineering) | [courtneyr-dev/wp-dev-prompts](https://github.com/courtneyr-dev/wp-dev-prompts) | CC0-1.0 |
| [`wordpress-accessibility`](https://github.com/courtneyr-dev/wp-dev-prompts/tree/main/skills/wordpress-accessibility) | [courtneyr-dev/wp-dev-prompts](https://github.com/courtneyr-dev/wp-dev-prompts) | CC0-1.0 |
| [`wordpress-dev`](https://github.com/courtneyr-dev/wp-dev-prompts/tree/main/skills/wordpress-dev) | [courtneyr-dev/wp-dev-prompts](https://github.com/courtneyr-dev/wp-dev-prompts) | CC0-1.0 |
| [`wordpress-performance`](https://github.com/courtneyr-dev/wp-dev-prompts/tree/main/skills/wordpress-performance) | [courtneyr-dev/wp-dev-prompts](https://github.com/courtneyr-dev/wp-dev-prompts) | CC0-1.0 |
| [`wordpress-playground`](https://github.com/courtneyr-dev/wp-dev-prompts/tree/main/skills/wordpress-playground) | [courtneyr-dev/wp-dev-prompts](https://github.com/courtneyr-dev/wp-dev-prompts) | CC0-1.0 |
| [`wordpress-testing`](https://github.com/courtneyr-dev/wp-dev-prompts/tree/main/skills/wordpress-testing) | [courtneyr-dev/wp-dev-prompts](https://github.com/courtneyr-dev/wp-dev-prompts) | CC0-1.0 |
| [`wordpress-audit-handoff`](https://github.com/courtneyr-dev/wp-release-audit-method/tree/main/skills/wordpress-audit-handoff) | [courtneyr-dev/wp-release-audit-method](https://github.com/courtneyr-dev/wp-release-audit-method) | GPL-2.0 |
| [`wp-release-followup`](https://github.com/courtneyr-dev/wp-release-audit-method/tree/main/skills/wp-release-followup) | [courtneyr-dev/wp-release-audit-method](https://github.com/courtneyr-dev/wp-release-audit-method) | GPL-2.0 |
| [`wp-release-party`](https://github.com/courtneyr-dev/wp-release-audit-method/tree/main/skills/wp-release-party) | [courtneyr-dev/wp-release-audit-method](https://github.com/courtneyr-dev/wp-release-audit-method) | GPL-2.0 |
| [`wp-release-prep`](https://github.com/courtneyr-dev/wp-release-audit-method/tree/main/skills/wp-release-prep) | [courtneyr-dev/wp-release-audit-method](https://github.com/courtneyr-dev/wp-release-audit-method) | GPL-2.0 |
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
| [`librarium`](https://github.com/jkudish/librarium) | [jkudish/librarium](https://github.com/jkudish/librarium) | MIT |
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

### Withheld — provenance unresolved (4)

An earlier third-party copy exists and authorship could not be established, so these are not republished here. `manifest.json` records the dates and evidence.

| Skill | Earlier copy | License |
|---|---|---|
| `wp-audit` | [linchpin/skills](https://github.com/linchpin/skills) | GPL-2.0 |
| `wp-github-actions` | [jdevalk/joost-blog](https://github.com/jdevalk/joost-blog) | GPL-3.0 |
| `wp-readme-optimizer` | [jdevalk/joost-blog](https://github.com/jdevalk/joost-blog) | GPL-3.0 |
| `wp-screenshots` | [flintfromthebasement/skills](https://github.com/flintfromthebasement/skills) | NONE |
## Attribution

Every external entry points at the **original source**, not whatever fork or collection it reached
this machine through. Where something arrived via a fork, the manifest names the upstream that
published it and records the fork separately.

The largest single body of work here is **[pstack](https://github.com/cursor/plugins/tree/main/pstack)
by [poteto](https://github.com/poteto) (Lauren Tan)** — 44 skills, MIT. Worth stating plainly because
`cursor/plugins` has **no root LICENSE** and licenses each plugin directory instead: checking the
repo root reports "unlicensed" and is wrong. `pstack/LICENSE` is MIT.

Other upstreams whose own credits were read before treating them as the origin:
[garrytan/gstack](https://github.com/garrytan/gstack) (MIT),
[borkweb](https://github.com/borkweb/skills) (MIT — his README credits @mattpocock, @blader,
@Devattom and gstack for the parts that are not his),
[readwiseio/readwise-skills](https://github.com/readwiseio/readwise-skills) (no license),
[RegionallyFamous/wp-pinch](https://github.com/RegionallyFamous/wp-pinch) (GPL-2.0-or-later,
Nick Hamze).

If you maintain something listed here and the attribution is wrong, open an issue — it will be
fixed rather than argued about.

## Why external skills are not vendored here

**A public repo with no LICENSE file is "all rights reserved."** You can read it; you cannot
redistribute it. Several widely-used skill repos ship no license, so copying them into a collection
like this one would not be legal — regardless of how freely they are shared in practice.

So the manifest records, for every external skill, its upstream repo, subpath, license, and whether
redistribution is permitted. `./install.sh --external` turns that into install commands that fetch
from the real source. You get the skills; the authors keep their terms; you get their updates
instead of a frozen copy of someone else's machine.

If you maintain one of the unlicensed repos listed here and would like it vendored, add a license
upstream and open an issue.

## Configuration and privacy

Skills that need personal data read a `config.yml` next to their `SKILL.md`, and every
`config.yml` is gitignored. Skills ship with a `config.example.yml` instead. No profile, employer,
hostname, or absolute home path is committed here — if you find one, it is a bug worth an issue.

If you fork this to publish your own set, scrub before you push. `scripts/sanitize.py` is the
filter used to build this repo: it rewrites home paths and personal names, drops employer-specific
lines, skips backup files and virtualenvs, and re-scans its own output, reporting anything left over
rather than shipping it quietly.

## Vault-backed skills

Several skills read and write a notes vault (Obsidian or plain Markdown). They resolve it from the
`VAULT_DIR` environment variable, defaulting to `~/Documents/Notes`:

```bash
export VAULT_DIR="$HOME/path/to/your/notes"
```

Set it before running any of the Readwise, synthesis, gatherer, or vault-hygiene skills. Nothing is
written outside that directory.

## Adding a skill

1. `mkdir skills/my-skill` and write a `SKILL.md` with `name` and `description` frontmatter.
2. Make the description say *when to use it*, in the words you would type. That text is all the model
   sees when deciding whether to invoke it.
3. Put anything long in `references/` and point to it from the body — keep `SKILL.md` scannable.
4. Run `./install.sh --list` to confirm it is picked up.

## License

MIT for everything in `skills/` and `scripts/`. External skills stay under their own licenses,
recorded per entry in `manifest.json`.
