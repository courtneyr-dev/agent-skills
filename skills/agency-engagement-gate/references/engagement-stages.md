# Engagement stages and their evidence

Source: company-fleets requirements S04-001 to S04-019 (agency fleet, `company-fleets/registry/requirements.json`) and the cross-fleet handoff contract (`company-fleets/schemas/handoff.schema.json`)
Location: project requirements (not published)
Version or retrieved date: research baseline 2026-11-25
Rights: project requirements, paraphrased in the registry

Source: factory-rig contracts and company-fleets handoff.v1
Location: `skills/factory-rig/scripts/factory_rig/contract.py`, `skills/company-fleets/scripts/fleetlib/handoff.py`, `skills/company-fleets/schemas/handoff.schema.json`
Version or retrieved date: agent-skills, read 2026-11-25
Rights: agent-skills (MIT); imported, not copied

Source: Kanopi cms-cultivator pr-quality-report and code-standards-checker (installed)
Location: https://github.com/kanopi/cms-cultivator
Version or retrieved date: ff328fcc77af
Rights: GPL-2.0; the engineering stages call these skills, this skill doesn't copy them

## Stages

| Stage | Typical producer | Evidence the acceptor reads |
|---|---|---|
| qualified-brief | estimator, delivery lead | `brief` pass: qualification, scope, exclusions, assumptions, acceptance with evidence, margin against a sourced floor, change control through the PM contract |
| research-requirements | research strategist | research plan and observed findings from real participants; simulated users are fixtures, not findings |
| decisions | brand and design lead, solution architect, content strategist | decision records for brand, content model and architecture |
| prototype | UX/UI designer, design-systems lead | prototype plus `agency-keyboard-audit` and design-system contrast checks |
| implementation | web engineer, CMS specialist | code with tests and `code-standards-checker` output for the platform `agency-platform-adapters` selected |
| integrated-verification | QA engineer, accessibility specialist, i18n engineer, security reviewer, performance engineer | keyboard, i18n, security and performance evidence on the release candidate |
| migration-rehearsal | migration lead | a rehearsal log on staging, or a skip with a human-accepted reason when there is nothing to migrate |
| release-recommendation | release engineer | deployment plan, rollback and content freeze, accepted by the delivery owner |
| support-improvement | support handoff owner, training lead | `support` pass on the runbook and a recorded handoff.v1 that passes `fleet handoff-check` |

## Rules and why

- **Producer never accepts.** A settled stage counts only with the contract owner's acceptance in the owner log of the contract's instance (`fleet owner-record --kind stage-acceptance`, under the coordinator's claim token); a file the producer writes counts for nothing. The producer must be a registered role, the acceptor a registered role or a human on the owner's roster, and the two differ after normalizing. The worker's stage ledger must name the same status and producer, and a skip needs a human acceptor and a reason. This is the company-fleets rule that producing evidence and accepting it stay separate.
- **Evidence is hash-bound twice.** A stage's evidence counts only while its file bytes match the ledger's SHA-256 and that exact hash is in the owner's acceptance. Rehashing the ledger after an edit doesn't carry the old acceptance over. Every path must resolve inside `--base`.
- **Scope changes go back through the PM contract.** The brief's hash is the contract's `spec.sha256`, and each acceptance records the contract hash and spec revision it was made under. An edited brief stops the stages (`scope-changed`). A ledger is bound to the contract it was claimed under, so a rewritten or reissued contract refuses the old ledger and every acceptance in it (`ledger-not-for-this-work`); the reissued contract gets a new instance and new acceptances. The gate never edits a hash itself.
- **Margin floors are company policy, not brief content.** The floor and rate card come from pins the contract owner records in the owner log of the brief's instance (`change_control.contract_ref`); the caller can't pass either, a ledger of another tenant is refused, and a brief that sets its own floor is refused. A `hypothesis` basis keeps a visible finding until a person calibrates it, and a `calibrated` basis must name a pin holding the measured history.
