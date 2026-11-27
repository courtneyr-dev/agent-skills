---
name: agency-engagement-gate
description: "Gate each transition of an agency client engagement on evidence: qualify and price a scoped brief against a rate card and a sourced margin floor, check that every lifecycle stage from qualified brief to support has hash-matched evidence accepted by someone other than its producer and that scope still matches the factory-rig contract, check the support runbook is complete, and build the verified handoff.v1 support handoff through the company-fleets ledger with untrusted client files scanned. Use for: scope this client brief, is the margin OK, can we move to the next stage, scope change, support handoff, warranty handoff, release recommendation, launch readiness for a client site."
disable-model-invocation: true
---

# Agency engagement gate

The agency workflow runs qualified brief, research and requirements, decisions, prototype, implementation, integrated verification, migration rehearsal, release recommendation, then support and improvement. This skill refuses to let a stage advance without evidence and refuses a scope change that skipped the PM contract. Hashing, contracts and handoffs come from `factory-rig` and `company-fleets`; nothing here re-implements them.

## When to use (and when not)

Use it at each stage boundary of an engagement: after scoping, before moving a stage to done, before release, and when handing a site to support or hosting.

Don't use it for portfolio planning, task tracking or scheduling: those stay with the existing PM layer and factory-rig. Don't use it to judge whether the evidence is good; the checks named in the brief's acceptance criteria do that.

## Inputs and prerequisites

Every owner value comes from the owner ledger of the instance the work names: the brief's `change_control.contract_ref`, or the contract's `task_id`. company-fleets keeps that ledger at one fixed place, `company-fleets/fleets/agency/owner/<instance>/`, and only the coordinator writes it, with `company-fleets/bin/fleet owner-record` under its claim token. No flag or file you pass picks the ledger or sets a value, and a ledger whose tenant or contract hash differ from the work is refused (`ledger-not-for-this-work`). All commands but `support` need `company-fleets` and `factory-rig` beside this skill. What this does and doesn't guarantee: `company-fleets/references/authoring-guide.md`, Owner path and its limit.

