# skill-retro

After a skill runs a batch of work, skill-retro reads the session, writes what it learned as concrete edits to that skill, and routes them to the repo that owns it: a pull request for your own and your employer's repos, a proposal process for repos that require one, a drafted issue for third-party skills. You approve everything before it leaves your machine.

Two parts:

- **The skill** (`/skill-retro`): reviews the session transcript with a fresh subagent, writes a retro note, prepares the edits.
- **The offer hook** (`scripts/retro_offer_hook.py`): a Claude Code Stop hook. When one skill drives 15 or more tool calls in a session, it asks you once, with clickable choices, whether to run a retro. It never runs one by itself.

## Install

You need Python 3.9 or later, git and the GitHub CLI signed in (`gh auth login`).

```sh
ln -s "$PWD/skills/skill-retro" ~/.claude/skills/skill-retro
cp skills/skill-retro/scripts/config.example.json skills/skill-retro/scripts/config.local.json
```

Edit `config.local.json` (gitignored):

| Key | What it does |
|---|---|
| `notes_dir` | Where retro notes are written. Default `~/skill-retros`. |
| `candidates_file` | Optional Markdown table that "not for the skill" lessons are appended to. |
| `threshold` | Tool calls under one skill before the hook offers a retro. Default 15. |
| `exclude` | Skills the hook never offers, glob patterns allowed: `["skill-retro", "superpowers:*"]`. |
| `own_orgs` | Your GitHub login and orgs; skills from these get PRs, not issues. |
| `employer_orgs` | Your employer's GitHub orgs; their skills get PRs too. |
| `rfc_repos` | Repos that take skill changes through a proposal process instead of a plain PR. |
| `rfc_process_skill` | The skill that runs that proposal process, e.g. `team-skills:skill-rfc-process`. |
| `commit_styles` | Per-org commit rules: `{"your-employer": "conventional, signed"}`. Other repos match their own `git log`. |
| `fork_repos` | Your forks of third-party packs; edits are committed there, never sent upstream. |
| `sync_manifest` | A skill-sync `sources.json`, if you use one, so tracked skills route to their source. |
| `owners` | Per-skill overrides: `{"my-skill": {"repo": "owner/name", "path": "skills/my-skill"}}`. |

Then add the hook to `~/.claude/settings.json`, with the absolute path to the script:

```json
"hooks": {
  "Stop": [
    {"hooks": [{"type": "command", "command": "python3 /absolute/path/to/skills/skill-retro/scripts/retro_offer_hook.py"}]}
  ]
}
```

Set `SKILL_RETRO_OFF=1` in scripts that run `claude -p` unattended, so the hook stays quiet where nobody can answer.

## Check where a skill's edits would go

```sh
python3 skills/skill-retro/scripts/skill_owner.py docs-style-review
python3 skills/skill-retro/scripts/skill_owner.py team-skills:writing-skills --json
```

## Claude chat edition

`chat/skill-retro/` is a version for claude.ai, which has no hooks, subagents, shell or `gh`. It reviews the current conversation (or an uploaded `.jsonl`), checks each lesson against an evidence log in place of the reviewer subagent, and hands over a note, a patch and the commands, or a rebuilt `.skill` for skills that live only on the account. Build it, then upload the file on claude.ai's Skills settings page:

```sh
python3 skills/skill-retro/scripts/build_chat_skill.py
```

The file lands in `skills/skill-retro/dist/skill-retro.skill` (gitignored). Account skills don't sync from git, so rebuild and re-upload after every change to `chat/` or `references/note-format.md`. Account skills also show up in Claude Code as `anthropic-skills:skill-retro`; its description sends Claude Code back to this one.

## Tests

```sh
python3 -m unittest discover skills/skill-retro/tests
```

The tests run offline and cover the hook's counting, its once-per-session rule and guards, and the owner lookup for employer repos, proposal repos, forks, the skill-sync manifest and plugin skills.
