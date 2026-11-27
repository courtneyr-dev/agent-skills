# Trainer-of-trainers procedures

The seven procedures from the Company Agent Fleets prompt, section 11. Each names its output and what counts as done.

## 1. Explain why a design choice fits the learner task

Output: a rationale table with one row per design choice: the choice, and why it fits the task learners will do after the session.

Done when each reason names a feature of the learner task (where it happens, under what constraints, what goes wrong). "Engaging" or "hands-on" isn't a reason.

## 2. Model a complete example and expose decision points

Output: one complete worked example of the task, start to finish, with each decision point numbered and said aloud: what the choice was, what the options were, what decided it.

Done when a new trainer can name every decision point back without the script. Worked examples followed by faded practice suit novices learning a new judgment (`sources.md`).

## 3. Observe actual practice and give specific feedback

Output: a focus list for the observer (four to six observable behaviors) and a feedback pattern: the moment, the criterion, its effect on learners, one next move.

Rules: feedback comes only from what the observer saw in that run. Nothing is drafted ahead. An observation record names its human observer and date.

## 4. Calibrate rubric interpretation across reviewers

Output: a calibration exercise with practice anchors (each labeled `generated-practice-anchor`, with an intended score and rationale) and three rounds: rate alone, compare and discuss descriptor words, reveal intended scores and reword descriptors that read two ways.

`scripts/agreement.py stats` on generated rehearsal ratings returns practice-only and the items to discuss. Agreement figures (exact, adjacent, Cohen's kappa, quadratic-weighted kappa) come only from real reviewers independently rating the same real work. Report the number of shared items with every figure.

## 5. Adjust support as demonstrated competence increases

Output: a fading table: each run or cycle, the coach's role, and the observed signal that allows the next step down. Signals are observed behaviors, never elapsed time or attendance.

If a run shows a gap, the coach returns to the previous level for that skill only.

## 6. Coach another trainer to adapt the method independently

Output: an adaptation exercise. The trainer restates the learner task for a new audience, keeps or changes each rationale row with a reason, builds their own modeled example with decision points, and names the evidence that would show the adaptation worked.

The coach reviews against those four points and doesn't rewrite the adaptation.

## 7. Evaluate transfer and revisit ineffective interventions

Output: an evidence plan checked by `scripts/evidence_plan.py`. Each measure has a kind, a level (reaction, learning, behavior, results), a human owner, timing and a baseline. At least one measure is a performance task, observation, work sample, system record or knowledge check at the learning level or above; a behavior or results measure covers transfer. A `revisit_if` rule says when the intervention counts as not working, and the first step on revisit is to recheck the needs analysis, since the cause may not be a skill gap.

Result fields stay empty until real collection fills them.
