---
name: cs-classroom-instruction
description: "Use when a school computer science teacher (PK-12, usually grades 6-12) needs a complete runnable lesson or lab, or needs feedback on learner code, predictions or traces they actually supplied. Builds the teacher guide, runnable examples with expected outputs, student tasks, misconception probes, rubric, answer rationale, accessibility checks and reteaching or extension, then executes every example and reference solution so wrong answer keys are caught. Responds to supplied learner work with feedback that quotes the learner's actual output, and never invents a response or claims progress. Use it for 'CS lesson', 'coding lab', 'Python lesson for grade 9', 'my student's code prints 42', 'give feedback on this submission', even when the teacher doesn't say 'lesson package'. Not for university course design (use edu-learning-progression with a bridge) or grading decisions, which stay with the teacher."
license: MIT
disable-model-invocation: true
---

# CS classroom instruction

A dedicated school CS teaching procedure. It builds a lesson package you can run and check, and it
answers real learner work with specific, executed feedback. The teacher of record keeps every
consequential decision: grades, placement, accommodations and what counts as mastery.

## When to use and when not to

Use it to build or repair a CS lesson or lab for a recorded grade band, and to respond to work a
learner actually submitted.

Don't use it to:
- Invent learner answers, observations, grades or learning gains. With no supplied work, the answer is "awaiting learner response".
- Treat passing tests, typing speed, memorized syntax, polished AI output or prior computing access as evidence of understanding.
- Claim a teaching assignment, certificate or standards alignment you haven't verified. Record them as unverified.
- Copy CSTA standards text. Cite the label and the link; the standards use a noncommercial share-alike license.
- Apply university (CS2023) expectations to school learners without a bridge; route that to edu-learning-progression.
- Handle real student records. Fixtures are synthetic; real records go through the school's approved process.

## Inputs and prerequisites

- Objective, grade band, prior knowledge, duration and the actual environment (devices, network, approved tools).
- The teaching assignment status. In Pennsylvania, CSPG 71 (Computer Science 7-12) is the staffing guideline; the school confirms the real assignment.
- For `respond`: the learner's actual work as JSON (code, prediction, explanation or trace).
- Python 3.9+ to run `scripts/lesson.py`. Shapes: `references/data-shapes.md`.

## Method

Follow this teaching sequence. Each step maps to a field in the lesson JSON.

1. **Objective and prior knowledge.** State one observable objective and the prior knowledge it rests on (`objective`, `context.prior_knowledge`).
2. **Complete example.** Show a meaningful, finished program and how its parts relate (`examples`, each with `expected_output`).
3. **Learner acts.** Ask the learner to predict, trace, modify, explain or construct (`tasks[].kind`).
4. **Wait.** Stop for the actual response (`teacher_guide.wait_points`). Don't continue as though the learner finished.
5. **Specific feedback.** Run `lesson.py respond` on the supplied work. Feedback quotes what the program printed and names one next action.
6. **Adjust support.** Use `teacher_guide.decision_points` and misconception probes to choose reteaching or extension.
7. **Transfer.** Include a `transfer` task: the same idea on a new problem.

Choose the language and tool from the objective, the learners' age and access needs, and the real
environment, and write that reason in `language_rationale`. Don't impose one language on every course.

Then prove the package:

```bash
python3 scripts/lesson.py check lesson.json             # runs every example and reference solution
python3 scripts/lesson.py respond lesson.json work.json # feedback on supplied work
python3 scripts/lesson.py respond lesson.json           # no work supplied: awaiting-learner-response
```

## Stopping conditions

- `check` returns `"ok": true`: every example and reference solution printed its stated output and every required section is present.
- `respond` returned one status for the supplied work. Stop there; the next step waits for the learner.
- Budget reached or the environment can't run Python: deliver the package marked unexecuted and say so.

## Output contract

`check` prints `{"ok", "errors", "examples", "task_runs", "note"}`. Each error names the example,
task or test, the stated answer and the executed one.

`respond` prints `{"status", "feedback", "next_action", "tests", "misconceptions", "progress_claim": null}`.
Status is one of:

| Status | Meaning |
|---|---|
| `awaiting-learner-response` | No work, or empty work. No feedback, no progress claim. |
| `tests-failing` | At least one test failed; feedback quotes the actual output and any matched misconception. |
| `prediction-differs` | A prediction task where the learner's prediction differs from the executed output. |
| `not-yet-evidence-of-understanding` | Tests pass, but there's no explanation or trace, the trace leaves out running values, or the work is marked AI-generated. |
| `ready-for-teacher-review` | Tests pass and the trace names every running value. The teacher judges understanding. |

`progress_claim` is always `null`. The script never records mastery.

## Failure states

- Exit 2 `invalid input`: unreadable JSON, a non-object, learner work without a `task_id`, or a task the lesson doesn't define.
- Exit 1 from `check`: findings such as a wrong stated output, a rubric that accepts passing code as sufficient, a teacher standard cited for a student objective, bundled standards text, a missing unplugged or low-bandwidth alternative, or no transfer task.
- Learner code that loops forever times out after 5 seconds and is reported as a failing test.

## Adapters and missing capability

| Adapter | Kind | Required | Notes |
|---|---|---|---|
| Local Python 3 | cli | yes | Runs examples and learner code with `python3 -I`, a temp directory, a minimal environment and a timeout. This is process isolation, not a sandbox. |
| School sandbox or LMS autograder | cli | no | Run real learner code there. Without it, use only synthetic or teacher-supplied work. |
| Learning Commons k12 skills | document | no | See below. |

The installed Learning Commons skills (`k12-lesson-plan-creation`, `k12-lesson-differentiation`,
`k12-lesson-prep`, `k12-check-for-understanding`, `k12-fixing-lesson-plans`; pinned commit
`b23623c`, Apache-2.0, copyright Anthropic, PBC and Learning Commons, terms in each skill's
LICENSE and NOTICE) cover math, ELA, science and social studies. CS is outside their subject routing,
and the check-for-understanding skill is math-only. Reuse their general practices by invoking them,
never by copying files: asset-based language, the observation template, and tiering an existing
lesson with `k12-lesson-differentiation` while keeping the CS objective's demand. The CS examples,
probes, tests and responder here are original.

Without Python, write the package and mark every expected output "not executed"; never present an
unexecuted answer key as checked.

## References

`references/sources.md` lists each source with version and rights: CSTA K-12 CS Standards (2026
edition, student outcomes) and CSTA Standards for CS Teachers (2020, teacher practice) as separate
records, CS2023 for university scope, and Pennsylvania CSPG 71. Live verification dates live in the
standards registry of `edu-standards-alignment`. `references/data-shapes.md` documents the JSON.

## Evaluation cases

Fixtures and evidence sit in `company-fleets/fleets/bcit-education/fixtures/cs-classroom-instruction/`
and `.../evidence/cs-classroom-instruction/`. Cases: a complete lesson passes `check`; a lesson with
two wrong answers is rejected; a rubric that accepts passing code is rejected; supplied learner work
(off-by-one, passing without explanation, AI-generated, full trace, empty, wrong prediction) gets the
matching status; no work returns `awaiting-learner-response`. Unit tests: `scripts/tests/test_lesson.py`.
