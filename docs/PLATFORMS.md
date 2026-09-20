# Platforms

A skill is a directory with a `SKILL.md` at its root. The file starts with YAML frontmatter holding
at minimum a `name` and a `description`; everything after it is instructions the agent reads when
the skill triggers. That format is portable — the only thing that differs between agents is where
they look for it.

## Where each agent reads skills, and how well that is proven

A directory an installer can write to is not proof that the agent loads what gets written there.
These two things are tracked separately: the **path**, and the **support grade** — what was actually
observed at runtime. Grades live in `manifest.json`; `./install.sh --grades` prints them.

| Agent | Directory | Grade | What was observed |
|---|---|---|---|
| Universal mount | `~/.agents/skills/` | — | aggregation namespace, not an agent |
| Claude Code | `~/.claude/skills/` | **L3** | listed, invoked, relative resource read |
| Codex CLI | `~/.codex/skills/` | **L3** | same, through a two-hop mount |
| Cursor | `~/.cursor/skills/` | **L2** | app bundle resolves this path; invocation unproven |
| Gemini CLI | `~/.gemini/skills/` | **L2** | CLI implements `SKILL.md` discovery; runtime blocked on auth |
| OpenClaw | `~/.openclaw/skills/` | **L1** | production symlink topology observed; runtime unproven |

- **L3** — runtime proven: discovered, invoked, current content returned, and a relative file under
  the skill directory read.
- **L2** — the shipped product implements the path; runtime invocation unproven here.
- **L1** — filesystem topology observed in production; runtime unproven.
- **L0** — unsupported or unverified.

`--apply` writes for L3 agents. Anything below L3 is reported as `PLAN` and skipped unless you pass
`--include-unverified`: those paths are filesystem-compatible and available, not verified.

Raising a grade takes a new runtime probe, not a new reading of the docs. The probe used here is a
disposable skill carrying two codewords — one in `SKILL.md`, one in a relative `references/` file —
so discovery and relative resource access are proven separately.

Project-scoped skills usually live in `.agents/skills/` or the agent's dotfolder inside the repo,
and take precedence over the user-level ones.

## Why install.sh symlinks

One canonical copy in `~/.agents/skills`, symlinked into each agent's directory. Every agent sees
the same version, and updating once updates all of them. Copies drift — the same skill ends up at
three different versions across three tools, and you find out when one of them behaves differently.

Claude Code and Codex are runtime-proven to follow symlinks, Codex through two hops. Cursor,
OpenClaw and Gemini are expected to, but that is not proven here — see the grades above.

If you hit an agent that does not follow links, copy the skill directories in yourself and re-copy
after every update. This installer only writes symlinks; it has no copy mode.

## Remote and containerized agents

An agent running on a server or in a container reads skills from *its* filesystem, not yours.
Symlinks to your laptop mean nothing there. Copy the skill directories to the remote host and
re-copy them when they change — a scheduled push after your update step keeps them honest.

## Skill descriptions and the listing budget

Agents load every skill's `name` and `description` into context so the model can decide what to
invoke. That listing is capped. Past a certain number of skills, agents start truncating — some drop
descriptions entirely, leaving the model with bare names and badly degraded triggering, and some
silently drop skills from the end of the list.

Practical consequences:

- **Keep descriptions tight and trigger-focused.** Say when to use it, in the words you would
  actually type. Save the detail for the body.
- **Install what you use.** A hundred installed skills are worse than twenty when the listing
  truncates — you lose triggering accuracy across all of them, not just the extras.
- **Check for a truncation warning** in your agent's startup output. It is easy to miss, and it is
  the difference between "the model chose not to use that skill" and "the model never saw it."
