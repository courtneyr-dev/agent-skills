# Security

## What a skill actually is

A skill is a set of instructions your coding agent reads and follows. It is not sandboxed. When a
skill says "run this script" or "read that file," a capable agent will do it. Some skills here ship
Python or shell scripts and run them.

**Installing a skill is closer to installing a shell alias than to installing a library.** Read a
skill before you install it, the same way you would read a script before piping it into bash. That
is also why the one-line installer in the README downloads and pages the script rather than piping
it straight to a shell.

## What this repo does to reduce risk

- **Every external skill is linked, never copied.** You install it from the author's own repo, so
  you can see who wrote it and what changed. `manifest.json` records the source, license, and
  whether redistribution is even permitted.
- **Provenance is checked, not assumed.** Skills were compared against upstream copies by content
  and first-commit date before being published here. Fifteen turned out to belong to other people
  and were removed.
- **No secrets, no hosts, no personal paths.** `scripts/sanitize.py` strips home paths, personal
  names, employer-specific lines, run state, and backup files, then re-scans its own output. It is
  a filter, not a guarantee.

## What to check before installing anything

1. Read the `SKILL.md`. If it tells the agent to run a script, read the script too.
2. Look for network calls, credential reads, and writes outside the directory you expect.
3. Check what it does with any config you give it — several skills read a vault path or an API
   token from your environment.
4. Prefer installing a path (`-p pkm`) over everything. Fewer skills is less surface.

## Reporting something

Open an issue for anything non-sensitive — a skill that overreaches, a script that does more than
its description says, a dependency that looks wrong.

For anything you would rather not post publicly, use GitHub's private vulnerability reporting on
this repository (Security → Report a vulnerability). Expect a reply within a week; this is a
personal project, not a staffed one, and that is worth knowing before you rely on it.

## Scope

This repo distributes instructions and small scripts. It has no server, no service, and no user
data. The realistic risks are a skill that does more than it claims, a supply-chain problem in an
upstream repo, or an agent following instructions it should have questioned.
