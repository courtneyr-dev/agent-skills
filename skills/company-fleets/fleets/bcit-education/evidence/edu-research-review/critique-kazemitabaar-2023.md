# Critique: AI code generators and novice learners (Kazemitabaar et al., CHI 2023)

Produced 2026-11-25 by the edu-research-review skill (review mode) for the CS education professor role. The paper is real and public; nothing below reports new data.

- Paper: Kazemitabaar, M., Chow, J., Ma, C. K. T., Ericson, B. J., Weintrop, D., Grossman, T. (2023). Studying the effect of AI code generators on supporting novice learners in introductory programming. Proceedings of CHI '23. doi:10.1145/3544548.3580919. arXiv:2302.07427v2.
- Evidence type: peer-reviewed conference paper (CHI full paper). Read from the arXiv HTML of v2, licensed CC BY 4.0 on arXiv; the ACM version carries an ACM license notice.
- Paper identity check: the DOI resolves in Crossref and the arXiv id resolves in the arXiv API with the same title, year and first author (`citations-live-kazemitabaar-2023.txt`, results `P-doi` and `P-arxiv`).
- Claims lint: `study-kazemitabaar-2023.json` gives 0 errors and 8 warnings (`evals` output in `evidence/evals/`).

## Question and theory

The paper asks five questions (Section 1): can novices use an AI code generator (RQ1), how task performance differs with and without it (RQ2), whether manual code modification suffers (RQ3), the effect on learning and retention (RQ4), and how prior programming competency interacts with the tool (RQ5). It frames the tool through cognitive load (Section 2.3) and, after the results, through use-modify-create sequencing and subgoal learning (Section 6.1). The use-modify-create explanation is post hoc: the study did not manipulate or measure it.

## Design and sample

- Between-subjects, two conditions: Codex available during training versus no generator (Section 4.1). Ten 90-minute remote sessions over three weeks on Google Meet.
- Assignment: after a 25-item Scratch pre-test, the 90 learners who completed session 1 were matched on pre-test scores and one member of each pair was randomly assigned to each condition (Section 4.2.1). This is a randomized design, so causal wording about training-phase performance is supported for this sample.
- Sample: 69 analyzed of 90 who started (77%), ages 10-17 (M=12.5), 48 male and 21 female, recruited through coding camps in two North American cities from more than 200 sign-ups, all with a personal computer, $50 gift card, Research Ethics Board approval reported (Section 4.2). Volunteers in an out-of-school remote program, not a school class.
- Measures: correctness on a 0/25/50/75/100 rubric scored by two graders with 79% exact agreement (Section 4.4), completion, time, errors from logs, 40 multiple-choice questions per post-test, and Likert items (Section 4.3).

## What the evidence supports

1. With the generator available, the Codex group completed more training tasks (90.9% vs 79.0%, d=0.68) and scored higher on authoring tasks (80.1% vs 44.4%, d=1.67) in less time (Section 5.1). This measures performance with the tool, inside this sample and setting.
2. On the following manual modification tasks during training, the difference between groups was not statistically significant (66.2% vs 58.4%, p=.202) (Section 5.1.4).
3. On the immediate post-test without the tool, the groups scored alike on authoring (61.3% vs 62.9%) and modification (59.7% vs 59.3%) (Section 5.2.1).
4. Learners in the Codex group reported more eagerness to keep programming (U=692, p=.025) (Section 5.4.1). This is self-report about motivation, not learning.

## Methodological limits

