# Input shapes for research_check.py

Every file is one JSON object. A top-level `label` says whether the content is synthetic or derived from a real public source. Unknown keys are ignored; the keys below are read.

## Study card (`claims`)

| Key | Type | Values |
|---|---|---|
| `evidence_type` | string | `peer-reviewed-study`, `preprint`, `systematic-review`, `conference-talk`, `association-webpage`, `practitioner-guidance` |
| `design` | string | `rct`, `matched-random`, `experimental`, `quasi-experimental`, `correlational`, `descriptive`, `qualitative`, `design-based`, `case-study`, `systematic-review`, `meta-analysis` |
| `comparison_group`, `random_assignment` | boolean | Both true plus an experimental design lets causal wording pass |
| `sample` | object | `n` (int), `sites` (int), `level` (`k12`, `higher-ed`, `workplace`), `setting`, `selection` (`volunteer`, `convenience`, `random-sample`, `census`), `attrition` {`started`, `analyzed`} |
| `confound_controls` | list of strings | Empty in a quasi-experiment is an error |
| `measures` | list | `name`, `kind` (`performance`, `self-report`, `observation`, `artifact`, `log`), `construct` |
| `analysis` | object | `equivalence_test` (bool), `subgroup_post_hoc` (bool) |
| `claims` | list, at least 1 | `id`, `text`, `scope` {`level`, `setting`}, `basis` (measure names), optional `subgroup`, `exploratory`, `transfer_argument`, `result_significant`, `strength` (`established` triggers the evidence-type rule), `source_location` |

Rules and severities: `causal-from-nonexperimental` (error; warn for a controlled quasi-experiment), `universal-from-narrow-sample` (error), `small-single-site` (error unless `exploratory`), `higher-ed-to-other-level` (error), `transfer-beyond-sample` (error, warn when hedged), `setting-shift` (warn), `self-report-learning` (error), `null-as-equivalence` (warn), `nonsignificant-as-effect` (warn), `post-hoc-subgroup` (warn), `weak-evidence-type` (error), `no-confound-controls` (error), `attrition` under 80% retained (warn), `selection` volunteer or convenience (warn). Hedge words (may, might, could, can, suggest, encouraging, potentially, initial, preliminary) lower a generalization error to a warning; they do not excuse causal wording.

## Research plan (`design`)

Required sections: `question`, `question_type` (`descriptive`, `causal`, `exploratory`, `design`, `relational`), `rationale`, `method` {`approach` (`qualitative`, `quantitative`, `mixed`, `experimental`, `quasi-experimental`, `design-based`), `justification`, `confound_controls`}, `participants` {`minors`}, `instruments` [{`construct`, `validity_evidence` or `validity_plan`}], `analysis`, `ethics` {`status` (`not-submitted`, `submitted`, `approved`), `approval_evidence`, `consent_assent`}, `data_management` {`storage`, `retention`, `access`, `deidentification`}. `participant_data` must be absent or empty.

## Program evaluation (`program`)

`evaluation_foci` must include `coherence`, `assessment-validity`, `accessibility`, `participation`, `evidence-of-learning`. `evidence` items carry `id`, `kind` and `dimensions`. `conclusions` carry `id`, `dimension`, `evidence` (ids) and optional `about_learning`.

- Dimensions: `business-subject-mastery`, `technology-fluency`, `pedagogical-competence`, `occupational-assessment-readiness`, `computing-understanding`. A conclusion fails when none of its evidence covers its dimension.
- Evidence kinds that count as actual evidence: `scored-student-work`, `assessment-results`, `classroom-observation`, `credential-results`, `enrollment-records`, `completion-records`, `accessibility-audit`, `curriculum-document`.
- Kinds that never establish learning: `satisfaction-survey`, `generated-lesson`, `simulated-learner`, `self-report`, `plan`.
- A `standards_mapping` without a `standards_check` (the edu-standards-alignment result) fails.

## References (`citations`)

```json
{"source": "...", "references": [
  {"id": "Grover2013", "doi": "10.3102/0013189X12463051",
   "cited": {"title": "Computational thinking in K-12: ...", "year": 2013, "authors": ["Grover", "Pea"]}}]}
```

`doi` resolves through `https://api.crossref.org/works/<doi>`, `arxiv` through `https://export.arxiv.org/api/query?id_list=<id>`; with neither, a Crossref bibliographic search (`rows=3`) runs on title, first two surnames and year. A reference is `verified` when title similarity is at least 0.85, the cited year matches an issued, print or online year, and the first cited surname matches a registry author or editor. A registry record with no people leaves `first_author` in `unchecked`. `mismatch` lists the failing fields; `unresolved` means no record or a lookup failure.

Resolver file for `--offline` and `--record`: `{"entries": {"doi:<lowercase doi>": meta, "arxiv:<id>": meta, "search:<normalized query>": {"candidates": [meta]}}}` where `meta` is `{"titles": [...], "years": [...], "authors": [...], "doi": "...", "source": "..."}`.
