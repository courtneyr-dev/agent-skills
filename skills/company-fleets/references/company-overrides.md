# Company override register

Every local adaptation of an upstream skill source, as section 14 of the fleet prompt requires. The record is `registry/overrides.json`; this page is rendered from it by `bin/fleet overrides --write`. Factory-rig's own register (`../../factory-rig/references/overrides.md`) covers the delivery layer.

Check status at render time: 14 overrides, 0 errors, 0 drifted upstream pins. A drifted pin means the ledger moved past the revision the override was checked against; rerun that override's evidence and re-pin.

## OVR-CF-01: Existing top-level router and one-dispatcher rule prevail over imported orchestration defaults

- Upstream: `msitarzewski/agency-agents` at `8ae6164602c9` (specialized/agents-orchestrator.md); `poteto/noodle` at `82d2921c5237` (scheduler loop); `cody-hutson/pmo-platform` at `8ed5e273d301` (delivery-engine and release-hub skills)
- Reason: Each imported orchestrator picks and starts work from its own queue, so two of them could run one workload.
- Implementation: `factory-rig/scripts/factory_rig/lease.py`, `company-fleets/scripts/fleetlib/ownership.py`, `company-fleets/scripts/fleetlib/workflow.py`, `company-fleets/scripts/fleetlib/checks.py`
- Precedence: The router (Claude Code plus credit-routing) picks the workload; the factory-rig lease decides who holds it; a fleet coordinator claims but never dispatches; agency-agents' orchestrator is not installed.
- Scope: Every fleet workload and every workflow run.
- Evidence: `company-fleets/scripts/foundation-evidence.sh`, `company-fleets/acceptance/matrix.json#ownership`
- Owner: company-fleets foundation workstream with factory-rig
- Retire when: A backend offers cross-backend ownership with the same fencing guarantee as the factory-rig lease.

## OVR-CF-02: Existing PM, verification, memory, publishing, provider, and permissions contracts remain authoritative

- Upstream: `alirezarezvani/claude-skills` at `ea7b5ab8da93` (c-level-advisor and ra-qm-team skills); `cody-hutson/pmo-platform` at `8ed5e273d301` (ppm-agent and pmo-* skills); `magnus919/agent-skills` at `6806511df28c` (verification-methodology and release-engineering)
- Reason: Imported packages describe their own project-management, verification, memory and publishing flows that would compete with the rig's.
- Implementation: `company-fleets/schemas/handoff.schema.json`, `company-fleets/scripts/fleetlib/handoff.py`, `company-fleets/registry/company.json`, `factory-rig/registry/overrides.json`
- Precedence: factory-rig contracts and merge gate, the one tracker per project, the rig's provider wrappers and Claude Code permission settings win; fleet skills only add checks inside them.
- Scope: All fleets.
- Evidence: `company-fleets/acceptance/matrix.json#existing-behavior`, `company-fleets/acceptance/matrix.json#evidence-integrity`
- Owner: Integrator (main session) with factory-rig
- Retire when: Never while the rig keeps one PM and gate layer; revisit if the rig adopts an imported PM layer as canonical.

## OVR-CF-03: Domain routers are bounded delegates

- Upstream: `samber/developer-relations-skills` at `c3a1b6912791` (skills/developer-relations-kickoff/SKILL.md); `alirezarezvani/claude-skills` at `ea7b5ab8da93` (business-growth/hooks/hooks.json (UserPromptSubmit router, not installed))
- Reason: samber's kickoff router and Alireza's prompt hook each route work on their own; inside the rig they may only suggest skills within one fleet workload.
- Implementation: `company-fleets/scripts/fleetlib/resolve.py`, `company-fleets/scripts/fleetlib/checks.py`, `devrel-program-kit/scripts/check_routes.py`
- Precedence: A domain router runs only after the fleet coordinator claimed the workload, and only names skills; `dispatch` is false on every role.
- Scope: DevRel, corporate and any fleet that adopts an upstream router skill.
- Evidence: `company-fleets/fleets/devrel/evidence/routes-launch-flags-sibling.txt`, `company-fleets/acceptance/matrix.json#selective-loading`
- Owner: DevRel fleet for samber; foundation for the dispatch rule
- Retire when: An upstream router exposes a bounded mode that the rig can check mechanically.

## OVR-CF-04: Generic numeric targets become explicit hypotheses or locally calibrated policies

