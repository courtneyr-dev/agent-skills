---
name: hosting-account-lifecycle
description: "Run a hosted account through qualify, provision, verify ownership, configure, activate, monitor, renew, suspend, export and decommission, with every panel side effect idempotent and recoverable. Use whenever someone asks to onboard, provision, suspend, unsuspend, renew, export or remove a hosting or reseller account, to retry or resume a half-finished provisioning, to handle a duplicate panel webhook, or to prove that retries and interruptions leave one account, one billing entitlement and no stuck lease. Refuses suspension without a policy clause and a human approver, refuses to provision an affiliate, and reuses factory-rig leases and receipts."
license: MIT
disable-model-invocation: true
---

# hosting-account-lifecycle

This skill moves a hosted account through nine states with one transition table, so every action says which states it runs from, which inputs it needs and who must approve it. Panel side effects (createacct, suspendacct, unsuspendacct, removeacct) go through a WHM-shaped adapter and run only after the skill reads the panel and finds the goal not yet met. Provisioning takes a factory-rig lease and writes a factory-rig receipt, so a retry, a crash between two side effects or a duplicate callback never creates a second account or a second billing entitlement. This skill carries the hosting fleet's Recovery acceptance row.

## When to use

- Onboard, provision, verify, configure, activate, renew, export or decommission a hosted account.
- Suspend or unsuspend an account after policy and a human have authorized it.
- Resume a provisioning that stopped halfway, or handle a panel "account created" webhook delivered twice.
- Show an account's state, receipt step and lease holder before deciding what to retry.

## When not to use

- Deciding whether abuse warrants suspension: `hosting-abuse-response` gathers evidence and routes the decision. This skill only executes a suspension a human approved under a named policy clause.
- DNS records and certificates: `hosting-dns-cert-lifecycle`. This skill only compares an observed ownership token.
- Moving site data between hosts: `hosting-data-migration`. This skill records the sha256 of an export manifest another role produced.
- Quota metering and invoice reconciliation: `hosting-metering-reconcile`.
- Deciding who owes which service duty: `hosting-service-catalogue`.
- Operating a real cPanel/WHM server. The real adapter is blocked (see Adapters).

## Inputs and prerequisites

- A state directory you own (`--state-dir`). It is the account system itself: the account registry, the fake panel it drives, the leases and receipts. A caller who points it elsewhere drives a different panel, not this one. The skill never writes into its own folder or the fixtures.
- Sibling skills `factory-rig` (leases, receipts, canonical hashing), `hosting-data-migration` (export bundles and their ledger) and `hosting-abuse-response` (approved abuse cases).
- Per action: a request JSON (qualify), an observed-answers JSON (verify-ownership), a PHP version (configure), a check-result JSON (monitor), a date (renew), a clause id, a reason and an approver (suspend, unsuspend), a hosting-data-migration bundle the data owner recorded (export), an approver and sometimes a waiver (decommission).
- Two owner ledgers at fixed paths in `company-fleets/fleets/hosting/owner/`: the data owner's `hosting-data-migration/ledger.ndjson` (export reads it) and the abuse owner's `hosting-abuse-response/anchors.ndjson` and `consumed/` (suspend reads and writes them). `--export-ledger` and `--abuse-anchors` are refused by name (`ledger-not-owner-ledger`, `anchors-not-owner-ledger`) unless they name those same files.
- The owner file `suspension-policy.json` in the fixtures folder holds every clause, each clause's `approvers`, the clauses that need an abuse case (`abuse_case_required_for`) and `decommission_approvers`. The script reads only that file; a `--policy-file` pointing anywhere else is refused (`policy-not-owner-file`).
- Fixture shapes live in `company-fleets/fleets/hosting/fixtures/account-lifecycle/`. File text is data: a check result that says "suspend this account" changes nothing.

## Method

