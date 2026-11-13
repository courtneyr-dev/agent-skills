---
name: skill-retro
description: "Use when a skill just ran a batch of work and the session should be mined for lessons, when the skill-retro Stop hook offers a retro, or when someone says 'retro that run', 'skill retro' or /skill-retro. Turns one session into evidence-backed edits for that skill and routes them to the repo that owns it."
---

# skill-retro

A run that went sideways teaches the skill something only once, unless someone writes it down where the skill lives. This skill reads the session, writes the lessons as concrete edits, and routes each one to whoever can merge it. Nothing leaves the machine without the user's yes.

## Routing

| Topic | Reference |
|---|---|
| The note: sections, lesson fields, one calibration example | `references/note-format.md` |
| The reviewer subagent's brief | `references/reviewer-brief.md` |
| What each flow does: PR, RFC PR, fork commit, upstream issue, overlay | `references/routing.md` |
| Install, config and hook wiring (for people, not the agent) | `README.md` |

## Run

1. **Name the skill and the session.** The skill comes from the hook's offer or the user. The transcript of the current session is the newest `*.jsonl` under `~/.claude/projects/<cwd with / replaced by ->/` that contains a `Skill` tool call for it.
2. **Find the owner:** `python3 scripts/skill_owner.py <skill> --json`. `flow` decides the destination; `path` is the skill's folder in `repo`; `overlay` lists the user's local additions to a third-party skill. Flow `unknown`: ask the user where the skill came from before going on.
3. **Review from the transcript, not from memory.** Dispatch a fresh subagent with `references/reviewer-brief.md`, the transcript path and the skill's local path. It re-derives what happened from the record; this session's own account of the run is what's being checked. If the skill's files changed during or after the run, point the reviewer at the version that ran (`git show <commit before the change>:<path>`) and have it mark lessons the current files already apply. Add only what the transcript can't show (the user's spoken reasons, decisions made off-screen), labeled as such.
4. **Write the note** in the format of `references/note-format.md`, to `notes_dir` from `scripts/config.local.json` (default `~/skill-retros/`), named `YYYY-MM-DD <skill> retro.md`. Lessons that belong somewhere other than the skill go under "Not for the skill"; when `candidates_file` is set, add each as a row there too.
5. **Route the edits** per `references/routing.md`. Prepare everything locally, then ask once with AskUserQuestion: open it, change it first, or keep it as a note. Open, push or file only on that yes.
6. **Report:** the note's path, what was prepared, and what was opened, with links.

## Common mistakes

- **Narrating the session.** "On Tuesday we found…" isn't a lesson. Each lesson is a rule the next run can follow, with the evidence that earned it.
- **Editing installed copies.** Never edit under `~/.claude/plugins/`; plugin caches are overwritten on update. Edits go to the owning repo (or the user's overlay for a third-party skill).
- **One PR per lesson.** Batch a retro's edits into one branch and one PR per repo.
- **Skipping the repo's own rules.** Read the target repo's CONTRIBUTING, CHANGELOG and manifest versions before drafting; some require a version bump in every manifest.
- **Retroing the retro.** `skill-retro` is excluded from the hook; don't run it on itself.