- Upstream: `msitarzewski/agency-agents` at `8ae6164602c9` (engineering/engineering-cms-developer.md:469); `alirezarezvani/claude-skills` at `ea7b5ab8da93` (finance and operations advisor benchmarks)
- Reason: Role seeds and advisors state universal targets (load times, margins, ratios) with no local baseline.
- Implementation: `company-fleets/registry/company.json`, `hosting-restore-exercise/scripts/restore_exercise.py`, `hosting-benchmark-matrix/SKILL.md`
- Precedence: A target is a hypothesis with its proposer and date until a local measurement calibrates it; an unmet target stays unmet.
- Scope: Hosting targets, agency estimates, corporate finance and capacity plans.
- Evidence: `company-fleets/fleets/hosting/evidence/restore-exercise-2026-11-26.json`, `company-fleets/acceptance/matrix.json#hosting`
- Owner: Hosting fleet for service targets; corporate fleet for finance
- Retire when: Each target has a calibrated local policy with its own evidence.

## OVR-CF-05: Script outputs include assumptions and applicability; queueing or financial models do not justify false precision

- Upstream: `alirezarezvani/claude-skills` at `ea7b5ab8da93` (capacity-planner, pricing-strategist, channel-economics scripts)
- Reason: Upstream calculators print point estimates with no stated assumptions, and three of them crash on malformed input (sources/README.md, Qualification).
- Implementation: `company-fleets/schemas/handoff.schema.json`, `company-fleets/sources/qualify.py`, `hosting-restore-exercise/scripts/restore_exercise.py`
- Precedence: Every handoff carries an assumptions list; a calculator result enters a decision only with its assumptions and the range it holds for.
- Scope: Corporate finance, capacity and pricing; hosting measurements.
- Evidence: `company-fleets/sources/evidence/qualification.json`, `company-fleets/fleets/hosting/evidence/restore-exercise-2026-11-26.json`
- Owner: Corporate fleet
- Retire when: The upstream scripts print assumptions and validate input themselves; recheck on each upgrade.

## OVR-CF-06: Personas cannot fabricate experience, certification, authority, customer quotes, or research findings

- Upstream: `msitarzewski/agency-agents` at `8ae6164602c9` (product/product-manager.md:14)
- Reason: Agency Agents profiles invent years of experience; a persona with a credential reads as authority the rig does not have.
- Implementation: `company-fleets/schemas/role.schema.json`, `company-fleets/scripts/fleetlib/checks.py`
- Precedence: A role persona is a viewpoint; the validator and each fleet's persona evals reject credentials, employers and invented findings.
- Scope: Every role in every fleet.
- Evidence: `company-fleets/fleets/consultancies/evidence/personas-are-viewpoints.txt`, `company-fleets/fleets/product/evidence/personas-are-viewpoints.txt`, `company-fleets/fleets/hosting/evidence/persona-evals-2026-11-26.txt`
- Owner: Foundation workstream (schema) and each fleet (persona evals)
- Retire when: Never; this is a standing rule.

## OVR-CF-07: Simulated reviews cannot replace required human research, language review, learner data, or external assessment

- Upstream: `DaRL-GenAI/instructional_agents` at `c19c6a528496` (Test Student persona review); `learning-commons-org/agent-skills` at `b23623c8b50f` (k12-check-for-understanding)
- Reason: The DaRL pipeline's simulated student and generated reviews look like evidence of learning or usability.
- Implementation: `company-fleets/scripts/fleetlib/workflow.py`, `agency-i18n-check/scripts/i18n_check.py`, `edu-trainer-development/scripts/agreement.py`
- Precedence: A workflow step marked human-data stops the run; linguistic review stays `required`; generated calibration sets are practice only.
- Scope: Localization, developer education, BCIT units, trainer development, compliance assessment.
- Evidence: `company-fleets/fleets/agency/evidence/i18n-clean-catalogs-keep-review-human.txt`, `company-fleets/fleets/instructional-design/evidence/edu-trainer-development/generated-calibration-practice-only.txt`, `company-fleets/acceptance/matrix.json#devrel`
- Owner: Education, instructional-design and agency fleets
- Retire when: Never; real human data replaces the boundary only when a person supplies it.

## OVR-CF-08: Company-specific tools and paths are adapted through native interfaces

