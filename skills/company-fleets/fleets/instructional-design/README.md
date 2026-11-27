# Instructional design fleet runbook

The instructional-design fleet decides whether instruction fixes a performance problem, then designs and checks learning for schools, client enablement, DevRel, product onboarding and internal professional development. It has 11 roles, 3 workloads and 2 registered skills, and draws on 4 skills the BCIT fleet registers. 16 script evaluation cases pass as of 2026-11-26; 1 case is blocked and 1 is not run. Every organization and learner in it is a synthetic Fixture Co fixture.

## How work reaches this fleet

The `school`, `agency` and `devrel` profiles activate this fleet. `instructional-design.learning-experience-architect` is the one coordinator for every workload; it delegates inside the workload and never dispatches. The router, PM layer and factory-rig keep execution ownership.

| Workload | Roles | Use it for |
|---|---|---|
| `instructional-design.workload.needs-analysis` | learning-experience architect, performance consultant, SME interviewer | Any request for training, a course or a workshop, before design starts |
| `instructional-design.workload.course-build` | architect, curriculum architect, SME interviewer, assessment and evaluation, writer and editor, accessible media, interactive developer; localization reviewer added under `agency` and `devrel` | A course or module once needs analysis supports instruction |
| `instructional-design.workload.trainer-development` | architect, facilitation lead, assessment and evaluation, learning analytics | Facilitation guide, rubric calibration and a plan to collect actual learning evidence |

```bash
cd skills/company-fleets
bin/fleet resolve --profile devrel --workload instructional-design.workload.trainer-development
```

## Process and its rationale

1. Needs analysis first (`edu-needs-analysis`). Missing knowledge or practice is diagnosed separately from tools, process, incentives, feedback and access, following Mager and Pipe's performance analysis and Gilbert's Behavior Engineering Model. A nontraining cause routes to its owner, not to a course (cases `nontraining-routes-to-process-tool`, `requested-workshop-not-recommended`). Missing evidence returns the questions to ask (`unsourced-evidence-collects-questions`).
2. Backward design: intended performance, then acceptable evidence (`edu-assessment-check` blueprint), then practice and support.
3. ADDIE organizes the work (analyze, design, develop, implement, evaluate) because each phase ends in an artifact this fleet can check, and implementation is a human step the sponsor owns. Iterative development is fine inside design and develop; the checks stay the same.
4. Evaluation plans collect actual learning and transfer evidence (`edu-trainer-development/scripts/evidence_plan.py`). A satisfaction survey, attendance or a generated artifact alone is refused, and so is any plan with outcome values filled in before data exists.

## Skills

| Skill | Owner fleet | What it does |
|---|---|---|
| `edu-needs-analysis` | instructional-design | Routes a performance problem to training or to nontraining remedies, with audience and task analysis when training is indicated |
| `edu-trainer-development` | instructional-design | Facilitation guides, modeled examples, observation, rubric calibration (agreement computed only from real `human:` ratings), evidence plans, teacher-education mode |
| `edu-assessment-check` | bcit-education | Blueprint alignment, evidence validity and fairness barriers |
| `edu-learning-progression` | bcit-education | Curriculum maps and prerequisite graphs |
| `edu-answer-key-check`, `bcit-learning-package` | bcit-education | Used when a module carries executable answers or a school unit |

Adopted upstream skills attached by role: `web-accessibility` and `verification-methodology` (magnus919/agent-skills, MIT), `docs-localization-strategy` and `technical-video-script` (samber/developer-relations-skills, MIT, Samuel Berthe), `unslop` (pstack). The two samber skills are written for developer docs and video, so the roles note them as adapted fits.

## DaRL instructional-agents pipeline: inspected, not installed

Inspected at DaRL-GenAI/instructional_agents-skills commit c8d3a36 (MIT, Copyright 2026 DaRL-GenAI) and DaRL-GenAI/instructional_agents commit c19c6a5 (MIT). `wateryqz/instructional_agents112` is kept as a provenance reference only.

| Wrapper | Needs | Status on the reference installation |
|---|---|---|
| `course-generate` | `pip install instructional-agents`, `OPENAI_API_KEY`, default model `gpt-4o-mini`, 20 to 60 minutes per run | Blocked: the rig does not switch to API billing or accept that default |
| `slide-evaluate` | Same package and key, default `gpt-4o-mini` | Blocked for the same reason |
| `latex-compile` | `pdflatex` or `xelatex` on PATH | Blocked: no LaTeX toolchain installed |
| `latex-to-pptx` | Python 3.11+ with `instructional-agents`, Node `pptxgenjs` installed globally | Blocked: package not installed; a global npm install is outside this build |

`course-generate` and `latex-compile` are attached to the learning-experience architect as blocked skills, so the router can see them without activating a second orchestrator. If a supported provider path is added later, wrap one stage at a time as a bounded task under the architect. The ADDIE pipeline's published results come from higher-education course generation (EACL 2026, aclanthology.org/2026.eacl-long.191); they do not establish quality for K-12 BCIT or workplace learning.

## Outputs and what is still missing

Delivered: needs assessment with audience and task analysis, curriculum map and prerequisite graph, objectives and assessment blueprint, facilitator and learner materials for the trainer package, accessibility review through WCAG 2.2 checks, and an evaluation plan with owners and baselines.

Not delivered, with the reason:

- Storyboards, captions and transcripts: no captioning or transcription tool and no storyboard procedure.
- Delivery and export package: no target LMS or QTI/CASE consumer is named. CASE 1.1 and QTI 3.0 are registered in the standards registry; use one only when the target supports that version, and validate with an actual import (case `lms-export-needs-target`, blocked).
- Linguistic review of translations stays with a human reviewer (case `linguistic-review-stays-human`, not run).
- Quality Matters K-12 (Sixth Edition, 2025) is an optional design reference; formal reviews belong to QM.

## The trainer-development package

`fixtures/edu-trainer-development/` holds the synthetic package: facilitation guide, rubric with generated practice anchors, calibration exercise and evidence plan. Generated calibration ratings prepare reviewers; `agreement.py` reports "practice-only" for them and computes exact, adjacent and Cohen's kappa only from real reviewer ratings, which no one has collected yet.

## Rerun everything

```bash
cd skills/company-fleets
python3 fleets/bcit-education/evalrun.py run --file fleets/instructional-design/evals.json --write
bin/fleet validate --strict --fleet instructional-design
for s in edu-needs-analysis edu-trainer-development; do (cd ../$s/scripts/tests && python3 -m unittest discover -p 'test_*.py'); done
```

## States

- Roles: 11 reference-only records, none activated, all behaviorally unverified. Nine have a role-targeted script case that passed on synthetic fixtures, but the fleet's builder graded those scripted skill checks and no independent grader has judged persona behavior, so `validate --strict` refuses a verified claim. The localization reviewer and interactive developer have only routing-only or blocked cases.
- Skills: 2 installed (unit tests pass on Python 3.9.6 and 3.14.7), none activated, each verified on synthetic cases only.
- No learner, participant or reviewer data exists here. Transfer and agreement stay unmeasured until real people supply them.
