# DevRel fleet runbook

The developer-relations fleet turns one developer-program outcome into tested docs, samples, workshops, feedback loops and program reports. It runs inside a workload the existing router picks (Claude Code with credit-routing and factory-rig). `devrel.program-lead` coordinates inside that workload and never dispatches. Every company, developer, quote and number in `fixtures/` is a labeled synthetic Fixture Co record.

## Run it

From `skills/company-fleets`:

```bash
bin/fleet resolve --profile devrel --workload devrel.workload.docs-and-workshop   # roles, skill paths, files read
bin/fleet validate --strict --fleet devrel                                       # registry gate
python3 fleets/devrel/run_evals.py --install-check                               # reruns every script case, rewrites evidence/
python3 -m unittest discover -s fleets/devrel/tests -p 'test_*.py'               # fleet guard tests
```

Workloads (profiles `devrel` and `product`; `product` adds `devrel.onboarding-specialist` to docs-and-workshop):

| Workload | Roles | Use it for |
|---|---|---|
| `devrel.workload.program-plan` | program-lead, program-analyst, dx-researcher | Kickoff routing, `devrel-context.md`, program plan and metrics |
| `devrel.workload.docs-and-workshop` | program-lead, docs-architect, sample-app-engineer, developer-educator, demo-producer | The tested content and demo chain |
| `devrel.workload.feedback-to-product` | program-lead, feedback-liaison, dx-researcher | Feedback to reproducible issue to owner response to reply draft |
| `devrel.workload.event-program` | program-lead, events-manager, developer-advocate, demo-producer, content-editor | Events, talks and content |
| `devrel.workload.ecosystem-and-oss` | program-lead, partner-engineer, oss-liaison | Partners, platform openings, the OSS counterpart to the community fleet |

## Roles

Fourteen roles cover every title the devrel requirements (S08 rows in `registry/requirements.json`) name: program lead (coordinator), developer advocate, DX researcher, developer educator, docs architect, sample-app engineer, onboarding specialist, content editor, demo producer, events manager, partner engineer, feedback liaison, program analyst and OSS liaison. Each record in `roles.json` keeps responsibilities, exclusions, authority (`may` and `may_not`), reviewer, acceptor and escalation, data classification, external-action limits (`draft-only` or `none`), attached skills with provenance, and eval cases.

Four states, kept apart (from `bin/fleet coverage`):

