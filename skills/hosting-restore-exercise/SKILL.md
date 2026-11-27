---
name: hosting-restore-exercise
description: "Run a real restore or disaster-recovery drill on a disposable local site: break it on purpose (process crash, corrupted database file, deleted database file), let a monitor detect it, restore the latest backup into a fresh data folder or fail over to a warm standby and fail back, then measure detection time, recovery time (RTO), lost writes (RPO) and restore success against stated targets. Unmet targets stay reported as unmet. Also hands the report to service assurance as a handoff.v1 and proves edited reports, logs or contracts fail the evidence gate. Use whenever someone asks to test backups, prove a restore works, run a DR, failover or business-continuity exercise, check RTO or RPO, or accept restore evidence."
license: MIT
disable-model-invocation: true
---

# hosting-restore-exercise

Backups count only once a restore from them has worked. This skill runs that restore on a
disposable local site (a SQLite file served by a local HTTP process), measures it, and keeps every
target's result as measured: `met`, `unmet` or `not-measured`. One lab run is a test result, never an
availability percentage or a service commitment.

## When to use

- Prove a backup restores, before a release hands a site to support or before a contract names a
  recovery objective.
- Run a business-continuity or disaster-recovery exercise, including failover and failback.
- Check that restore evidence handed to service assurance is fresh.

## When not to use

- Production hosts: this skill never touches them. A human operator runs the production drill with
  the same steps and records it as a separate result.
- Schema changes and customer exports: use `hosting-data-migration`.
- Declaring incidents and customer communication: use `hosting-incident-response`.
- Comparing results with provider claims: use `hosting-benchmark-matrix`, which reads this report.

## Inputs and prerequisites

- A targets file: `{"tenant_id", "source", "targets": {...}}` with any of `detection_seconds`,
  `rto_seconds`, `rpo_lost_writes` (`{"max": N}`) and `restore_success`, `failback_success`
  (`{"required": true}`). `source` says who proposed the targets and that no contract exists, if so.
- For the evidence gate: two owner files at fixed paths in
  `company-fleets/fleets/hosting/fixtures/restore-exercise/`, the factory-rig contract `contract.json`
  (its `spec.sha256` names the targets file) and the handoff owner record `handoff-owner.json` (producer,
  reviewer, acceptance owner). `--contract` and `--owner` are refused by name
  (`contract-not-owner-file`, `owner-record-not-owner-file`) unless they name those same files, so no
  caller file replaces the contract or its hash.
- Python 3.9+, a free loopback port. Nothing leaves 127.0.0.1.

## Method

1. Run `scripts/restore_exercise.py run --targets T [--failure crash|corrupt|delete] [--mode restore|failover]`.
   It seeds the site, starts it, takes a backup, makes `--writes-after-backup` writes (default 3),
   injects the failure, and polls the monitor until it reports unhealthy.
2. Restore mode copies the backup into a fresh folder with the SQLite backup API, checks the content
   checksum, starts a new process and points the router file at it. Failover mode points the router
   at a warm standby started from the backup, then fails back to a primary rebuilt from a standby
   backup.
3. The monitor must report healthy through the router with the backup's row count and checksum.
4. Read `targets`: each one is `met`, `unmet` or `not-measured`. Hand every unmet target to the
   production-readiness backlog through `hosting-benchmark-matrix`; don't relax a target to pass.
5. Hand the evidence over in three separate commands. The producer runs
   `run --targets T --handoff-dir H`, which writes `report.json` and `monitor-log.jsonl`. The reviewer
   the owner record names (`hosting.service-assurance-lead`) runs
   `review --handoff-dir H --targets T`: its own re-derivation of every target status, a check
   that the monitor saw the fault and the recovery, and one `reviewed-sha256:` line per output, in
   `review-check.txt`. An owner record naming the producer as reviewer is refused (`self-review`).
   Then `evidence-gate --handoff-dir H --targets T [--workdir D]` refuses a targets file that isn't the
   owner contract's spec (`spec.sha256`, `targets-not-in-contract`) or a handoff with no review
   (`handoff-incomplete`), opens the handoff.v1 from the owner record bound to the owner contract's
   hash, and
   must accept the fresh evidence and reject an edited report, an edited monitor log, an edited review
   file and a relaxed contract. The report edit always changes bytes, so an all-met run tests it too.
6. For post-incident learning, record findings with Magnus `incident-learning` templates.

## Stopping conditions

- The report exists with a verdict, or the run is blocked (exit 3). The script never retries a
  failed restore; a second attempt is a new exercise with its own report.

## Output contract

`run` prints the report: `exercise`, `backup`, `restore`, `measured` (`detection_seconds`,
`rto_seconds`, `rpo_lost_writes`, `restore_success`, `failback_success`), `targets` (each with
`target`, `measured`, `status`), `verdict` (`restored-all-targets-met`,
`restored-targets-not-all-met`, `restore-failed`), `unmet`, `timeline`, `assumptions`.
`monitor` prints one probe; it accepts only http URLs on 127.0.0.1, localhost or ::1 (anything else
exits 2). `review` prints `verdict` (`reviewed`, `review-failed` or `refused`). `evidence-gate` prints
`verdict` (`stale-evidence-rejected`, `gate-accepted-stale-evidence`, or `refused` when the fresh
handoff itself fails, with `refusal` or `fresh.errors`), `fresh`, `stale_cases`, `review`.

## Failure states

- Exit 1: a target unmet or not measured, a failed restore, an unhealthy monitor probe, a review that
  failed or was refused, a gate that refused the fresh handoff (`contract-not-owner-file` and
  `owner-record-not-owner-file` included), or a gate that accepted stale evidence.
- Exit 2: invalid input (unknown target name, non-numeric max, `required` not true, missing file,
  non-empty workdir for `run` or `evidence-gate`, a monitor log that isn't UTF-8, unreadable router, a
  monitor URL that isn't http on the loopback interface).
- Limit: a process running as the same OS user can rewrite `contract.json` or `handoff-owner.json`, or
  run all three steps under any listed name. Only separate OS accounts or signed records stop that.
- Exit 3: blocked, the local service didn't start or the monitor never saw the failure within 30 s.

## Adapters and missing capability

The lab needs no adapter. A production restore needs the operator's backup tool and a staging host;
none is configured for Fixture Co, so production restore results stay unverified and the benchmark
records them as `not measured`.

## References

`references/sources.md`: SQLite backup API, the Google SRE book's chapter on data integrity, NIST SP
800-34 contingency planning, and the Magnus skills this one hands to.

## Tests

```bash
cd ~/.claude/skills/hosting-restore-exercise/scripts && python3 -W ignore -m unittest discover -s tests
```

## Evaluation cases

Fleet cases in `company-fleets/fleets/hosting/evals.json`: `hosting.eval.restore-crash-detected-and-restored`,
`hosting.eval.restore-unmet-rpo-stays-unmet`, `hosting.eval.restore-corrupt-file-detected`,
`hosting.eval.restore-failover-failback`, `hosting.eval.restore-unmeasurable-target-not-met`,
`hosting.eval.restore-invalid-target-refused`, `hosting.eval.restore-stale-evidence-rejected`.

Cases that replay the 2026-11-26 independent review's probes: `hosting.eval.restore-relaxed-targets-refused`, `hosting.eval.restore-self-review-refused`, `hosting.eval.restore-monitor-local-only`.

Cases that replay the hosting re-review's probes: `hosting.eval.restore-caller-contract-refused`; `hosting.eval.restore-self-review-refused` now shows a caller's owner record refused by name.
