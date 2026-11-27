# Local override register

Generated from `registry/overrides.json` by `frig render-overrides`; edit the JSON, not this file. Each entry names the upstream file and revision, the conflict observed, the local behavior, where it lives, how it is tested, and when to retire it.

## OVR-ONE-DISPATCHER

- **Owner:** factory-rig
- **Upstream:** Noodle loop scheduler; PMO delivery-engine/release-hub; Curia dispatcher; Matt implement-spec
- **Observed conflict:** Each backend can pick and start work from its own queue, so two backends could run one task.
- **Local behavior:** Exactly one dispatcher per workload: `frig dispatch` takes a lease keyed by logical repo + task id with a fencing epoch before anything starts; expiry never reclaims a live holder; `fence` stops it first.
- **Implementation:** scripts/factory_rig/lease.py, orchestrate.dispatch
- **Precedence and scope:** Router decision first, lease second; backends only execute.
- **Verification:** tests.test_core.LeaseTests (8 incl. 8-process race), tests.test_flow.test_competing_backend_cannot_dispatch_the_same_task
- **Retire when:** A backend exposes a cross-backend ownership API that gives the same fencing guarantee.

## OVR-NOODLE-PROVIDER-LAUNCH

- **Owner:** factory-rig
- **Upstream:** poteto/noodle dispatcher/command.go @82d2921 (lines 36-59)
- **Observed conflict:** Noodle hardcodes `--dangerously-bypass-approvals-and-sandbox` (Codex) and `--permission-mode bypassPermissions` (Claude), then appends [agents.*].args after them, so config cannot remove them.
- **Local behavior:** Noodle launches providers through bin/codex and bin/claude shims. They rewrite argv to the rig policy (Codex `-s workspace-write --ignore-user-config`, reasoning effort per model; Claude acceptEdits + an allowlist), refuse any restored bypass, then exec the real binary by absolute path. HOME, CODEX_HOME and the environment are untouched.
- **Implementation:** scripts/factory_rig/provider_wrapper.py, bin/codex, bin/claude, config/provider-policy.json ($FRIG_POLICY)
- **Precedence and scope:** [agents.<p>].path in .noodle.toml points at the rig bin dir; the wrapper outranks Noodle defaults.
- **Verification:** tests.test_core.ProviderWrapperTests (10), tests.test_noodle_integration (audit shows the flag dropped on every launch), live-pilot provider audit (run records retained privately, not published)
- **Retire when:** Noodle exposes a permission policy setting, or the wrapper is replaced by an upstream patch carrying the same tests.

## OVR-NOODLE-COMPLETION

- **Owner:** factory-rig
- **Upstream:** poteto/noodle loop/cook_completion.go @82d2921; adapters/README.md
- **Observed conflict:** A runtime completion event is not acceptance; v0.1.5 has no supervised merge check; the backlog `done` callback can remove local work before an external callback succeeds.
- **Local behavior:** Pin 82d2921 (has ModeGate.CanAutoMerge) in supervised mode so candidates park for review. Only `frig complete` lands them after re-running verify in a fresh checkout, an independent review bound to task, attempt, contract hash, candidate and base, and an unchanged base; receipts make each step idempotent and resumable. Noodle's own `merge` control command is sent only afterwards, to close its order.
- **Implementation:** scripts/factory_rig/gate.py, receipts.py, orchestrate.complete, noodle_control.py, noodle_backlog.py
- **Precedence and scope:** Gate decides; Noodle state is informational.
- **Verification:** tests.test_flow (17), tests.test_noodle_integration.test_happy_path_through_real_noodle_supervised_mode, live pilot
- **Retire when:** Noodle binds approvals to candidate revisions itself.

## OVR-NOODLE-SKILL-RESOLUTION

- **Owner:** factory-rig
- **Upstream:** poteto/noodle skill/resolver.go @82d2921 (List vs Resolve)
- **Observed conflict:** `skills list` and the task-type registry skip symlinked skill directories (DirEntry.IsDir is false for symlinks) while Resolve() follows them, so rig skills reached through the <skills-root> mount are not registered and orders naming them are silently dropped at normalization. Orders for unregistered task types vanish with no error.
- **Local behavior:** `frig noodle-init` writes real-directory copies of factory-execute and the schedule stub into <project>/.agents/skills with hashes; dispatch preflight refuses on a missing skill or any drift from the canonical copy.
- **Implementation:** scripts/factory_rig/noodle_setup.py, orchestrate.noodle_has_skills
- **Precedence and scope:** Project .agents/skills is first in skills.paths; first match wins.
- **Verification:** tests.test_core.NoodleSetupTests, tests.test_flow (skill missing, copy drift), real-Noodle run that dispatched the worker
- **Retire when:** Noodle lists and registers symlinked skills.

## OVR-NOODLE-SCHEDULER-BUDGET

