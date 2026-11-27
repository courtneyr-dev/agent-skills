# Background-agent permissions

A background agent, and any agent it starts, can't get a permission prompt answered, so it hangs until
someone stops it. On the reference install, ten helper agents hung on Bash prompts over two days. These
practices and rules avoid most of that. This skill never edits your settings: permission rules are yours
to change.

## Practices (no setting needed)

- Agents that build or integrate do the work with their own tools; they don't start helper agents that need Bash.
- The main session starts independent reviewers, because agents it starts can get prompts answered.
- Every unattended brief tells the agent to write its registry or roles file first and to write files before verifying.
- Keep the machine awake for the length of an unattended run.
- Size each agent to one deliverable, resumable with a message.

## Suggested allow rules

Start narrow. Replace `<skills-root>` with the absolute path of the folder that holds this skill, then add
the rules under `permissions.allow` in your Claude Code settings, or run `/fewer-permission-prompts`, which
proposes a list from your transcripts.

```json
[
  "Bash(python3 -W ignore -m unittest *)",
  "Bash(<skills-root>/factory-rig/bin/frig *)",
  "Bash(node <skills-root>/project-manager/scripts/*)"
]
```

Don't allow `git commit`, `git push`, `git add`, any `rm -r`, `npx`, `pip install`, `docker`, or
`terraform apply`. Those stay with the main session so a person can see them.
