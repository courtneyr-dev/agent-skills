# Handoffs, ownership and boundaries

How fleets pass work to each other. The shape is `schemas/handoff.schema.json` (handoff.v1); the code is `scripts/fleetlib/handoff.py`, `ownership.py`, `tenancy.py` and `untrusted.py`.

## Who writes which field

| Writer | Fields |
|---|---|
| Contract owner, when the handoff opens | `handoff_id`, `workload_id`, `tenant_id`, `client_id`, `operating_profile`, `outcome`, `scope`, `exclusions`, `acceptance_criteria`, `sources`, `producer`, `reviewer`, `acceptance_owner`, `execution_owner`, `data`, `authority`, `budget`, `stop_conditions`, `cancellation`, `next_consumer`, `readiness_criteria`, `contract_hash` |
| Worker, while it works | `inputs`, `outputs`, `evidence`, `summary`, `assumptions`, `unresolved_decisions`, `untrusted_findings` |
| fleetlib | `schema_version`, `idempotency_key`, `reconciliation_state` |

The owner opens a handoff through the owner path: `bin/fleet owner-record --kind open` under the coordinator's claim token appends the owner fields to the instance's ledger (`fleets/<fleet>/owner/<instance>/owner-log.ndjson`) and writes `opened/<handoff_id>.json` once (`Ledger.open()`), and `--kind intake` records each input's labels and sha256. `apply_worker_update()` applies worker fields and returns every other field it was asked to change as refused. The gate (`bin/fleet handoff-check --handoff H --contract C --base B`, `ownerlog.check_submission()`) reads the ledger of the instance the contract names, refuses it when its tenant, workload or contract hash differ from the handoff's, and compares every owner field and every input with its log, so editing the handoff file afterward fails too, and so does a submission whose input the owner never listed. Cross-fleet workflow runs (`workflow.py`) record each handoff's owner fields in the run folder's own owner log, and resume and `fleet workflow verify` compare with that log, not with `opened/`. See `authoring-guide.md`, Owner path, for the threat model. Text in a client file, issue, community post, lesson resource or fetched page can make a worker propose a change; it can't make the change.

## Evidence that counts

Each evidence entry names the output it checked (`about`), that output's hash at the time (`about_sha256`), its own hash, and the factory-rig contract hash. `evidence_errors()` recomputes all of them with factory-rig's `sha_file` and `contract_hash`. Evidence is stale, and the handoff fails, when:

- the output changed after the handoff recorded it
- the evidence file changed after it was recorded
- the contract changed since the handoff or the evidence was bound to it
- the evidence checked an older version of the output
- an output has no fresh evidence, or the handoff has no outputs at all
- an evidence path is itself an output
- the evidence file doesn't contain the `about_sha256` it claims to have reviewed. Write it as a line `reviewed-sha256: <hash>`. Rehashing a changed output without a new review leaves the old review stale.

The seven cases live in `fixtures/stale-evidence/cases.json`.

## Retries

`idempotency_key` is factory-rig's receipt key over the workload, `handoff_id`, producer and consumer, contract hash and output hashes. `Ledger.submit()` refuses a handoff its owner never opened or whose owner fields differ, then stores one file per key under `submitted/`: a retry returns `duplicate`, a different body under the same key returns `conflict`, and two racing submitters can't both win. Every submission starts `submitted` whatever state the caller sent. `Ledger.reconcile()` settles each one through the full gate, recomputed now, and leaves settled ones alone.

## One coordinator per workload

`bin/fleet claim` takes a factory-rig lease keyed on tenant, workload and instance. Only the workload's coordinator may claim it; another fleet's coordinator, a specialist, or a second copy of the same coordinator is refused until the holder releases with its epoch, or its lease expires after its process is gone. A live holder past expiry blocks everyone until factory-rig's `LeaseStore.fence()` stops it.

## Tenants and classification

- A record stays in its tenant unless it's public, an approved abstraction, or covered by a grant a `human:` principal approved.
- An approved abstraction is a separate derived record: `approved_abstraction: true`, `derived_from` naming its source, and a classification of public or internal. The flag on a confidential or restricted record lifts nothing.
- Student records and moderation cases never cross on the abstraction rule; only a human-approved grant moves them.
- Handoff inputs pass through the same `can_read()` rule, read as the handoff's tenant at the handoff's label. A handoff can't take a non-public input from another tenant, can't label itself lower than its most sensitive input, can't name another tenant as a destination, and can't send confidential or restricted data to an `external:` destination.
- An input with `category` `student-record` or `moderation-case` keeps the handoff inside the producer's fleet and its own `tenant:` destination.
