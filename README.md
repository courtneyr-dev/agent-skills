# agent-skills

Skills for coding agents — Claude Code, Cursor, Codex, OpenClaw, Gemini CLI, or anything else
that reads a `SKILL.md`. A skill is just a directory with instructions; the only thing that
varies between agents is where they look for it.

**34 skills here**, plus [79 more](docs/CATALOG.md) that live in other people's
repos and install from their own sources.

New to this? **[What is a skill?](docs/WHAT-IS-A-SKILL.md)**

---

## Pick a path

Install by what you actually do. Each path is a small, coherent set — you are meant to take one
or two, not all six.

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
| [`skill-sync`](skills/skill-sync/) | Keep GitHub-sourced skills updated, and audit which skills are used, dormant, or dead. |

**[Full catalog →](docs/CATALOG.md)** — every skill with an example of it running, plus the
externals and their licenses. **[Searchable version →](https://courtneyr-dev.github.io/agent-skills/)**

## Install

```bash
git clone https://github.com/courtneyr-dev/agent-skills.git
cd agent-skills
./install.sh --guided
```

`--guided` asks one question per path and installs only what you say yes to. Or name them:

```bash
./install.sh -p pkm -p writing    # just these
./install.sh --paths              # see the options
./install.sh                      # everything — see the warning below
```

One canonical copy in `~/.agents/skills`, symlinked into each agent's directory, so `git pull`
updates every agent at once. Codex, Cursor, Claude Code and OpenClaw all follow the symlinks;
`--copy` writes real directories for anything that does not.

### Why not install everything

Agents load every installed skill's name and description into context to decide what to invoke,
and that listing is capped. Past a few dozen skills, agents start truncating it — some drop all
descriptions and leave the model with bare names, some silently drop skills off the end. A
hundred installed skills is not a hundred available skills; it is a degraded version of the
twenty you actually wanted. Take a path or two.

<details>
<summary>One-line install (reads a script off the internet — your call)</summary>

```bash
curl -fsSL https://raw.githubusercontent.com/courtneyr-dev/agent-skills/main/install.sh -o /tmp/as.sh \
  && less /tmp/as.sh && bash /tmp/as.sh --guided
```

Deliberately not a `curl | bash` one-liner. This repo's whole argument is that you should know
where code came from before you run it; piping a script straight into a shell is the opposite of
that. Read it first.
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

MIT for everything in `skills/` and `scripts/`. External skills stay under their own licenses,
recorded per entry in [manifest.json](manifest.json).

