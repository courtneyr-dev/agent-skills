## What this changes

<!-- One or two sentences. What does the skill do, or what did you fix? -->

## Provenance

The one hard rule here is not publishing what you did not write unless its license permits it.

- [ ] **I wrote this**, or it is from a repo whose license permits redistribution
- [ ] If it came from somewhere else, I checked for an **earlier copy** by content and
      first-commit date — not by name
- [ ] I checked the license across the **whole upstream tree**, not just the repo root
      (some repos license each directory separately)
- [ ] If the upstream has **no license file**, I added it as a manifest link instead of copying it

## Privacy

- [ ] No absolute home paths, hostnames, API keys, or run state
- [ ] No employer-internal rules, and nothing personal about a specific human
- [ ] Anything configurable ships a `config.example.*` with the real one gitignored
- [ ] I read the actual diff, not just the sanitizer output

## If this adds a skill

- [ ] `SKILL.md` frontmatter has `name` and a `description` written as **when to use it**
- [ ] Added to `manifest.json` with a summary, an example, and a path
- [ ] `./install.sh --list` picks it up
