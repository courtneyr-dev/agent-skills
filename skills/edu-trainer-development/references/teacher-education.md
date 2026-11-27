# Teacher-education mode

Covers two capabilities from the education addendum: `bcit-teacher-education` (methods course, microteaching, observation and coaching package) and `educator-professional-learning` (competency gap, source-backed development path, practice task, evidence of improvement). The trainer-of-trainers procedures in `procedures.md` apply; this file adds what teacher preparation needs.

## Methods-course module

A module teaches candidates to teach one piece of subject content. It contains, in this order:

1. Context: candidate audience, grade band they'll teach, duration, prerequisites, resources, low-bandwidth alternative.
2. Authentic business task: a real-world decision the calculation feeds (a pricing decision, a staffing schedule, a budget), done first by candidates as learners.
3. Computing practice: the spreadsheet, query or code work the task needs, with an answer key checked by execution (`edu-answer-key-check`), including at least one deliberately wrong key or solution the check must catch.
4. Pedagogical rationale: a table tying each teaching choice to the task and to a named misconception.
5. Microteaching cycle: plan, teach peers, observe, feedback, reteach.
6. Observation instrument: items with look-fors, each tied to one evidence line; no observations recorded until a human observer fills it.
7. Assessment criteria: a rubric with one evidence line per criterion and generated practice anchors.
8. Calibration exercise for supervisors.
9. Evidence lines (below).
10. Standards and sources: labels only (NBEA content areas, ISTE Educator roles), no standard text, alignment marked unverified until a reviewer with access checks it.
11. Supervisor decisions: placement, qualification, certification recommendations and grades stay with human supervisors.

`scripts/package.py check` with kind `teacher-education-module` checks the files, the sections, the anchors, the calibration status, the evidence plan, the empty observation list and the evidence lines.

## Four evidence lines, kept apart

The addendum requires that evidence for one doesn't establish the others:

| Line | What shows it | What doesn't |
|---|---|---|
| Business subject mastery | The candidate's own answers, checked against an executed key | A tidy spreadsheet; a good lesson plan |
| Technology fluency | The candidate's formulas, queries or code, executed | Correct business answers typed in by hand |
| Pedagogical competence | Observed teaching rated by a human supervisor; written rationale | Subject mastery; a generated lesson |
| Occupational assessment readiness | A separately selected assessment (for example a specific NOCTI product) | Any of the above; this mode never claims it |

A manifest whose `evidence_lines` entry lists `inferred_from` another line fails the check.

## ISTE Educator roles

Tag look-fors and module parts with the seven ISTE Standards for Educators role labels: Learner, Leader, Citizen, Collaborator, Designer, Facilitator, Analyst. Labels only; the standard text stays at its source under ISTE's terms. Student-standard labels such as "Empowered Learner" belong to the ISTE Standards for Students and fail the check when tagged as educator roles.

## Educator professional learning

For one teacher or teacher educator:

1. Competency gap: the specific practice the person wants to change, with the observed or work-sample evidence that shows the gap. A self-rating alone isn't a gap finding.
2. Source-backed path: two to four sources, each with its type (peer-reviewed study, systematic review, practitioner guidance, association page) and what it supports. Trace research claims to the paper and its methods.
3. Practice task: one task the person does in their own setting, with the look-for an observer would see.
4. Evidence of improvement: an evidence plan (`evidence_plan.py`) with a baseline from before the practice and a human owner. The plan stays empty of results until real collection.

## Boundaries

No candidate or teacher data is processed in this mode without the program's own approval and consent process. Organization memberships, licenses and academic qualifications are separate records the agent never infers or claims.
