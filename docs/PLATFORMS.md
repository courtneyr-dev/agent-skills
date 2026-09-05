# Platforms

A skill is a directory with a `SKILL.md` at its root. The file starts with YAML frontmatter holding
at minimum a `name` and a `description`; everything after it is instructions the agent reads when
the skill triggers. That format is portable — the only thing that differs between agents is where
they look for it.

## Where each agent reads skills

| Agent | Directory |
|---|---|
| Universal (read by several tools) | `~/.agents/skills/` |
| Claude Code | `~/.claude/skills/` |
| Cursor | `~/.cursor/skills/` |
| Codex CLI | `~/.codex/skills/` |
| OpenClaw | `~/.openclaw/skills/` |
| Gemini CLI | `~/.gemini/skills/` |

Project-scoped skills usually live in `.agents/skills/` or the agent's dotfolder inside the repo,
and take precedence over the user-level ones.

## Why install.sh symlinks

One canonical copy in `~/.agents/skills`, symlinked into each agent's directory. Every agent sees
the same version, and updating once updates all of them. Copies drift — the same skill ends up at
three different versions across three tools, and you find out when one of them behaves differently.

Codex, Cursor, Claude Code and OpenClaw all follow symlinks. If you hit an agent that does not,
`./install.sh --copy` writes real directories instead; re-run it after every update.

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