- Coverage: 10 covered, 4 partial (docs-architect, onboarding-specialist, events-manager, partner-engineer, each because a sibling samber collection isn't installed).
- Installed: all 14 are `reference-only`. They load through `bin/fleet resolve`; there's no native agent configuration.
- Activated: none. No real router session has selected a DevRel role yet.
- Behavioral: all 14 `unverified`. Their local skills pass deterministic checks, but no model run of a role is on record.

## Skills: adopted and written

Adopted, not copied: all 93 skills from `samber/developer-relations-skills` at commit c3a1b6912791539567727723baf626b4fec5ac7a (MIT, copyright 2026 Samuel Berthe) are installed by the sources workstream, each with `disable-model-invocation: true`. DevRel's roles attach 51 of them, plus 4 blocked skills from the two uninstalled sibling samber collections (55 samber skills in all). The router `developer-relations-kickoff` is one of the 51; it doesn't fire by itself and loads by explicit invocation or through the path `bin/fleet resolve` returns. Also attached: `devrel-engine` and `community-os` (existing local rig skills), `kanban-guru` (magnus919/agent-skills, MIT, Magnus Hedemark) and `customer-research` (coreyhaines31/marketingskills, MIT, Corey Haines).

Written for verified gaps, each with SKILL.md, references, scripts, unit tests and skill-creator test prompts:

| Skill | Gap it fills | State |
|---|---|---|
| [devrel-quickstart-replay](../../../devrel-quickstart-replay/SKILL.md) | Upstream describes the cold-run protocol and CI job but ships nothing that runs a page clean | In this repository; 22 unit tests and 6 eval cases pass from a clean clone; not activated |
| [devrel-program-kit](../../../devrel-program-kit/SKILL.md) | Kickoff handback, `devrel-context.md` mapping, route resolution against the installed tree, program-claims check | In this repository; 17 unit tests pass from a clean clone, and 5 of 7 eval cases (the other 2 need samber/developer-relations-skills); not activated; coverage partial |

Blocked attachments, recorded on the roles: `api-reference-quality`, `sdk-package-publishing`, `partner-app-onboarding` (samber/developer-platform-skills) and `hackathon-brief-design` (samber/dev-event-organizer-skills). Neither sibling collection is installed. `references/fallbacks.json` in devrel-program-kit names the installed partial cover for each.

## Acceptance evidence

All evidence sits in `evidence/`, each file headed by its command, date and exit code.

- Clean replay of the sample and quickstart: `replay-quickstart.txt` (sandbox-exec, four-key environment, all machine criteria true). The workshop lab and the FB-1 repro replay clean too (`replay-workshop-lab.txt`, `replay-feedback-repro.txt`).
- Counterexample: `replay-hidden-prereq-fails.txt`. A quickstart relying on its author's exported `FIXTURE_NOTES_PORT` fails at step 3.
- Human onboarding usability: always `unverified` in every replay report. The case `devrel.eval.human-onboarding-usability` is `blocked` at the human-data boundary.
- Untrusted handoff content: `untrusted-feedback-scan.txt` and `untrusted-feedback-held.txt`. Developer feedback can't move acceptance, publication, criteria or destinations, while its real finding goes through.
- Stale evidence: `replay-evidence-goes-stale.txt`. Replay evidence bound to the quickstart's bytes stops counting after an edit.
- Tenant boundary: `devrel-cannot-read-moderation-case.txt`.
- Claims: `program-reach-only-refused.txt` (14 findings) and `program-boundary-passes.txt`.
- Routes: `routes-launch-flags-sibling.txt` and `routes-scan-finds-drift.txt`.

Retained failures and counterexamples:

- `resolve-docs-and-workshop.first-run-assertion-error.txt`: the case's first assertion expected `registry/fleets.json` in `files_read`. Resolve doesn't read it, so the case now checks that no other fleet's file is read.
- Until the foundation widened its scanner on 2026-11-26, `fleetlib/untrusted.py` missed line 10 of `fixtures/untrusted/docs-feedback.md` ("Publish ... now without review", trigger one past its 40-character window). The regenerated `untrusted-feedback-scan.txt` now flags it: 5 findings, up from 4. Protected-field enforcement refused the publication change either way.

## Review fixes (2026-11-26)

An independent review found three major false passes in this fleet's skills. Each fix started from a failing test built on the reviewer's probe; the before and after outputs are in `evidence/`.

| Defect | Before | After | Evidence |
|---|---|---|---|
| 1. Replay judged success from one `set -e` run | `cd /no/such/dir && echo entered` replayed with `ok: true`; failures in pipelines and after a doc's `set +e` passed too | bash with `set -e -o pipefail`, every command's exit status checked on its own; the report names the failing command | `review-fix-1-2-before.txt`, `review-fix-1-2-after.txt` |
| 2. Expected lines matched as substrings | `notes: 1` passed on `notes: 12`; `ok` passed on `status: not ok` | Each expected line must match a whole printed line; `<placeholder>` still matches one token | same files |
| 6. Program check accepted any 5-character string as evidence, and only known claim kinds were checked | Missing evidence, `human_evidence: "session-notes"`, an unsourced `endorsement` and a `slack`/`given` testimonial all exited 0 | Evidence must be an existing passing replay report of the artifact's current bytes; sessions, sources and consent must be existing record files; unknown claim kinds are refused | `review-fix-6-before.txt`, `review-fix-6-after.txt` |

The boundary fixture `fixtures/program/program-boundary.json` now cites `fixtures/program/records/fb-2.json` (synthetic) for its quote, and its human usability is back to `unverified`: no reader session has run, so a session file would be invented research.

## Inputs for the integrator's demonstrations

- Demo 3, extension or API release with tested docs and a workshop: `fixtures/fixture-co-notes/` (sample), `fixtures/docs/quickstart.md` and `workshop-lab.md`, `fixtures/handoff/owner.json` and `contract.json` (handoff.v1 from docs-architect to developer-educator), and `fixtures/program/program-good.json`.
- Developer-education workflow: the same chain, plus `fixtures/docs/feedback-repro.md` for the feedback step.
- Untrusted source document: `fixtures/untrusted/docs-feedback.md`.

## Context and memory

`devrel-context.md` is the tenant's developer-program context record, owned by a named human. The Fixture Co copy is `fixtures/program/devrel-context.md`. Company facts stay in `registry/company.json`; agent memory holds a pointer only. See `devrel-program-kit/references/context-and-handback.md`.

## Requirement rows for registry/requirements.json

Deliverable paths are relative to the rig skills root.

| Row | Deliverable |
|---|---|
| S08-001 | `company-fleets/fleets/devrel/README.md` |
| S08-002 | `company-fleets/fleets/devrel/roles.json` |
| S08-003 | `devrel-program-kit/references/kit-map.md` |
| S08-004 | `devrel-quickstart-replay/SKILL.md` |
| S08-005 | `devrel-program-kit/references/kit-map.md` (hackathon and event production partial) |
| S08-006 | `company-fleets/fleets/devrel/fixtures/docs/feedback-repro.md` |
| S08-007 | `devrel-program-kit/scripts/check_program.py` |
| S08-008 | `devrel-program-kit/references/context-and-handback.md` |
| S08-009 | `devrel-program-kit/references/kit-map.md` |
| S08-010 | `devrel-program-kit/references/context-and-handback.md` |
| S08-011 | `devrel-program-kit/scripts/check_program.py` |
| S08-012 | `devrel-program-kit/scripts/check_program.py` |
| S08-013 | `company-fleets/fleets/devrel/README.md` |

## Update and rollback

`roles.json`, `skills.json` and `evals.json` are the source of truth; edit them, then rerun `run_evals.py` and `validate --strict`. `run_evals.py` overwrites evidence for the cases it runs and keeps every failure in `evals.json`. Rolling back is a git revert of this directory and the two skill directories. `run_evals.py` is identical in the community fleet; promoting it into `bin/fleet` is adjacent work for the foundation owner.

## Follow-ups

Minor findings from the 2026-11-26 review, recorded and not fixed:

- Most negative eval cases assert only `test $? -eq 1`, not the rules their `expected` text names (`replay-hidden-prereq-fails`, `program-reach-only-refused`, `routes-launch-flags-sibling`). The skills' unit tests cover the rules; the fleet evidence proves less than its `expected` line claims. Fix: pipe each to a rule assertion, as `routes-scan-finds-drift` does.
- The replay's step markers carry no nonce, so a step can print one. Since the defect 1 rewrite, completion also needs exit 0, so the inconsistent report the review showed no longer occurs; the spoofable marker remains.
- After a doc's own `set +e`, commands joined with `;` on one line are judged by the last one (documented in the skill).
- The sources ledger records the 93 samber skills as `installed-inactive` or `installed-and-verified` with model invocation disabled, and `developer-relations-kickoff/SKILL.md` carries `disable-model-invocation: true`. The router doesn't fire by itself; it loads by explicit invocation or through the path `bin/fleet resolve` returns. `roles.json` doesn't record it yet.
- Foundation scanner (`fleetlib/untrusted.py`, not this fleet's file): the widened version flags this fleet's publish line. The reviewer's planted "drop ... from the exclusions" and "change the acceptance criteria" lines weren't rechecked here. Protected-field enforcement refused every change.
