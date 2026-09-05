---
name: skill-sync
description: "Use when the user says 'add this skill from GitHub', 'update my skills', 'sync skills', or 'are my skills up to date', or when a standalone skill needs registering with its source repo. Marketplace plugins are out of scope."
---

# skill-sync

Keeps standalone skills in `~/.claude/skills/` in sync with the GitHub repos they came from. All logic lives in `sync_skills.py` (no model dependency); a weekly launchd job (`com.you.skill-sync`, Mondays 07:30) runs `apply --notify` automatically.

Marketplace plugins are out of scope — Claude Code auto-updates those itself.

## Quick reference

```bash
SYNC=~/.claude/skills/skill-sync/sync_skills.py
python3 $SYNC list                                        # what's tracked
python3 $SYNC check                                       # report only, no writes
python3 $SYNC apply                                       # apply safe updates
python3 $SYNC add <skill> <owner/repo> [--path skills/x] [--ref main]
python3 $SYNC adopt <skill>                               # take upstream (also installs new skills)
python3 $SYNC baseline <skill>                            # accept current local as the new base
python3 $SYNC remove <skill>                              # stop tracking (files stay)
```

Reports land in `~/.claude/skill-sync/reports/latest.md`.

## Installing a skill from GitHub

When the user shares a GitHub repo/PR containing a skill and says "add this to my skills":

1. Identify `owner/repo` and the skill's subdirectory (use `gh` per the gh-fetch skill).
2. `add <skill-name> <owner/repo> --path <subdir>` then `adopt <skill-name>`.

This installs it AND tracks it for future updates — always prefer this over a bare file copy.

## Registering an already-installed skill

`add` it with its source repo. If local matches upstream, a baseline is recorded automatically. If it reports `unbaselined`, the local copy differs from upstream head: diff them, then `adopt` (take upstream) or `baseline` (keep local as the base).

## Reading `check`/`apply` output

| Status | Meaning | Action |
|---|---|---|
| `up-to-date` | nothing to do | — |
| `update-available` / `updated` | upstream changed, local untouched | `apply` updates it |
| `local-edits` | you edited it, upstream unchanged | leave, or PR the edit upstream |
| `conflict` | both changed since last sync | diff local vs `~/.claude/skill-sync/state/<skill>/` vs upstream cache in `~/.claude/skill-sync/repos/`, merge by hand, then `adopt` or `baseline` |
| `unbaselined` | tracked but no baseline | `adopt` or `baseline` |

## Common mistakes

- **`baseline` is not "keep my fork forever."** It marks local as the new base, so the next upstream change WILL overwrite it on `apply`. For a permanent local fork, `remove` the skill from tracking.
- **Don't hand-merge inside `state/`** — snapshots are tool-managed. Merge in the skill dir, then `baseline`.
- **Conflicts never auto-resolve.** The weekly job only notifies; a human (or an explicitly-asked session) resolves them.

## Own-repo skills (out of scope here)

`~/.claude/skills` is itself a sparse git checkout of `your-org/claude-config` — for skills the user authors, sync via plain git in `~/.claude/claude-config` (commit, pull, push). skill-sync tracks only skills whose upstream is someone else's repo.

## Automation

launchd plist: `~/Library/LaunchAgents/com.you.skill-sync.plist`. Disable with `launchctl bootout gui/$UID/com.you.skill-sync`. Logs: `~/.claude/skill-sync/reports/launchd.log`.
