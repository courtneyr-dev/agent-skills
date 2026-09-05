# Plugins

Not every skill in a working setup is a loose `SKILL.md`. Many arrive as **plugins** — bundles of
skills, agents, commands, and MCP servers installed from a marketplace. `manifest.json` records
those under `plugin_marketplaces` and `plugins_installed`.

Plugins are never vendored here. They belong to their authors, they update on their own schedule,
and copying them would strand you on a frozen version.

## Installing

Add the marketplace, then install the plugin:

```bash
/plugin marketplace add <owner>/<repo>
/plugin install <plugin-name>@<marketplace-name>
```

Both are Claude Code slash commands, run inside a session. Every entry in the manifest with
`"verified": true` has a `repo` you can pass to the first command.

## What is recorded

| Field | Meaning |
|---|---|
| `repo` | The GitHub source, where one is known |
| `source` | `github`, `github (recovered)`, or `local-directory (missing)` |
| `verified` | The repo's `.claude-plugin/marketplace.json` was fetched and confirmed to publish the cached plugin |
| `plugins_installed` | Plugins actually installed from that marketplace on the reference machine |
| `plugins_cached` | Plugins present in the local cache, installed or not |

`verified` is a checked fact, not a guess. Each recovered repo was confirmed by fetching its
marketplace manifest and matching a plugin name against the local cache. Marketplaces that could not
be confirmed carry `repo: null` rather than a plausible-looking guess — an unverified repo name is
worse than a missing one, because someone will install it.

## Marketplaces registered from local directories

A marketplace can be registered from a local path instead of a repo. That works until the path
disappears, and then the registration silently rots: the plugins keep working from cache, but the
marketplace can never update or reinstall them, and nobody else can reproduce your setup.

Registering from `/tmp` guarantees this outcome. If you add a marketplace from a local clone, keep
the clone somewhere permanent, or re-add it from its GitHub repo once you are done developing
against it.

## Account-level skills

Some namespaced skill sets — `canva:`, `legal:`, `marketing:`, `sales:`, `data:`,
`small-business:`, and other Anthropic-published collections — are enabled per account rather than
installed from a repo. They are not listed in the manifest because there is nothing to install:
enable them in your own Claude settings and they appear.
