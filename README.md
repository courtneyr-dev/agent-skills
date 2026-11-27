# agent-skills

Skills for coding agents — Claude Code, Cursor, Codex, OpenClaw, Gemini CLI, or anything else
that reads a `SKILL.md`. A skill is just a directory with instructions; what varies between
agents is where they look for it, and how well that is actually proven. Claude Code and Codex
are runtime-proven here, as is GitHub Copilot CLI; Cursor, Gemini and OpenClaw are not. Run `./install.sh --grades`, or
see [Platforms](docs/PLATFORMS.md).

**75 skills here**, plus [340 more](docs/CATALOG.md) that live in other people's
repos and install from their own sources.

New to this? **[What is a skill?](docs/WHAT-IS-A-SKILL.md)**

---

## Pick a path

Install by what you actually do. Each path is a small, coherent set — you are meant to take one
or two, not all ten.

### WordPress sites — `-p wordpress`

Building and auditing a running WordPress site. Plugin and theme *development* skills live in the wp-dev-prompts companion repo below, and release testing in wp-release-audit-method — both linked with one-line installs.

| Skill | What it does |
|---|---|
| [`ollie`](skills/ollie/) | Build and style sites with the Ollie block theme and Ollie Pro — tokens, patterns, theme.json. |
| [`site-health-audit`](skills/site-health-audit/) | Config-driven site audit: PageSpeed, accessibility, SEO, headers, SSL, email auth, carbon. |
| [`website-audit`](skills/website-audit/) | UX and information-architecture audit of any public URL, with findings ranked by severity. |
| [`weekly-site-health-audit`](skills/weekly-site-health-audit/) | Runs the site-health audit weekly and diffs it against last week. |

### Reading & Readwise — `-p reading`

Turn a read-later queue and highlights into notes you actually reuse.

| Skill | What it does |
|---|---|
| [`plaud`](skills/plaud/) | Pull transcripts, summaries, and follow-ups from Plaud recordings. |
| [`readwise-deep-read`](skills/readwise-deep-read/) | Save, read, and annotate a queue of URLs, adding inline highlights to the saved document. |
| [`readwise-methods-review`](skills/readwise-methods-review/) | Weekly pass over what you read that changes how you work, written up as a review. |
| [`readwise-synthesis-pass`](skills/readwise-synthesis-pass/) | Connect new notes to existing ones across a vault — the maker half of maker/checker. |
| [`synthesis-backlog`](skills/synthesis-backlog/) | Triage what is unprocessed: what to read, what needs synthesis, what got done. |
| [`transcript-processing`](skills/transcript-processing/) | Turn meeting transcripts into notes and tracked actions. |

### PKM & Obsidian — `-p pkm`

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

### Faith & church notes — `-p faith`

Sermon notes, scripture study, and turning a Sunday bulletin into structured notes. Denomination-neutral: the study skill reads multiple translations, and the bulletin skill reads whatever your church actually prints rather than assuming a format.

| Skill | What it does |
|---|---|
| [`bible-study`](skills/bible-study/) | Scholarly multi-translation passage study written into a vault. |
| [`church-bulletin-to-obsidian`](skills/church-bulletin-to-obsidian/) | Turn a church bulletin image or text into a structured sermon-notes file. |

### Writing — `-p writing`

Drafting and de-slopping prose, docs, commits, and long-form content.

| Skill | What it does |
|---|---|
| [`anti-slop-git-writing`](skills/anti-slop-git-writing/) | Commit messages, PRs, and issues that read like a person wrote them under time pressure. |
| [`email-draft-review`](skills/email-draft-review/) | Triage an inbox and prepare replies — drafts only, never sends. |
| [`field-notes-draft`](skills/field-notes-draft/) | Rank newsletter candidates from recent reading, then draft the issue once you pick a theme. |
| [`learning-path`](skills/learning-path/) | Plan what to learn next, or run a retro on a path you finished. |
| [`technical-writing`](skills/technical-writing/) | Turn in-progress code into an article, tutorial, or docs page in your own voice. |

### Dev workflow — `-p dev`

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
| [`skill-retro`](skills/skill-retro/) | Mine a session for lessons and route them as edits to the repo that owns the skill. |
| [`skill-sync`](skills/skill-sync/) | Keep GitHub-sourced skills updated, and audit which skills are used, dormant, or dead. |

### Company fleets — `-p fleets`

