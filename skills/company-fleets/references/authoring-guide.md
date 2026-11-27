# Fleet authoring guide

You add roles, workloads, skills and evaluation cases for one fleet by editing only that fleet's directory. `bin/fleet validate --strict` is the gate before you hand back: when it prints `"ok": true`, every fleet's files meet the contract and no `TODO` placeholder remains. `--fleet <your-fleet>` narrows the report to your files plus any record elsewhere that your change broke.

The worked example is `fixtures/sample-fleets/` (an agency, a hosting and an education fleet). Copy from it.

## Your files

Every fleet owns exactly these, and nobody else writes them:

```
fleets/<fleet>/roles.json    roles and workloads
fleets/<fleet>/skills.json   skills your fleet builds or adopts
fleets/<fleet>/evals.json    positive, negative and boundary cases
fleets/<fleet>/evidence/     raw outputs that back any status claim
```

Don't edit `registry/*.json`, `schemas/` or another fleet's directory. If you need a new profile or fleet, ask the integrator.

Fleet ids: `corporate`, `agency`, `hosting`, `product`, `consultancies`, `devrel`, `community`, `bcit-education`, `instructional-design`.

## Naming

| Record | Pattern | Example |
|---|---|---|
| Role | `<fleet>.<slug>` | `agency.accessibility-specialist` |
| Workload | `<fleet>.workload.<slug>` | `hosting.workload.restore-exercise` |
| Eval case | `<fleet>.eval.<slug>` | `bcit-education.eval.missing-standard-is-a-gap` |
| Skill | `<slug>`, the rig directory name | `agency-keyboard-audit` lives at `skills/agency-keyboard-audit/SKILL.md` |
| Person | `human:<title>` | `human:teacher-of-record` |

Slugs are lowercase letters, digits and single hyphens. A proposed id without a fleet prefix, such as the education addendum's `cs-education-professor`, becomes `<fleet>.cs-education-professor`.

## Add a role

1. Run `bin/fleet new-role --fleet <fleet> --slug <slug> [--kind coordinator] [--name "Display name"]`. It appends a schema-valid skeleton to `roles.json` and a smoke case to `evals.json`.
2. Replace every value that starts with `TODO`. Validate warns until none remain.
3. Run `bin/fleet validate --fleet <fleet>`.

Rules validate enforces:

- `dispatch` is always `false`. The existing router is the only top-level dispatcher.
- A fleet has at most one `coordinator`. Every workload names exactly one, from its own fleet, so one role can claim it.
- `relations.acceptor` and every reviewer differ from the role itself. Producing evidence and accepting it stay separate.
- Every role principal you name in `relations` or `handoff.next_consumers` exists in some fleet.
- `evals` lists at least one case id, each id exists in some `evals.json`, and at least one of them targets this role.
- Each attached skill either exists at `skills/<id>/SKILL.md` or carries a `blocked_reason`.
- A persona is a viewpoint. Don't write biographies, credentials, employers or years of experience.

## Add a workload

Add an object to `workloads` in your `roles.json`:

```json
{"id": "agency.workload.accessibility-audit", "name": "Accessibility audit", "description": "...",
 "profiles": ["agency"], "roles": ["agency.engagement-coordinator", "agency.accessibility-specialist"],
 "by_profile": {"managed": ["hosting.support-handoff-owner"]}}
```

List the smallest role set, starting with your fleet's coordinator. `by_profile` adds roles only under that profile. Every profile you list must activate your fleet (see `registry/profiles.json`). Check the result with `bin/fleet resolve --profile <p> --workload <id>`; its `files_read` shows exactly which registry files it opened.

## Add a skill

1. Build the skill itself at `skills/<id>/` in the rig, with its own `SKILL.md`, references and scripts, following skill-creator. If your brief doesn't assign you that path, attach it with a `blocked_reason` instead.
2. Add its record to your `skills.json`. Copy the shape from `fixtures/sample-fleets/agency/skills.json`. `evals` needs at least one positive, one negative and one boundary case id. Each case's `kind` must match its bucket, and each case targets the skill or a role that attaches it.
3. A skill id is registered in one fleet only. Other fleets attach it by id from their roles.

