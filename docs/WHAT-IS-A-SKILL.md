# What is a skill?

A skill is a folder with a `SKILL.md` inside it. That file starts with a few lines of YAML naming
the skill and saying when to use it, and everything after that is instructions your coding agent
reads and follows.

```
skills/
  my-skill/
    SKILL.md          ← name, description, instructions
    references/       ← optional: longer material, read only when needed
    scripts/          ← optional: things the skill runs
```

The frontmatter is the part that matters most:

```yaml
---
name: bible-study
description: Use when the user says "bible study", asks to study a passage, or wants a
  scholarly multi-translation study written into a vault.
---
```

## How an agent decides to use one

Your agent loads **every installed skill's name and description** into its context at the start of
a session — but not the bodies. It reads that list, and when your request matches a description, it
opens that skill and follows it.

Two consequences follow, and both surprise people:

**The description is the whole trigger.** A beautifully written skill with a vague description
never fires. Descriptions should read like the words you would actually type — "when the user says
'run the job scan'" — not like a summary of what the skill contains.

**More skills make every skill worse.** That listing is capped. Past a few dozen skills, agents
start truncating it; some drop all descriptions and leave the model with bare names, and some
silently drop skills off the end. So a hundred installed skills is not a hundred available skills —
it is a degraded version of the twenty you actually use.

This is why this repo installs by path and leads with a starter set instead of telling you to take
everything. Check your agent's startup output for a truncation warning; it is easy to miss and it
is the difference between "the model chose not to use that skill" and "the model never saw it."

## Where they go

| Agent | Directory |
|---|---|
| Universal | `~/.agents/skills/` |
| Claude Code | `~/.claude/skills/` |
| Cursor | `~/.cursor/skills/` |
| Codex CLI | `~/.codex/skills/` |
| OpenClaw | `~/.openclaw/skills/` |
| Gemini CLI | `~/.gemini/skills/` |

`install.sh` puts one copy in `~/.agents/skills` and symlinks it into each of the others, so
updating once updates every agent. More detail in [PLATFORMS.md](PLATFORMS.md).

## Skills, plugins, MCP servers

Easy to conflate, genuinely different:

- **Skill** — instructions. No code required. Portable across agents.
- **Plugin** — a bundle from a marketplace that can contain skills, agents, commands, and MCP
  servers. Installed with `/plugin`. See [PLUGINS.md](PLUGINS.md).
- **MCP server** — a running process exposing tools an agent can call. Gives new *capabilities*;
  a skill gives *judgment about when and how to use them*.

A skill often exists to use an MCP server well.

## Writing one

Start by writing the description as the sentence you would say out loud. Then write the body as
instructions to a competent colleague who has not seen this problem before: name the failure modes,
give the actual commands, and say what "done" looks like. Put anything long in `references/` and
link to it, so the main file stays skimmable.

The best test is whether the skill fires when you expect it to, without you naming it.
[CONTRIBUTING.md](../CONTRIBUTING.md) has the conventions used here.

## Is installing a skill safe?

A skill is instructions your agent will follow, including instructions to run scripts. It is not
sandboxed. Read one before you install it. [SECURITY.md](../SECURITY.md) covers what to look for.