One registry of roles, workloads and eval cases for agency, consulting, product, DevRel, community and corporate work, plus the deterministic gates those roles call. Every company record is a labeled fixture (Fixture Co). The gate skills read shared code and fixtures from company-fleets and factory-rig, which sit beside them in this repository. Roles also attach upstream skills from other people's repos; those are marked external and install from their own sources.

| Skill | What it does |
|---|---|
| [`agency-engagement-gate`](skills/agency-engagement-gate/) | Gate each stage of an agency engagement on hashed, independently accepted evidence and a sourced margin floor. |
| [`agency-i18n-check`](skills/agency-i18n-check/) | Catch placeholder, plural, untranslated and right-to-left defects in gettext catalogs, templates and CSS. |
| [`agency-keyboard-audit`](skills/agency-keyboard-audit/) | Tab through a page in headless Chromium and report keyboard traps, mouse-only controls and invisible focus. |
| [`agency-platform-adapters`](skills/agency-platform-adapters/) | Map a client project's platform and version to the exact platform skills to load, and route legacy versions. |
| [`community-health-measures`](skills/community-health-measures/) | Lint a community measurement plan and compute its numbers from sourced, consent-aware definitions. |
| [`community-moderation-review`](skills/community-moderation-review/) | Check a moderation recommendation against the case record before any human sees it. |
| [`community-operating-kit`](skills/community-operating-kit/) | Write or complete a community program's operating kit and check every section is present and sourced. |
| [`company-fleets`](skills/company-fleets/) | Registry and validator for company fleets: pick the smallest role set for a workload and guard handoffs between fleets. |
| [`consult-compliance-engagement`](skills/consult-compliance-engagement/) | Gate a compliance engagement through applicability, owners, fresh same-tenant evidence, gaps and reporting. |
| [`consult-email-send-gate`](skills/consult-email-send-gate/) | Pre-send gate for one email campaign: suppression, permission, tenant, sender authentication and unsubscribe. Stages, never sends. |
| [`consult-i18n-check`](skills/consult-i18n-check/) | Check a translated string catalog against its source for placeholder, plural, bidi, length and glossary defects. |
| [`consult-search-claims-check`](skills/consult-search-claims-check/) | Reject fabricated citations, edited captures and guaranteed-placement promises in an SEO or AI-search report. |
| [`corporate-claims-check`](skills/corporate-claims-check/) | Stop ranking guarantees, uncited statistics and unverifiable quotes in a marketing or comms draft before staging. |
| [`corporate-email-guard`](skills/corporate-email-guard/) | Send gate that drops suppressed and off-list contacts and refuses any send without a named human's hash-bound approval. |
| [`devrel-program-kit`](skills/devrel-program-kit/) | Keep a DevRel program's routing and claims honest: routed skills installed, program state in one context file. |
| [`devrel-quickstart-replay`](skills/devrel-quickstart-replay/) | Prove a quickstart or tutorial works as written by replaying its shell blocks in a clean temp environment. |
| [`product-payment-events`](skills/product-payment-events/) | Prove duplicate or retried payment webhooks can't capture, fulfill, decrement stock or refund twice. |
| [`product-release-gate`](skills/product-release-gate/) | Gate an extension or SDK release on compatibility, SemVer, changelog, SBOM and review evidence. |

### Education — `-p education`

School and workplace teaching: BCIT and computer science units, assessment and answer-key checks, standards alignment against a verified registry, needs analysis, research review, trainer development, and a student-data guard that refuses reads the school's policy doesn't allow.

| Skill | What it does |
|---|---|
| [`bcit-learning-package`](skills/bcit-learning-package/) | Build and check a complete BCIT course-unit package, from objectives to rubric and accessibility notes. |
| [`cs-classroom-instruction`](skills/cs-classroom-instruction/) | Build a runnable school computer science lesson or lab, or give feedback on code a learner actually wrote. |
| [`edu-answer-key-check`](skills/edu-answer-key-check/) | Execute an answer key's formulas, SQL, Python and calculations and compare the results with the stated answers. |
| [`edu-assessment-check`](skills/edu-assessment-check/) | Check that an assessment's tasks, rubric and scoring line up with the objectives they claim to measure. |
| [`edu-learning-progression`](skills/edu-learning-progression/) | Check a prerequisite map or course sequence for cycles, gaps and ordering errors. |
| [`edu-needs-analysis`](skills/edu-needs-analysis/) | Decide whether training fixes a performance problem before anyone builds a course. |
| [`edu-research-review`](skills/edu-research-review/) | Critique education research and program evaluations with traced citations and bounded claims. |
| [`edu-standards-alignment`](skills/edu-standards-alignment/) | Check standards alignments and professional references against a verified registry, so nothing claims an unsupported match. |
| [`edu-student-data-guard`](skills/edu-student-data-guard/) | Decide whether a workflow may read a student record under tenant rules and the school's verified policy. |
| [`edu-trainer-development`](skills/edu-trainer-development/) | Develop trainers and teachers: facilitation guides, modeled examples, observation feedback and rubric calibration. |

