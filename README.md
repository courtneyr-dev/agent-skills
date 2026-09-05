# agent-skills

Skills for coding agents — Claude Code, Cursor, Codex, OpenClaw, Gemini CLI, or anything else
that reads a `SKILL.md`. A skill is just a directory with instructions; the only thing that
varies between agents is where they look for it.

**36 skills here**, plus [77 more](docs/CATALOG.md) that live in other
people's repos and install from their own sources.

---

## Start here

Do not install all 36. Agents load every skill's name and description into context to
decide what to invoke, and that listing is capped — past a few dozen skills, agents start
truncating and some drop descriptions entirely, which makes *every* skill trigger worse. Install
the handful you will actually use.

These are the ones the author actually runs, counted from real transcripts over
**2026-07-24 → 2026-09-05**:

| Skill | Runs | What it does |
|---|---:|---|
| [`readwise-deep-read`](skills/readwise-deep-read/) | 107 | Save, read, and annotate a queue of URLs, adding inline highlights to the saved document. |
| [`anti-slop-git-writing`](skills/anti-slop-git-writing/) | 68 | Commit messages, PRs, and issues that read like a person wrote them under time pressure. |
| [`readwise-synthesis-pass`](skills/readwise-synthesis-pass/) | 17 | Connect new notes to existing ones across a vault — the maker half of maker/checker. |
| [`vault-hygiene-checker`](skills/vault-hygiene-checker/) | 14 | Verify a synthesis pass actually landed — the checker half of maker/checker. |
| [`credit-routing`](skills/credit-routing/) | 11 | Decide what to delegate, to which model, at what effort — before starting the work. |
| [`synthesis-backlog`](skills/synthesis-backlog/) | 5 | Triage what is unprocessed: what to read, what needs synthesis, what got done. |

The other 28 did not fire once in that window. Some are new, some are situational, and
some you will never need — which is the point of installing by path rather than wholesale.

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
./install.sh                      # everything (see the warning above)
```

One canonical copy in `~/.agents/skills`, symlinked into each agent's directory, so `git pull`
updates every agent at once. Codex, Cursor, Claude Code and OpenClaw all follow the symlinks;
`--copy` writes real directories for anything that does not.

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

## Paths

| Path | Skills | |
|---|---:|---|
| [`-p wordpress`](docs/CATALOG.md#wordpress-sites) | 4 | Site building with Ollie, plus health, performance and UX audits of a live site. |
| [`-p reading`](docs/CATALOG.md#reading-readwise) | 6 | Turn a read-later queue and highlights into notes you actually reuse. |
| [`-p pkm`](docs/CATALOG.md#pkm-obsidian) | 7 | Vault hygiene, wikis as memory, decision records, daily gathering, task sync. |
| [`-p faith`](docs/CATALOG.md#faith-church-notes) | 2 | Sermon notes, scripture study, and Sunday bulletins turned into structured notes. |
| [`-p writing`](docs/CATALOG.md#writing) | 7 | Drafting and de-slopping prose, docs, commits, and long-form content. |
| [`-p dev`](docs/CATALOG.md#dev-workflow) | 10 | Routing work between models, repo hygiene, scheduling, and notifications. |

**[Full catalog →](docs/CATALOG.md)** — every skill, what it does, an example of it running,
and how often it actually gets used.

## Where skills came from

Every external entry points at the **original source**, never a fork or a collection it passed
through. Fifteen skills that looked like the author's own turned out to belong to other people
and were removed rather than republished.

The largest single body of work here is
**[pstack](https://github.com/cursor/plugins/tree/main/pstack) by
[poteto](https://github.com/poteto) (Lauren Tan)** — 44 skills, MIT. Worth stating plainly:
`cursor/plugins` has no root LICENSE and licenses each plugin directory instead, so checking the
repo root reports "unlicensed" and is wrong.

Skills with **no upstream license at all** are linked, never copied — no license means all
rights reserved, however freely something is shared. Four more are withheld entirely because an
earlier third-party copy exists and authorship could not be established.

[How each source was verified →](docs/CATALOG.md#external--install-from-source) ·
[Machine-readable manifest →](manifest.json)

If you maintain something listed here and the attribution is wrong, open an issue — it will be
fixed rather than argued about.

## More

- [Platforms](docs/PLATFORMS.md) — where each agent reads skills, and the listing budget
- [Plugins](docs/PLUGINS.md) — 31 marketplaces and the plugins installed from them
- [Contributing](CONTRIBUTING.md) — adding a skill, and what gets rejected

## License

MIT for everything in `skills/` and `scripts/`. External skills stay under their own licenses,
recorded per entry in [manifest.json](manifest.json).

