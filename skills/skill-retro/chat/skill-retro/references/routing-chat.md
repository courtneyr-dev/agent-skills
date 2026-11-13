# Routing a retro's edits from chat

Chat can't push a branch, so the job is to hand the owner something they can apply in one step. Ask which row fits when the user hasn't said.

| Owner | What you prepare | How it lands |
|---|---|---|
| Only on the user's claude.ai account | Every changed file in full, plus a rebuilt `<skill>.skill`: a zip with the `<skill>/` folder at its root. With code execution, copy `/mnt/skills/user/<skill>/`, apply the edits, zip it into `/mnt/user-data/outputs/`. | The user uploads it on the Skills settings page where the old one lives, replacing it. |
| A GitHub repo the user owns | A unified diff of the skill's folder, a branch name `skill-retro/<skill>-<date>`, a commit subject that matches the repo's `git log` (ask if you can't see it), and a PR title and body. | A connected tool opens the PR on the user's yes; otherwise the user runs the commands below. If the skill is also on the claude.ai account, include the rebuilt `.skill` too. |
| A shared team repo with a review or RFC process | The same diff, with the retro note as the proposal brief. | The user takes it through that process; a person merges. Don't open anything yourself. |
| A third-party maintainer | A drafted issue: what happened, the evidence, the proposed text. | The user files it, or a connected tool files it on yes. No pull request unless the user asks. |
| The user's own additions to a third-party skill | Edits to the user's copy only (their account upload or their fork). | As the first two rows. Lessons about upstream's text still go upstream as an issue. |
| Unknown | — | Ask where the skill came from before going on. |

## Making the diff

With code execution: copy the skill folder twice (`a/` and `b/`), apply the edits to `b/`, then `diff -ru a b > retro.patch`. Before handing it over, run `git apply --check -p1 ../retro.patch` from inside `a/`; it must print nothing. Without code execution, give each edit as the note's "Add" text with the file and section it goes in.

## Commands for the user

```sh
git switch -c skill-retro/<skill>-<date>
git apply -p1 --directory=<path to the skill folder> retro.patch
git commit -am "<subject>"
git push -u origin HEAD
gh pr create --title "<title>" --body-file pr-body.md
```

## The PR body

One line on where the lessons came from (the retro note's title), then the lessons as a short list, each with its evidence line. Link nothing private: no chat share links, no local paths. One branch and one PR per repo per retro.
