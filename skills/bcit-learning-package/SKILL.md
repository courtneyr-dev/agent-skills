---
name: bcit-learning-package
description: "Builds and checks a complete Business, Computer and Information Technology (BCIT) learning package for a public-school course unit: observable objectives, honest standards references, teacher guidance, student materials, a worked example, practice, checks for understanding, rubric with answer rationale, misconceptions, accessibility and differentiation that keep the learning demand, an offline route, and reteaching and teacher review points. Use when a teacher or the BCIT fleet asks for a unit, lab, lesson sequence or course module in accounting, personal finance, entrepreneurship, marketing, management, business law, international business, career development, business communication, digital productivity, IT, databases, web or cybersecurity. Runs the assessment, answer-key and standards checks on its own files and refuses learning gains no one collected. Not for CS interactive teaching (cs-classroom-instruction) or generic K-12 math, ELA, science or social studies (Learning Commons k12 skills)."
license: MIT
disable-model-invocation: true
---

# BCIT learning package

The instructional cycle for one unit: context and prerequisites, measurable objectives, standards mapping, authentic assessment, lesson and lab sequence, instruction, learner response, feedback and reteaching, assessment review, revision. The rig drafts the artifacts and checks them; the teacher of record teaches, collects the learning evidence and decides.

## When to use and when not to

Use it for BCIT units across the ten NBEA content areas, with authentic business and computing tasks on age-appropriate synthetic data isolated from production services. Don't use it to stand in for the teacher of record, to infer diagnoses or fixed learning styles, or to produce learner answers, observations, grades or gains.

## Inputs and prerequisites

- Course, grade band, duration, resources and technology constraints from the teacher. Teaching assignment and certification are recorded as unverified until a person confirms them (Pennsylvania CSPG 33 covers BCIT; CSPG 71 covers CS 7-12).
- Sibling skills installed: `edu-assessment-check`, `edu-answer-key-check`, `edu-standards-alignment`.

## Method

1. Draft objectives with a level (apply, analyze, evaluate for authentic tasks) and a construct.
2. Map standards in `alignment.json` with `edu-standards-alignment`; keep gaps as gaps.
3. Write the assessment first (backward design), then the teacher guide, student materials and worked example. Use the headings the manifest points to.
4. Work the key by hand, then write `answer-key.json` for execution.
5. Write `package.json` (see the demo below) and run `python3 scripts/package_check.py check package.json`.
6. Fix every error. A `partial` standards note stays on the label until a teacher verifies mappings.

Reuse from Learning Commons (external: install from its repository; Apache-2.0, LICENSE and NOTICE kept in each skill folder): `k12-lesson-differentiation` for tiered versions and `k12-fixing-lesson-plans` for an audit pass. Their subject scope is math, ELA, science and social studies, so they don't supply BCIT content, and `k12-check-for-understanding` is math-oriented; use them for structure, not as BCIT coverage. A test run recorded that `k12-lesson-plan-creation`'s HTML renderer failed on its own example and its DOCX renderer needs python-docx, so this skill emits Markdown and JSON.

## Stopping conditions

`package_check` returns `ok: true`, or each remaining error is reported to the teacher as a blocker with its fix.

## Output contract

A package folder with `package.json`, teacher guide, student materials, worked example, `assessment.json`, `answer-key.json` and `alignment.json`. `package_check` prints JSON with `ok`, `errors` (code, message), `notes` and the results of the three sibling checks. Exit 0 ok, 1 findings or invalid, 2 usage.

## Failure states

`file-missing`, `section-missing`, `context-missing`, `demand-lowered`, `invented-learning-evidence`, `<check>-failed`, `missing-capability` (a sibling skill is not installed; never a pass).

## Adapters and missing capability

No LMS, gradebook or student-information system is connected. Delivery stays with the teacher. Without a sibling skill, that part of the package is reported unchecked.

## References

`references/sources.md`. Demo package: `company-fleets/fleets/bcit-education/fixtures/bcit-unit-store/` (synthetic Fixture Co student-run store unit).

## Evaluation cases

In `company-fleets/fleets/bcit-education/evals.json`: `store-unit-package-complete` (positive); `incomplete-package-rejected` (negative); `missing-sibling-is-missing-capability` (boundary). Unit tests: `scripts/tests/test_package_check.py`.