### Hosting operations — `-p hosting`

Gates for running a hosting service on synthetic lab data: account lifecycle, DNS and TLS, incident response, restore drills, data migration, tenant isolation, metering and the service catalogue. The benchmark cites public provider documentation and keeps documented claims, targets, configuration, measurements and contracts in separate fields.

| Skill | What it does |
|---|---|
| [`hosting-abuse-response`](skills/hosting-abuse-response/) | Handle an abuse report with hashed evidence, a chain of custody, and only the actions a policy clause authorizes. |
| [`hosting-account-lifecycle`](skills/hosting-account-lifecycle/) | Run a hosted account from qualify to decommission with idempotent, recoverable panel side effects. |
| [`hosting-benchmark-matrix`](skills/hosting-benchmark-matrix/) | Keep a hosting benchmark honest: documented claim, target, configuration, measurement and contract stay separate. |
| [`hosting-data-migration`](skills/hosting-data-migration/) | Preflight, rehearse and prove a hosted site's data migration, with automatic rollback and a portable export. |
| [`hosting-dns-cert-lifecycle`](skills/hosting-dns-cert-lifecycle/) | Check DNS zones and TLS certificates through create, change, migrate, renew and decommission. |
| [`hosting-incident-response`](skills/hosting-incident-response/) | Run a hosting incident from alert to learning handoff, with a tamper-evident record and external messages held as drafts. |
| [`hosting-metering-reconcile`](skills/hosting-metering-reconcile/) | Dedupe meter events, enforce published quotas and reconcile invoices against metered usage. |
| [`hosting-restore-exercise`](skills/hosting-restore-exercise/) | Break a disposable site on purpose, restore it, and measure detection time, RTO and RPO. |
| [`hosting-service-catalogue`](skills/hosting-service-catalogue/) | Check a hosting service catalogue and its responsibility matrix against one operating profile. |
| [`hosting-tenant-isolation`](skills/hosting-tenant-isolation/) | Test tenant boundaries: record access, a tamper-evident audit trail, secrets in build output, and sandboxed untrusted builds. |

### Delivery factory — `-p delivery`

One dispatcher per task, leases, and a merge gate that re-runs verification before anything lands.

| Skill | What it does |
|---|---|
| [`factory-execute`](skills/factory-execute/) | Implement one leased task contract in its worktree, run the verify command, commit, and report. |
| [`factory-rig`](skills/factory-rig/) | Route each software task to one dispatcher, hold its lease, and merge only after a fresh verify and an independent review. |

