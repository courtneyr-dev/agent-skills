---
name: community-health-measures
description: "Use whenever someone plans, reviews or computes community or open-source measures: a measurement plan, community health metrics, contributor counts, response times, event follow-up numbers, a board or newsletter stat. Lints the plan so every metric has a question, a definition, a CHAOSS or TODO Group source (or a local definition with a rationale), an aggregate level, a consent basis and a minimum group of 5, and refuses volunteer rankings, inferred burnout or protected traits, undefined health scores, metrics over moderation cases, and participation counted as sales leads. Then computes only clean plans, dropping confidential records and withdrawn consent and suppressing small groups. Trigger on \"community health\", \"measurement plan\", \"top contributors\", \"leaderboard\", \"health score\", \"who's burning out\", \"metrics for the board\". Not for DevRel program ROI (devrel-program-kit) or the community-health diagnosis method (developer-community-health)."
disable-model-invocation: true
---

# community-health-measures

Measures exist to change a decision, so each one starts from a question. This skill keeps a measurement plan honest and computes it without naming anyone. Use samber's `developer-community-health` for the diagnosis method and its `contributor-absence-factor.sh`; use this skill for the plan's rules and the aggregate numbers.

## Inputs

- A plan (`plan.json`): `community` and `metrics[]`. Each metric has `id`, `question`, `definition`, `source` (`{"kind": "chaoss", "url": "https://chaoss.community/kb/metric-..."}`, `{"kind": "todo-group", "url": ...}`, or `{"kind": "local", "rationale": ...}`), `level` (`community`, `cohort` or `channel`), `min_group_size` (5 or more), `consent_basis`, `publish` (`public` or `internal`), and an optional `compute` rule: `count`, `distinct-people` or `median-hours` over a `record_type`, with an equality `filter` and, for hours, `start` and `end` fields. A score also needs `components` (metric ids in the plan) and `weights` that sum to 1.
- Activity records (`activity.json`): `records[]` with `type`, `person`, optional `classification` and `consent`, and the fields the compute rules name. Use synthetic or consented, already-collected data only. Never scrape people to fill it.

## Method

1. Pick the questions the community or its funders need answered. Prefer a CHAOSS metric; write a local definition only when none fits.
2. Lint until it exits 0:

```bash
python3 scripts/measures.py lint plan.json
```

3. Compute:

```bash
python3 scripts/measures.py aggregate --plan plan.json --activity activity.json
```

4. Report each value with its definition and source. A suppressed value is reported as suppressed, never estimated. A metric without a compute rule (a survey, say) is collected by the people who own that instrument.

## Stopping conditions

- Lint exit 1: rewrite the metric. Don't rename a ranking to dodge the phrase list; change what it measures.
- A question only a per-person view can answer (for example, "who needs help?") goes to the maintainer liaison or mentorship lead as a private conversation, not a metric.

## Output contract

`lint` prints `{ok, metrics, violations[{metric, rule, message}]}`. `aggregate` prints `{community, metrics[{id, computed, value, unit, level, publish} | {id, computed: false, suppressed?, reason}], excluded_records{confidential-or-case, consent-withdrawn}, note, ok}` and never a person identifier.

| Rule | Refuses |
|---|---|
| `undefined-metric`, `unsourced`, `no-consent`, `no-audience` | A metric without a question, a definition, a source, a consent basis or an audience |
| `individual-level`, `ranking` | Per-person levels, leaderboards, top-N lists, per-member counts |
| `inference` | Burnout, wellbeing, mood or protected traits inferred from activity |
| `undefined-composite` | A health or engagement score without published components and weights |
| `confidential-source` | Any metric whose record type or wording points at moderation cases, conduct reports, complaints, sanctions or bans. `aggregate` also drops every record whose type, category or classification marks it as a case or confidential |
| `sales-leads` | Participation turned into sales leads or prospects |
| `small-groups` | A minimum group below 5 |

## Failure states

- Exit 2: a file is unreadable, `metrics` or `records` isn't a list, or a metric has no id.
- The phrase lists catch common wording, not every wording. The structural rules (level, group floor, source) hold regardless, and case records are dropped by type, category or classification whatever a metric calls them; a human reviewer reads the definitions.
- `\bage\b` and similar words can flag an innocent metric such as "account age". Rename it ("account tenure") rather than weakening the rule.

## Boundaries

- Aggregates only. Never publish, email or post the results; hand them to the community strategy lead.
- Confidential moderation cases stay in the case log. Transparency counts from that log are a separate product a human approves.
- No inferring burnout, intent or protected traits, even internally.

## References

`references/sources.md` lists CHAOSS, TODO Group and the upstream skill, with versions and rights.

## Tests

```bash
cd scripts/tests && python3 -W ignore -m unittest -v test_measures
```