- **Owner:** factory-rig
- **Upstream:** poteto/noodle loop/reconcile.go ensureScheduleOrderPresent; loop_cycle_pipeline.go
- **Observed conflict:** Every `noodle start` injects a scheduler LLM session and a mise change injects another. If a worker stage fails the failure event waits 'for later recovery' and the scheduler loops: 8 real provider sessions in 3 minutes were observed on 2026-11-25 (first live attempt).
- **Local behavior:** A no-op `schedule` stub skill (empty orders) keeps the scheduler inert; the empty backlog adapter keeps Noodle from scheduling work; `frig noodle-run` owns the process and stops it on a worker failure, on more than 3 scheduler sessions, or at a wall limit. Recovery is `frig abandon` (tracker blocked, lease released, worktree untouched). Budget one start-time scheduler session plus one per mise change.
- **Implementation:** noodle/schedule-stub/SKILL.md, scripts/factory_rig/noodle_run.py, noodle_backlog.py, orchestrate.abandon
- **Precedence and scope:** Runner limits outrank Noodle's loop.
- **Verification:** tests.test_noodle_integration (failed worker stops runner; scheduler budget stop)
- **Retire when:** Noodle offers a setting that disables or bounds scheduler sessions.

## OVR-NOODLE-GITIGNORE

- **Owner:** factory-rig
- **Upstream:** poteto/noodle worktree/commands.go Create
- **Observed conflict:** With `.worktrees/` (trailing slash) git check-ignore fails before the directory exists, so Noodle appends a duplicate line and dirties the integration checkout, which the gate refuses to merge into.
- **Local behavior:** noodle-init writes the pattern `.worktrees` (no slash) and `.noodle/`.
- **Implementation:** noodle_setup.ensure_gitignore
- **Precedence and scope:** n/a
- **Verification:** tests.test_core.NoodleSetupTests.test_gitignore_pattern_matches_before_the_worktrees_directory_exists
- **Retire when:** Upstream checks ignore status of the pattern or the path with a trailing slash.

## OVR-MODEL-CATALOG

- **Owner:** factory-rig
- **Upstream:** a model policy that names a slug the Codex account cannot use
- **Observed conflict:** A slug missing from the account's Codex catalog fails with model_not_in_accessible_catalog; a worker launched with it fails within seconds.
- **Local behavior:** Dispatch checks the model slug against $CODEX_HOME/models_cache.json before leasing.
- **Implementation:** orchestrate.codex_model_problem; policy effort_by_model
- **Precedence and scope:** Preflight first.
- **Verification:** a live pilot ran with a catalog slug; the failed first attempt's noodle.log and provider-audit.jsonl are retained privately, not published
- **Retire when:** The model policy names current slugs.

## OVR-SKILL-INVOCATION

- **Owner:** factory-rig
- **Upstream:** mattpocock/skills in-progress (disable-model-invocation: true)
- **Observed conflict:** chief-of-staff and software-factory are user-invocable only; Codex has allow_implicit_invocation.
- **Local behavior:** Restrictions preserved. They are installed inactive and reached only by the user typing the skill name; the router never reads them indirectly to bypass the restriction.
- **Implementation:** installed unmodified via skill-sync (dest <skills-root>)
- **Precedence and scope:** Upstream frontmatter wins.
- **Verification:** skill-sync check up-to-date; frontmatter inspected
- **Retire when:** The skills graduate or are removed.

## OVR-PMO-DOD

- **Owner:** factory-rig
- **Upstream:** pmo-platform delivery-engine gate-definitions.md LG-5 (lines 137-147), pmo-scrum-master SKILL.md
- **Observed conflict:** PMO's delivery-engine Mode F merges the Definition of Done check with release readiness (LG-5/G3) and includes Product Owner acceptance; Scrum makes the Definition of Done the Developers' accountability and Sprint Review a non-gate.
- **Local behavior:** When PMO is activated, route DoD checks to the Developers' evidence and treat G3/LG-5 as readiness evidence only. Release authorization stays with the existing release policy. pmo-scrum-master, which omits Mode F, is the default PMO entry for Sprint work.
- **Implementation:** documented routing rule (references/operating-modes.md); no PMO file edited
- **Precedence and scope:** factory-rig ownership table over PMO gates
- **Verification:** design decision; management eval M3 and M4 check the Scrum and readiness separation on installed Magnus skills, not on PMO
- **Retire when:** PMO is activated and its gates are tested natively.

## OVR-STATE-AUTHORITY

- **Owner:** factory-rig
- **Upstream:** yysun/project-manager (.projects authoritative), Noodle backlog adapter, PMO hub-state
- **Observed conflict:** Several systems hold task state; projections can overwrite the source of truth.
- **Local behavior:** One authority per project: yysun `.projects` in yysun-led mode, otherwise the existing tracker. The Noodle backlog adapter prints nothing, refuses add/edit, and logs `done` callbacks without writing tracker state. Tracker writes happen only through yysun's own scripts.
- **Implementation:** noodle_backlog.py, yysun.py
- **Precedence and scope:** Selected authority wins; everything else is a projection.
- **Verification:** tests.test_core.BacklogAdapterTests, tests.test_flow
- **Retire when:** n/a