- Upstream: `kanopi/cms-cultivator` at `ff328fcc77af` (composer-security-update and pr-quality-report (DDEV, Teamwork, Snyk)); `hashicorp/agent-skills` at `5e30fa5c867b` (terraform-test SKILL.md:28 (apply by default))
- Reason: Kanopi assumes DDEV, Teamwork and Snyk and HashiCorp's skill applies real infrastructure; none of that exists or is authorized here.
- Implementation: `agency-platform-adapters/scripts/resolve_adapter.py`, `company-fleets/sources/README.md`
- Precedence: A step uses the project's actual tools through the platform adapter; terraform runs only in plan mode or with mock providers.
- Scope: Agency engineering, product releases, hosting operations.
- Evidence: `company-fleets/fleets/agency/evidence/adapter-legacy-wordpress-routed.txt`, `company-fleets/fleets/agency/evidence/adapter-headless-blocked.txt`
- Owner: Agency fleet
- Retire when: A project names its tools and the adapter resolves them without a manual step.

## OVR-CF-09: Duplicate skill names receive unambiguous selection or namespaced wrappers

- Upstream: `coreyhaines31/marketingskills` at `8fd2fcade2fd` (customer-research, seo-audit); `zstvns/design-skills` at `d612aa928d7e` (design-system)
- Reason: These names also ship in synced plugins, so a name alone does not say which copy loads.
- Implementation: `company-fleets/scripts/fleetlib/resolve.py`, `company-fleets/scripts/fleetlib/checks.py`, `company-fleets/sources/README.md`
- Precedence: Roles load a skill by path (resolve returns skills/<id>/SKILL.md); a skill id is registered in one fleet only; the hidden rig copies never compete in the model's list.
- Scope: Marketing, design and research skills.
- Evidence: `company-fleets/scripts/foundation-evidence.sh`, `company-fleets/acceptance/matrix.json#selective-loading`
- Owner: Sources workstream (names) and foundation (one-fleet rule)
- Retire when: Claude Code namespaces plugin and rig skills so names cannot collide.

## OVR-CF-10: Standards access and redistribution rights are recorded before ingestion

