# BCIT education fleet runbook

The bcit-education fleet drafts and checks public-school Business, Computer and Information Technology (BCIT) teaching work: units across the ten NBEA content areas, CS lessons, standards and credential audits, teacher-education modules and faculty research reviews. It has 19 roles, 8 workloads and 8 registered skills, and 71 script evaluation cases that pass as of 2026-11-26. Every company, classroom and learner in it is a synthetic Fixture Co fixture. No role is a teacher of record, holds a credential or acts outside the classroom.

## How work reaches this fleet

The existing router (Claude Code plus credit-routing) picks a workload; `bin/fleet resolve` returns its smallest role set. `bcit-education.program-lead` is the one coordinator for every workload here. It delegates inside the workload and never dispatches; execution ownership stays with the router, the PM layer and factory-rig. There is no academic scheduler.

| Workload | Roles | Use it for |
|---|---|---|
| `bcit-education.workload.course-unit` | program lead, curriculum and standards, accounting and finance, IT and computing, assessment, accessibility | An accounting, finance or IT unit, end to end through teacher review |
| `bcit-education.workload.business-unit` | program lead, business and management, business pathways (law, marketing, international, career), communication and productivity, curriculum and standards, assessment | A unit in the other NBEA business areas |
| `bcit-education.workload.cs-lesson` | program lead, CS classroom teacher, assessment | One runnable CS lesson and responses to supplied learner work |
| `bcit-education.workload.standards-audit` | program lead, curriculum and standards, NOCTI coordinator, ISTE coach | Standards, edition, NBEA ten-area and ISTE coverage checks |
| `bcit-education.workload.teacher-education-module` | program lead, BCIT professor, assessment, instructional coach | A methods module with microteaching, observation and calibration |
| `bcit-education.workload.faculty-review` | program lead, CS professor, BCIT professor | Research critique, study design or program evaluation |
| `bcit-education.workload.progress-feedback` | program lead, progress and feedback assistant | Feedback on learner work the teacher supplies |
| `bcit-education.workload.classroom-operations` | program lead, lab operations, classroom and family support, career and work-based learning | Lab recovery plans, routines, family-message drafts, career plans |

```bash
cd skills/company-fleets
bin/fleet resolve --profile school --workload bcit-education.workload.course-unit
```

Only the `school` profile activates this fleet. Under any other profile `resolve` refuses (case `resolve-refuses-agency-profile`).

## Skills

Written for this fleet (original, MIT in agent-skills):

| Skill | What it does | Main command |
|---|---|---|
| `edu-standards-alignment` | Registry of 23 standards records and 12 organizations; alignment, coverage and organization-reference checks | `scripts/standards_check.py align FILE` |
| `edu-answer-key-check` | Executes spreadsheet formulas, SQL, Python and calculations against the key | `scripts/answer_key.py check FILE` |
| `edu-assessment-check` | Objective, task, rubric alignment; recall-only and output-only evidence; fairness barriers | `scripts/assessment_check.py check FILE` |
| `edu-student-data-guard` | Student-data policy adapter on top of the company-fleets tenant rules | `scripts/data_guard.py check REQUEST` |
| `bcit-learning-package` | Complete BCIT unit package, checked with the three skills above | `scripts/package_check.py check package.json` |
| `cs-classroom-instruction` | Runnable CS lessons and responses to supplied learner work that never invent progress | `scripts/lesson.py check|respond` |
| `edu-learning-progression` | Prerequisite graphs and course sequences; no university concept in school without a bridge | `scripts/progression.py check FILE` |
| `edu-research-review` | Paper critique, citation verification, overclaim lint, study design and program evaluation | `scripts/research_check.py claims|design|program|citations` |

Learning Commons (learning-commons-org/agent-skills at b23623c, Apache-2.0, Copyright 2026 Anthropic, PBC and Learning Commons): skill-sync installed all five skills as complete copies in `skills/k12-*`, with LICENSE and NOTICE kept. Each copy is modified by one frontmatter line, `disable-model-invocation: true`, so the model doesn't load them on its own and a person invokes them by name; `CHANGES.md` in each folder carries the Apache-2.0 section 4(b) notice. Roles attach two of them: `k12-lesson-differentiation` (three instructor and accessibility roles) and `k12-fixing-lesson-plans` (curriculum and standards specialist). `k12-lesson-plan-creation`, `k12-lesson-prep` and `k12-check-for-understanding` are installed but attached to no role, because their scope is math, ELA, science and social studies, so they supply structure, not BCIT content.

Other adopted skills, attached by role: Magnus `web-accessibility` and `verification-methodology` (magnus919/agent-skills, MIT), and the instructional-design fleet's `edu-trainer-development`.

The addendum's proposed capabilities map to these skills: computing-education-research-review, education-research-design and bcit-program-research-review to `edu-research-review`; cs-learning-progression-design to `edu-learning-progression`; cs-classroom-instruction to `cs-classroom-instruction`; computing-assessment-validation to `edu-answer-key-check` plus `edu-assessment-check`; bcit-teacher-education and educator-professional-learning to `edu-trainer-development`.

