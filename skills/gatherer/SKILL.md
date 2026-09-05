---
name: gatherer
description: "Use when the user says 'gather my work', 'what's on my plate', or 'daily gather', or when a review needs your open GitHub issues and PRs, watched Trac tickets, and Things tasks pulled into today's daily note."
---

# Gatherer

One script, no model in the loop: it collects open work from GitHub (`gh`), WordPress core Trac (the wordpress-trac MCP endpoint, called over plain HTTP), and Things 3 (AppleScript), then writes a `## Gathered` section into today's daily note. You run it and relay the receipt.

## Steps

1. Run it:

   ```bash
   python3 $HOME/.claude/claude-config/skills/gatherer/scripts/gather.py
   ```

   Rerunning the same day replaces the section; nothing else in the note changes. `--dry-run` prints the section without writing, `--print` writes and prints, `--sources github,things` skips a source, `--things-lists today,inbox,anytime` widens Things. `--help` lists the rest.

2. Read the receipt on stdout (a run takes about 5 seconds): `## Gathered written → <note>`, or `unchanged` when nothing moved, and then the summary line (counts per source, any `failed:` or `stale from` note). stderr carries one `gather:` line per source plus any retry.

3. Report back, and you're done once this is sent: the summary line verbatim, plus each source marked failed or stale and its fix from the table below. Leave the items themselves out unless you ask. Exit 1 means the daily note doesn't exist yet (the 9am job creates it): the section went to stdout instead, so paste it or rerun once the note exists.

## Where things live

- Note: `$VAULT_DIR/Review/Daily/YYYY-MM-DD.md`. The section goes in front of `## 📥 Daily Inboxes` when that heading exists, else in front of Daily Routine, Time Log, or Metadata, else at the end. Its body sits between `<!-- gathered:start -->` and `<!-- gathered:end -->`. Things lines are plain bullets, not checkboxes, so things-obsidian-sync ignores them.
- State: `$VAULT_DIR/Reports/_gatherer-state.json` holds the last run and each source's last good list. A source that fails shows that list marked stale instead of vanishing.
- Trac watchlist: `trac-watchlist.txt` next to this file, one ticket id per line. The Trac MCP can't search by owner, reporter, or cc (`searchTickets` ignores those filters; `getTicket` returns reporter and cc blank, see `~/.claude/knowledge/wiki/tools/wordpress-trac-access.md`), so "tickets you owns or follows" is this list. When you say "follow ticket N" or "watch #N", append the id with a short note. Closed tickets stay listed but drop out of the section; the summary says "of N watched".

## Failure modes

| Symptom in the summary | Cause | Fix |
|---|---|---|
| GitHub `failed: ... gh auth login` | `gh` logged out | `gh auth login`, rerun |
| GitHub retries on `HTTP 429` or `403` | rate limit (search allows 30 calls a minute) | the script waits for `Retry-After` or the reset, 5 tries; rerun later if it still fails |
| Trac `network:` or `HTTP 5xx` | the MCP worker is down | 5 backoff tries, then the stale list; rerun later |
| Things `AppleScript timed out` | Things 3 not responding | open Things, rerun |
| Trac `watchlist unreadable` | file missing | recreate `trac-watchlist.txt` |

## Cadence

On demand. Add a launchd plist only after the user says the output has earned it; scaffold it with loop-template when you do.
