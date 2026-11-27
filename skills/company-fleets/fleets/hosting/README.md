# Hosting and application-platform fleet

The hosting fleet covers Fixture Co's hosting business from affiliate referral through reseller,
shared, managed, platform and enterprise service, with 26 roles, 17 workloads and 10 original skills
that run real checks on disposable local services. Every company, tenant and record here is a
synthetic fixture. Nothing in this fleet touches a production host, a real panel, a real DNS zone or a
real customer.

State on 2026-11-26 (local date of the eval runs), after the fixes for the independent review in
`company-fleets/evidence/reviews/hosting.md` and for its re-review in `hosting-rereview.md`, measured in
the working tree:

- `bin/fleet validate --strict` passes with 0 errors and 0 warnings.
- 170 script cases pass: 91 original, 39 that replay the first review's probes and 40 that replay the
  re-review's. 166 ran in a temporary copy of the skills root. The 4 Docker cases ran in place, because
  Docker mounts only the folders it shares and the copy sits in a temp folder it doesn't.
- 444 unit tests pass on Python 3.14.7 and again on 3.9.
- 6 model-judgment cases are not-run, because the fleet's builder graded their only sample. 1 case is
  blocked (Terraform isn't installed).

A clean checkout passes the same suites only after the new and moved files are committed; the
change's report lists the paths that need `git add -f`.

## Run a hosting workload

The router picks the workload; the fleet never dispatches.

```bash
cd skills/company-fleets
bin/fleet resolve --profile managed --workload hosting.workload.restore-exercise
bin/fleet claim --lease-root STATE/leases --tenant tenant-a --workload hosting.workload.restore-exercise \
  --instance drill-1 --role hosting.general-manager --owner-pid $$ --contract-hash HASH
```

`resolve` lists the roles and the skill paths to load; only those load. Only
`hosting.general-manager`, the fleet's one coordinator, can claim a workload instance, and a second
claim on the same instance is refused by the factory-rig lease. Release with
`bin/fleet release ... --epoch N` when the work ends.

## Profiles and workloads

| Profile | Workloads |
|---|---|
| affiliate | `affiliate-referral`, `service-catalogue` |
| reseller | `account-lifecycle`, `service-catalogue`, `dns-cert-cutover`, `site-migration`, `customer-exit`, `metering-billing`, `abuse-report` |
| shared | the reseller set, plus `restore-exercise`, `incident-response`, `tenant-isolation-review`, `vps-server-operations` |
| managed | the shared set without `vps-server-operations`, plus `resilience-exercise`, `benchmark-readiness`, `agency-support-handoff` |
| platform | the managed set, plus `untrusted-app-build`, `managed-cloud-operations` |
| enterprise | the managed set without `agency-support-handoff`, plus `vps-server-operations` (dedicated tenancy), `managed-cloud-operations` |

VPS and dedicated servers, managed cloud/PaaS and advanced resilience aren't operating profiles in
`registry/profiles.json`; they're the workloads `vps-server-operations`, `managed-cloud-operations`
and `resilience-exercise`. An affiliate holds no operator duty: `hosting-service-catalogue` refuses a
catalogue that makes Fixture Co accountable for an affiliate's infrastructure, backups or incidents.

## Roles

Each required title from section 5 of the prompt has one role record in `roles.json`, plus
`hosting.support-handoff-owner`, which takes agency releases into managed hosting. A persona is a
professional viewpoint: no biography, credential, employer or authority.

| Section 5 title | Role id |
|---|---|
| Hosting general manager | `hosting.general-manager` (coordinator) |
| Product/service designer | `hosting.service-designer` |
| Partner manager | `hosting.partner-manager` |
| Solutions architect | `hosting.solutions-architect` |
| Platform engineer | `hosting.platform-engineer` |
| Linux/system administrator | `hosting.systems-administrator` |
| cPanel/WHM specialist | `hosting.panel-specialist` |
| DNS/domain engineer | `hosting.dns-domain-engineer` |
| Network/edge engineer | `hosting.network-edge-engineer` |
| Database reliability engineer | `hosting.database-reliability-engineer` |
| Storage/backup engineer | `hosting.storage-backup-engineer` |
| Build/runtime engineer | `hosting.build-runtime-engineer` |
| SRE | `hosting.site-reliability-engineer` |
| Observability engineer | `hosting.observability-engineer` |
| Capacity/FinOps analyst | `hosting.capacity-finops-analyst` |
| Security engineer | `hosting.security-engineer` |
| Vulnerability/abuse response | `hosting.abuse-response-analyst` |
| Incident commander | `hosting.incident-commander` |
| Communications coordinator | `hosting.communications-coordinator` |
| Release/change manager | `hosting.change-manager` |
| Migration specialist | `hosting.migration-specialist` |
| Support tiers | `hosting.support-engineer` |
| Technical account management | `hosting.technical-account-manager` |
| Billing/entitlements | `hosting.billing-entitlements-analyst` |
| Service assurance | `hosting.service-assurance-lead` |

Producers never accept their own evidence: specialists hand to `hosting.service-assurance-lead` or a
named human (`human:hosting-operations-owner`, `human:security-owner`, `human:abuse-policy-owner`,
`human:communications-approver`, `human:change-approver`, `human:finance-owner`,
`human:hosting-business-owner`, and each tenant's data owner such as `human:tenant-a-owner`). Who may
approve what is written in owner files, not in the request or artifact being checked (next section).

## Owner records: where each gate gets its trusted values

A gate takes a trusted value only from a record its owner wrote, never from the artifact, label or flag
the checked party supplies (authoring guide, "Gate trust rule"). Two kinds of owner record exist, and
each sits at one fixed path:

- Owner files (policies, SLO, contract, price list, terms, disclosure log, issuer, released hosts,
  advisories, targets) live in `fixtures/<skill>/`, `benchmark/` or the rig registry. No gate reads one
  from a flag. A flag that names a different file is refused by name (`policy-not-owner-file`,
  `slo-not-owner-file`, `contract-not-owner-file`, `prices-not-owner-file`, and so on); `--issuer` is
  refused outright.
- Case-specific owner values are written by an owner command into a ledger under
  `owner/<skill>/` in this folder: `hosting-incident-response/anchors.ndjson`,
  `hosting-abuse-response/anchors.ndjson` and `consumed/`, `hosting-data-migration/ledger.ndjson`,
  `hosting-tenant-isolation/records/<preview_id>/`. The consumer reads only what that ledger holds.
  A ledger, anchors or records path the caller names is refused by name (`anchors-not-owner-ledger`,
  `ledger-not-owner-ledger`, `records-not-owner-ledger`), and so is an artifact folder that sits in
  the owner folder or holds it (`record-inside-owner-ledger`, `case-inside-owner-ledger`,
  `anchor-inside-case`, `ledger-inside-artifact`). The ids that select an entry (incident id, case id,
  manifest hash, preview id) come from the artifact and resolve only inside that fixed folder.

| Gate | Owner record the gate reads | Written by |
|---|---|---|
| Abuse suspension | `abuse-response/policies.json` (clauses, approvers), `tenant-hosts.json`; `owner/hosting-abuse-response/anchors.ndjson` | `approve`; every intake and propose appends the custody head |
| Account suspend | `account-lifecycle/suspension-policy.json`; the approved abuse case verified against the abuse anchors; the account's domain in the account registry (state folder); `owner/hosting-abuse-response/consumed/<case_id>.json` | `hosting-abuse-response approve`; `qualify`; the first `suspend` consumes the case |
| Account export, decommission | `owner/hosting-data-migration/ledger.ndjson`; the issued token and domain registry in the state folder | `data_migration.py export`; `qualify` |
| Bundle import, rollback | `owner/hosting-data-migration/ledger.ndjson` (manifest sha256 and tenant; backup database, file hash, content checksum; the checksum a migration left) | `export`, `migrate` |
| Incident resolve, comms, show | `incident-response/slo.json`, its sha256 pinned at `open`; `owner/hosting-incident-response/anchors.ndjson`; `comms-approvers.json` | `open`, every append, `approve` |
| Preview promotion | `owner/hosting-tenant-isolation/records/<preview_id>/{scan,sandbox,dependencies,approval}.json`, bound to the preview's content hash (its text and every file in its build and source folders); `promotion-policy.json`; `secrets-manifest.json`; `advisories.json` | `secrets scan --record-for` (scans the preview's own build folder), `sandbox-build --record-for` (the harness probe on the preview's own source), `record-dependencies` (the preview's own lockfile), `approve` |
| Cross-tenant grant | `tenant-isolation/tenant-owners.json` | the tenant's data owner |
| Restore evidence | `restore-exercise/contract.json` (`spec.sha256` = the targets file) and `handoff-owner.json` (producer and reviewer) | the contract owner; `review` (a separate command) |
| Benchmark measurement, target, contract | `evidence/benchmark-evidence-manifest.json` (file sha256, and the file and JSON path per dimension), `benchmark/targets.json`, `benchmark/contracts.json`, read from the rig, never `--root` or the matrix | `benchmark.py record-evidence --dimension --json-path` when evidence is produced; hosting operations |
| DNS CAA, dangling records | `dns-cert/issuer-policy.json`, `dns-cert/decommissioned.json` | the platform engineer |
| Reconcile, commission | `metering/prices.json` (with `max_tolerance`), `terms.json`, `disclosure-log.json` | finance; Fixture Co's site |
| Catalogue profiles | `company-fleets/registry/profiles.json` | the integrator |

What this guarantees: a submitter that holds only the gate commands, its own artifacts and its own
flags can't make a gate accept a value the owner didn't record, can't name the file or ledger a gate
trusts, and every probe from both reviews fails with a named reason.

What a process running as the same OS user can still do, because nothing in these scripts can see who
runs them:

- Write the owner folder and the owner files directly: append an anchor or a record, rewrite a ledger
  line (these ledgers carry no hash chain of their own), delete a `consumed/` marker, or edit a policy,
  SLO, contract, price list, issuer or advisory file.
- Run any owner command under any listed name, such as `approve --by human:abuse-policy-owner`,
  `data_migration.py export`, `benchmark.py record-evidence` or `sandbox-build --record-for`. The
  scripts can't check who typed `--by`.
- Run a modified copy of a script, or repoint a module's `OWNER_ROOT` in its own Python process, as
  the unit tests do.
- Point `account_lifecycle.py --state-dir` at a state folder it wrote. That drives that folder's fake
  panel only, never the account system's.

Closing that gap takes OS separation (the owner folder and owner files writable only by the owner's
account, workers running as another user) or signed records. The rig does neither today. The real
panel step's own sign-in is the check on who executes a suspension.

## Skills

### Written for this fleet

| Section 5 procedure | Skill | Script |
|---|---|---|
| Account lifecycle; reseller provisioning; Recovery row | `hosting-account-lifecycle` | `scripts/account_lifecycle.py` |
| Service catalogue and responsibility matrix | `hosting-service-catalogue` | `scripts/catalogue_check.py` |
| Tenant isolation, secrets, audit trail, build boundaries, AI-generated app hosting | `hosting-tenant-isolation` | `scripts/isolation_check.py` |
| DNS and certificate lifecycle | `hosting-dns-cert-lifecycle` | `scripts/dns_cert.py` |
| Backup restoration, recovery, BC/DR exercises, failover and failback | `hosting-restore-exercise` | `scripts/restore_exercise.py`, `scripts/site_service.py` |
| Data migration, upgrade compatibility, rollback, portable export and exit | `hosting-data-migration` | `scripts/data_migration.py` |
| SLI/SLO, alert routing, incident command, post-incident learning | `hosting-incident-response` | `scripts/incident.py` |
| Capacity, quotas, metering, billing, cost attribution, commissions | `hosting-metering-reconcile` | `scripts/metering.py` |
| Abuse handling with evidence preservation | `hosting-abuse-response` | `scripts/abuse_case.py` |
| "More robust" benchmark and readiness backlog | `hosting-benchmark-matrix` | `scripts/benchmark.py` |

### Adopted from installed upstream skills

Attached by id, never copied: Magnus Hedemark's `production-readiness`, `incident-learning`,
`release-engineering` and `verification-methodology` (MIT); Alireza Rezvani's
`partnerships-architect`, `channel-economics`, `customer-success-manager`, `support-ops`,
`capacity-planner` and `access-lifecycle` (MIT); HashiCorp's `terraform-test` and
`terraform-style-guide` (MPL-2.0); Cloudflare's `cloudflare-one` and `workers-best-practices`
(Apache-2.0, reference use only without a Cloudflare account); Trail of Bits' `differential-review`
and `supply-chain-risk-auditor` (CC BY-SA 4.0).

## Acceptance rows and where the proof is

| Row | Cases | Evidence |
|---|---|---|
| Hosting: a failure is detected, restoration works, unmet targets stay unmet | `restore-crash-detected-and-restored`, `restore-corrupt-file-detected`, `restore-unmet-rpo-stays-unmet`, `restore-unmeasurable-target-not-met` | `evidence/evals/restore-*.txt`, `evidence/restore-exercise-2026-11-26.json` |
| Recovery: retries, interruption and callbacks don't duplicate work | `account-lifecycle-recovery-demo`, `account-lifecycle-duplicate-callback`, `gm-second-claim-refused` | `evidence/evals/account-lifecycle-*.txt` |
| Tenant boundaries | `tenant-isolation-records-isolated`, `tenant-isolation-abstraction-mislabel-caught`, `tenant-isolation-sandbox-isolated`, `tenant-isolation-sandbox-control-leaks` | `evidence/evals/tenant-isolation-*.txt` |
| Evidence integrity | `restore-stale-evidence-rejected`, `benchmark-tampered-measurement-refused`, `abuse-response-tampered-evidence-refused` | `evidence/evals/` |
| Untrusted content | `abuse-response-embedded-instruction-ignored`, `tenant-isolation-promote-embedded-instruction`, `abuse-analyst-ignores-embedded-order` | `evidence/evals/`, `evidence/persona-evals-2026-11-26.txt` |
| "More robust" | `benchmark-*` cases | `benchmark/2026-11-26-matrix.json`, `benchmark/2026-11-26-matrix.md`, `benchmark/2026-11-26-readiness-backlog.md` |

The restore drill with its follow-up improvement (demonstration 2 in the prompt): the proposed
zero-loss RPO stays unmet (3 writes lost after the last backup), and the readiness backlog's first
item is to add log shipping or shorten the backup interval.

## Requirement rows S05-001 to S05-027

`requirements-map.json` holds the proposed status, deliverable and blocker for each of the 27 hosting rows in `registry/requirements.json`, in that file's field names, for the integrator to merge. Deliverable paths are relative to the rig skills root and every one exists.

- Delivered in full (15): S05-001, S05-010, S05-011, S05-012, S05-013, S05-015, S05-016, S05-017, S05-018, S05-019, S05-020, S05-022, S05-025, S05-026, S05-027.
- Blocked (12): the deliverable holds the part that exists and the blocker names what's missing.
  `bin/fleet coverage --sync` copied these statuses into `registry/requirements.json`.
  - S05-002: Reseller billing and provisioning run through a fake WHM-shaped adapter; no upstream provider is selected.
  - S05-003: Real cPanel/WHM adapter blocked: no provider selected, no credentials; mail is optional and not exercised.
  - S05-004: Covered as a workload, not a profile; no real VPS, Plesk or other panel is exercised.
  - S05-005: Compatibility, security and migrations are built and tested; staging, content workflows and multisite operations have no procedure yet.
  - S05-006: Identity, custom domains and quota enforcement for the developer platform have no runtime demo; builds, previews, secrets, rollback and exportability do.
  - S05-007: Terraform checks blocked: the terraform binary is not installed; plan-only and mocked-provider use is documented, never apply.
  - S05-008: Audit trail, data boundaries and change control are tested; SSO/RBAC and dedicated tenancy have no procedure or adapter yet.
  - S05-009: Failover, failback and restoration are tested on one machine; multi-region failure domains and supply-chain resilience are not exercised.
  - S05-014: Identity (SSO) boundaries have no procedure yet.
  - S05-021: No provider is selected and no credentials exist, so the cPanel/WHM and reseller adapters are fakes that mirror WHM API 1 function names; a real adapter needs a chosen provider.
  - S05-023: No plan or contract exists for Fixture Co, so the contractual-commitment column is empty by design.
  - S05-024: performance_under_load, support, accessibility, regions and cost have no measurement yet; they stay not-measured.

## Review findings, before and after

Each "before" is the review's probe on the code as reviewed; each "after" is the same input now. Proof
names the eval case (prefix `hosting.eval.`) or unit test that replays it. M15 was wrong (see its row).

| # | Before | After | Proof |
|---|---|---|---|
| B1 | Undotted CNAME, MX, NS, A to a retired host and apex named by origin: `pass` | `dangling-record` / `apex-cname`, exit 1 | `dns-cert-undotted-dangling-cname`, `dns-cert-dangling-mx-ns-a` |
| B2 | Affiliate accountable for 7 infra functions, responsible for backups: `pass` | `beyond-referral` / `must-not-hold`, exit 1 | `service-catalogue-affiliate-beyond-referral-refused` |
| B3 | Resolve with a saved `violation` verdict or a 1-byte file: `resolved` | `recovery-evidence-invalid`; still-failing events `not-recovered` | `incident-response-resolve-still-down-refused` |
| B4 | 20-minute run plus one old event: claim `100.0000%` | `insufficient-window`, 1 of 24 hours covered | `incident-response-claim-lab-run-plus-old-event-refused` |
| M1 | Builder's preview claims clean scan, sandbox, deps, own approval: `promote` | claims ignored; re-scan finds 2 secrets; owner records refuse | `tenant-isolation-promote-builder-claims-ignored` |
| M2 | Grantee self-approved grant on tenant-b log, creds, backup: 3 reads | 0 reads; 3 grants listed under `ignored_grants` | `tenant-isolation-self-granted-read-denied` |
| M3 | Tenant-b qualifies tenant-a's domain with tenant-a's token: verified | `domain-held`; tokens issued at qualify | `account-lifecycle-held-domain-refused` |
| M4 | Analyst policy, any `human:` approver suspends (abuse, account); self-approved comms | `policy-not-owner-file`, `approver-not-authorized`, `approval-needs-approve-step` | `abuse-response-analyst-policy-refused`, `-unlisted-approver-refused`, `account-lifecycle-own-policy-refused`, `-abuse-suspend-needs-approved-case`, `incident-response-drafter-cannot-approve-own-update` |
| M5 | Any file as export, then `removeacct` | only a ledger-recorded bundle for this tenant; re-checked at decommission | `account-lifecycle-any-file-export-refused` |
| M6 | Case, record, bundle, backup or benchmark evidence rehashed in place: accepted | head or hash differs from the owner's anchor, ledger or manifest | `abuse-response-rewritten-case-refused`, `incident-response-rehashed-record-refused`, `data-migration-rehashed-bundle-refused`, `-relabeled-bundle-refused`, `-edited-backup-refused`, `benchmark-rehashed-evidence-refused` |
| M7 | Producer wrote the review; relaxed targets turned unmet into met | `review` is a separate command; `targets-not-in-contract`; `self-review` | `restore-relaxed-targets-refused`, `restore-self-review-refused` |
| M8 | `kind: production`, `"contract": "yes"`, 7 superiority or SLA wordings: `pass` | evidence must be a 30-day slo-check claim; registry-only contracts; the 7 wordings refused. The re-review found phrasings and fields this missed (its major 7 and minor 4, below) | `benchmark-lab-labeled-production-refused`, `-self-declared-contract-refused`, `-named-provider-comparison-refused` |
| M9 | 6 roles verified on builder-graded samples | 6 unverified; `evalrun.py roles` fails the old state (12 problems) | `evalrun.py roles` |
| M10 | A-to-CNAME cutover with a 1-day A TTL: `pass` | `ttl-before-change` | `dns-cert-a-to-cname-cutover-ttl` |
| M11 | Zone names its own CA and permits only it: `pass` | `caa-blocks-issuer`, `zone-issuer-ignored` | `dns-cert-zone-cannot-name-its-issuer` |
| M12 | EUR invoices, total 999.99, 9999 GB billed: `ok` | `currency_mismatch`, `total_mismatch`, `quantity_mismatch` | `metering-invoice-currency-total-quantity-checked` |
| M13 | Last point 0.95 over 0.8: `projected`, 18 days | `reached`, 0 days | `metering-capacity-already-over-is-reached` |
| M14 | Referral row sets `disclosure_shown: true`: not flagged | owner disclosure log decides; `disclosure-claim-unverified` | `metering-forged-disclosure-flag-refused` |
| M15 | `VACUUM INTO` file appears after import | Wrong: the probe's own manifest recompute ran the SQL with no authorizer and wrote it; import at HEAD writes nothing | `test_vacuum_into_in_a_bundle_writes_nothing_outside` |
| M16 | Bundle with no tenant imports into tenant-b | export needs `--tenant`; import takes the tenant from the ledger | `data-migration-untenanted-export-refused` |
| M17 | Rollback restores site-a's backup onto site-b | ledger holds no backup of site-b: refused | `data-migration-other-site-backup-refused` |
| M18 | Content wiped with counts kept; malformed or no directives: `migrated` | content compared; malformed or missing directive exit 2; unstated tables refused | `data-migration-content-wipe-caught`, `-unstated-tables-refused` |
| M19 | `{"requires": {}}`: `compatible`, 0 checks | refused, 0 checks; unknown key exit 2 | `data-migration-empty-preflight-refused` |
| m1 | `run` overwrote evidence without `--write` | writes only with `--write` | git status after `evalrun.py run` |
| m2 | Folder Docker can't see: `leak`, exit 1 | trusted mount check: `blocked`, exit 3 | `test_a_folder_docker_cannot_see_is_blocked_not_a_leak` |
| m3 | All-met run: report edit changed no bytes, wrong verdict | edit always changes bytes; refused fresh handoff is `refused` | `test_an_all_met_run_still_rejects_an_edited_report` |
| m4 | `monitor --url file://...` read a file | http on loopback only, exit 2 | `restore-monitor-local-only` |
| m5 | Tenant-b report opened as tenant-a and approved | `tenant-mismatch` from the owner host map | `abuse-response-wrong-tenant-refused` |
| m6 | Callback ids global; changed retry dropped silently | per account; changed retry `conflict` | `account-lifecycle-callback-conflict` |
| m7 | README said no other fleet names a hosting role | names the three workflows and the check to run | this README, "Roll back" |
| m8 | 12 rows `delivered` with blockers | `blocked` | `requirements-map.json` |
| m9 | Coordinator's cancellation told itself | tells `human:hosting-business-owner` and the router | `roles.json` |
| m10 | `window_days: "thirty"`: traceback | exit 2 | `test_a_non_numeric_window_is_invalid_input` |
| m11 | DNS: in-zone missing target, type `FOO`, TTL 2^40, `message` doc, `*.example` SAN | `missing-target`; exit 2; exit 2; doc says `detail`; no match | `test_in_zone_target_with_no_records`, `test_unknown_type_and_huge_ttl_are_invalid_input`, `test_wildcard_over_a_single_label_matches_nothing` |
| m12 | Forged resolve crashed `show`; evidence never re-hashed; `--at 2001` silent | `tampered-record`; `evidence-changed`; `recorded_at` beside `ts`, `backdated` flagged, future refused | `test_a_forged_resolve_without_evidence_is_a_tampered_line_not_a_crash`, `test_resolve_records_the_evidence_hash_and_show_rechecks_it`, `test_backdated_open_is_flagged_and_a_future_one_refused` |
| m13 | Padded or renamed retries billed twice; duplicate referral and quota rows; sub-cent amounts | counted once and flagged; exit 2; exit 2; exit 2 | `test_padded_or_renamed_retries_count_once_and_fail`, `test_a_duplicate_referral_row_refuses_the_file`, `test_duplicate_quota_rows_refuse_the_file` |
| m14 | `TBD` escalation, NaN or -30 limit, another company: `pass` | rule 3 and rule 4 violations; exit 2 | `test_placeholder_escalation_and_obligations_are_empty`, `test_nan_and_negative_values_are_violations`, `test_company_must_be_fixture_co` |

## Re-review findings, before and after

The re-review is `company-fleets/evidence/reviews/hosting-rereview.md`. "Before" is
its result on that HEAD; the X2, major 1 (DNS, metering), major 5, major 6, major 7, major 8, minor 4
and minor 8 results were rerun on a copy of that HEAD for this table and matched. "After" is the same
input now. Proof names the eval case (prefix `hosting.eval.`) or unit test that replays it.

| # | Before | After | Proof |
|---|---|---|---|
| X1 | 29 git-ignored fixtures missing from HEAD; a clean checkout failed validate and 28 cases | fixed before this round; new files here use names the ignore rules don't match, except the ones the change's report lists for `git add -f` | the clean-checkout run in the change's report |
| X2 | log clean to 12:35Z, half 503s from 12:36Z: `resolve --at 12:35Z` gave `resolved`, exit 0 | `not-recovered` with `later_outage.at` 12:36Z, exit 1: every event after the recovery point is judged | `incident-response-resolve-clean-then-down-refused`, `test_resolve_judges_every_event_after_the_recovery_point` |
| 1, metering | `commission --disclosures my-disclosures.json`: `ok` | `disclosures-not-owner-file`; terms and prices are owner files too | `metering-caller-disclosures-refused` |
| 1, DNS | `zone-check --issuer evil-ca.example`: `pass` | `issuer-not-owner-file`; the zone alone fails `caa-blocks-issuer` | `dns-cert-issuer-flag-refused` |
| 1, restore | `evidence-gate --contract contract-mine.json` with relaxed targets: `restored-all-targets-met` | `contract-not-owner-file`; another `--owner` is `owner-record-not-owner-file` | `restore-caller-contract-refused`, `restore-self-review-refused` |
| 1, incident | `open --slo lax-slo.json`, then resolve on a still-failing log: `resolved` | `slo-not-owner-file` at open and at resolve; open pins the owner's `slo.json` | `incident-response-caller-slo-refused` |
| 2, account export | `export --export-ledger bundle/ledger.jsonl`, then `removeacct` | `ledger-not-owner-ledger`; export reads only the data owner's fixed ledger; no `removeacct` | `account-lifecycle-export-ledger-in-bundle-refused` |
| 2, migration import | `import --ledger mine.jsonl` imported a forged bundle | `ledger-not-owner-ledger`; without the flag, `matches no export` | `data-migration-caller-ledger-refused` |
| 2, incident and abuse anchors | a rewritten record or case plus a one-line ledger the submitter wrote: `resolved`, `intact` | `anchors-not-owner-ledger`; without the flag, `anchor-mismatch` and `tampered` | `incident-response-caller-anchors-refused`, `abuse-response-caller-anchors-refused` |
| 2, account suspension | a relabeled tenant-b case with anchors in its folder suspended tenant-a | `anchors-not-owner-ledger`; without the flag the case fails verification | `account-lifecycle-abuse-anchors-in-case-refused` |
| 3 | an empty-folder scan, a script printing its own probe line and a hand-written report, then `approve`: `promote` | `scan-not-preview-content`; an empty `--src` is exit 2; the harness probe decides the sandbox; `report-not-from-lockfile`; records only in the fixed folder | `tenant-isolation-empty-folder-scan-refused`, `-owner-scan-covers-the-build`, `-empty-source-sandbox-invalid`, `-liar-build-control-leaks`, `-hand-written-report-refused`, `-caller-records-refused` |
| 4 | a case naming only `login.tenant-a.example` suspended `client-a.example`, and again after unsuspend | `case-not-for-this-account`; the first suspension consumes a case, a second gets `case-consumed` | `account-lifecycle-abuse-case-other-host-refused`, `-abuse-case-consumed-once` |
| 5 | `upstream:fixture-co` accountable for 5 affiliate functions: `pass`, 0 violations | `fail` with 5 `must-not-hold` | `service-catalogue-company-as-upstream-refused` |
| 6 | matrix `json_path` set to the target (AB1) or target `max` 5 (AB2): `met` | `measured-evidence` with `evidence-refused`; `target-not-on-record` with the status still `unmet` | `benchmark-matrix-json-path-refused`, `-matrix-target-refused` |
| 7 | 11 phrasings, among them "99.99 percent" and "Pantheon trails Fixture Co": `pass` | all 11 `fail`, also when written with fullwidth digits, zero-width characters or Cyrillic letters | `benchmark-reviewed-phrasings-refused`, `test_every_phrasing_from_the_re_review_is_refused` |
| 8 | change types `"CNAME "` and `" cname"`: `pass` | `ttl-before-change`; an unknown type is exit 2 | `dns-cert-padded-change-type-ttl` |
| m1 | 4 Docker tests raised `KeyError` in a folder Docker can't see | they skip with the blocked reason | `TempCase.docker_run` in `test_isolation_check.py` |
| m2 | `quick_validate` rejects all 10 SKILL.md files | unchanged on purpose: `disable-model-invocation` is a rig key the repo validator accepts; `evidence/skill-tests.txt` records the 10 failed `quick_validate` steps | `evalrun.py skills` |
| m3 | non-UTF-8 input: traceback, exit 1; a reused `evidence-gate --workdir`: `FileExistsError` | exit 2 with a named error across 23 inputs in all 10 scripts; reused workdir exit 2 | unit tests with `non_utf8` in their names |
| m4 | claim summaries, subject, contract note and `source` keys unscanned; string-shaped fields gave tracebacks | scanned; exit 2 | `benchmark-claim-summary-and-subject-scanned`, `-string-shaped-field-invalid` |
| m5 | an extra profile gave a `KeyError` traceback | exit 2 with a named error; `--profiles` is refused | `service-catalogue-caller-profiles-refused`, `test_a_profile_without_function_coverage_is_invalid_input_not_a_crash` |
| m6 | a renamed retry at the same instant in another format counted twice; `--tolerance` uncapped; `--prices` a caller file | counted once and flagged; `tolerance-above-owner-max`; `prices-not-owner-file` | `metering-retry-same-instant-counted-once`, `-tolerance-above-owner-max-refused` |
| m7 | a U-label entry missed its punycode target; `::ffff:198.51.100.7` missed; no `--decommissioned` meant no check | matched; matched; the owner list is always read | `dns-cert-ipv4-mapped-aaaa-dangling`, `-dangling-checked-without-a-flag`, `test_a_u_label_entry_catches_its_punycode_target_and_the_reverse` |
| m8 | `ATTACH ... CREATE TABLE o.leak` in a migration: `migrated`, a second database written | `rolled-back` (not authorized), nothing written | `data-migration-attach-in-migration-refused` |
| m9 | rollback restored onto whatever database sat at the recorded path | `db-changed-since-migration`, database untouched | `data-migration-swapped-database-rollback-refused` |
| m10 | tenant-b qualified `shop.client-a-shop.example` | `domain-held` | `account-lifecycle-subdomain-of-held-domain-refused` |
| m11 | `client-a.example.evil.test` confirmed tenant-a; a two-tenant report confirmed either; a second intake broke the first case | `tenant_confirmed: false`; `tenant-ambiguous`; `case-exists`, first case intact | `abuse-response-lookalike-host-not-confirmed`, `-two-tenants-refused`, `-same-report-twice-refused` |
| m12 | category `credentials` or `Credential` with an owner grant crossed tenants | no spelling of credential or backup crosses | `tenant-isolation-credential-spelling-denied` |
| m13 | 24 single requests, one per hour: `availability_claim 100.0000` | `insufficient-events`: 1000 needed at 99.9 percent | `incident-response-sparse-events-claim-refused` |
| m14 | a disclosure entry dated 2027 counted | `disclosure-entry-invalid` | `metering-disclosure-after-conversion-refused` |

One review sub-claim didn't hold: `AWS_SECRET=fx_demo_LeakedSyntheticValue001` has 23 characters after
`fx_demo_`, and the old scan needed 24, so it returned `clean`. The scan now matches `fx_demo_` tokens of 16 or
more characters and `NAME=value` lines whose name says secret, password, token or key.

## Rerun everything

```bash
cd skills/company-fleets
bin/fleet validate --strict --fleet hosting
python3 fleets/hosting/tools/evalrun.py skills --write   # quick_validate plus unit tests on 3.14 and 3.9
python3 fleets/hosting/tools/evalrun.py run --write      # every script case in a temporary copy; raw output to evidence/evals/ (only with --write)
python3 fleets/hosting/tools/evalrun.py run --write --in-place \
  --only hosting.eval.tenant-isolation-sandbox-isolated --only hosting.eval.tenant-isolation-sandbox-control-leaks \
  --only hosting.eval.tenant-isolation-liar-build-control-leaks --only hosting.eval.role-build-runtime-engineer
python3 fleets/hosting/tools/evalrun.py roles            # refuse a verified role or graded case the builder graded
```

`run` copies the skills root to a temp folder, as `bin/fleet eval-run` does, so a case's writes to the
owner folder land in the copy. Docker mounts only the folders it shares, so the 4 Docker cases report
`blocked` there; run them with `--in-place`, which is safe because they only read. `skills` reports 10
failed steps: `quick_validate` rejects the `disable-model-invocation` key every hosting SKILL.md
carries. The key is intentional and the repo's own validator accepts it.

Unit tests that need owner state build a throwaway copy of the rig with `tools/mirror.py`, or repoint a
module's `OWNER_ROOT` in process, so they never write the real owner folder.

The model-judgment cases need a fresh agent session reading `roles.json` and a grader other than the
fleet's builder. The 2026-11-26 raw answers are in `evidence/persona-evals-2026-11-26.txt`; its line 4
names the builder as grader, so those grades don't count.

## Four states, kept apart

| | Coverage | Installed | Activated | Behavioral |
|---|---|---|---|---|
| Roles (26) | 23 covered, 3 partial | 26 installed | 0 | 0 verified, 26 unverified (6 had a builder-graded sample) |
| Skills (10) | 8 covered, 2 partial | 10 installed | 0 | 10 verified by their fleet cases |

Activated stays at 0: no router session has selected a hosting skill yet.

## Limits and blockers

- Real cPanel/WHM and reseller adapters: blocked. No provider is selected and no credentials exist;
  the account lifecycle uses a fake adapter with WHM API 1 function names.
- Terraform: blocked. The binary isn't installed. Resume: install Terraform 1.7 or later, then run
  `terraform test` with `mock_provider` blocks and `command = plan`. Never apply.
- Production engines: SQLite and a local HTTP process stand in for database servers and hosting nodes.
- SSO/RBAC, staging and content workflows, multisite and multi-region failure domains have no procedure
  yet. `requirements-map.json` names each gap per requirement row.
- One lab run is never an availability percentage, and no contract exists, so every commitment in the
  benchmark is empty.

## Roll back

Remove the ten `skills/hosting-*` folders, this folder's `owner/` folder and `tools/mirror.py`, and reset this folder's three registry files to the
foundation's empty skeletons: `{"schema_version": 1, "fleet": "hosting", "roles": [], "workloads": []}`
in `roles.json`, and the same with an empty `skills` or `evals` list in the other two. Three workflows
outside this folder name hosting roles: `workflows/hosting-incident.json`, `agency-engagement.json` and
`compliance-engagement.json`. Remove or rework their hosting steps first, then run
`bin/fleet workflow check <name>` for each and `bin/fleet validate --strict`; `validate` doesn't read
workflows, so it won't catch a dangling role on its own.
