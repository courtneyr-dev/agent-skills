---
name: decision-sync
description: Use when a decision captured by the aim/cross-check/own discernment skills should be filed into the Obsidian vault as a durable decision record, or when the user says "log this decision", "file the decision", "sync the decision", or "add this to the decision log". Reads a discernment-<slug>.md from the working directory, routes it to the right PARA folder, and writes it with vault frontmatter and backlinks.
---

# Decision sync

The `aim` → `cross-check` → `own` skills produce a `discernment-<slug>.md` in whatever directory
you were working in. That file is where the reasoning lives while the decision is open. This skill
moves the finished record into the vault, where it survives the repo it was made in.

Run it once a decision is actually made — after `own` has written its section. A decision still in
progress belongs in the working directory, not the vault.

## Where records go

| Situation | Destination |
|---|---|
| Decision is about a specific active project | `Projects/<project>/decisions/` |
| Everything else — tooling, workflow, standing policy | `Areas/Decisions/` |

Ask which project only when the working directory doesn't make it obvious. Never invent a project
folder; if no match exists, use `Areas/Decisions/`.

## Workflow

1. **Find the source.** Look for `discernment-*.md` in the working directory. If several exist, ask
   which one. If none exists, say so and stop — don't reconstruct a decision record from the chat.

2. **Check it's finished.** The file needs a populated `## Own` section. If `## Own` is missing or
   empty, tell the user the decision isn't captured yet and offer to run `own` first.

3. **Read it and write the vault note.** Preserve the reasoning verbatim — the Aim framing, the
   rubric result, the confidence calibration, the case against, and the final call. This record's
   value is that it shows the thinking, not just the outcome. Do not summarize away the
   disconfirming evidence.

4. **File it** with `file_decision.py` (below), which handles frontmatter, the ID, and the index.

5. **Link it.** Add `[[wikilinks]]` to related vault notes — the project note, any Permanent Note
   the reasoning draws on, the source material named in `## Aim`. Links to notes that don't exist
   yet are fine; they mark where the thinking should continue.

6. **Report** the vault path and what you linked. Leave the original `discernment-*.md` in place —
   the repo copy is the working artifact and deleting it loses the local trail.

## Helper

```bash
python3 ~/.claude/skills/decision-sync/file_decision.py <source.md> --title "<title>" [--project "<name>"] [--status decided|revisit] [--dry-run]
```

It writes the note, stamps `type: decision` frontmatter matching vault convention, assigns a
timestamp ID, and appends a row to `Areas/Decisions/Decision Log.md`. Use `--dry-run` to see the
destination and frontmatter without writing.

## Boundaries

- Never file a decision the user hasn't actually made. An open question is not a decision record.
- Never edit the reasoning to make the call look better-supported than the cross-check found it.
  A record that hides its own low-confidence claims is worse than no record.
- This skill writes to the vault only. It does not commit, publish, or share anything.
