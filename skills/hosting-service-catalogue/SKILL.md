---
name: hosting-service-catalogue
description: "Check a hosting service catalogue and its responsibility matrix against one operating profile (affiliate, reseller, shared, managed, platform or enterprise), including upstream-provider dependencies and customer-visible limits, so the company never claims a duty it can't control and never drops one it owes. Use whenever someone drafts, reviews or publishes a hosting plan, package list, SLA or support boundary, asks who is accountable for backups, accounts, incidents or hardware, adds an upstream provider, or asks whether an affiliate or reseller is promising too much. Renders a readable responsibility matrix next to the structured file."
license: MIT
disable-model-invocation: true
---

# hosting-service-catalogue

This skill checks a service catalogue (a JSON file of services, the functions each service performs, who is accountable and responsible for each function, the limits customers see and the upstream providers behind it) against the function vocabulary for one operating profile. An affiliate refers customers and operates no infrastructure, so its catalogue can't make Fixture Co accountable for backups. A shared host owes backups, so a catalogue that omits them fails. The check is deterministic and runs offline.

## When to use

- Draft or review a hosting plan, package list, support boundary or responsibility matrix.
- Decide which party owns a function when a customer, Fixture Co and an upstream provider all touch it.
- Add or change an upstream provider and confirm its obligations and escalation path are written down.
- Confirm every limit a customer sees has a number and a unit before it's published.
- Produce a readable Markdown matrix for a reviewer.

## When not to use

- Provisioning, suspending or removing an actual account: `hosting-account-lifecycle`.
- Measuring usage against quotas and reconciling invoices: `hosting-metering-reconcile`.
- Testing that tenants can't reach each other's data: `hosting-tenant-isolation`.
- Certifying compliance, setting prices or choosing a provider. The check finds contradictions in a catalogue; it doesn't judge whether the commitments are wise.
- VPS or dedicated operations, managed cloud and advanced resilience are not profiles. Declare them as `capability_sets` inside the catalogue's profile.

## Inputs and prerequisites

- A catalogue JSON: `label`, `company` (must be `fixture-co`), `profile`, `capability_sets`, `parties`, and `services` with `functions` (`function`, `accountable`, `responsible`), `customer_visible_limits` (`name`, `value`, `unit`) and `upstream_dependencies` (`provider`, `service`, `obligations`, `escalation_path`). Parties are `fixture-co`, `customer` or `upstream:<slug>`, and each must appear in `parties`.
- `references/functions.json`: function ids per profile (`must_hold`, `optional`, `must_not_hold`) and per capability set, taken from the hosting profile requirements S05-001 to S05-010.
- The registry profiles file, `company-fleets/registry/profiles.json`, read by fixed path. It supplies each profile's name, `responsible_for` and `not_responsible_for` text. A `--profiles` path other than that file is refused (`profiles-not-registry-file`). This skill never edits it.

## Method

1. Run `check --catalogue F`. It validates the file first; an unknown function id, profile, capability set or party stops with exit 2.
2. Rule 1: each `must_hold` function of the profile and of every declared capability set has exactly one accountable party across the catalogue. Missing is a violation; two parties is a violation. Optional functions (shared `mail`) may be absent, but one that's listed needs one owner.
3. Rule 2: a `must_not_hold` function (affiliate: infrastructure, accounts, backups, restores, incident-response; reseller: hardware, network, data-center) is never accountable to `fixture-co`, and `fixture-co` is never in its `responsible` list. The affiliate profile is `referral_only`: `fixture-co` may hold only the six referral functions, accountable or responsible, and the catalogue may declare no capability set (`beyond-referral`). `upstream:fixture-co` is Fixture Co itself and counts as `fixture-co` in every rule, so naming the company as its own upstream fails the same way.
4. Rule 3: a function accountable to `upstream:<slug>` needs an `upstream_dependencies` entry for that provider in the same service, with non-empty obligations and escalation path. Placeholders such as `TBD`, `none`, `n/a` or `unknown` count as empty.
5. Rule 4: every customer-visible limit has a finite numeric value of 0 or more and a unit. A service that holds `quotas` lists at least one limit.
6. Fix each violation in the catalogue, not in the vocabulary, then rerun until the verdict is `pass`.
7. Run `matrix --catalogue F` (add `--format markdown` for raw Markdown) and hand the table to the reviewer with the structured file.

## Stopping conditions

- Verdict `pass` with every assumption in the output read and accepted.
- A violation that needs a business decision (who should own backups) goes to a human. Don't assign an owner to make the check pass.
- Exit 2: fix the input before judging anything.

## Output contract

`check` prints JSON: `verdict` (`pass` or `fail`), `profile` (registry id, name, responsible_for, not_responsible_for), `violations` (each with `rule` 1 to 4, `name`, `service`, `function`, `message`), `checked` (profile, capability sets, `must_hold`, `optional_absent`, `optional_present`) and `assumptions`. `matrix` prints JSON with `markdown` and `rows`, or raw Markdown with `--format markdown`. The matrix describes the catalogue and doesn't judge it. Cite the rule number and function id for every finding.

## Failure states

- Exit 0: verdict `pass`, or a matrix rendered.
- Exit 1: verdict `fail` with at least one violation, or a refusal (`profiles-not-registry-file`).
- Exit 2: bad JSON, a file that isn't UTF-8, missing file or flag, unknown function id, profile or capability set, non-hosting profile, a profile with no function coverage in `references/functions.json`, undeclared or malformed party, duplicate service id, or a registry file that lacks a hosting profile the vocabulary covers. Stdout is `{"error": "..."}`.
- Limit: a process running as the same OS user can rewrite the registry file or `references/functions.json`. Only separate OS accounts or signed records stop that.

## Adapters and missing capability

No adapters. Both inputs are local files. If the registry profiles file is missing, restore it from the rig; the check doesn't guess profile text and doesn't read a copy. The check can't confirm that an upstream provider actually performs the obligations a catalogue lists; a human reviews the provider's contract.

## References

`references/sources.md` lists the prompt lines behind `references/functions.json`, the registry file and the fixtures.

## Tests

```
cd skills/hosting-service-catalogue/scripts && python3 -W ignore -m unittest discover -s tests
```

## Evaluation cases

Fleet ids: `hosting.eval.service-catalogue-shared-valid`, `hosting.eval.service-catalogue-affiliate-valid`, `hosting.eval.service-catalogue-affiliate-backups-refused`, `hosting.eval.service-catalogue-missing-escalation`, `hosting.eval.service-catalogue-optional-mail-absent`, `hosting.eval.service-catalogue-two-accountable-refused`, `hosting.eval.service-catalogue-platform-managed-cloud-valid`. Model-run prompts are in `evals/evals.json`.

Cases that replay the 2026-11-26 independent review's probes: `hosting.eval.service-catalogue-affiliate-beyond-referral-refused`.

Cases that replay the hosting re-review's probes: `hosting.eval.service-catalogue-company-as-upstream-refused`, `-caller-profiles-refused`.
