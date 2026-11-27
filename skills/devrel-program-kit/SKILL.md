---
name: devrel-program-kit
description: "Use when a developer-relations program needs its operating kit or a check on its claims: after samber's developer-relations-kickoff routes the work, this skill confirms every routed skill is installed (and names the installed fallback when a sibling collection isn't), keeps program state in the tenant's devrel-context.md instead of a new memory store, hands the ordered chain back to the existing router, and checks the program plan so reach never stands in for success, revenue claims carry attribution limits, quotes, testimonials and conference acceptances have sources, budgets aren't invented, and every quickstart, lab or demo in the chain has clean-replay evidence. Trigger on \"DevRel program plan\", \"developer program kit\", \"exec report for DevRel\", \"DevRel metrics review\", \"check the kickoff routes\", \"which devrel skills do we have\", or before any DevRel report leaves the team."
disable-model-invocation: true
---

# devrel-program-kit

samber's `developer-relations-kickoff` is the DevRel domain router: it interviews, routes and writes `devrel-context.md`. This skill is its adapter to the rig and the kit's quality gate. It doesn't route work itself and never dispatches; the existing router (Claude Code with credit-routing and factory-rig) runs whatever the chain names.

## Inputs

- The kickoff's short-list as `{"routes": [{"skill": "samber/<collection>@<skill>", "order": n}]}`.
- The tenant's `devrel-context.md` (format: kickoff § 5 and its `developer-relations-kickoff/references/context-artifact.md`).
- A program plan JSON: `context_record`, `goals`, `non_goals`, `segments`, `budget`, `staffing`, `metrics[{id, class: reach|usefulness|business, definition, instrumentation, owner, attribution?}]`, `claims[{kind, text, source?, consent?}]`, `reports[{audience, headline_metrics}]`, `chain[{type, artifact, verified_by, evidence, human_usability, human_evidence?}]`. The Fixture Co example is `company-fleets/fleets/devrel/fixtures/program/program-good.json`.

## Method

1. Run the kickoff. Then check its routes resolve:

```bash
python3 ~/.claude/skills/devrel-program-kit/scripts/check_routes.py routes routes.json
```

   An unresolved route comes back with installed fallbacks from `references/fallbacks.json` and a coverage label. Replace it, or record the gap as blocked. Never route to a name the check didn't resolve.
2. Map the context as `references/context-and-handback.md` says: one `devrel-context.md` per tenant, owned by a named human; memory holds a pointer only.
3. Build the kit sections from `references/kit-map.md`. Each section names the installed skill that produces it.
4. Build the content and demo chain (sample app, quickstart, workshop lab, demo, feedback repro). Prove each runnable artifact with `devrel-quickstart-replay` and record the evidence path in the plan's `chain`. Keep `human_usability: unverified` until a session with real, unfamiliar readers is on record.
5. Check the plan until it exits 0:

```bash
python3 ~/.claude/skills/devrel-program-kit/scripts/check_program.py program.json --base DIR
```

   Paths in the plan (chain `evidence`, `human_evidence`, claim `source` and `consent`) resolve under `--base`, default the current directory. Each must be an existing file: a passing `devrel-quickstart-replay` report whose `doc_sha256` matches the artifact's current bytes, a recorded session file, or a retained source or consent record.

6. Hand the chain back as handoff.v1 stages (company-fleets `schemas/handoff.schema.json`). The next consumer is a role or a `human:` owner, never this skill.

## Stopping conditions

- Both checks exit 0 and every runnable chain entry has replay evidence: hand off.
- A route stays unresolved with coverage `blocked`: keep the rest of the chain, record the blocker in `devrel-context.md` under Open, and continue.
- The plan needs a budget, a segment's evidence, a quote or a conference result nobody has supplied: leave it as `owner-to-provide` or omit the claim. Don't invent one to finish the kit.

## Output contract

`check_routes.py` prints `{ok, counts{installed, drift, sibling-not-installed}, unresolved[{ref, status, fallback, coverage, why}], installed}`. `scan DIR...` reads the same references straight from skill files, so a renamed or removed upstream skill surfaces as `drift`. `check_program.py` prints `{ok, violations[{rule, where, message}]}`. Both exit 0 when clean, 1 with findings, 2 on invalid input.

| check_program rule | Refuses |
|---|---|
| `no-non-goals` | A plan with no stated non-goals |
| `no-usefulness-metric`, `reach-headline`, `unknown-metric` | Reach or business numbers presented as success |
| `undefined-metric` | A metric without class, definition, instrumentation or owner |
| `causal-revenue` | Business metrics without attribution limits, or "drove", "caused" or "generated" revenue wording |
| `fabrication-risk`, `unknown-claim` | Quotes, testimonials, customer results, acceptances, case studies or revenue claims without a retained source record file (and a consent record file for quotes and testimonials); any other claim kind |
| `invented-budget` | Budget or headcount figures the owner didn't provide |
| `competing-context` | Program state kept anywhere but the tenant's `devrel-context.md` |
| `untested-chain`, `unmeasured-usability` | Runnable artifacts without an existing, passing replay report of their current bytes; usability claimed without a recorded session file |

## Failure states

- Exit 2 names the malformed field. Fix the input; the checks never fill a gap.
- The causal-wording rule reads definitions and revenue claim text, not attribution notes, so "can't show it caused" is allowed. Other causal phrasings can slip past; the program lead reads every exec report.

## Boundaries

- Never publish, post, submit a CFP, email developers or contact speakers. Content leaves as drafts for a human; `shared-content-publishing` is archived in this rig, so a human publishes.
- Never schedule the kickoff's § 7 routines. Propose them as dry-runs to the PM layer (`kanban-guru`, `technical-program-management`); this rig starts no recurring jobs.
- Don't patch a project's agent-instruction file, as kickoff § 5 allows, without the record owner's approval.

## Missing capability

Two sibling collections the kickoff routes to aren't installed: `samber/developer-platform-skills` (API reference quality, sample-app strategy, SDK publishing, partner onboarding) and `samber/dev-event-organizer-skills` (hackathons, event production, speaker coaching). The fallbacks cover them partially; the rest stays recorded as blocked until you install those collections.

## Tests

```bash
cd ~/.claude/skills/devrel-program-kit/scripts/tests && python3 -W ignore -m unittest -v test_kit
```