## OVR-YYSUN-EVIDENCE

- **Owner:** factory-rig
- **Upstream:** yysun/project-manager skills/project-manager/scripts/lib/contracts.js validateManifest
- **Observed conflict:** The tracker validates evidence shape, not truth: a manifest with a fabricated sha256 and an unverified review was accepted (probe 2026-11-25).
- **Local behavior:** Every manifest is built from values the adapter computed: file hashes read from disk, verify exit codes it ran, review record hashes.
- **Implementation:** yysun.build_manifest
- **Precedence and scope:** n/a
- **Verification:** tests.test_flow.test_tracker_accepts_fabricated_evidence_so_the_gate_must_compute_it documents the gap
- **Retire when:** The tracker verifies evidence content.

## OVR-KANBAN-MEASURES

- **Owner:** factory-rig
- **Upstream:** magnus919/agent-skills kanban-guru SKILL.md:96
- **Observed conflict:** The skill lists Flow Efficiency among four core measures; the Kanban Guide's four are WIP, Throughput, Work Item Age and Cycle Time.
- **Local behavior:** A skill-sync overlay (SKILL.local.md appended) makes the Guide's four core and flow efficiency a supplementary diagnostic.
- **Implementation:** a local overlay appended to kanban-guru (not published)
- **Precedence and scope:** Local text after upstream text.
- **Verification:** grep of installed SKILL.md; management eval M5 and M6 graded
- **Retire when:** Upstream aligns with the Kanban Guide.

## OVR-FORECAST-BASELINES

- **Owner:** factory-rig
- **Upstream:** magnus919 technical-project-management SKILL.md:49-66
- **Observed conflict:** none observed
- **Local behavior:** Upstream already separates commitments from forecasts and preserves baselines; used unmodified.
- **Implementation:** none
- **Precedence and scope:** upstream
- **Verification:** management eval M1, M2, M5
- **Retire when:** n/a

## OVR-CONTEXT-SIZE

- **Owner:** factory-rig
- **Upstream:** Magnus skills (multi-agent-coordination 340K, release-engineering 588K); PMO (59 skills, 71 KB CLAUDE.md)
- **Observed conflict:** Loading everything would exhaust context.
- **Local behavior:** Only each SKILL.md loads by description; references and templates load by link on demand. Skills with dangling sibling links (Magnus links to ~40 uninstalled siblings) are routed by the router, not by following dead links. PMO stays out of ~/.claude (scoped workspace) so its 71 KB CLAUDE.md and hooks load only when a session starts there.
- **Implementation:** installation choices; factory-rig/SKILL.md is under 120 lines
- **Precedence and scope:** n/a
- **Verification:** sizes measured; the live skill list shows only descriptions
- **Retire when:** n/a

## OVR-NATIVE-ADAPTERS

- **Owner:** factory-rig
- **Upstream:** PMO hooks and AskUserQuestion/Agent usage; Curia
- **Observed conflict:** Platform-specific tools do not carry over to other consumers.
- **Local behavior:** PMO hooks and tools stay native to Claude Code inside the scoped workspace; Codex gets no PMO capability. Curia stays on its supported Linux host.
- **Implementation:** none (boundaries documented)
- **Precedence and scope:** native
- **Verification:** PMO deployed only under $PMO_WORKSPACE; checked no files in ~/Claude, ~/.config/pmo-platform or ~/.claude/skills
- **Retire when:** n/a

## OVR-PMO-PATH-ISOLATION

- **Owner:** factory-rig
- **Upstream:** pmo-platform install.sh, lib-instance-path.sh:406, validate-install.sh:116,1211, five hooks reading $HOME/.config/pmo-platform
- **Observed conflict:** --config-root is honored only through PMO_PLATFORM_CONFIG_ROOT; five hooks and the validator read $HOME paths; the validator checks live ~/.claude/skills unless PMO_PLATFORM_DEPLOY_ROOT is exported.
- **Local behavior:** Install with --workspace-root, --config-root and PMO_PLATFORM_DEPLOY_ROOT/PMO_PLATFORM_CONFIG_ROOT/CLAUDE_WORKSPACE_ROOT all exported to the scoped tree; validate with the same variables. PMO stays installed-inactive.
- **Implementation:** references/operations.md (commands)
- **Precedence and scope:** env variables over defaults
- **Verification:** installer wrote only under the scoped tree; validator A6b FAIL is about user-scope hook wiring (see registry blocker)
- **Retire when:** Upstream isolates all readers.

## OVR-UPSTREAM-DRIFT

- **Owner:** factory-rig
- **Upstream:** all pinned sources
- **Observed conflict:** Upstream moves; local overrides rot silently.
- **Local behavior:** registry/components.json lists watched files per component with the checks to rerun; `frig drift` compares pinned and current revisions and names affected checks. skill-sync check covers installed skill content.
- **Implementation:** scripts/factory_rig/drift.py
- **Precedence and scope:** n/a
- **Verification:** tests.test_core drift cases; `frig drift` run
- **Retire when:** n/a