## Add an eval case

Add an object to your `evals.json`. For a script case, put the raw command in `check.argv` and the assertions in `check.expect`: `exit` (a list of codes), `contains`, `absent`, and `json` (dotted path to value). `bin/fleet eval-run --fleet <fleet>` runs every script case with one engine; it also reads the four older per-fleet wrappers, so existing cases need no edit. `--write` saves `fleets/<fleet>/evidence/<id>.txt` and records the outcome. `target` is a role id or a skill id. Set `"synthetic": true` for fixture data. `outcome.status` is `not-run`, `pass`, `fail` or `blocked`. A `pass` or `fail` needs `outcome.evidence`, the path of the raw output under `fleets/<fleet>/evidence/`. Keep failures; don't delete a failing case to get green.

## The four states

Each role and skill carries `verification` with four separate fields. Don't merge them.

| Field | Values | Meaning |
|---|---|---|
| `coverage` | `gap`, `partial`, `covered` | The record maps the required function |
| `installed` | `not-installed`, `reference-only`, `installed`, `blocked` | The files exist in the rig and load |
| `activated` | `not-activated`, `activated`, `blocked` | The router selected it in a real session |
| `behavioral` | `unverified`, `verified`, `failed`, `blocked` | An eval ran and its outcome is on record |

`installed`, `activated`, `verified` and `failed` each need an `evidence` path that exists under your `fleets/<fleet>/evidence/`. `activated` also needs `installed`. `verified` needs one of the record's eval cases at `pass`, and `failed` one at `fail`. `blocked` needs a `note`. `reference-only` never counts as installed.

A role's `behavioral: verified` also needs `grader`, the principal who judged the samples, and should name `builder`, whoever built them. `validate --strict` refuses a verified role with no grader, a grader equal to the builder, or a grader that is the role itself; plain `validate` only warns, so drafts still pass. A fleet's own grader check, such as hosting's `# Grader:` evidence line, still applies on top.

## Evidence

Write raw command output to `fleets/<fleet>/evidence/<name>.txt` and point to it by that path, relative to the skill directory. Validate rejects evidence anywhere else. A review or check that backs a handoff output must contain the line `reviewed-sha256: <hash of the output it reviewed>`; the handoff gate rejects evidence that doesn't name the bytes it checked. Start the file with the command you ran and the date. Label synthetic data as synthetic.

## Gate trust rule

A gate trusts only records its owner wrote: the owner log (next section), the contract, the rig registry. It never trusts a field, label, policy file, hash, threshold or approval that the party being checked supplied, and that includes a second file the same caller hands over. Independent reviews of four fleets (`evidence/reviews/`) found about fifteen breaks of this rule, the corporate-agency re-review found eleven more, and the second re-review found that the ledger itself came from the caller, in fifteen classes:

