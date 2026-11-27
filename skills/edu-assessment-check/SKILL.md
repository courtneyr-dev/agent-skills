---
name: edu-assessment-check
description: "Checks that an assessment can show what its objectives claim: objectives, tasks, rubric criteria and scoring rationale line up; the task's evidence matches the objective's cognitive level; and nothing outside the intended construct gets in the way. Use whenever someone writes or reviews a rubric, quiz, lab, performance task, exit ticket, assessment blueprint or scoring guide for BCIT, CS, business or professional learning: 'check my rubric', 'is this quiz enough', 'does this assess the objective', 'is this fair', 'is this accessible'. Rejects a recall-only quiz offered for an application objective, rejects passing code or AI output as evidence of understanding, flags irrelevant reading demand, paid or brand-specific tools, internet-only access, color-only cues and time limits outside the construct, and refuses unlabeled student work. Not for executing answer keys (edu-answer-key-check) or standards mapping (edu-standards-alignment)."
license: MIT
disable-model-invocation: true
---

# Assessment alignment, validity and fairness

An assessment is evidence for a claim about learning. This skill checks that the evidence can carry the claim, and that the task measures the construct rather than reading level, tool access or speed.

## When to use and when not to

Use it on any assessment before teachers or trainers rely on it, and after changing objectives. Don't use it to score learners or to judge whether a learner understood; those stay with the teacher or trainer, using the evidence this skill confirms the task can collect.

## Inputs and prerequisites

A JSON file with `context.reading_grade_target`, `objectives` (`id`, `text`, `level` from remember, understand, apply, analyze, evaluate, create, and `construct`), `tasks` (`id`, `objective_ids`, `cognitive_level`, `evidence` from recall, explanation, product, process-trace, performance, passing-tests, ai-output, `prompt`, `demands`), `rubric` (`id`, `task_id`, `objective_id`, `criterion`, `levels` with descriptors, `scoring_rationale`) and optional `student_work`. Levels follow the revised taxonomy (Anderson and Krathwohl, 2001).

## Method

1. Run `python3 scripts/assessment_check.py check FILE`. The checker reads each prompt (and any `tools` list) as well as the labels. Where they disagree, the text wins and a `label-text-mismatch` error names the difference: a multiple-choice or definition prompt is judged recall; a prompt that collects chatbot or AI output, or only an autograder result, with no learner explanation or trace is judged output-only; a named paid tool (for example Microsoft Excel 365) or an online step raises `paid-software` or `no-offline-route` even when `demands` says otherwise.
2. Fix alignment errors first: every objective needs a task and a scoring criterion; each criterion names a task that assesses its objective and gives a scoring rationale with at least two described levels.
3. Fix validity errors: an apply-or-higher objective needs at least one task at that level that collects more than recall; an understand-or-higher objective needs evidence beyond passing tests or AI output (an explanation, trace or observed performance).
4. Resolve fairness flags without lowering the demand: reword prompts, add a free or school-provided route, an offline route, text cues alongside color, and remove time limits unless speed is the construct (`construct_is_speed`, for example keyboarding fluency).
5. Rerun until `ok` is true, then hand standards questions to `edu-standards-alignment` and keys to `edu-answer-key-check`.

## Stopping conditions

No errors and no flags, or each remaining flag is accepted by the teacher with a written reason.

## Output contract

JSON with `ok`, `errors` and `flags` (each `code`, `where`, `message`) and per-objective `level`, `tasks` and `criteria`. Exit 0 only when both lists are empty; 1 otherwise or for invalid input; 2 for usage.

## Failure states

`status: invalid` for missing lists, unknown levels or evidence kinds, or duplicate ids. The reading grade is a Flesch-Kincaid screen with a heuristic syllable count, and the prompt-text check is a keyword screen; both can miss wording they don't list, so a teacher still reads the task.

## Adapters and missing capability

None required. Real student work is refused (`unlabeled-student-work`) until `edu-student-data-guard` allows it under a verified school policy.

## References

`references/sources.md`.

## Evaluation cases

In `company-fleets/fleets/bcit-education/evals.json`: `assessment-aligned` (positive); `recall-quiz-rejected`, `passing-code-not-understanding`, `fairness-barriers-flagged`, `mislabeled-recall-quiz-rejected`, `mislabeled-ai-output-rejected`, `prompt-paid-tool-online-flagged` (negative); `speed-construct-not-flagged` (boundary). Unit tests: `scripts/tests/test_assessment_check.py`.