## Standards, qualification and professional sources

Records live in `skills/edu-standards-alignment/references/`. Each was fetched on 2026-11-25; raw excerpts are in `evidence/sources/`. Student outcomes (CSTA 2026 and 2017, ISTE Students, NBEA), teacher practice (CSTA teacher 2020, ISTE Educators, Coaches, Leaders), university curricula (CS2023), state qualification (Pennsylvania certificates, CSPG 33 for BCIT PK-12, CSPG 71 for CS 7-12) and occupational assessment (NOCTI) are separate records. NBEA, NOCTI and ISTE do not jointly award a teaching license; licensure is the state's.

Rights limits the checks enforce: CSTA standards are CC BY-NC-SA, so identifiers and labels are cited and text is never bundled; ISTE allows free noncommercial educational use with attribution; NOCTI forbids incorporating blueprint content into retrieval systems or derivative materials, so no competency or item enters the rig. Pennsylvania's State Board endorsed the CSTA 2017 edition in 2018, which is why a district adoption of 2017 is kept rather than forced to 2026.

The twelve organizations (CSTA, ACM SIGCSE, ACM SIGCITE formerly SIGITE, NBEA CBTR, ACTE Business Education Division, SIEC-ISBE, AIS SIGED, ISCAP, PBEA, ISTE+ASCD, AERA, AECT) are knowledge sources only: not installable, no membership held or inferred, no enrolling, paying, submitting or contacting.

## Acceptance checks and where their evidence is

| Prompt check | Cases (in `evals.json`) | Evidence |
|---|---|---|
| Missing, protected or unsupported standards yield a gap | `standards-honest-gaps-pass`, `missing-standard-is-a-gap`, `standards-overclaim-rejected` | `evidence/edu-standards-alignment/` |
| Student/teacher mix-up, wrong edition, district adoption kept | `standards-mixup-and-edition-caught`, `district-adoption-preserved` | same |
| NBEA ten areas; computing-only fails | `nbea-ten-areas-covered`, `computing-only-not-bcit` | same |
| Professional-source accuracy | `org-sources-cited-correctly`, `org-credential-claims-rejected`, `source-registries-valid` | same |
| Assessment alignment; labeled synthetic work | `assessment-aligned` | `evidence/edu-assessment-check/` |
| Recall-only quiz rejected for an application objective | `recall-quiz-rejected` | same |
| Passing code or AI output is not understanding | `passing-code-not-understanding`, `cs-passing-code-not-evidence`, `cs-ai-output-not-evidence` | same and `evidence/cs-classroom-instruction/` |
| Fairness barriers flagged, construct kept | `fairness-barriers-flagged`, `speed-construct-not-flagged` | `evidence/edu-assessment-check/` |
| Answers executed; intentionally incorrect solution caught | `unit-answer-key-executes`, `incorrect-solution-caught`, `unsupported-formula-not-passed`, `teacher-module-*-key-*`, `cs-wrong-answer-key-caught` | `evidence/edu-answer-key-check/`, `evidence/bcit-teacher-education-module/` |
| BCIT unit with complete materials | `store-unit-package-complete`, `incomplete-package-rejected` | `evidence/bcit-learning-package/` |
| CS teacher lesson and supplied learner work | `cs-lesson-runs-complete`, `cs-feedback-quotes-off-by-one`, `cs-empty-work-awaits`, `cs-teacher-waits-for-learner` | `evidence/cs-classroom-instruction/` |
| BCIT teacher-education module | `teacher-education-module-complete`, `teacher-module-merged-evidence-rejected` | `evidence/bcit-teacher-education-module/` |
| CS paper critique with verified citations | `research-professor-paper-critique`, `research-real-paper-citations-replay` | `evidence/edu-research-review/critique-kazemitabaar-2023.md` |
| Research overclaim | `research-overclaim-rejected`, `research-higher-ed-transfer-flagged` | `evidence/edu-research-review/` |
| Tenant boundaries (classroom A vs B) | `classroom-b-roster-refused`, `same-classroom-synthetic-allowed`, `external-roster-send-refused`, `real-records-stop-at-boundary`, `inline-principal-refused`, `requester-policy-file-rejected` | `evidence/edu-student-data-guard/` |
| Labels can't hide a weak assessment | `mislabeled-recall-quiz-rejected`, `mislabeled-ai-output-rejected`, `prompt-paid-tool-online-flagged` | `evidence/edu-assessment-check/` |
| Invented ids that fit the format | `invented-wellformed-ids-rejected` | `evidence/edu-standards-alignment/` |
| Untrusted lesson resource | `lesson-resource-injection-flagged` | same |
| Selective loading | `resolve-course-unit`, `resolve-business-unit`, `resolve-classroom-operations` | `evidence/routing/` |

## Handoffs

