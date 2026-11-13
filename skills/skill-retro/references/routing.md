# Routing a retro's edits

`scripts/skill_owner.py <skill> --json` returns `flow`, `repo`, `path`, and sometimes `fork`, `overlay` and `plugin`. Prepare everything locally first; open, push or file only after the user says yes.

| flow | Where it goes | How |
|---|---|---|
| `pr` | `repo`, from `fork` when one is set | Branch `skill-retro/<skill>-<date>` in a clean clone or worktree of the repo (never the user's working branch). Apply the edits, run the repo's checks, commit, show the title, body and diff. Push and `gh pr create` on yes. |
| `rfc-pr` | a repo in `rfc_repos` | Load the skill named in `rfc_process_skill` and follow it; the retro note is the candidate brief. A human merges. If `rfc_process_skill` is empty, ask the user how that repo takes proposals. |
| `fork-commit` | the user's fork of a third-party pack | Commit to the fork's main on yes. Never open a PR or issue upstream. |
| `upstream-issue` | a third-party maintainer | Draft the issue: what happened, evidence, the proposed text. `gh issue create` on yes. No PR unless the user asks. |
| overlay | the user's own repo that holds the skill (`overlay` is set) | A lesson about the user's additions (a pinned description, a kept file, `SKILL.local.md`) edits that overlay in the repo that tracks the skill, as a `pr` there. Lessons about upstream's text still go upstream. |
| `unknown` | — | Ask the user where the skill came from; add the answer to `owners` in `config.local.json`. |

## Commits and PRs

- `commit_style` comes from `commit_styles` in the config, per org. "conventional, signed" means a Conventional Commits subject and a signed commit; repos with that rule usually reject unsigned ones.
- Otherwise it's "match the repo's git log": copy the subject style of the last few commits.
- PR body: one line on where the lessons came from (the retro note's title, not its local path), then the lessons as a short list, each with its evidence line. Link nothing private.
- One branch and one PR per repo per retro.
