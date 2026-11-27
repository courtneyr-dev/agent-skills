SYNTHETIC FIXTURE (Fixture Co)

# Trainer-development package (fixture)

A complete trainer-of-trainers package for one Fixture Co session, used to evaluate `edu-trainer-development`. Fixture Co, its client and every person here are fictional.

| File | What it is |
|---|---|
| `manifest.json` | Package manifest checked by `scripts/package.py check` |
| `facilitation-guide.md` | Facilitation guide: design rationale, modeled example with decision points, observation and feedback, calibration, fading support, coaching another trainer, transfer evaluation |
| `rubric.json` | Two-criterion rubric with eight generated practice anchors |
| `calibration-exercise.md` | Three-round calibration exercise |
| `calibration-practice-ratings.json` | Generated rehearsal ratings; the script returns practice-only |
| `evidence-plan.json` | Plan to collect actual learning and transfer evidence; all result fields empty |
| `evidence-plan-survey-only.json` | Counterexample: survey and attendance only (rejected) |
| `evidence-plan-prefilled.json` | Counterexample: fabricated results filled in on purpose (rejected) |
| `counterexample/` | Counterexample package: missing guide sections, an anchor labeled as real expert-rated work, a survey-only plan (incomplete) |

Human-data boundary: nothing here is a rating, observation, survey response or learning gain.
