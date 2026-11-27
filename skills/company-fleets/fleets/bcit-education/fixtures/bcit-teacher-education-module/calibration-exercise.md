SYNTHETIC FIXTURE (Fixture Co)

# Supervisor calibration exercise: break-even methods module

Purpose: prepare methods-course supervisors to score `rubric.json` the same way before they score real microteaching. The six anchors are generated practice anchors.

1. Each supervisor scores T1 to T6 alone and writes the descriptor words that decided each score.
2. Compare side by side, widest spread first. Discuss the descriptor words, not the person.
3. Reveal the intended scores. Record any descriptor that the group reads two ways and reword it before real scoring.

Two traps the anchors set on purpose:

- T1 and T3 look confident and tidy. C1 and C2 score correctness against the executed key, so they score 0.
- T4 sounds reasonable but gives a generic reason; C3 asks for a reason tied to the task and a misconception.

`calibration-practice-ratings.json` shows two generated rating patterns (one credits tidy outcomes, one reads descriptors literally). Running `agreement.py stats` on it returns `practice-only: no inter-rater agreement claimed` with the anchors to discuss.

Real agreement: after real microteaching, two supervisors rate the same segments independently (`"source": "human-rated"`, `human:<id>` raters) and the script computes agreement on that file. Supervisor ratings stay with the teacher-preparation program; none are recorded here.
