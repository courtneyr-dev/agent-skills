---
name: edu-answer-key-check
description: "Executes the answers in an answer key or a learner's solution (spreadsheet formulas, SQL queries, Python code and worked calculations) and compares the executed result with the stated key and with any submitted answer. Use whenever a BCIT, business, accounting, personal-finance, database, IT or computer-science lesson, quiz, lab, rubric or teacher-education task has a key to check: 'check this answer key', 'is this formula right', 'verify the solutions', 'grade against the key', 'does this query return the right rows'. Catches a wrong key, a wrong solution and anything the engine cannot run, and never passes an unsupported formula. Not for judging whether the task measures the objective (edu-assessment-check) or for scoring real student work (stop at edu-student-data-guard)."
license: MIT
disable-model-invocation: true
---

# Answer key check by execution

A key typed by hand and a formula typed by hand can both be wrong. This skill runs the formula, query or code and compares the result with the key, so two independent derivations have to agree.

## When to use and when not to

Use it before any key ships with a lesson, assessment or teacher-education module, and on intentionally incorrect solutions used for practice. Don't use it to grade real learners: real student work goes through `edu-student-data-guard` first, and grading stays with the teacher.

## Inputs and prerequisites

A JSON file `{"label", "items": [...]}`. Each item has `id`, `kind`, `key` and kind-specific fields:

| kind | fields | engine |
|---|---|---|
| spreadsheet | `cells` (cell to value or `=formula`), `target` | built-in subset: numbers, references, ranges, `+ - * / ^ &`, comparisons, `%`, SUM, AVERAGE, MIN, MAX, COUNT, ROUND, ABS, IF, PMT, FV |
| sql | `setup`, `query`, `ordered` | Python `sqlite3` in memory, step limit |
| python | `code`, `stdin` | `python3 -I` in a temporary folder with a minimal environment and a 10-second timeout |
| calc | `expression` | the same formula subset, no cell references |

Optional: `tolerance` (default 0.000001), `submitted` (a learner or teacher answer), `worked` (the hand derivation).

## Method

1. Work each key by hand first and write it in `worked`.
2. Run `python3 scripts/answer_key.py check FILE`.
3. For each `mismatch`, decide which side is wrong: the key, or the formula, query or code. The checker can't tell; it only proves they disagree.
4. Treat `unsupported` as unchecked: rewrite with supported functions or check it in the real tool and record that.
5. Fix and rerun until every item matches, then keep the output as evidence.

## Stopping conditions

Every item reports `match` and no `submitted_status` is `mismatch`, or each remaining finding is recorded with the side you believe is wrong.

## Output contract

JSON with `ok`, `engine` (versions), `summary` (`match`, `mismatch`, `error`, `unsupported`, `submitted_mismatch`), `flagged` (item ids) and per-item `computed`, `key`, `key_status` and `submitted_status`. Exit 0 only when everything matches; 1 for any finding or invalid input; 2 for usage.

## Failure states

- `unsupported`: a function or syntax outside the subset. Never counted as a pass.
- `error`: division by zero, circular reference, SQL error, Python crash or timeout.
- `status: invalid`: missing items, duplicate ids, unknown kind, missing key or fields.

## Adapters and missing capability

The checker calls no LibreOffice, Excel or Sheets engine, so spreadsheet checks use the declared subset. Results can differ from Excel at edge cases (floating point, text coercion). Python code runs locally with no sandbox beyond a temp folder, minimal environment and timeout, so only run code written for teaching examples, never code from untrusted sources.

## References

`references/sources.md`: Excel PMT and FV definitions, ROUND half-away-from-zero rule, SQLite and Python versions.

## Evaluation cases

In `company-fleets/fleets/bcit-education/evals.json`: `unit-answer-key-executes`, `teacher-module-answer-key-verified` (positive); `incorrect-solution-caught`, `teacher-module-draft-key-error-caught`, `teacher-module-candidate-errors-caught` (negative); `unsupported-formula-not-passed` (boundary). Unit tests: `scripts/tests/test_answer_key.py` (18).