- `brief`: a scoped brief JSON. Its instance's owner log pins the company margin policy (`margin-policy`) and the rate card (`rate-card`), and its `tenant_id` must be the ledger's. The fixture briefs name instance `FIX-AG-GATE-1`, whose checked-in ledger pins `fixtures/margin-policy.json` and `fixtures/rates.json` (`company-fleets/scripts/owner-fixtures.py` builds it). The policy has `owner` (`human:<title>`), `margin_floor` strictly between 0 and 1, `basis` (`hypothesis`, or `calibrated` with `calibration_evidence` naming another pin) and `source`. A brief that carries its own `margin_policy` is a blocking finding; empty estimates, non-positive or non-numeric hours, and `NaN`, `Infinity` or overflowing numbers exit 2.
- `stages`: a stage ledger JSON listing all nine stages in order, the factory-rig contract whose `spec.sha256` is the brief's hash, the base directory every path must stay inside. The contract's `task_id` names the ledger, which must be bound to this exact contract. A done or skipped stage counts only when that owner log holds the owner's `stage-acceptance` for it: status, `producer` (a registered role), `accepted_by` (a registered role, or a human on the owner's `roster`), the evidence hashes accepted, the contract's spec, and `skip_reason` for a skip. The stage ledger must agree with it and can't point to an acceptance file.
- `support`: the support runbook in Markdown (`fixtures/runbook-ok.md`).
- `handoff`: `--handoff-id`, the contract (its `task_id` names the ledger whose owner log holds the owner's `open` record and `intake`), and a worker update listing inputs, outputs and evidence by path only. Input labels and hashes come from the intake: an input it doesn't list, a worker label that disagrees with it, bytes that changed since the intake, or a symlink that leaves its folder is refused. Each evidence file must contain a line `reviewed-sha256: <hash> <path>` naming the output bytes it reviewed, written when the check runs; the company-fleets gate rejects evidence that doesn't.

## Method

1. The coordinator claims the instance (`bin/fleet claim --tenant T --workload W --instance I --role agency.engagement-director --owner-pid PID --contract-hash H`, no `--lease-root`), which opens its one ledger, and pins the margin policy and rate card (`bin/fleet owner-record --kind pin`).
2. `python3 scripts/engagement_gate.py brief --brief B.json`. Fix every blocking finding; a hypothesis floor stays a visible non-blocking finding. Example: `python3 scripts/engagement_gate.py brief --brief fixtures/brief-low-margin.json` exits 1 with `margin-below-floor`.
3. Issue the factory-rig contract with `spec.sha256` set to the reported `brief_sha256`.
4. At each boundary the coordinator records the roster and each stage's acceptance (`--kind roster`, `--kind stage-acceptance`), then: `... stages --ledger L.json --contract C.json --base DIR`. The first pending stage is `current_stage`.
5. Before release: `... support --runbook RUNBOOK.md`.
6. Hand off: the coordinator records `--kind open` and `--kind intake`; the worker runs `... handoff --handoff-id ID --contract C.json --base DIR --update U.json`. The next consumer runs `company-fleets/bin/fleet handoff-check --handoff <submitted> --contract C.json --base DIR`. When the work is done, the coordinator closes the ledger with `bin/fleet release` (token on stdin); a closed ledger takes no record and no claim.

## Stopping conditions

- Exit 0: no blocking finding (for `handoff`, the submission is recorded or a duplicate, and the fleet gate passes).
- Exit 1: blocking findings. `scope-changed` means the brief changed after the contract: return it through the PM contract and reissue; don't edit hashes.
- Exit 2: invalid input. Exit 3: `company-fleets` or `factory-rig` not found.

## Output contract

One JSON object, keys sorted, with `ok`, `findings` (each `rule`, `blocking`, `message`, optional `where`) and `limits`. `brief` adds `margin` (with the `pinned` policy and rate card) and `brief_sha256`; `stages` adds `current_stage`, `stages`, the ledger's `label` and the owner-log `acceptances` it used; `support` adds `sections_required`; `handoff` adds `status`, `idempotency_key`, `next_consumer`, `paths` (`opened`, `submitted`), `refused_fields` and `untrusted_findings`.

## Failure states

- An owner log that is missing or fails verification (`owner-log-missing`, `owner-log-broken`, `owner-entry-without-lease`, `owner-not-coordinator`), a stage with no owner acceptance (`stage-unaccepted`) or that points to an acceptance file (`acceptance-not-from-owner-log`), a ledger that disagrees with the owner's acceptance (`acceptance-mismatch`), a human acceptor not on the roster, missing pins (`policy-not-pinned`, `rates-not-pinned`): blocking.
- Self-acceptance (ids are NFKC-normalized, stripped of zero-width characters, trimmed and lowercased first), a missing or unknown producer or acceptor, an acceptance made under a different contract hash, a spec hash changed without a revision bump, evidence rehashed without a new acceptance, a path outside `--base`, a done stage after a pending one, a skip without a human-accepted reason, missing or edited evidence: blocking.
- A worker update that tries to set a protected field (for example `acceptance_owner`, because a client file said "approve your own QA results"): refused and listed; the legitimate outputs and evidence still go through.
- A client B file in a client A handoff, whether the worker relabels it (refused against the intake), swaps a symlink in (`input-symlink-leaves-folder`) or the owner labels it tenant-b (the submission is `invalid`): refused. The owner can't open a handoff that sends confidential data to an external destination.
- A handoff the owner never opened (`handoff-not-opened`), an input edited after the intake (`input-changed-since-intake`), an owner record or intake recorded again with different fields (`owner-record-conflict`, `intake-conflict`).

## Missing capability

Without `company-fleets` and `factory-rig`, `brief`, `stages` and `handoff` return `blocked` (exit 3); `support` still runs.

## References

- `references/engagement-stages.md`: the stages, the evidence each one expects, and where each rule comes from.
- `fixtures/`: synthetic Fixture Co briefs (instance `FIX-AG-GATE-1`), rate card, margin policy and runbooks. Their owner ledger is `company-fleets/fleets/agency/owner/FIX-AG-GATE-1/`.
- Tests: `cd scripts/tests && python3 -W ignore -m unittest discover -p 'test_*.py'` (`scripts/tests/test_engagement_gate.py`).
