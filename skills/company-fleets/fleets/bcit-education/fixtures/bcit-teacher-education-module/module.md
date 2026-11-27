SYNTHETIC FIXTURE (Fixture Co)

# Methods-course module: teaching break-even analysis with spreadsheets and data

A teacher-education module for a business, computer and information technology (BCIT) methods course. Teacher candidates learn to teach break-even analysis through the Fixture Co student-run store, practice the spreadsheet and query work themselves, then microteach a 12-minute segment to peers. Fixture Co, its store, its sales data and every person here are fictional. The module records no candidate work, observations, ratings or results.

## Context

- Audience: teacher candidates in a secondary BCIT methods course (synthetic). Grade band they'll teach: 9-12.
- Duration: two 75-minute methods-course sessions plus one microteaching slot per candidate.
- Prerequisites for candidates: cost and revenue concepts from an accounting course; basic spreadsheet formulas.
- Resources: any spreadsheet tool; SQLite or a printed query sheet; the store data in `answer-key.json` (synthetic).
- Low-bandwidth alternative: the store data and every task print on three pages; break-even can be worked by hand.

## Authentic business task

The Fixture Co student-run store wants to sell custom stickers this semester. Students must tell the store's student managers how many stickers they need to sell before the stickers stop losing money, and what happens if the price changes.

- Fixed costs for the semester: $450 (printer lease share and design software).
- Price per sticker: $2.50. Variable cost per sticker: $1.00 (stock and ink).
- Questions students answer: contribution margin per sticker, break-even units, break-even revenue, units needed for a $150 profit target, and the margin of safety if they expect to sell 360.
- The real decision the task feeds: whether the managers should change the price. That makes the calculation a means, not the goal.

Candidates first do the task as learners, then plan how they'd teach it.

## Computing practice

Candidates build the model twice: once in a spreadsheet with cell references, once as queries on three weeks of store sales.

- Spreadsheet: inputs in B2 to B4, contribution margin in B5 (`=B3-B4`), break-even units in B6 (`=B2/B5`), break-even revenue (`=B6*B3`), target-profit units (`=(B2+B7)/B5`).
- Queries: revenue by item (`GROUP BY item`) and total sticker units from the `sales` table.
- Every key value is in `answer-key.json` and is checked by execution with `edu-answer-key-check`, not by reading it over. `answer-key-draft.json` holds a draft key with a deliberate error (break-even computed as fixed costs divided by price, 180 instead of 300); the check must catch it. `candidate-solutions.json` holds a sample candidate solution with two deliberate errors (the same price-instead-of-margin formula and a revenue query missing `GROUP BY`); the check must flag both.

## Pedagogical rationale

| Choice | Why it fits teaching this task |
|---|---|
| Start from the store managers' price decision | Students care about the answer when it changes a decision; the formula alone gives them nothing to check it against. |
| Worked example, then faded practice | Novices first study a complete break-even model with each step explained, then complete versions with steps removed, then build one alone (worked-example fading). |
| Predict before computing | Asking students to predict whether a price rise lowers break-even exposes the common misconception that break-even depends on price alone. |
| Cell references, not typed numbers | A model with references answers "what if the price changes?" in one edit; typed numbers hide the relationship being taught. |
| Same model as a query | Querying real sales shows students where the expected-units figure comes from, which connects the model to data. |

Common misconceptions to probe: dividing fixed costs by price instead of contribution margin; treating the printer lease as a variable cost; reading break-even units as the profit point; typing results instead of formulas.

## Microteaching cycle

1. Plan: each candidate plans a 12-minute segment (the worked example, or the predict-then-compute check) using the rationale table.
2. Teach: the candidate teaches peers, who respond as themselves, not in scripted student roles.
3. Observe: a human supervisor or peer observer fills `observation-instrument.json` during the segment.
4. Feedback: the observer names the moment, the look-for it relates to, its effect and one next move. Feedback comes only from what the observer saw in that segment.
5. Reteach: the candidate reteaches the same segment with the change and the observer records whether the look-for appeared.

## Observation instrument

`observation-instrument.json` lists five items, each tied to one evidence line and to look-fors an observer can see or hear. Its `observations` list is empty: a human observer fills it.

## Assessment criteria

`rubric.json` scores four criteria, each on its own evidence line: business accuracy, spreadsheet and query correctness, pedagogical rationale, and responsive checking for understanding. Spreadsheet and query correctness is scored against the executed answer key, so a polished-looking sheet with a wrong formula scores low.

## Calibration exercise

Before supervisors score real microteaching, they rehearse with `calibration-exercise.md` and the generated practice anchors in `rubric.json`. `calibration-practice-ratings.json` is a rehearsal sheet; the agreement script returns practice-only for it. Real agreement needs two supervisors rating the same real segments.

## Evidence lines

Evidence for one line never establishes another:

- Business subject mastery: the candidate's own answers to the store task, checked against the executed key.
- Technology fluency: the candidate's spreadsheet formulas and queries, executed.
- Pedagogical competence: observed microteaching and the written rationale, rated by a human supervisor.
- Occupational assessment readiness: not assessed. This module doesn't prepare for or predict any NOCTI or other occupational credential result; that needs a separately selected assessment.

## Standards and sources

- NBEA content areas touched, by label only: Accounting; Economics and Personal Finance; Entrepreneurship; Information Technology. No standard IDs are claimed: the licensed NBEA text isn't in the rig, so any alignment stays unverified until a reviewer with access checks it.
- ISTE Standards for Educators roles tagged by label only: Learner, Designer, Facilitator, Analyst, Collaborator, Citizen. No standard text is reproduced.

## Supervisor decisions

Human supervisors keep every consequential decision: field placement, whether a candidate meets the program's standard, certification recommendations and any grade. The module and its agent produce materials, instruments and drafts for them; it decides nothing about a candidate.