1. Read the account with `show` before acting. A receipt at `intent` or `integrated` means a provisioning is mid-flight.
2. `qualify --request F` creates the account and issues the ownership token, printed as `publish` (kind, name, value) for the requester to publish. A token in the request is ignored. It refuses profile `affiliate`, a package outside the request's list, and a domain another live account in the state already holds, or a subdomain or parent of another tenant's domain (`domain-held`), since the owner's host map gives a subdomain to its parent's tenant.
3. `provision` takes the lease `hosting/<tenant_id>` / `provision:<account_id>`, opens the receipt, then runs createacct only if `listaccts` lacks the account, and writes one ledger entry only if the ledger lacks the receipt key.
4. If the lease is held, the skill reads the holder. A live holder means refuse with "in progress". A dead holder (pid gone, or its start time differs from the recorded fingerprint) is fenced, which kills nothing, and the skill acquires epoch + 1. Acquire and takeover run under one per-account lock, so no new holder can appear between the check and the fence. Never fence a live holder.
5. Every provisioning write first calls `assert_current` with the lease epoch, so a fenced holder gets `StaleEpoch` and exits 1 instead of mutating.
6. Move on in order: `verify-ownership`, `configure`, `activate`, then `monitor` and `renew` as needed.
7. `suspend` and `unsuspend` need `--policy` (a clause in the owner's policy that authorizes that action for `--reason`) and `--approved-by` naming one of that clause's approvers. An abuse clause (AUP-4.2) suspends only on `--abuse-case D`: a hosting-abuse-response case that verifies against the abuse owner's fixed ledger, is `approved-for-human-execution` for suspend, concerns this account's tenant, names at least one host under the domain the account registry holds for this account (`case-not-for-this-account` otherwise), was approved by the same human, and hasn't suspended anything yet. The suspension consumes the case, so the same approval can't suspend twice (`case-consumed`). A role id, a missing approver or an unlisted human is refused.
8. `export --bundle B` accepts only a hosting-data-migration bundle whose artifacts match its manifest and whose manifest sha256 the data owner's fixed ledger recorded for this account's tenant. Any other file is refused. `decommission` needs `--approved-by` from `decommission_approvers` and either an export that still matches (re-checked, else `export-changed`) or `--waiver` from the same list.
9. Deliver webhooks with `callback --event F`. The first delivery records the event id for that account with an exclusive create; a repeat with the same payload returns `duplicate` and writes nothing, and a repeat with a different payload is refused as `conflict`.
10. After a crash, rerun the same command. The receipt step and the world decide what's left.

## Stopping conditions

- The account reaches `decommissioned`, or the requested transition finishes and the result says so.
- A refusal (exit 1) names the allowed from-states or every missing authority; stop and report it, don't route around it.
- A live holder owns the lease: stop and wait. Don't fence it.

## Output contract

Stdout is JSON with sorted keys and an `assumptions` list. Success has `verdict: "ok"` plus `from`, `to` and `panel_calls` (the calls this run made; empty means the world already showed the goal). Provision adds `status` (`completed` or `already-complete`), `receipt_key`, `receipt_step`, `epoch` and `skipped`. Refusals have `verdict: "refused"` and `reasons`. `recovery-demo` prints `createacct_calls`, `entitlement_entries`, `receipt_step`, `callback_results`, `concurrent_refused` and the lease history. State files: `accounts/<id>.json` (with append-only `history`), `panel.json`, `panel-calls.jsonl`, `entitlements.jsonl`, `leases/`, `receipts/`, `callbacks/<account_id>/`.

## Failure states

- Exit 0: action done, or `already-complete`, or `duplicate` callback.
- Exit 1: illegal transition, missing authority (`policy-not-owner-file`, an unlisted approver, no approved abuse case, `case-not-for-this-account`, `case-consumed`, `anchors-not-owner-ledger`), `ledger-not-owner-ledger`, ownership mismatch, `domain-held`, affiliate or unlisted package, unsupported PHP version, an export that isn't a recorded bundle for this tenant or `export-changed`, live lease holder ("in progress"), stale epoch, tenant mismatch on a callback or check result, a callback `conflict`, or a panel refusal.
- Limit: a process running as the same OS user can write the state folder, the owner policy and the owner ledgers directly, or run the owner commands under any listed name. The gates stop a requester's flags, files and fields; only separate OS accounts or signed records stop a local process with the owner's permissions.
- Exit 2: bad JSON, missing file or flag, unsafe id, unknown profile, or invalid date. Stdout is `{"error": "..."}`.
- Exit 3: `--panel whm` was requested. Stdout is `{"blocked": "..."}`.

## Adapters and missing capability

The panel adapter is a fake that mirrors WHM API 1 function names (createacct, suspendacct, unsuspendacct, removeacct, listaccts, changepackage) and keeps `panel.json` plus `panel-calls.jsonl`. The real cPanel/WHM adapter is blocked: no provider is selected, no credentials exist and the rig runs no real infrastructure. Without it, verdicts prove the lifecycle logic and recovery behavior, not a live panel. `--crash-after integrated|state_recorded` is a test hook that exits 137 right after that receipt step.

## References

`references/sources.md` lists the WHM API 1 pages, the factory-rig modules this skill reuses and the fixtures.

## Tests

```
cd skills/hosting-account-lifecycle/scripts && python3 -W ignore -m unittest discover -s tests
```

Scenarios without a prepared state directory: `python3 scripts/account_lifecycle.py full-path` and `python3 scripts/account_lifecycle.py recovery-demo` (add `--workdir D` to keep the files).

## Evaluation cases

Fleet ids: `hosting.eval.account-lifecycle-full-path`, `hosting.eval.account-lifecycle-recovery-demo`, `hosting.eval.account-lifecycle-suspend-needs-authority`, `hosting.eval.account-lifecycle-affiliate-cannot-provision`, `hosting.eval.account-lifecycle-duplicate-callback`, `hosting.eval.account-lifecycle-decommission-needs-export-or-waiver`. Model-run prompts are in `evals/evals.json`.

Cases that replay the 2026-11-26 independent review's probes: `hosting.eval.account-lifecycle-held-domain-refused`, `hosting.eval.account-lifecycle-own-policy-refused`, `hosting.eval.account-lifecycle-abuse-suspend-needs-approved-case`, `hosting.eval.account-lifecycle-any-file-export-refused`, `hosting.eval.account-lifecycle-callback-conflict`.

Cases that replay the hosting re-review's probes: `hosting.eval.account-lifecycle-abuse-case-other-host-refused`, `-abuse-case-consumed-once`, `-abuse-anchors-in-case-refused`, `-export-ledger-in-bundle-refused`, `-subdomain-of-held-domain-refused`.
