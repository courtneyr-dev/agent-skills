---
name: edu-needs-analysis
description: "Decides whether instruction addresses a performance problem before anyone designs a course, workshop, module or e-learning. Use whenever someone asks for training, a course, onboarding or a workshop to fix a performance problem (missed deadlines, skipped steps, errors, low adoption), asks for a needs assessment, performance analysis, audience or task analysis, or asks 'do we need training for this?'. Separates missing knowledge or practice from tools, process, access, feedback, expectations and incentives, and routes nontraining causes to their owners instead of a course. Not for designing the course itself once training is indicated."
license: MIT
disable-model-invocation: true
---

# Needs analysis: does instruction fix this?

A course fixes a gap in knowledge or practice. It doesn't fix a broken tool, a blocked approval, missing access, unclear expectations, absent feedback or a scorecard that punishes the right behavior. This skill finds which cause the evidence supports before anyone builds instruction.

## When to use, and when not

Use when a request names a performance problem and proposes training, or when a needs assessment, audience analysis or task analysis is asked for. It serves schools, client enablement, DevRel, product onboarding and internal professional development.

Don't use it to design the course after training is indicated: hand the route to the learning-experience architect. Don't diagnose individuals: no medical, psychological or learning-style inferences, and no judgments about a named person's capacity. Don't contact performers, managers or clients; the skill reads evidence you're given.

## Inputs and prerequisites

A case JSON file:

- `problem`: the observed discrepancy, with numbers where you have them.
- `audience`: `who` is required; `size`, `context` and `access_needs` feed the audience analysis.
- `task`: `name` and `steps` are required; `frequency`, `criticality` and `conditions` feed the task analysis.
- `evidence`: one entry per diagnostic question, each `{"value": true|false|null, "source": "..."}`. Keys: `can_do_when_required`, `did_it_before`, `performed_often`, `expectations_clear`, `feedback_given`, `tools_adequate`, `process_clear`, `access_ok`, `consequences_aligned`.
- `requested_solution` (optional): what the requester asked for, such as "course".

Read `references/diagnostic-questions.md` for what each key asks and what counts as evidence.

## Method

1. Write the discrepancy as observed performance against expected performance. If you can't, stop and collect it.
2. Fill the audience and task analysis from the request; list what's missing rather than guessing.
3. Answer each diagnostic question only from a named source: an observation, a system log, a work sample, an interview. A value without a source counts as missing.
4. Run `python3 scripts/needs.py route case.json`.
5. Report the route in the output contract below. When the requester asked for a course and the route says no course, say so plainly and name each remedy's owner.

## Stopping conditions

- `status: route` or `no-gap-found`: stop and hand the result on.
- `status: collect-evidence`: stop and return the open questions. Don't route on a guess.
- Invalid input (exit 2): fix the case file; don't loosen the checks.

## Output contract

`scripts/needs.py` prints JSON with these keys:

- `status`: `route`, `no-gap-found` or `collect-evidence`.
- `course_indicated`: `true` only for a skill the performer never had; `false` when the performer can already do the task or the skill faded; `null` while the skill question is open.
- `remedies`: each with `code`, `factor`, `remedy` and `because` (the evidence source). Codes: `SKILL-TRAINING`, `SKILL-PRACTICE`, `SKILL-FEEDBACK`, `ENV-INFO-EXPECTATIONS`, `ENV-INFO-FEEDBACK`, `ENV-RESOURCE-TOOL`, `ENV-RESOURCE-PROCESS`, `ENV-RESOURCE-ACCESS`, `ENV-INCENTIVE`.
- `questions`: the diagnostic questions still open.
- `not_recommended`: the requested course, when the evidence rules it out or defers it.
- `notes`, `warnings`: transfer risks and unsourced values.
- `audience_task_analysis`: the audience and task as given, plus `analysis_gaps`.

Exit 0 route decided, 1 evidence missing, 2 invalid input or usage.

The written report adds: the discrepancy, the audience and task analysis, each remedy with its owner, and what would change the route.

## Failure states

- No observed discrepancy: return collect-evidence with the discrepancy as the first question.
- Self-report only for `can_do_when_required`: record it as missing; ask for an observed attempt.
- Requester insists on a course the evidence rules out: report the route and the requester's decision separately; the requester owns that choice.

## Adapters and missing capability

No adapter is required; the script reads a local file. Evidence comes from whoever holds it (LMS reports, ticket logs, observation notes). Without that access, return the questions and stop at the human-data boundary.

## References

See `references/sources.md` for editions and rights. The method paraphrases Mager and Pipe's performance analysis and Gilbert's Behavior Engineering Model; no text or figures are copied.

## Evaluation cases

Fixtures live in `company-fleets/fleets/instructional-design/fixtures/edu-needs-analysis/` (synthetic, Fixture Co). Cases: a tool and process obstacle routes away from a course (positive), a real skill gap routes to training (positive), a requested workshop for an incentive problem is not recommended (negative), and a request with no sourced evidence returns questions (boundary). Unit tests: `cd scripts/tests && python3 -m unittest`.
