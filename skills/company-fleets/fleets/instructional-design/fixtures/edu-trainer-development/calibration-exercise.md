SYNTHETIC FIXTURE (Fixture Co)

# Rubric calibration exercise: accessible publishing rubric

Purpose: prepare reviewers to apply `rubric.json` the same way before they rate real editor posts. This exercise uses generated practice anchors. It produces discussion points, not an agreement figure.

## Before the session

- Each reviewer reads the two criteria and their level descriptors.
- The facilitator hides each anchor's `intended_score` and `rationale`.

## Round 1: rate alone (10 minutes)

1. Each reviewer scores anchors A1 to A8 alone, writing one sentence naming the descriptor words that decided the score.
2. Nobody talks until everyone has scored all eight.

## Round 2: compare and discuss (20 minutes)

1. Reveal the scores side by side. Start with the widest spread.
2. For each disagreement, each reviewer reads the descriptor words they relied on. Discuss the words, not the reviewers.
3. Reveal the anchor's intended score and rationale. Where the group still disagrees with it, record the descriptor that needs rewording.

`calibration-practice-ratings.json` shows the shape of a rehearsal sheet with two generated rating patterns: a literal reader who over-credits appearance descriptions (A2) and long link text (A7), and a lenient reader who under-penalizes filenames (A1). Run it to get the discussion list:

```
python3 <skills-root>/edu-trainer-development/scripts/agreement.py stats calibration-practice-ratings.json
```

The script returns `practice-only: no inter-rater agreement claimed` and lists the anchors to discuss. That's the intended result for generated ratings.

## Round 3: real agreement (after this exercise, with real work)

1. Two reviewers independently rate the same real work samples collected under `evidence-plan.json`, each recorded as `"source": "human-rated"` with a `human:<id>` rater.
2. Run the same script on that file. Only then does it report exact and adjacent agreement and Cohen's kappa.
3. Report the number of shared items with every figure; under 10 items the script labels the figure a calibration signal, not a reliability estimate.

No real ratings exist in this package.
