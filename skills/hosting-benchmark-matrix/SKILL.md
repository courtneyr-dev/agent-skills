---
name: hosting-benchmark-matrix
description: "Keep a dated hosting benchmark honest against public Acquia, Pantheon and WordPress VIP documentation: each dimension (restore, recovery objectives, isolation, deployment reversibility, performance under load, observability, support, accessibility, data portability, regions, cost, availability) records the documented provider claim, the proposed target, the configured capability, the measured test result and the contractual commitment as five separate fields. Refuses superiority claims, claims resting on agent or role counts, availability percentages from lab runs, commitments with no contract, and measured values that don't match their hashed evidence. Produces the production-readiness backlog. Use whenever someone compares the company's hosting with those providers, says 'more robust', drafts an SLA or uptime claim, or asks what stands between the lab and production."
license: MIT
disable-model-invocation: true
---

# hosting-benchmark-matrix

A comparison is only as good as the line between what a provider says, what the operator
proposes, configures, measures and signs. This skill keeps those five apart in one dated
matrix, checks every measured number against its evidence file, and turns the gaps into a
production-readiness backlog. A larger agent roster is never evidence.

## When to use

- Comparing Fixture Co hosting with Acquia, Pantheon or WordPress VIP on any measurable dimension.
- Before anyone writes "more robust", an uptime figure or a recovery objective in a plan, page or
  contract.
- Building the production-readiness backlog after a restore exercise.

## When not to use

- Running the measurements: `hosting-restore-exercise`, `hosting-tenant-isolation` and
  `hosting-data-migration` produce the evidence this matrix cites.
- Launch go/no-go: Magnus `production-readiness` owns the gate; this skill feeds it the backlog.
- Publishing a comparison: publication stays with a human and the existing publishing workflow.

## Inputs and prerequisites

- A matrix JSON (`as_of`, `contract` or null, `statements`, `dimensions`). Each dimension holds
  `provider_claims` (provider, claim, quote of 25 words or fewer, https URL, `retrieved_on`, status
  `documented`, `not documented publicly` or `page unreachable`), `proposed_target` (`max`, `equals`
  or a `summary`; an availability target with a percentage needs `"hypothesis": true` and no
  guarantee or promise wording), `configured_capability`, `measured_result` (value, evidence path,
  `evidence_sha256`, `json_path`, runs), `contractual_commitment`.
- Evidence files under `company-fleets/fleets/hosting/evidence/`, each recorded by its owner in
  `benchmark-evidence-manifest.json` with `benchmark.py record-evidence --path REL --dimension D
  --json-path P` when it's produced: the file's sha256, and which file and JSON path measure the
  dimension. Targets come from the owner's `fleets/hosting/benchmark/targets.json`. The manifest, the
  targets and the contracts registry (`fleets/hosting/benchmark/contracts.json`) are always read from
  the rig, never from `--root` or the matrix.
- Provider claims come from public pages only. Recheck them when `retrieved_on` is old.

## Method

1. Refresh provider claims from each provider's own public docs; record "not documented publicly"
   instead of guessing. Keep quotes exact and short.
2. Run the lab exercises, save their JSON outputs as evidence, and record each file in the owner
   manifest with `record-evidence`, naming the dimension and JSON path each one measures. `check`
   reads the value at the JSON path the owner recorded for the dimension, in the file the owner
   recorded, and compares that file's sha256 with the manifest; a matrix that cites another file or
   path is refused (`measured-evidence`). A matrix target that differs from the owner's is refused
   (`target-not-on-record`), and the owner's target always decides the status. An
   availability value counts only when its evidence is an `hosting-incident-response` `slo-check`
   availability claim covering 30 days or more; a `kind` or `window_days` label in the matrix decides
   nothing. A `contract` counts only when the contracts registry lists it.
3. Run `scripts/benchmark.py check --matrix M`. Fix every violation; never edit a measurement to
   reach a target. Statements, the subject, the contract note, provider claim summaries and every
   dimension field except provider quotes are checked after the text is normalized the way
   corporate-claims-check does it (HTML entities, NFKC, zero-width and format characters, look-alike
   letters, case). They're checked for superiority wording (better, best, most robust, number one,
   #1, wins), for comparisons with a named provider (Acquia, Pantheon, WordPress VIP, "providers",
   "competitors") using words such as than, trails, lags behind, unlike or versus, for availability
   percentages written with %, percent, per cent or "four nines" beside uptime, availability, up,
   online, SLA, SLO or guarantee, and for promises such as "never go down". A provider claim summary
   may quote the provider's own percentages; a comparison with Fixture Co in it is refused.
4. Run `backlog --matrix M --markdown` and hand the items to the general manager and Magnus
   `production-readiness`. Unmet targets come first.
5. Run `render --matrix M` for the readable table beside the JSON.

## Stopping conditions

- `check` passes and the backlog is handed off, or a violation remains and the matrix stays
  unpublished.

## Output contract

`check`: `verdict`, `violations` (rule, dimension, message), `statuses` per dimension (`met`,
`unmet`, `not-measured`, `measured-no-target`, or `evidence-refused` when the dimension's evidence
fails), `assumptions`. `backlog`: items with dimension, kind
(`close-gap`, `measure`, `configure`, `commit`) and detail. `render`: a Markdown table.

## Failure states

- Exit 1: any violation (rules `dimension-coverage`, `five-fields`, `provider-claims`,
  `measured-evidence`, `target-not-on-record`, `availability-from-lab`, `no-contract`,
  `contract-not-on-record`, `superiority`, `roster-size`).
- Exit 2: invalid input (unreadable JSON, a file that isn't UTF-8, no `as_of`, unknown dimension, a
  non-integer `window_days`, a string where an object or list belongs, an unreadable owner file).
- Limit: a process running as the same OS user can rewrite the evidence, the manifest, the targets
  and the registry together, or run `record-evidence` itself. Only separate OS accounts or signed
  records stop that.

## Adapters and missing capability

No provider account or contract exists, so the `contractual_commitment` column stays null and
provider performance is never measured here. A future load-testing or synthetic-monitoring adapter
would fill `performance_under_load` and `availability`; until then they stay `not-measured`.

## References

`references/sources.md`: the dated provider pages, the prompt's "more robust" acceptance text, and
the rig skills this one reads from.

## Tests

```bash
cd ~/.claude/skills/hosting-benchmark-matrix/scripts && python3 -W ignore -m unittest discover -s tests
```

## Evaluation cases

Fleet cases in `company-fleets/fleets/hosting/evals.json`: `hosting.eval.benchmark-dated-matrix-passes`,
`hosting.eval.benchmark-superiority-refused`, `hosting.eval.benchmark-availability-from-lab-refused`,
`hosting.eval.benchmark-tampered-measurement-refused`, `hosting.eval.benchmark-commitment-without-contract`,
`hosting.eval.benchmark-backlog-unmet-first`.

Cases that replay the 2026-11-26 independent review's probes: `hosting.eval.benchmark-lab-labeled-production-refused`, `hosting.eval.benchmark-self-declared-contract-refused`, `hosting.eval.benchmark-named-provider-comparison-refused`, `hosting.eval.benchmark-rehashed-evidence-refused`.

Cases that replay the hosting re-review's probes: `hosting.eval.benchmark-matrix-json-path-refused`, `-matrix-target-refused`, `-reviewed-phrasings-refused` (all 11 phrasings), `-claim-summary-and-subject-scanned`, `-string-shaped-field-invalid`.