- Upstream: `learning-commons-org/agent-skills` at `b23623c8b50f` (skills/*/LICENSE and NOTICE); `trailofbits/skills` at `149d7b21f406` (LICENSE (CC-BY-SA-4.0))
- Reason: Standards bodies (NBEA, NOCTI, ISTE, CSTA) restrict access and redistribution, and some skill text is share-alike.
- Implementation: `edu-standards-alignment/scripts/standards_check.py`, `company-fleets/sources/ledger.json`
- Precedence: A standard without recorded edition, access and license is a gap, never an alignment; NBEA stays blocked until a person records them.
- Scope: BCIT education, instructional design and every imported skill.
- Evidence: `company-fleets/fleets/bcit-education/evidence/edu-standards-alignment/source-registries-valid.txt`, `company-fleets/acceptance/matrix.json#bcit-standards`
- Owner: Education fleet (standards) and sources workstream (skill licenses)
- Retire when: Never; each new source records its rights first.

## OVR-CF-11: Marketing loops stage outputs and respect actual scheduling/send authority

- Upstream: `coreyhaines31/marketingskills` at `8fd2fcade2fd` (email-sequence, social-content and launch skills)
- Reason: Upstream marketing procedures end in scheduling and sending; the rig has no send authority.
- Implementation: `corporate-email-guard/scripts/email_guard.py`, `consult-email-send-gate/scripts/send_gate.py`, `company-fleets/scripts/fleetlib/workflow.py`
- Precedence: Marketing steps run with publication staged-only and external_actions draft-only; a send needs a named human holding that authority.
- Scope: Corporate marketing, lifecycle email, launch campaigns.
- Evidence: `company-fleets/fleets/corporate/evidence/email-send-without-authority-refused.txt`, `company-fleets/acceptance/matrix.json#email`
- Owner: Corporate and consultancies fleets
- Retire when: Never while no send authority is delegated to an agent.

## OVR-CF-12: Client, community, and education records keep their access boundaries

- Upstream: `samber/developer-relations-skills` at `c3a1b6912791` (community and moderation skills); `learning-commons-org/agent-skills` at `b23623c8b50f` (k12 teaching skills)
- Reason: Upstream community and teaching skills assume one shared context; the rig serves several tenants, moderation cases and classrooms.
- Implementation: `company-fleets/scripts/fleetlib/tenancy.py`, `edu-student-data-guard/scripts/data_guard.py`, `community-moderation-review/scripts/case_check.py`
- Precedence: A record stays in its tenant unless public, an approved abstraction, or granted by a named human; student records and moderation cases need the grant.
- Scope: Every handoff and every fleet that holds tenant records.
- Evidence: `company-fleets/fleets/agency/evidence/client-b-file-refused-in-client-a-handoff.txt`, `company-fleets/fleets/community/evidence/confidential-cases-stay.txt`, `company-fleets/acceptance/matrix.json#tenant-boundaries`
- Owner: Foundation workstream
- Retire when: Never; this is a standing rule.

## OVR-CF-13: Native Claude/Codex/MCP differences remain explicit

- Upstream: `alirezarezvani/claude-skills` at `ea7b5ab8da93` (scripts/codex-install.sh); `cloudflare/skills` at `ff191de7d903` (account-bound MCP skills)
- Reason: Upstream installers copy skills into Codex directories and some skills assume an MCP server or account that only one harness has.
- Implementation: `company-fleets/sources/ledger.json`, `factory-rig/scripts/factory_rig/provider_wrapper.py`
- Precedence: The ledger records side effects and native-tool needs per repository; installers are read, never run; Codex mounts come only from your machine's mount list.
- Scope: Every imported skill.
- Evidence: `company-fleets/sources/evidence/sync-check.txt`, `company-fleets/sources/evidence/hide-pins.txt`
- Owner: Sources workstream and integrator
- Retire when: A behavior check runs the same skill under Claude and Codex and records both.

## OVR-CF-14: Upstream upgrades trigger affected compatibility checks

- Upstream: `WordPress/agent-skills` at `32ea909f7d01` (trunk); `samber/developer-relations-skills` at `c3a1b6912791` (skills/); `alirezarezvani/claude-skills` at `ea7b5ab8da93` (installed packages)
- Reason: Upstream trees move (WordPress tracks trunk); a silent upgrade could change a skill a fleet relies on.
- Implementation: `company-fleets/sources/verify_sources.py`, `company-fleets/scripts/fleetlib/coverage.py`
- Precedence: After skill-sync applies an upgrade, verify_sources reports tree drift and `fleet overrides` reports every override whose pinned upstream revision moved; the affected fleet evals rerun before the override is re-pinned.
- Scope: Every override in this register and every ledger repository.
- Evidence: `company-fleets/acceptance/matrix.json#source-drift`
- Owner: Sources workstream and integrator
- Retire when: Never; it is the update check itself.

## Licenses and share-alike obligations

The combined library is not MIT. The sources ledger (`sources/ledger.json`) records 24 upstream repositories under 7 licenses: MIT (13), GPL-2.0-or-later (4), Apache-2.0 (2), NOASSERTION (2), BUSL-1.1 (1), CC-BY-SA-4.0 (1), MPL-2.0 (1). Original rig skills (company-fleets, the fleet skills, factory-rig) are published under MIT in agent-skills.

Share-alike or copyleft sources: material adapted from these keeps their license and attribution, so a local adapter that copies their text inherits it.

- `kanopi/cms-cultivator` at `ff328fcc77af`: GPL-2.0-or-later. Copyleft: redistributed modifications stay GPL.
- `WordPress/agent-skills` at `32ea909f7d01`: GPL-2.0-or-later. Copyright (C) 2026 WordPress Contributors
- `woocommerce/agent-skills` at `89cc969d2273`: GPL-2.0-or-later. GPL version line not read; recheck before redistribution.
- `Automattic/claude-woocommerce-toolkit` at `d70538707247`: GPL-2.0-or-later. Version clause not confirmed beyond the v2 header.
- `hashicorp/agent-skills` at `5e30fa5c867b`: MPL-2.0. File-level copyleft.
- `trailofbits/skills` at `149d7b21f406`: CC-BY-SA-4.0. ShareAlike: adapted material must carry the same license and attribution.

Not redistributable as is:

- `yysun/project-manager` at `e96369e2a130`: NOASSERTION. Treat redistribution as unlicensed until a LICENSE file exists.
- `cody-hutson/pmo-platform` at `8ed5e273d301`: BUSL-1.1. Additional Use Grant: non-production, personal, educational and internal business use; Change Date 2030-05-27 to Apache-2.0. Source-available, not open source.
- `alp82/curia` at `0c61595315e7`: NOASSERTION. Treat the application as all rights reserved.

Keep each upstream LICENSE and NOTICE file with its installed directory; skill-sync copies whole directories.