Professors set or review research, curriculum and pedagogical rationale; they join only through `faculty-review` or `teacher-education-module`, for research, program design, consequential assessment changes or uncertain pedagogical claims. Classroom roles turn approved objectives into lessons and return actual implementation evidence, which only the teacher collects. The instructional-design fleet packages materials and delivery formats. Every handoff uses `handoff.v1`; untrusted content is scanned with `bin/fleet scan` and stays data.

## The human-data boundary

The rig produces drafts, executed keys and checks. It does not produce learner answers, observations, grades, agreement statistics or learning gains, and it refuses real student records: `skills/edu-student-data-guard/references/school-policy.json` authorizes nothing until a named person verifies the actual school's tools, role access, consent basis and retention.

## Rerun everything

```bash
cd skills/company-fleets
python3 fleets/bcit-education/evalrun.py run --file fleets/bcit-education/evals.json --write
bin/fleet validate --strict --fleet bcit-education
for s in edu-standards-alignment edu-answer-key-check edu-assessment-check edu-student-data-guard \
         bcit-learning-package cs-classroom-instruction edu-learning-progression edu-research-review; do
  (cd ../$s/scripts/tests && python3 -m unittest discover -p 'test_*.py')
done
```

`evalrun.py run --write` replaces each case's retained evidence and records pass or fail. Without `--write` it writes to a scratch folder it prints, so you can compare a rerun against the retained output first. `requirements-map.json` proposes a status for each of the 96 education requirement rows for the integrator to apply.

## States and open items

- Roles: 19 reference-only records (no native agent definitions), none activated by the router, all behaviorally unverified. Each has at least one role-targeted script case that passed on synthetic fixtures, but the fleet's builder graded those scripted skill checks and no independent grader has judged persona behavior, so `validate --strict` refuses a verified claim (it needs a `grader` who is neither the builder nor the role).
- Skills: 8 installed (unit tests pass on Python 3.9.6 and 3.14.7), none activated, each behaviorally verified on synthetic cases only.
- NBEA and PBEA pages refused automated fetches (HTTP 403 and 406). Resume: a person opens each page in a browser and records edition, access and license in the registry.
- No NOCTI credential is selected, no district or teaching assignment is known, and the Pennsylvania BCIT academic standards edition is unverified, so those mappings stay gaps.
- Coverage is `partial` for nine roles whose areas have no demonstrated unit or procedure yet (for example work-based-learning placement, family-language support, lab inventory).

## Review fixes (2026-11-26)

An independent review (`company-fleets/evidence/reviews/education.md`) found 3 majors; each now has a failing-first test and retained before-and-after output in `evidence/review-fixes/`.

- `edu-student-data-guard` resolved inline principal and record objects as given, and took `--policy` and `--tenants` from the requester. It now accepts ids only, reads the policy and tenants only from fixed paths, and treats a policy as verified only with a `human:` verifier, a date and an evidence file that exists. Since the foundation's tenancy change on 2026-11-26, grants come only from the owner file `references/owner-grants.json` (a grant on the record counts for nothing), and another classroom's student records stay refused whatever the grant.
- `edu-assessment-check` judged only declared labels. It now reads the prompt and any `tools` list: recall wording, chatbot or autograder-only collection, named paid tools and online steps override the labels.
- `edu-standards-alignment` accepted any well-formed identifier. The registry now stores the published ids (identifiers only, cited under CSTA's CC BY-NC-SA and ISTE's noncommercial terms), and a human review counts only when its evidence file exists.

## Follow-ups

Minor findings from the same review, not fixed yet:

- `bcit-learning-package`: learning gains written into the teacher guide's prose (for example "28 students raised their scores by 40%") pass; only the structured `learning_evidence` block is checked. Lint the Markdown files for outcome claims.
- `edu-answer-key-check`: a SQL `setup` can `ATTACH` a database file on disk, so "sqlite3 in memory" isn't enforced. Deny `SQLITE_ATTACH` with `Connection.set_authorizer`.
- `edu-answer-key-check`: an unsupported formula in a cell the target never evaluates passes silently. List unchecked cells in the result.
- `company-fleets` scanner (`scripts/fleetlib/untrusted.py`, foundation code): a zero-width space inside "ignore prior instructions" and an instruction hidden in a link title evade it. Normalize Unicode format characters and scan link titles; owner is the foundation workstream.
- `edu-standards-alignment/references/organizations.json`: NBEA itself isn't registered, only NBEA CBTR, so `{"name": "NBEA"}` fails `org-refs`. Add an NBEA record once a person verifies nbea.org in a browser.
- `fixtures/bcit-unit-store/alignment.json`: the ISTE 1.5 row names `human:teacher-of-record` while the label says no human reviewed the mappings. Remove the reviewer from that row.
- Learning Commons notices: make `CHANGES.md` survive upstream updates by registering it as an overlay, for example `python3 skills/skill-sync/sync_skills.py keep k12-lesson-prep CHANGES.md --append-to SKILL.md` for each of the five skills (this writes sources.json, so the integrator runs it).
