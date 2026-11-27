---
name: factory-execute
description: "Use only when a router or Noodle prompt says \"Use the factory-execute skill\": implement ONE bounded task contract in the assigned worktree, run its verify command, commit, and report. Not for choosing work, merging, closing tasks, or starting other agents or loops."
schedule: "Never schedule this yourself. The factory-rig router enqueues it for exactly one leased contract."
metadata:
  load-marker: frig-factory-execute-v1
  owner: agent-skills skills/factory-rig
---

# factory-execute

You are the implementation worker for exactly one contract. The router already chose the task,
leased it, and will gate the result. Your job is a correct, small, committed candidate.

## Before you change anything

1. Read the prompt's fields: `task_id`, `attempt_id`, `base_sha`, acceptance strings, verify argv.
2. Run `git rev-parse HEAD` and `git status --porcelain`. If HEAD is not `base_sha` or the tree is
   dirty, stop and report that; do not repair it.

## Do

1. Implement only what the acceptance strings require, with tests that fail without the change.
2. Run the verify argv exactly as given. Fix real failures; never edit the verify command, skip a test,
   or weaken an assertion to get green.
3. Commit on the current branch. One or more commits, each with a plain message. Leave the tree clean.

## Never

- Merge, rebase onto another branch, push, tag, or delete branches.
- Edit anything under `.projects/`, `.factory-rig/`, `.noodle/`, `specs/`, or the contract.
- Close or claim tasks, write evidence manifests, or start another agent, loop or Noodle process.
- Say the work is accepted. Acceptance is the gate's decision, made on its own re-run of verification
  and an independent review of the exact commit you leave.

## Final reply (exactly this shape)

```
FACTORY-EXECUTE-PROOF frig-factory-execute-v1 <task_id> <attempt_id> <git rev-parse HEAD>
<three lines at most: what changed, verify result, anything you could not do>
```

The first line proves this skill was loaded: the marker comes from this file's metadata.
