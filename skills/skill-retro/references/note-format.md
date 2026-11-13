# The retro note

One Markdown file per retro. Readers: the user deciding what to approve, and a maintainer who never saw the session. Every lesson must make sense to the maintainer on its own.

## Sections, in order

1. **Title and frontmatter**: `title`, `created`, `skill`, `repo`, `flow`, `session` (transcript path).
2. **Outcome**: one paragraph. What the run set out to do, what it produced, how long it took, in numbers.
3. **What worked**: bullets, only what the skill should keep doing and why.
4. **What cost time, by cause**: one short subsection per cause, each with its count or minutes from the transcript.
5. **Proposed edits**: one numbered lesson each, in the shape below. Name the owning repo and how a change lands (PR, version bump) in one line before the first lesson.
6. **Not for the skill**: lessons that belong to a tool, a repo's AGENTS.md, a hook or a person, each with where it should go.
7. **One thing to ask a person**: the question no experiment can settle, with whom.

## Lesson shape

```markdown
## Lesson 1. Stop a review loop on evidence, then route the rest to people

- **File:** `references/docs-mode.md`, "How to review a Doc".
- **Add:** "Stop reviewing when two consecutive passes return no blocking findings. Cap same-lens passes at three. Send what remains to a named role as a numbered question, and stop."
- **Why:** passes 3 to 5 returned 8, 4 and 4 warnings, all wording; the open items needed an engineer's answer.
- **Check it works:** the next review ends by pass 3 with the same blocking count.
```

**Add** is the exact text to insert or replace, ready to paste. **Why** cites the transcript: counts, commands, error text. **Check it works** names what the next run should show.

Not this:

```markdown
## Lesson 1. Be more careful with reviews

The review went on too long and we should probably stop earlier next time.
```

It names no file, gives no text to add, cites no evidence, and can't be checked.
