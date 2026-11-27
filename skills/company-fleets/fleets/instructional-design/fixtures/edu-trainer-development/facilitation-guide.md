SYNTHETIC FIXTURE (Fixture Co)

# Facilitation guide: coaching a new trainer to run "Accessible link text and alt text"

Fixture Co is fictional. This guide prepares a new trainer to run a 60-minute session for client editors, coached by a lead facilitator. It records no observations, ratings, survey results or learning gains; those come from real sessions under the evidence plan in `evidence-plan.json`.

## Purpose and audience

- Learners: client editors (fixture) who publish posts in a CMS under weekly deadlines.
- Trainer being developed: a Fixture Co staff member running the session for the first time.
- Coach: the lead facilitator, who has run the session before.
- Intended performance: editors publish posts whose alt text and link text score 2 or 3 on `rubric.json`; the new trainer runs the session without the lead stepping in.
- Precondition: `edu-needs-analysis` found a real skill gap (editors had never written alt text for informative images). If the cause were a CMS that hides the alt-text field, this session would be the wrong remedy.

## Session at a glance

| Minutes | Segment | What learners do |
|---|---|---|
| 0-5 | Why it matters | Hear a screen reader read two versions of the same post |
| 5-20 | Modeled example | Watch the trainer think aloud through one complete post |
| 20-40 | Guided practice | Fix three draft posts in pairs, using the rubric |
| 40-50 | Independent task | Fix two new drafts alone (the end-of-session performance task) |
| 50-60 | Debrief | Compare their fixes to the rubric descriptors; note one change for their next post |

Low-bandwidth alternative: the drafts and rubric print on two pages; the screen-reader demo has a transcript.

## Design rationale

Each choice follows from the learner task: editors write alt text and link text inside a CMS, alone, under deadline.

| Choice | Why it fits the task |
|---|---|
| Practice on realistic CMS drafts, not a quiz about WCAG numbers | The job is writing text in context; recalling criterion numbers isn't the performance. |
| One complete worked example before practice | Novices learn a new writing judgment faster from a full example than from rules alone (worked-example research, `references/sources.md`). |
| Rubric descriptors name observable text features | Editors can check their own post against "names the destination" without a trainer present. |
| Pairs first, then alone | Pairs expose reasoning; the solo task shows what each editor can do. |
| Screen-reader demo up front | Editors rarely hear their pages read aloud; the demo shows the consequence the rubric scores. |

## Modeled example and decision points

The trainer works one post from start to finish, saying each decision out loud. The post (fixture): a product update with a revenue chart, a team photo and a link reading "click here".

1. Decision point: is the image informative or decorative? The team photo adds no information the caption lacks, so it's decorative and gets empty alt text. The chart carries the post's main claim, so it's informative.
2. Decision point: what does the chart convey here? Not "bar chart in blue". It conveys "Support tickets fell from 420 in March to 310 in April". That sentence is the alt text.
3. Decision point: where does the rest of the data go? The full monthly numbers go in a table under the chart, so the alt text stays short.
4. Decision point: what does the link lead to? "Click here" becomes "Read the April support report". The trainer checks that the text makes sense in a list of links read out of context.
5. Check: the trainer scores the finished post against `rubric.json` aloud, criterion by criterion.

The new trainer's job during this segment is to name each decision point back to the lead after the session. Skipping the "why" turns the example into a script to copy.

## Practice and observation

During guided practice, the trainer circulates and asks one question per pair: "Which decision point were you at when you chose that wording?" The trainer answers with the descriptor, not a corrected sentence, so editors keep the reasoning.

## Observation and feedback

The lead observes the new trainer's runs with this focus list:

- Did the modeled example include every decision point, said out loud?
- Did the trainer respond to what editors actually wrote, or to a prepared answer?
- Did feedback to editors name the rubric descriptor?
- Did the trainer stop guided practice on time to leave the solo task intact?

Feedback to the new trainer follows one pattern: the moment (time and what happened), the criterion it relates to, its effect on learners, and one next move. The lead writes feedback only from what they observed in that run; no feedback is drafted in advance.

## Rubric calibration

Before rating real work, reviewers rehearse with `calibration-exercise.md`. The anchors in `rubric.json` are generated practice anchors: they prepare reviewers to apply the descriptors and surface disagreements to discuss. They aren't evidence of how reviewers agree. Real inter-rater agreement comes only from two human reviewers rating the same real work samples independently, run through `scripts/agreement.py`.

## Fading support

Support drops as the new trainer demonstrates each skill, not on a calendar.

| Run | Lead's role | Move on when the lead has observed |
|---|---|---|
| 1 | Co-facilitates; models the worked example; new trainer runs guided practice | The new trainer names all five decision points afterward |
| 2 | Observes with the focus list; steps in only for an accuracy error | No accuracy interventions needed, and feedback to editors names descriptors |
| 3 | Absent; reviews the new trainer's own notes on request | The new trainer runs the session and the solo task stays intact |

If a run shows a gap, the lead returns to the previous row for that skill only.

## Coaching another trainer to adapt the method

The trainer is ready to adapt the session when they can explain each design choice in the rationale table in their own words. The adaptation exercise: redesign the session for Fixture Co developers writing button labels and form error messages. The new trainer must:

1. Restate the learner task for developers.
2. Keep or change each row of the rationale table, saying why.
3. Build one complete modeled example with its decision points.
4. Name what evidence would show the adapted session worked.

The lead reviews the adaptation against those four points and doesn't rewrite it.

## Transfer evaluation

Transfer means editors' published posts improve, not that the session felt useful. `evidence-plan.json` names the measures: rubric scores on editors' real posts before and after (behavior), the end-of-session task (learning), the lead's observation of run 2 (the trainer's behavior), and a reaction survey kept separate from learning evidence. If posts don't improve after two cycles, revisit the needs analysis before changing the session: the cause may be the CMS, not the skill.

## What this package does not claim

It records no ratings, observations, survey results or gains. Every number in a future report has to come from the collection the evidence plan describes.