| Class | What broke | Check that holds |
|---|---|---|
| Label differs from content | `i18n_check` trusted `Language: en` on an Arabic catalog; claim `kind` and assessment labels were self-declared | Derive the class from the content, or refuse when label and content disagree |
| Self-written policy or principal | The brief set its own margin floor; the candidate listed its own allowed licenses; an inline principal widened access; any `human:` string approved | Load policy and principals from owner files by id; refuse inline ones |
| Recomputed hashes | Replace the SBOM, recompute every hash, keep the old review | Bind the review to the bytes it saw (`reviewed-sha256:`) and compare with the owner record |
| Producer equals acceptor, with a field deleted or padded | Deleted `producer`, `"agency.x "` with a trailing space, an unknown acceptor | Require both fields, compare exact registered ids, refuse unknown principals |
| Approval not bound to its subject | An approved `marketing` send relabeled `transactional`, audience grown, subject changed | Hash kind, audience, subject and headers into the approval |
| Tenant or classification from the worker | `build_update` copied `tenant_id` and `classification` from the worker's update | Take tenant and label from the owner record; the worker can't set them |
| Author-set thresholds | Margin floor `-1` or `0.05`; KPI targets in the brief | Read thresholds from a company-owned policy with its basis |
| Header trusted over content | A `Language` header, a `::replay-end::` marker printed by the step itself | Check the content; treat in-band markers as data |
| Malformed rows loaded silently | `dotted@example.com.` and a zero-width suppression row loaded and suppressed nothing; unvalidated payment events | Validate every row and refuse the file on the first bad one |
| Evidence path outside the base | `../../../../etc/hosts` with its real hash passed as stage evidence | Resolve each path and refuse anything outside the base |
| Trusted value moved into a second caller file | The intake, stage acceptance files, `--policy` and `--rates`, and a register's own `sign_off` each came from the caller | Read the value from the owner log; a flag that tries to supply it is a usage error |
| Input name bound, bytes not | A symlink gave Client B's brief a Client A path | Record each input's sha256 in the owner's intake; refuse a symlink that leaves its folder |
| Text a reader sees that the check skips | Zero-width and soft-hyphen characters, `&shy;`, Cyrillic look-alikes, fullwidth letters, code fences, footnote text | Check what renders: decode entities, NFKC, drop format characters, fold look-alikes, read every block |
| Non-finite numbers | A price of `Infinity` or `1e400` made the margin `NaN`, which no floor compares against | Refuse `NaN`, `Infinity` and overflowing numbers when parsing |
| Ledger picked by the caller | `--owner-ledger` and `--ledger` took any folder: another tenant's ledger, one minted with `fleet claim`, or a released one claimed again at epoch 2 | Derive the ledger from the work's instance at its one fixed place; refuse a ledger of other work; one ledger per instance, closed on release |

Declare probes for your gate in `skills/<id>/evals/adversarial.json` and run `bin/fleet adversarial --skill <id>`; the shared transforms cover these classes.

## Owner path and its limit

Owner values live in one append-only, hash-chained log per workload instance. Each instance has one ledger folder at a fixed place, `fleets/<fleet>/owner/<instance>/` in this skill: `owner-log.ndjson` (the log), `owner-head.json` (its entry count and last hash) and `leases/` (the factory-rig lease store, with the token hash in `<key>.owner-seal.json`). `scripts/fleetlib/ownerlog.py` owns both sides. The file names avoid the repository's `*.jsonl` and `*token*` ignore rules, so the fixture ledgers are committed with the gates that read them.

