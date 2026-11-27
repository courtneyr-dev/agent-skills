---
name: edu-trainer-development
description: "Develops trainers, facilitators and teachers: facilitation guides with design rationale, complete modeled examples with decision points, observation and specific feedback, rubric calibration, fading support, coaching another trainer to adapt a method, and plans to collect actual learning and transfer evidence. Use whenever someone asks for a train-the-trainer or trainer-of-trainers package, a facilitation guide, rubric calibration or norming, inter-rater agreement, a teacher professional-learning plan, a methods-course module, microteaching, an observation instrument or coaching cycle, or asks how to show training worked. Refuses to report agreement from generated ratings and refuses evidence plans built on satisfaction surveys or pre-filled results."
license: MIT
disable-model-invocation: true
---

# Trainer development

Helps someone who teaches (a trainer, facilitator, teacher or teacher educator) get better at it, and plans how to find out whether it worked. A generated lesson, a happy survey or a generated calibration example isn't proof of learning, transfer or reviewer agreement; this skill keeps those apart.

## When to use, and when not

Use for train-the-trainer packages, facilitation guides, rubric calibration, coaching cycles, educator professional learning, and BCIT teacher-education modules (methods course, microteaching, observation and coaching; see `references/teacher-education.md`).

Don't use it to decide whether training is the remedy: run `edu-needs-analysis` first. Don't use it to grade, place, certify or evaluate a person for employment: human supervisors and managers own those decisions. Don't invent observations, ratings, survey results or gains to complete a package; stop at the human-data boundary and leave result fields empty.

## Inputs and prerequisites

- The learner task the trainer teaches, and a needs analysis that found a real skill gap.
- A rubric whose descriptors name observable features, or the task to write one.
- Who the human owners are: the lead or coach, the reviewers, the person who collects real data.
- For a teacher-education module: the business task, the computing practice and its answer key.

## Method

Follow `references/procedures.md` for each step.

1. Explain why each design choice fits the learner task (a rationale table: choice, why it fits).
2. Model a complete example and say each decision point aloud.
3. Plan observation of actual practice with a focus list; feedback names the moment, the criterion, its effect and one next move, written only from what was observed.
4. Calibrate the rubric: reviewers rate generated practice anchors alone, compare, discuss descriptor words. `scripts/agreement.py stats` returns practice-only for generated ratings; it computes agreement only from real `human-rated` ratings by `human:<id>` raters.
5. Fade support on demonstrated competence, with the observed signal for each step down.
6. Coach another trainer to adapt the method: they restate the task, justify each design choice, build their own modeled example and name their evidence.
7. Plan transfer evaluation with `scripts/evidence_plan.py check`: measures with a human owner, timing and baseline, a human-data boundary, a revisit rule, and no results filled in.
8. Check the whole package with `scripts/package.py check manifest.json`.

## Stopping conditions

- `package.py` returns `complete`: hand the package to its human owner.
- Any finding: fix the package; don't remove a required section to pass.
- Real data needed (ratings, observations, outcomes): stop and hand the plan to the named human owner.

## Output contract

All three scripts print JSON. Exit 0 ok, 1 refused or findings, 2 invalid input or usage.

- `agreement.py stats RATINGS.json`: `status` is `computed` (per rater pair: `n_items`, `exact_agreement`, `adjacent_agreement`, `kappa`, `weighted_kappa_quadratic`, `notes`) or `practice-only` (`message`, `reasons`). Both list `discussion` items where ratings differ or miss the anchor.
- `evidence_plan.py check PLAN.json`: `status` accepted or rejected, `findings`, `warnings`, `evidence_measures`, `transfer_measures`.
- `package.py check MANIFEST.json`: `status` complete or incomplete, `findings`, plus the calibration and evidence-plan status and, for a teacher-education module, each evidence line's status.

Manifest kinds: `trainer-package` (guide, rubric, calibration exercise, calibration ratings, evidence plan) and `teacher-education-module` (those plus observation instrument, answer key, four separate `evidence_lines` and `iste_educator_labels`).

## Failure states

- Generated or synthetic ratings: practice-only, never an agreement figure.
- Fewer than 10 shared items: the figure carries a note that it's a calibration signal, not a reliability estimate.
- A plan whose only evidence is a survey, attendance, completion, a self-report or a generated artifact: rejected.
- Pre-filled outcome values anywhere in a plan: rejected.
- A synthetic package carrying observation records, or a teacher module inferring one evidence line from another: incomplete.

## Adapters and missing capability

No adapter is required. Real ratings and observations come from the people who collect them (an LMS export, a supervisor's form). Without them, the package stays a plan and its result fields stay empty. Answer keys in teacher-education modules are executed with `edu-answer-key-check`; without it, mark the key unverified.

## References

- `references/procedures.md`: the seven trainer-of-trainers procedures in detail.
- `references/teacher-education.md`: methods course, microteaching, observation and coaching; educator professional learning.
- `references/sources.md`: editions, DOIs and rights.

## Evaluation cases

Fixtures: `company-fleets/fleets/instructional-design/fixtures/edu-trainer-development/` (trainer package and counterexamples) and `company-fleets/fleets/bcit-education/fixtures/bcit-teacher-education-module/` (BCIT module). Positive: the complete package and module pass; the evidence plan is accepted. Negative: survey-only and pre-filled plans are rejected; the counterexample package and the merged-evidence module are incomplete. Boundary: generated calibration ratings return practice-only. Unit tests: `cd scripts/tests && python3 -m unittest`.
