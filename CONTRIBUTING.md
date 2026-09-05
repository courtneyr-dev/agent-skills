# Contributing

## Adding a skill

1. `mkdir skills/my-skill` with a `SKILL.md` carrying `name` and `description` frontmatter.
2. Make the description say **when to use it**, in the words someone would actually type. That text
   is all the model sees when deciding whether to invoke the skill — everything else is only read
   after it triggers.
3. Put anything long in `references/` and link to it from the body. A `SKILL.md` that cannot be
   skimmed will not be followed.
4. Add a one-line summary and a realistic example to `manifest.json`, and put the skill in a path.
5. `./install.sh --list` to confirm it is picked up.

## What gets rejected

**Anything you did not write, unless its license permits redistribution and you say so.** This is
the one hard rule. A public repo with no LICENSE file is all rights reserved, however freely it is
shared. If a skill came from somewhere else, link to the original instead — `manifest.json` has an
`external` kind for exactly this.

Check for an earlier copy before assuming something is yours to publish: compare content and
first-commit dates, not names. Aggregator repos copy in both directions, so a name match proves
nothing. And never conclude "no license" from a repo root — some repos license each directory
separately.

**Anything carrying personal or employer detail.** Absolute home paths, hostnames, employer-internal
rules, someone's health or employment history, run state, API keys. `scripts/sanitize.py` catches
the common cases and re-scans its own output, but it is a filter, not a guarantee. Read the diff.

**Skills that only make sense for one person's setup.** A skill wired to a specific vault layout,
a specific employer, or one person's plugins belongs in a private repo. If it can be made
config-driven, do that instead — ship a `config.example.yml` and gitignore the real one.

## Style

Descriptions are trigger conditions, not summaries. Bodies are instructions to an agent, written in
second person. Keep the prose specific: name the failure mode, give the number, say what breaks.
Skip the throat-clearing.

## Reporting a misattribution

Open an issue with the original source and, if you have it, the first-commit date. Attribution
errors get fixed, not argued about.