- **Claim.** The contract owner claims the instance: `bin/fleet claim --tenant T --workload W --instance I --role <coordinator> --owner-pid PID --contract-hash H`, with no `--lease-root`. The claim creates `fleets/<fleet of W>/owner/I/` and refuses with `ledger-exists` when that folder exists in any state, so an instance gets one ledger. It writes entry 1, `ledger-open`, with the tenant, workload, instance and contract hash, and prints a one-time token; the store keeps only its SHA-256. (`fleet claim --lease-root DIR` still takes a plain factory-rig lease, as the hosting fleet uses it; no gate reads such a folder, and it refuses a store that sits beside an owner log, a copy's included, with `owner-ledger-lease-store`.)
- **Write.** `bin/fleet owner-record --tenant T --workload W --instance I --epoch E --kind K --record FILE`, token on stdin. No flag picks the folder. The command refuses unless the lease is active at epoch E, the token matches, the ledger isn't closed (`ledger-closed`), and E is the epoch the log itself records as current (`stale-epoch`, `epoch-without-transition`).
- **Close.** `bin/fleet release --tenant T --workload W --instance I --epoch E`, token on stdin, writes `ledger-close` and releases the lease. A closed ledger takes no record and no claim.
- **Kinds.** `open` (a handoff's owner fields, write-once; its tenant and workload must be the lease's), `intake` (each input's path, tenant, classification, trust, source kind and sha256, write-once; a symlink leaving its folder is refused), `roster` (humans who may accept a stage), `stage-acceptance` (stage, status, producer, acceptor, evidence hashes, the contract's spec), `pin` (a policy, rate card or list: path, sha256 and content; JSON is parsed, other files are kept as text), `claims-sign-off` (a register's sources hash, signer and author, who must differ), `send-approval` (a named human's approval bound to a staged campaign's and recipient list's hashes, write-once).
- **Entry.** `seq`, `kind`, `subject`, `body`, the lease's `contract_hash`, `lease` (tenant, workload, instance, holder, epoch), `prev` (the previous entry's hash) and `hash`.
- **Epochs.** A value counts only at the epoch the log records. The log moves to a later epoch only through a `lease-transition` entry, which `open_ledger` writes when an open ledger is claimed again in process (a workflow run resuming its own run folder). Because `fleet claim` refuses an instance that has a ledger, a gate ledger stays at epoch 1, and a later lease taken on its store by other means (after expiry, through factory-rig directly) can't record anything.
- **Read.** Each gate derives the instance from the work it judges: the brief gate from the brief's `change_control.contract_ref` and `tenant_id`, the stage gate, the handoff command and `fleet handoff-check` from the contract's `task_id` and hash (plus the handoff's tenant and workload), the claims check from the register's `instance` and `tenant_id`, the email guard from the campaign's `campaign_id`. It reads only that instance's ledger and refuses one whose tenant, workload or contract hash differ (`ledger-not-for-this-work`). `read()` refuses the whole log, by name: an edited, reordered, inserted or substituted entry, a second `ledger-open` or an entry after `ledger-close` (`owner-log-broken`), a log shorter than its head (`owner-log-truncated`), no head (`owner-head-missing`), an entry at an epoch or holder the log's own lease records don't show (`owner-entry-without-lease`), a holder that isn't the workload's coordinator (`owner-not-coordinator`), bytes that aren't UTF-8 (`owner-log-broken`), or no log (`owner-log-missing`).
- **Fixtures.** `scripts/owner-fixtures.py` builds the checked-in fixture ledgers through the same path and closes them. It leaves an existing ledger as it is; to rebuild one, move its folder out of the owner root first. Tests repoint `ownerlog.FLEETS_ROOT` to a temp folder and run gates in process.

### Threat model

Fleet gates run as local processes under one OS user.

- **Holds.** Take a submitter that runs only the installed gate commands (`engagement_gate.py`, `claims_check.py`, `email_guard.py`, `fleet handoff-check`) and the fleet CLI (`fleet claim`, `fleet owner-record`, `fleet release`), without the owner's claim token, after the owner has claimed the instance. It can't make a gate accept a value the owner didn't record in that instance's ledger. No flag, file, label or field it passes picks the ledger or sets a value; a second ledger for the instance can't be claimed; a released ledger, or a copy of one, takes no new claim or record; and a later lease can't record. Each attack in the second corporate-agency re-review fails closed with a named rule (the agency and corporate READMEs list each one).
- **Doesn't hold.** A process running as the same user can still:
  - write the owner root directly: append an entry and rewrite the head with a recomputed chain, move a ledger folder out and claim the instance again, or rewrite the lease record and the token hash. The chain and head expose an edited, deleted, reordered, truncated or substituted entry as long as the head isn't rewritten with it; they don't expose a writer that updates both.
  - read the token from the owner's process or memory.
  - claim an instance first. If it claims the instance before the owner, the owner's claim fails with `ledger-exists`, which is the owner's signal to stop. It can also name a new instance id in work it writes itself (a brief's `contract_ref`, a register's `instance`, a campaign's `campaign_id`, a contract's `task_id`), claim that id and record its own values. The gate then judges that instance, not the owner's; whoever consumes the verdict must check that the instance is the one the engagement was issued under.
  - run a modified copy of a gate, or point `ownerlog.FLEETS_ROOT` elsewhere in its own Python process, as the tests do.
- **Closing the gap** takes OS separation: run workers as a different user, or in a sandbox that denies them writes to `fleets/*/owner`, reads of the owner's process, and claims; or have a person issue instance ids. The rig doesn't do this today.

## Check before you hand back

```bash
cd skills/company-fleets
bin/fleet validate --fleet <fleet>     # while you work
bin/fleet validate --strict            # before you hand back: must print "ok": true
bin/fleet coverage                     # your role, skill and eval counts, states kept apart
bin/fleet resolve --profile <p> --workload <id>
```
