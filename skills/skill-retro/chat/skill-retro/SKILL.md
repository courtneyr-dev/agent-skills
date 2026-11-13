---
name: skill-retro
description: "Use in Claude chat after a skill runs, or when someone says 'skill retro' or 'retro that run': turns the run into evidence-backed edits for that skill. In Claude Code, use the local skill-retro."
---

# skill-retro (Claude chat edition)

A run that went sideways teaches the skill something only once, unless someone writes it down where the skill lives. This skill reads the record of a run, writes the lessons as concrete edits, and hands them over in the form the skill's owner can apply. Nothing gets filed, sent or uploaded without the user's yes.

If you have a shell and a `~/.claude/skills/skill-retro/` folder, you're in Claude Code: stop and use that skill instead. It reads the session file and opens the pull request itself.

## Routing

| Topic | Reference |
|---|---|
| Where the record comes from: this chat, an uploaded transcript, pasted text | `references/reading-the-record.md` |
| The note: sections, lesson fields, one calibration example | `references/note-format.md` |
| Who owns the skill and what to hand over for each owner | `references/routing-chat.md` |

## Run

1. **Name the skill and the run.** Take them from the user, or from the skill this conversation used most recently. If two runs or two skills fit, ask which one.
2. **Get the record** per `references/reading-the-record.md`, and say which source you're using.
3. **Get the skill as it ran.** With code execution, read `/mnt/skills/user/<skill>/SKILL.md` (or `/mnt/skills/public/<skill>/` for a built-in skill) and every file it routes to. Without it, ask the user to paste `SKILL.md` or attach the `.skill` file. If the skill changed after the run, review against the version that ran and mark lessons the current version already covers.
4. **Build the evidence log before writing any lesson.** Number each event from the record: what the skill told the run to do, what happened, and the proof (a quoted error, a count, a user correction), with where it appears (`U4` for the fourth user turn, or a line number in an upload). Your own earlier summaries in this chat are claims to check against the record, not evidence. Then try to disprove each lesson: name the log entry that would show it wrong. Drop a lesson with no supporting entry; mark anything you inferred as inferred. An empty retro is a valid result.
5. **Find the owner.** Ask one question with the options in `references/routing-chat.md` unless the user already said.
6. **Write the note** in the format of `references/note-format.md`. In the frontmatter, `session` is `this conversation, YYYY-MM-DD` or the uploaded file's name, and `flow` is the owner row you used. With code execution, save it as `YYYY-MM-DD <skill> retro.md` in `/mnt/user-data/outputs/`; otherwise give it in one Markdown code block.
7. **Prepare the edits** per `references/routing-chat.md`. Show them, then ask once: hand them over as prepared, change them first, or keep the note only. Use a connected tool to open, file or send anything only on that yes.
8. **Report:** what you delivered, what the user still has to do (apply, push, re-upload), and what you couldn't check.

## Common mistakes

- **Narrating the session.** "First we tried…" isn't a lesson. Each lesson is a rule the next run can follow, with the evidence that earned it.
- **Lessons from memory.** Every lesson points at a log entry. If compaction hid the part of the chat that matters, say so and ask for the export.
- **Forgetting the account copy.** Skills uploaded to claude.ai don't update from git. When the edit lands in a repo, tell the user the account copy stays stale until they re-upload it.
- **One patch per lesson.** Batch a retro's edits into one patch and one pull request per repo.
- **Retroing the retro.** Don't run skill-retro on itself.