- **Null results read as equivalence.** "Does not impede learning gains" (Section 6, RQ4) and "not decreasing performance" (Abstract) rest on non-significant t-tests. The paper reports no equivalence test or power analysis, and the authors note sample size may hide effects (Section 7). The data are compatible with a small harm or a small benefit. Lint: `null-as-equivalence` on C1 and C2.
- **Retention claims rest on post hoc subgroups.** The abstract's finding that high pre-test scorers did better on retention with Codex comes from splitting each condition at the pre-test, giving cells of 16-18 learners, after the main retention comparisons were non-significant (Section 5.3, Figure 10). Treat it as a hypothesis. Lint: `post-hoc-subgroup` on C3.
- **A non-significant result described as an effect.** Section 6 says access "reduced stress"; Section 5.4.1 reports that comparison at p=.056. Lint: `nonsignificant-as-effect` on C5.
- **Item exclusion after assignment.** The evaluation analysis drops topics where a learner finished less than 50% of training (Section 5.2). The Codex group finished more of the later topics (arrays: 23/33 vs 9/36 completed, Section 5.1.1), so different learners contribute to each topic's post-test comparison. This can tilt the topic-level results the paper highlights (arrays, loops).
- **Completers only.** 21 of 90 dropped out and the pairs were broken; the analysis uses independent-samples t-tests on completers (Sections 4.2, 5). The paper reports no difference in dropout characteristics it checked, but not dropout by condition.
- **Multiple comparisons.** Dozens of t-tests across phases, task types, topics and error types; Bonferroni is applied only within topic and error-type families (Section 5). Several highlighted p-values sit between .04 and .05.
- **Condition differences beyond the tool.** The Codex group watched a different orientation video (Section 4.1.2). Experimenters graded and gave escalating hints synchronously; grading was blind to condition (Figure 5), which limits but does not remove experimenter effects.
- **Transfer not measured.** The authors state the post-tests "did not leave the boundaries of what learners were trained on" (Section 7). The study shows retention of trained task types after one week, not transfer to new problems or algorithm design.
- **Tool and time.** Codex as configured in 2022 differs from current assistants; three weeks with a novelty effect is a short window.

## What the evidence does not support

- That AI code generators improve learning for school students in general. The conclusion's "could help more students to engage in programming and broaden participation in computing" (Section 8) reaches past a volunteer camp sample with full device access. Lint: `transfer-beyond-sample` and `setting-shift` on C4 (warnings, since the sentence is hedged).
- That classroom use is safe for learning. A whole-class setting adds peers, grading stakes and access differences the study did not sample; the authors name high school and university classrooms as future work (Section 7).
- Anything about BCIT subjects such as spreadsheets or accounting.

## Citation check

Live check of the paper's identifier records and 23 of its 95 printed references (`citations-live-kazemitabaar-2023.txt`, resolver recorded for offline replay):

- 23 verified (21 references plus the DOI and arXiv records).
- 1 mismatch: the paper cites Kirschner, Sweller and Clark (2006) as "Why unguided learning does not work: An analysis of the failure of discovery learning, problem-based learning, experiential learning and inquiry-based learning". The published title is "Why Minimal Guidance During Instruction Does Not Work: An Analysis of the Failure of Constructivist, Discovery, Problem-Based, Experiential, and Inquiry-Based Teaching" (doi:10.1207/s15326985ep4102_1). Year and authors match; the printed title is wrong.
- 1 unresolved: Parsons and Haden (2006), "Parson's programming puzzles", ACE 2006. Crossref search found no matching record; this is a registry gap, not evidence the paper is fake. Check it in the ACM Digital Library by hand.
- A first live run hit Crossref rate limits on 5 lookups (`citations-live-run1-ratelimited.txt`); the script now throttles and retries twice.

## Bounded classroom application (hypothesis to test)

Setting: one grade 9-12 introductory Python class, with the teacher of record deciding.

Hypothesis: if learners must predict and trace AI-generated code before they may edit or submit it (the paper's own design suggestion in Section 6.2.2), their scores on tool-free code-modification tasks will match or exceed a comparison unit taught without the generator.

How to check it locally:

1. Keep every graded check tool-free and include modification and tracing items, not only authoring.
2. Collect scored student work under the school's student-data policy (edu-student-data-guard) and compare with a prior unit or a parallel class, naming the differences between groups.
3. Treat one class's results as local evidence for that class. A null difference is not proof of no harm; report the interval.
4. Stop using the generator for a learner who submits generated code they cannot trace or explain; passing code is not evidence of understanding.

Nothing here has been tried with real students. Any result needs actual classroom evidence collected by the teacher.
