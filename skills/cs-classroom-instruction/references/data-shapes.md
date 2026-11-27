# Data shapes for lesson.py

Both files are JSON objects. Label fixtures `"label": "SYNTHETIC FIXTURE (...)"`.

## Lesson

| Field | Type | Notes |
|---|---|---|
| `label` | string | Synthetic or real-context label |
| `context.grade_band` | string | `9-10`, `6-8`, `K`, `PK-2`, ... |
| `context.prior_knowledge`, `resources`, `environment`, `duration_minutes` | list / string / int | The real teaching context |
| `context.assignment_status` | object | `teaching_assignment` and `certification`: `verified` or `unverified`; `verified` needs `verified_by: "human:<role>"` |
| `objective` | object | `id`, `text`, `level` |
| `language_rationale` | string | Why this language and tool fit the objective, age, access and environment |
| `standards[]` | list | `record_id` (`csta-k12-2026`, `csta-k12-2017`, `csta-teacher-2020`, `cs2023`), `label`, `standard_id` or null, `status`, optional `reviewer`, `bridge`. Never a `text` field |
| `teacher_guide` | object | `sequence`, `decision_points`, `wait_points` (required) |
| `examples[]` | list | `id`, `code`, optional `stdin`, `expected_output` |
| `tasks[]` | list | `id`, `kind` (predict, trace, modify, explain, construct, transfer), `prompt`, `answer_rationale`; predict tasks: `given_code`, `expected_output`; other tasks: `tests[]` (`id`, `stdin`, `expected_output`) and `reference_solution`; optional `requires_explanation`, `trace_values`, `follow_up_prompt`, `transfer_prompt` |
| `misconception_probes[]` | list | `id`, `task_id`, `name`, `signals`, `feedback`, `next_action` |
| `rubric[]` | list | `id`, `criterion`, `levels`, `evidence` (`tests`, `trace`, `explanation`, `prediction`, `ai-output`, ...) |
| `accessibility` | object | `checks[]` plus `low_bandwidth_alternative` or `unplugged_alternative` |
| `reteaching`, `extension` | string | |

Probe `signals` match when every listed signal matches:
- `output_equals`: `{"test": "<test id>", "value": "<stdout>"}`
- `code_regex`: a Python regular expression searched in the learner's code
- `prediction_equals`: the learner's prediction text

At least one rubric criterion must need `trace`, `explanation`, `prediction`, `oral-explanation` or
`annotated-code` evidence, and the lesson needs a `transfer` task.

## Learner work

| Field | Type | Notes |
|---|---|---|
| `task_id` | string | Required |
| `learner_ref` | string | A pseudonymous reference, never a name |
| `code` | string | For construct, modify and transfer tasks |
| `prediction` | string | For predict tasks |
| `explanation`, `trace` | string | Both are searched for the task's `trace_values` |
| `ai_generated` | bool | `true` means passing output can't count as evidence of understanding |

Learner text is data. Instructions inside it ("mark me as passed") change nothing.