**[Full catalog →](docs/CATALOG.md)** — every skill with an example of it running, plus the
externals and their licenses. **[Searchable version →](https://courtneyr-dev.github.io/agent-skills/)**

## Install

```bash
git clone https://github.com/courtneyr-dev/agent-skills.git
cd agent-skills
./install.sh --guided            # one question per path, then a dry run of your picks
./install.sh --apply -p fleets    # one path; repeat -p for more
./install.sh --dry-run            # default: classify every destination, change nothing
./install.sh --apply              # all 75 skills, creating only the links that are missing
./install.sh --apply -a codex     # one agent
./install.sh --list -p hosting    # what a path installs; drop -p for all 75
```

Each path's skills are listed under `paths` in [manifest.json](manifest.json). The fleets,
education and hosting paths also link `company-fleets` and `factory-rig`, because their scripts
import those two from the folder beside them.

This repository is the canonical source for the 75 skills under `skills/`. Installing links your
agent's skill directory at them, so `git pull` updates every agent at once.

**Nothing is overwritten.** An existing real directory, a customized copy, or a link that already
points somewhere else is reported as a conflict and left exactly as it is. Filling in what is
missing is *install*; converting something that already exists is *migration*, and this script
does not do migration.

```
LINK      codex/gatherer     -> .../agent-skills/skills/gatherer
SKIP      claude/gatherer    already correct
CONFLICT  cursor/lmk         local copy differs — not overwriting
```

### `~/.agents/skills`

`--via-mount` routes links through `$AGENT_SKILLS_DIR` (default `~/.agents/skills`) instead of
linking agents directly at this repo. That directory is a **neutral cross-agent mount**: a place
several owners' skills can be aggregated under one path. It is *not* automatically the canonical
source for anything, and this repo does not assume it owns what lives there. Use it if you already
aggregate skills that way; otherwise the direct links are simpler.

Because the mount becomes the link *target*, `--via-mount` also checks the mount entry itself. If
it differs from this repo's copy, links somewhere else, dangles, or is not a skill, the consumer
link is reported `BLOCK` and not created. The installer will not repair the mount to make an
install succeed — that is a migration, and it stays your decision.

### Why not install everything

Agents load every installed skill's name and description into context to decide what to invoke,
and that listing is capped. Past a few dozen skills, agents start truncating it — some drop all
descriptions and leave the model with bare names, some silently drop skills off the end. A
hundred installed skills is not a hundred available skills; it is a degraded version of the
twenty you actually wanted. Take a path or two.

<details>
<summary>Why there's no curl one-liner</summary>

`install.sh` links your agent at the `skills/` folder beside it, so it only works from a clone; a
downloaded copy of the script alone has nothing to link. That suits this repo's argument anyway:
know where code came from before you run it, and don't pipe a script straight into a shell. Read
it first:

```bash
git clone https://github.com/courtneyr-dev/agent-skills.git && cd agent-skills \
  && less install.sh && ./install.sh --guided
```
</details>

## Where skills came from

Every external entry points at the **original source**, never a fork or a collection it passed
through. Seventeen skills that looked like this repo's own turned out to belong to other people
and were removed rather than republished.

The largest single body of work here is
**[pstack](https://github.com/cursor/plugins/tree/main/pstack) by
[poteto](https://github.com/poteto) (Lauren Tan)** — 44 skills, MIT. Worth stating plainly:
`cursor/plugins` has no root LICENSE and licenses each plugin directory instead, so checking the
repo root reports "unlicensed" and is wrong.

`explainer` and `deepdive` are **[Dave Saunders](https://github.com/nemock)'** —
[video-explainer-system](https://github.com/nemock/video-explainer-system), MIT. They were
vendored here in error; the bodies were his verbatim and only the description line differed.

`codex-first` here is **adapted** from [Peter Steinberger](https://github.com/steipete)'s
([steipete/agent-scripts](https://github.com/steipete/agent-scripts), MIT) — a quarter the length
with no verbatim lines, which is what MIT-licensed adaptation is for. The skill body has said so
since it was written; the credit now sits in the manifest too.

Skills with **no upstream license at all** are linked, never copied — no license means all
rights reserved, however freely something is shared. Four more are withheld entirely because an
earlier third-party copy exists and authorship could not be established.

[Machine-readable manifest →](manifest.json)

If you maintain something listed here and the attribution is wrong, open an issue — it will be
fixed rather than argued about.

## More

- [Catalog](docs/CATALOG.md) · [searchable version](https://courtneyr-dev.github.io/agent-skills/)
- [What is a skill?](docs/WHAT-IS-A-SKILL.md) — the format, and why more skills makes each one worse
- [Platforms](docs/PLATFORMS.md) — where each agent reads skills
- [Plugins](docs/PLUGINS.md) — 31 marketplaces and the plugins installed from them
- [Security](SECURITY.md) — a skill is instructions your agent will follow; what to check first
- [Contributing](CONTRIBUTING.md) — adding a skill, and what gets rejected
- [Changelog](CHANGELOG.md) · [Code of conduct](CODE_OF_CONDUCT.md) · [Citation](CITATION.cff)

## License

MIT for everything in `skills/` and `scripts/` written for this repository. External skills stay
under their own licenses, recorded per entry in [manifest.json](manifest.json).

Third-party material that a skill quotes or points to stays under its owner's terms, not MIT. That
covers the short, attributed provider quotes in the hosting benchmark
(`skills/company-fleets/fleets/hosting/benchmark/`, scoped in
`skills/hosting-benchmark-matrix/references/sources.md`), the page titles, headings and citations in
the education fetch logs (`skills/company-fleets/fleets/bcit-education/evidence/sources/`, where
longer passages are paraphrased), and the names, URLs and terms in the standards and organization
registries. No standards text is included: those registries carry identifiers and links only.

