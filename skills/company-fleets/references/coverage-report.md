# Company-fleets coverage report

Generated 2026-11-27 by `bin/fleet coverage --sync --write` from `registry/requirements.json`, the fleet records and the integration evidence. Coverage, installation, activation and behavioral verification are four separate states: a delivered row means a deliverable exists, not that it was activated or verified.

## Requirement rows

- Rows: 235 (sections 3 to 11 of prompt 2 and the education addendum)
- Delivered with a deliverable: 228, of which 22 also name a blocker for the part still missing
- Blocked with an explicit blocker: 7
- Assigned without a deliverable: 0
- Unassigned: 0
- Rows with neither a deliverable nor a blocker: 0
- Mapped by: fleets/agency/requirements-map.json 19; fleets/bcit-education/requirements-map.json 94; fleets/community/README.md 14; fleets/consultancies/README.md 24; fleets/corporate/requirements-map.json 30; fleets/devrel/README.md 13; fleets/hosting/requirements-map.json 27; fleets/product/README.md 12; integration (coverage.py) 2

## Four states per fleet

Role and skill counts from the fleet records (`bin/fleet coverage`). Registry errors at render time: 0.

| Fleet | Roles | Role coverage | Role installed | Role activated | Role behavioral | Skills | Skill behavioral | Eval outcomes |
|---|---|---|---|---|---|---|---|---|
| corporate | 23 | covered 23 | reference-only 23 | not-activated 23 | unverified 23 | 2 | verified 2 | not-run 23; pass 39 |
| agency | 21 | covered 19; partial 2 | reference-only 21 | not-activated 21 | unverified 21 | 4 | verified 4 | not-run 21; pass 45 |
| hosting | 26 | covered 23; partial 3 | installed 26 | not-activated 26 | unverified 26 | 10 | verified 10 | blocked 1; not-run 6; pass 170 |
| product | 14 | covered 12; partial 2 | reference-only 14 | not-activated 14 | unverified 14 | 2 | verified 2 | not-run 2; pass 43 |
| consultancies | 20 | covered 18; partial 2 | reference-only 20 | not-activated 20 | unverified 20 | 4 | verified 4 | not-run 2; pass 49 |
| devrel | 14 | covered 10; partial 4 | reference-only 14 | not-activated 14 | unverified 14 | 2 | verified 2 | blocked 1; pass 24 |
| community | 18 | covered 18 | reference-only 18 | not-activated 18 | unverified 18 | 3 | verified 3 | blocked 1; pass 27 |
| bcit-education | 19 | covered 10; partial 9 | reference-only 19 | not-activated 19 | unverified 19 | 8 | verified 8 | pass 71 |
| instructional-design | 11 | covered 5; gap 1; partial 5 | reference-only 11 | not-activated 11 | unverified 11 | 2 | verified 2 | blocked 1; not-run 1; pass 16 |

No role or skill records `activated`: activation means the router selected it in a real session, and no session log was recorded as evidence.

## Sections 12 to 15

- Section 12 workflows: 8 templates in `workflows/`, checked with `bin/fleet workflow check` and run with `bin/fleet workflow run`.
- Section 13 compounding improvement: records in `improvement/records/`, gate `bin/fleet improve gate`.
- Section 14 override register: `registry/overrides.json`, rendered in `references/company-overrides.md`.
- Section 15 deliverables: this report; the vault index stays with the main-session integrator.

## Rows by section


### 3. Shared company services

| Row | Status | Deliverable | Blocker or missing part | Mapped by |
|---|---|---|---|---|
| S03-001 | delivered | `company-fleets/fleets/corporate/roles.json` |  | fleets/corporate/requirements-map.json |
| S03-002 | delivered | `company-fleets/fleets/corporate/roles.json#corporate.strategy-advisor` |  | fleets/corporate/requirements-map.json |
| S03-003 | delivered | `company-fleets/fleets/corporate/roles.json#corporate.workload.strategy-decision` |  | fleets/corporate/requirements-map.json |
| S03-004 | delivered | `company-fleets/fleets/corporate/roles.json#corporate.technology-advisor` |  | fleets/corporate/requirements-map.json |
| S03-005 | delivered | `company-fleets/fleets/corporate/roles.json#corporate.workload.technology-decision` |  | fleets/corporate/requirements-map.json |
| S03-006 | delivered | `company-fleets/fleets/corporate/roles.json#corporate.product-portfolio-lead` |  | fleets/corporate/requirements-map.json |
| S03-007 | delivered | `company-fleets/fleets/corporate/roles.json#corporate.workload.metric-definition` |  | fleets/corporate/requirements-map.json |
| S03-008 | delivered | `company-fleets/fleets/corporate/roles.json#corporate.finance-advisor` |  | fleets/corporate/requirements-map.json |
| S03-009 | delivered | `company-fleets/fleets/corporate/roles.json#corporate.workload.finance-close` |  | fleets/corporate/requirements-map.json |
| S03-010 | delivered | `company-fleets/fleets/corporate/roles.json#corporate.revenue-lead` |  | fleets/corporate/requirements-map.json |
| S03-011 | delivered | `company-fleets/fleets/corporate/roles.json#corporate.workload.proposal-and-pricing` |  | fleets/corporate/requirements-map.json |
| S03-012 | delivered | `company-fleets/fleets/corporate/roles.json#corporate.marketing-lead` |  | fleets/corporate/requirements-map.json |
| S03-013 | delivered | `company-fleets/fleets/corporate/roles.json#corporate.workload.campaign-staging` |  | fleets/corporate/requirements-map.json |
| S03-014 | delivered | `company-fleets/fleets/corporate/roles.json#corporate.partnerships-manager` |  | fleets/corporate/requirements-map.json |
| S03-015 | delivered | `company-fleets/fleets/corporate/roles.json#corporate.workload.partner-program` |  | fleets/corporate/requirements-map.json |
| S03-016 | delivered | `company-fleets/fleets/corporate/roles.json#corporate.customer-success-lead` |  | fleets/corporate/requirements-map.json |
| S03-017 | delivered | `company-fleets/fleets/corporate/roles.json#corporate.workload.customer-onboarding` |  | fleets/corporate/requirements-map.json |
| S03-018 | delivered | `company-fleets/fleets/corporate/roles.json#corporate.people-ops-advisor` |  | fleets/corporate/requirements-map.json |
| S03-019 | delivered | `company-fleets/fleets/corporate/roles.json#corporate.workload.capacity-plan` |  | fleets/corporate/requirements-map.json |
| S03-020 | delivered | `company-fleets/fleets/corporate/roles.json#corporate.security-lead` |  | fleets/corporate/requirements-map.json |
| S03-021 | delivered | `company-fleets/fleets/corporate/roles.json#corporate.workload.risk-review` |  | fleets/corporate/requirements-map.json |
| S03-022 | delivered | `company-fleets/fleets/corporate/roles.json#corporate.internal-operations` |  | fleets/corporate/requirements-map.json |
| S03-023 | delivered | `company-fleets/fleets/corporate/roles.json#corporate.workload.vendor-review` |  | fleets/corporate/requirements-map.json |
| S03-024 | delivered | `company-fleets/fleets/corporate/roles.json#corporate.data-analytics-lead` |  | fleets/corporate/requirements-map.json |
| S03-025 | delivered | `company-fleets/fleets/corporate/roles.json#corporate.workload.metric-definition` |  | fleets/corporate/requirements-map.json |
| S03-026 | delivered | `company-fleets/fleets/corporate/roles.json#corporate.communications-lead` |  | fleets/corporate/requirements-map.json |
| S03-027 | delivered | `company-fleets/fleets/corporate/roles.json#corporate.workload.crisis-communications` |  | fleets/corporate/requirements-map.json |
| S03-028 | delivered | `company-fleets/fleets/corporate/roles.json#corporate.contract-liaison` |  | fleets/corporate/requirements-map.json |
| S03-029 | delivered | `company-fleets/fleets/corporate/roles.json#corporate.strategy-advisor` |  | fleets/corporate/requirements-map.json |
| S03-030 | delivered | `company-fleets/fleets/corporate/README.md` |  | fleets/corporate/requirements-map.json |

### 4. Web development and design agency fleet

| Row | Status | Deliverable | Blocker or missing part | Mapped by |
|---|---|---|---|---|
| S04-001 | delivered | `company-fleets/fleets/agency/roles.json#agency.engagement-director` |  | fleets/agency/requirements-map.json |
| S04-002 | delivered | `agency-engagement-gate/SKILL.md` |  | fleets/agency/requirements-map.json |
| S04-003 | delivered | `company-fleets/fleets/agency/roles.json#agency.research-strategist` |  | fleets/agency/requirements-map.json |
| S04-004 | delivered | `company-fleets/fleets/agency/roles.json#agency.research-strategist` |  | fleets/agency/requirements-map.json |
| S04-005 | delivered | `company-fleets/fleets/agency/roles.json#agency.content-strategist` |  | fleets/agency/requirements-map.json |
| S04-006 | delivered | `company-fleets/fleets/agency/roles.json#agency.workload.cms-migration` |  | fleets/agency/requirements-map.json |
| S04-007 | delivered | `company-fleets/fleets/agency/roles.json#agency.brand-design-lead` |  | fleets/agency/requirements-map.json |
| S04-008 | delivered | `company-fleets/fleets/agency/demo/client-a-donate/deliverable/tokens.css` |  | fleets/agency/requirements-map.json |
| S04-009 | delivered | `company-fleets/fleets/agency/roles.json#agency.solution-architect` |  | fleets/agency/requirements-map.json |
| S04-010 | delivered | `company-fleets/fleets/agency/demo/client-a-donate/deliverable/build.py` |  | fleets/agency/requirements-map.json |
| S04-011 | delivered | `company-fleets/fleets/agency/roles.json#agency.qa-engineer` |  | fleets/agency/requirements-map.json |
| S04-012 | delivered | `agency-keyboard-audit/SKILL.md` |  | fleets/agency/requirements-map.json |
| S04-013 | delivered | `company-fleets/fleets/agency/roles.json#agency.release-engineer` |  | fleets/agency/requirements-map.json |
| S04-014 | delivered | `company-fleets/fleets/agency/demo/client-a-donate/support/runbook.md` |  | fleets/agency/requirements-map.json |
| S04-015 | delivered | `agency-platform-adapters/references/adapters.json` |  | fleets/agency/requirements-map.json |
| S04-016 | delivered | `company-fleets/fleets/agency/roles.json#agency.workload.client-engagement` |  | fleets/agency/requirements-map.json |
| S04-017 | delivered | `agency-engagement-gate/references/engagement-stages.md` |  | fleets/agency/requirements-map.json |
| S04-018 | delivered | `agency-platform-adapters/references/platform-sources.md` |  | fleets/agency/requirements-map.json |
| S04-019 | delivered | `agency-platform-adapters/references/adapters.json` |  | fleets/agency/requirements-map.json |

### 5. Hosting and application-platform fleet

| Row | Status | Deliverable | Blocker or missing part | Mapped by |
|---|---|---|---|---|
| S05-001 | delivered | `company-fleets/fleets/hosting/roles.json#hosting.workload.affiliate-referral` |  | fleets/hosting/requirements-map.json |
| S05-002 | delivered | `company-fleets/fleets/hosting/roles.json#hosting.workload.account-lifecycle` | Reseller billing and provisioning run through a fake WHM-shaped adapter; no upstream provider is selected | fleets/hosting/requirements-map.json |
| S05-003 | delivered | `hosting-account-lifecycle/SKILL.md` | Real cPanel/WHM adapter blocked: no provider selected, no credentials; mail is optional and not exercised | fleets/hosting/requirements-map.json |
| S05-004 | delivered | `company-fleets/fleets/hosting/roles.json#hosting.workload.vps-server-operations` | Covered as a workload, not a profile; no real VPS, Plesk or other panel is exercised | fleets/hosting/requirements-map.json |
| S05-005 | delivered | `hosting-service-catalogue/references/functions.json` | Compatibility, security and migrations are built and tested; staging, content workflows and multisite operations have no procedure yet | fleets/hosting/requirements-map.json |
| S05-006 | delivered | `company-fleets/fleets/hosting/roles.json#hosting.workload.untrusted-app-build` | Identity, custom domains and quota enforcement for the developer platform have no runtime demo; builds, previews, secrets, rollback and exportability do | fleets/hosting/requirements-map.json |
| S05-007 | delivered | `company-fleets/fleets/hosting/roles.json#hosting.workload.managed-cloud-operations` | Terraform checks blocked: the terraform binary is not installed; plan-only and mocked-provider use is documented, never apply | fleets/hosting/requirements-map.json |
| S05-008 | delivered | `hosting-tenant-isolation/SKILL.md` | Audit trail, data boundaries and change control are tested; SSO/RBAC and dedicated tenancy have no procedure or adapter yet | fleets/hosting/requirements-map.json |
| S05-009 | delivered | `company-fleets/fleets/hosting/roles.json#hosting.workload.resilience-exercise` | Failover, failback and restoration are tested on one machine; multi-region failure domains and supply-chain resilience are not exercised | fleets/hosting/requirements-map.json |
| S05-010 | delivered | `hosting-service-catalogue/SKILL.md` |  | fleets/hosting/requirements-map.json |
| S05-011 | delivered | `company-fleets/fleets/hosting/roles.json` |  | fleets/hosting/requirements-map.json |
| S05-012 | delivered | `hosting-account-lifecycle/SKILL.md` |  | fleets/hosting/requirements-map.json |
| S05-013 | delivered | `hosting-service-catalogue/SKILL.md` |  | fleets/hosting/requirements-map.json |
| S05-014 | delivered | `hosting-tenant-isolation/SKILL.md` | Identity (SSO) boundaries have no procedure yet | fleets/hosting/requirements-map.json |
| S05-015 | delivered | `hosting-dns-cert-lifecycle/SKILL.md` |  | fleets/hosting/requirements-map.json |
| S05-016 | delivered | `hosting-incident-response/SKILL.md` |  | fleets/hosting/requirements-map.json |
| S05-017 | delivered | `hosting-metering-reconcile/SKILL.md` |  | fleets/hosting/requirements-map.json |
| S05-018 | delivered | `hosting-abuse-response/SKILL.md` |  | fleets/hosting/requirements-map.json |
| S05-019 | delivered | `hosting-data-migration/SKILL.md` |  | fleets/hosting/requirements-map.json |
| S05-020 | delivered | `hosting-restore-exercise/SKILL.md` |  | fleets/hosting/requirements-map.json |
| S05-021 | delivered | `hosting-account-lifecycle/SKILL.md` | No provider is selected and no credentials exist, so the cPanel/WHM and reseller adapters are fakes that mirror WHM API 1 function names; a real adapter needs a chosen provider | fleets/hosting/requirements-map.json |
| S05-022 | delivered | `hosting-tenant-isolation/SKILL.md` |  | fleets/hosting/requirements-map.json |
| S05-023 | delivered | `company-fleets/fleets/hosting/benchmark/2026-11-26-matrix.json` | No plan or contract exists for Fixture Co, so the contractual-commitment column is empty by design | fleets/hosting/requirements-map.json |
| S05-024 | delivered | `hosting-benchmark-matrix/SKILL.md` | performance_under_load, support, accessibility, regions and cost have no measurement yet; they stay not-measured | fleets/hosting/requirements-map.json |
| S05-025 | delivered | `hosting-benchmark-matrix/scripts/benchmark.py` |  | fleets/hosting/requirements-map.json |
| S05-026 | delivered | `hosting-benchmark-matrix/SKILL.md` |  | fleets/hosting/requirements-map.json |
| S05-027 | delivered | `company-fleets/fleets/hosting/benchmark/2026-11-26-readiness-backlog.md` |  | fleets/hosting/requirements-map.json |

### 6. Extension, theme, integration, and SaaS product fleet

| Row | Status | Deliverable | Blocker or missing part | Mapped by |
|---|---|---|---|---|
| S06-001 | delivered | `company-fleets/fleets/product/README.md` | Gate and matrix are platform-neutral; names seven platforms. Partial: only WordPress.org has a pinned checklist | fleets/product/README.md |
| S06-002 | delivered | `company-fleets/fleets/product/README.md` |  | fleets/product/README.md |
| S06-003 | delivered | `company-fleets/fleets/product/README.md` |  | fleets/product/README.md |
| S06-004 | delivered | `company-fleets/fleets/product/README.md` |  | fleets/product/README.md |
| S06-005 | delivered | `company-fleets/fleets/product/README.md` |  | fleets/product/README.md |
| S06-006 | delivered | `company-fleets/fleets/product/README.md` |  | fleets/product/README.md |
| S06-007 | delivered | `company-fleets/fleets/product/README.md` | Gate migration-and-rollback stage. Partial: it checks recorded results; it does not run migrations | fleets/product/README.md |
| S06-008 | delivered | `company-fleets/fleets/product/README.md` |  | fleets/product/README.md |
| S06-009 | delivered | `company-fleets/fleets/product/README.md` |  | fleets/product/README.md |
| S06-010 | delivered | `company-fleets/fleets/product/README.md` | WordPress.org pinned. Blocker for Chrome Web Store, Mozilla Add-ons, Shopify, Drupal.org, Woo Marketplace and WordPress themes: no pinned policy text; resume by pinning each policy and adding it to the registry | fleets/product/README.md |
| S06-011 | delivered | `company-fleets/fleets/product/README.md` |  | fleets/product/README.md |
| S06-012 | delivered | `company-fleets/fleets/product/README.md` |  | fleets/product/README.md |

### 7. Specialist consultancy practices

| Row | Status | Deliverable | Blocker or missing part | Mapped by |
|---|---|---|---|---|
| S07-001 | delivered | `company-fleets/fleets/consultancies/README.md` |  | fleets/consultancies/README.md |
| S07-002 | delivered | `company-fleets/fleets/consultancies/README.md` |  | fleets/consultancies/README.md |
| S07-003 | delivered | `company-fleets/fleets/consultancies/README.md` |  | fleets/consultancies/README.md |
| S07-004 | delivered | `company-fleets/fleets/consultancies/README.md` | Roles and Zach Stevens's skills. Partial: asset-rights and token-consistency checks are manual | fleets/consultancies/README.md |
| S07-005 | delivered | `company-fleets/fleets/consultancies/README.md` | Roles and Zach Stevens's skills. Partial: asset-rights and token-consistency checks are manual | fleets/consultancies/README.md |
| S07-006 | delivered | `company-fleets/fleets/consultancies/README.md` |  | fleets/consultancies/README.md |
| S07-007 | delivered | `company-fleets/fleets/consultancies/README.md` |  | fleets/consultancies/README.md |
| S07-008 | delivered | `company-fleets/fleets/consultancies/README.md` |  | fleets/consultancies/README.md |
| S07-009 | delivered | `company-fleets/fleets/consultancies/README.md` |  | fleets/consultancies/README.md |
| S07-010 | delivered | `company-fleets/fleets/consultancies/README.md` |  | fleets/consultancies/README.md |
| S07-011 | delivered | `company-fleets/fleets/consultancies/README.md` |  | fleets/consultancies/README.md |
| S07-012 | delivered | `company-fleets/fleets/consultancies/README.md` | consult-search-claims-check and Corey Haines's skills. Partial: observed visibility needs the tenant's exports | fleets/consultancies/README.md |
| S07-013 | delivered | `company-fleets/fleets/consultancies/README.md` | consult-search-claims-check and Corey Haines's skills. Partial: observed visibility needs the tenant's exports | fleets/consultancies/README.md |
| S07-014 | delivered | `company-fleets/fleets/consultancies/README.md` |  | fleets/consultancies/README.md |
| S07-015 | delivered | `company-fleets/fleets/consultancies/README.md` |  | fleets/consultancies/README.md |
| S07-016 | delivered | `company-fleets/fleets/consultancies/README.md` |  | fleets/consultancies/README.md |
| S07-017 | delivered | `consult-compliance-engagement/references/applicability-registry.json` |  | fleets/consultancies/README.md |
| S07-018 | delivered | `company-fleets/fleets/consultancies/README.md` |  | fleets/consultancies/README.md |
| S07-019 | delivered | `company-fleets/fleets/consultancies/README.md` |  | fleets/consultancies/README.md |
| S07-020 | delivered | `company-fleets/fleets/consultancies/README.md` |  | fleets/consultancies/README.md |
| S07-021 | delivered | `company-fleets/fleets/consultancies/README.md` |  | fleets/consultancies/README.md |
| S07-022 | delivered | `company-fleets/fleets/consultancies/README.md` |  | fleets/consultancies/README.md |
| S07-023 | delivered | `company-fleets/fleets/consultancies/README.md` |  | fleets/consultancies/README.md |
| S07-024 | delivered | `company-fleets/fleets/consultancies/README.md` |  | fleets/consultancies/README.md |

### 8. Complete developer-relations system

| Row | Status | Deliverable | Blocker or missing part | Mapped by |
|---|---|---|---|---|
| S08-001 | delivered | `company-fleets/fleets/devrel/README.md` |  | fleets/devrel/README.md |
| S08-002 | delivered | `company-fleets/fleets/devrel/roles.json` |  | fleets/devrel/README.md |
| S08-003 | delivered | `devrel-program-kit/references/kit-map.md` |  | fleets/devrel/README.md |
| S08-004 | delivered | `devrel-quickstart-replay/SKILL.md` |  | fleets/devrel/README.md |
| S08-005 | delivered | `devrel-program-kit/references/kit-map.md` | (hackathon and event production partial) | fleets/devrel/README.md |
| S08-006 | delivered | `company-fleets/fleets/devrel/fixtures/docs/feedback-repro.md` |  | fleets/devrel/README.md |
| S08-007 | delivered | `devrel-program-kit/scripts/check_program.py` |  | fleets/devrel/README.md |
| S08-008 | delivered | `devrel-program-kit/references/context-and-handback.md` |  | fleets/devrel/README.md |
| S08-009 | delivered | `devrel-program-kit/references/kit-map.md` |  | fleets/devrel/README.md |
| S08-010 | delivered | `devrel-program-kit/references/context-and-handback.md` |  | fleets/devrel/README.md |
| S08-011 | delivered | `devrel-program-kit/scripts/check_program.py` |  | fleets/devrel/README.md |
| S08-012 | delivered | `devrel-program-kit/scripts/check_program.py` |  | fleets/devrel/README.md |
| S08-013 | delivered | `company-fleets/fleets/devrel/README.md` |  | fleets/devrel/README.md |

### 9. Complete community and open-source system

| Row | Status | Deliverable | Blocker or missing part | Mapped by |
|---|---|---|---|---|
| S09-001 | delivered | `company-fleets/fleets/community/README.md` |  | fleets/community/README.md |
| S09-002 | delivered | `company-fleets/fleets/community/roles.json` |  | fleets/community/README.md |
| S09-003 | delivered | `community-operating-kit/references/kit-map.md` |  | fleets/community/README.md |
| S09-004 | delivered | `community-moderation-review/SKILL.md` |  | fleets/community/README.md |
| S09-005 | delivered | `community-operating-kit/references/kit-map.md` |  | fleets/community/README.md |
| S09-006 | delivered | `community-operating-kit/references/kit-map.md` |  | fleets/community/README.md |
| S09-007 | delivered | `community-operating-kit/scripts/kit_check.py` |  | fleets/community/README.md |
| S09-008 | delivered | `community-health-measures/scripts/measures.py` |  | fleets/community/README.md |
| S09-009 | delivered | `community-health-measures/references/sources.md` |  | fleets/community/README.md |
| S09-010 | delivered | `community-operating-kit/references/kit-map.md` |  | fleets/community/README.md |
| S09-011 | delivered | `community-operating-kit/references/kit-map.md` |  | fleets/community/README.md |
| S09-012 | delivered | `community-health-measures/scripts/measures.py` |  | fleets/community/README.md |
| S09-013 | delivered | `community-moderation-review/scripts/case_check.py` |  | fleets/community/README.md |
| S09-014 | delivered | `company-fleets/fleets/community/fixtures/kit/community-a-kit.md` |  | fleets/community/README.md |

### 10. Public-school BCIT educator system

| Row | Status | Deliverable | Blocker or missing part | Mapped by |
|---|---|---|---|---|
| S10-001 | delivered | `company-fleets/fleets/bcit-education/roles.json` |  | fleets/bcit-education/requirements-map.json |
| S10-002 | delivered | `company-fleets/fleets/bcit-education/roles.json` |  | fleets/bcit-education/requirements-map.json |
| S10-003 | delivered | `company-fleets/fleets/bcit-education/roles.json` |  | fleets/bcit-education/requirements-map.json |
| S10-004 | delivered | `company-fleets/fleets/bcit-education/roles.json` |  | fleets/bcit-education/requirements-map.json |
| S10-005 | delivered | `edu-standards-alignment/references/standards-registry.json` |  | fleets/bcit-education/requirements-map.json |
| S10-006 | delivered | `edu-standards-alignment/references/standards-registry.json` |  | fleets/bcit-education/requirements-map.json |
| S10-007 | delivered | `edu-standards-alignment/scripts/standards_check.py` |  | fleets/bcit-education/requirements-map.json |
| S10-008 | delivered | `edu-standards-alignment/references/standards-registry.json` |  | fleets/bcit-education/requirements-map.json |
| S10-009 | blocked |  | NBEA's page returned HTTP 403 to automated fetches on 2026-11-25, so the 2023 edition and licensing are not observed; the ten-area coverage check works (nbea-ten-areas-covered, computing-only-not-bcit). Resume: a person opens nbea.org/business-education-curriculum-standards and records edition, access and license in the registry. | fleets/bcit-education/requirements-map.json |
| S10-010 | blocked |  | No NOCTI credential category or identifier is selected; the program or teacher chooses one. Until then every NOCTI alignment is a gap and blueprint content stays out of the rig. | fleets/bcit-education/requirements-map.json |
| S10-011 | delivered | `edu-standards-alignment/scripts/standards_check.py` |  | fleets/bcit-education/requirements-map.json |
| S10-012 | delivered | `edu-standards-alignment/references/standards-registry.json` |  | fleets/bcit-education/requirements-map.json |
| S10-013 | delivered | `edu-standards-alignment/scripts/standards_check.py` |  | fleets/bcit-education/requirements-map.json |
| S10-014 | delivered | `edu-student-data-guard/SKILL.md` |  | fleets/bcit-education/requirements-map.json |
| S10-015 | delivered | `edu-standards-alignment/scripts/standards_check.py` |  | fleets/bcit-education/requirements-map.json |
| S10-016 | delivered | `company-fleets/fleets/bcit-education/README.md` |  | fleets/bcit-education/requirements-map.json |
| S10-017 | delivered | `bcit-learning-package/SKILL.md` |  | fleets/bcit-education/requirements-map.json |
| S10-018 | blocked |  | The Learning Commons Knowledge Graph is not connected; connector availability would not establish NBEA, NOCTI or ISTE coverage. Drafts stay labeled with the coverage edu-standards-alignment reports. | fleets/bcit-education/requirements-map.json |
| S10-019 | delivered | `bcit-learning-package/SKILL.md` |  | fleets/bcit-education/requirements-map.json |
| S10-020 | delivered | `bcit-learning-package/scripts/package_check.py` |  | fleets/bcit-education/requirements-map.json |
| S10-021 | delivered | `bcit-learning-package/scripts/package_check.py` |  | fleets/bcit-education/requirements-map.json |
| S10-022 | delivered | `company-fleets/fleets/bcit-education/fixtures/bcit-unit-store/package.json` |  | fleets/bcit-education/requirements-map.json |
| S10-023 | delivered | `bcit-learning-package/scripts/package_check.py` |  | fleets/bcit-education/requirements-map.json |

### 11. Instructional design and trainer development

| Row | Status | Deliverable | Blocker or missing part | Mapped by |
|---|---|---|---|---|
| S11-001 | delivered | `company-fleets/fleets/instructional-design/roles.json` |  | fleets/bcit-education/requirements-map.json |
| S11-002 | delivered | `edu-needs-analysis/SKILL.md` |  | fleets/bcit-education/requirements-map.json |
| S11-003 | delivered | `company-fleets/fleets/instructional-design/README.md` |  | fleets/bcit-education/requirements-map.json |
| S11-004 | delivered | `company-fleets/fleets/instructional-design/README.md` |  | fleets/bcit-education/requirements-map.json |
| S11-005 | blocked | `company-fleets/fleets/instructional-design/README.md` | Facilitator and learner materials, scripts and accessibility checks exist (edu-trainer-development, edu-assessment-check, web-accessibility); storyboard, caption and transcript production has no tool or procedure yet. | fleets/bcit-education/requirements-map.json |
| S11-006 | blocked | `company-fleets/fleets/instructional-design/README.md` | No target LMS or QTI/CASE consumer is named, so no delivery package or platform integration can be validated by an actual import. The evaluation and evidence plan exist (edu-trainer-development/scripts/evidence_plan.py). | fleets/bcit-education/requirements-map.json |
| S11-007 | delivered | `company-fleets/fleets/instructional-design/README.md` |  | fleets/bcit-education/requirements-map.json |
| S11-008 | delivered | `company-fleets/fleets/instructional-design/README.md` |  | fleets/bcit-education/requirements-map.json |
| S11-009 | delivered | `company-fleets/fleets/instructional-design/README.md` |  | fleets/bcit-education/requirements-map.json |
| S11-010 | delivered | `edu-research-review/scripts/research_check.py` |  | fleets/bcit-education/requirements-map.json |
| S11-011 | delivered | `edu-standards-alignment/references/standards-registry.json` |  | fleets/bcit-education/requirements-map.json |
| S11-012 | delivered | `edu-standards-alignment/references/standards-registry.json` |  | fleets/bcit-education/requirements-map.json |
| S11-013 | delivered | `edu-trainer-development/SKILL.md` |  | fleets/bcit-education/requirements-map.json |
| S11-014 | delivered | `edu-trainer-development/scripts/evidence_plan.py` |  | fleets/bcit-education/requirements-map.json |
| S11-015 | delivered | `edu-trainer-development/scripts/agreement.py` |  | fleets/bcit-education/requirements-map.json |

### Education addendum: Doctoral faculty and computer science teaching

| Row | Status | Deliverable | Blocker or missing part | Mapped by |
|---|---|---|---|---|
| ED-001 | delivered | `company-fleets/fleets/bcit-education/README.md` |  | fleets/bcit-education/requirements-map.json |
| ED-002 | delivered | `company-fleets/fleets/bcit-education/roles.json` |  | fleets/bcit-education/requirements-map.json |
| ED-003 | delivered | `company-fleets/fleets/bcit-education/roles.json` |  | fleets/bcit-education/requirements-map.json |

### Education addendum: 1. Professor of Computer Science Education — doctoral level

| Row | Status | Deliverable | Blocker or missing part | Mapped by |
|---|---|---|---|---|
| ED-004 | delivered | `company-fleets/fleets/bcit-education/roles.json` |  | fleets/bcit-education/requirements-map.json |
| ED-005 | delivered | `company-fleets/fleets/bcit-education/roles.json` |  | fleets/bcit-education/requirements-map.json |
| ED-006 | delivered | `company-fleets/fleets/bcit-education/roles.json` |  | fleets/bcit-education/requirements-map.json |
| ED-007 | delivered | `company-fleets/fleets/bcit-education/roles.json` |  | fleets/bcit-education/requirements-map.json |
| ED-008 | delivered | `company-fleets/fleets/bcit-education/roles.json` |  | fleets/bcit-education/requirements-map.json |
| ED-009 | delivered | `edu-research-review/SKILL.md` |  | fleets/bcit-education/requirements-map.json |
| ED-010 | delivered | `edu-research-review/SKILL.md` |  | fleets/bcit-education/requirements-map.json |
| ED-011 | delivered | `edu-research-review/SKILL.md` |  | fleets/bcit-education/requirements-map.json |

### Education addendum: 2. Professor of Business, Computer and Information Technology Education — doctoral level

| Row | Status | Deliverable | Blocker or missing part | Mapped by |
|---|---|---|---|---|
| ED-012 | delivered | `company-fleets/fleets/bcit-education/roles.json` |  | fleets/bcit-education/requirements-map.json |
| ED-013 | delivered | `company-fleets/fleets/bcit-education/roles.json` |  | fleets/bcit-education/requirements-map.json |
| ED-014 | delivered | `company-fleets/fleets/bcit-education/roles.json` |  | fleets/bcit-education/requirements-map.json |
| ED-015 | delivered | `company-fleets/fleets/bcit-education/roles.json` |  | fleets/bcit-education/requirements-map.json |
| ED-016 | delivered | `company-fleets/fleets/bcit-education/roles.json` |  | fleets/bcit-education/requirements-map.json |
| ED-017 | delivered | `company-fleets/fleets/bcit-education/roles.json` |  | fleets/bcit-education/requirements-map.json |
| ED-018 | delivered | `edu-answer-key-check/SKILL.md` |  | fleets/bcit-education/requirements-map.json |
| ED-019 | delivered | `edu-trainer-development/references/teacher-education.md` |  | fleets/bcit-education/requirements-map.json |

### Education addendum: 3. Computer Science Teacher — school classroom practice

| Row | Status | Deliverable | Blocker or missing part | Mapped by |
|---|---|---|---|---|
| ED-020 | delivered | `company-fleets/fleets/bcit-education/roles.json` |  | fleets/bcit-education/requirements-map.json |
| ED-021 | delivered | `cs-classroom-instruction/SKILL.md` |  | fleets/bcit-education/requirements-map.json |
| ED-022 | delivered | `cs-classroom-instruction/SKILL.md` |  | fleets/bcit-education/requirements-map.json |
| ED-023 | delivered | `cs-classroom-instruction/SKILL.md` |  | fleets/bcit-education/requirements-map.json |
| ED-024 | delivered | `cs-classroom-instruction/SKILL.md` |  | fleets/bcit-education/requirements-map.json |
| ED-025 | delivered | `cs-classroom-instruction/SKILL.md` |  | fleets/bcit-education/requirements-map.json |
| ED-026 | delivered | `cs-classroom-instruction/SKILL.md` |  | fleets/bcit-education/requirements-map.json |
| ED-027 | delivered | `cs-classroom-instruction/SKILL.md` |  | fleets/bcit-education/requirements-map.json |
| ED-028 | delivered | `cs-classroom-instruction/SKILL.md` |  | fleets/bcit-education/requirements-map.json |

### Education addendum: 4. Add reusable skills and connect the roles

| Row | Status | Deliverable | Blocker or missing part | Mapped by |
|---|---|---|---|---|
| ED-029 | delivered | `edu-research-review/SKILL.md` |  | fleets/bcit-education/requirements-map.json |
| ED-030 | delivered | `edu-research-review/SKILL.md` |  | fleets/bcit-education/requirements-map.json |
| ED-031 | delivered | `edu-learning-progression/SKILL.md` |  | fleets/bcit-education/requirements-map.json |
| ED-032 | delivered | `cs-classroom-instruction/SKILL.md` |  | fleets/bcit-education/requirements-map.json |
| ED-033 | delivered | `edu-answer-key-check/SKILL.md` |  | fleets/bcit-education/requirements-map.json |
| ED-034 | delivered | `edu-trainer-development/references/teacher-education.md` |  | fleets/bcit-education/requirements-map.json |
| ED-035 | delivered | `edu-research-review/SKILL.md` |  | fleets/bcit-education/requirements-map.json |
| ED-036 | delivered | `edu-trainer-development/SKILL.md` |  | fleets/bcit-education/requirements-map.json |
| ED-037 | delivered | `company-fleets/fleets/bcit-education/README.md` |  | fleets/bcit-education/requirements-map.json |
| ED-038 | delivered | `company-fleets/fleets/bcit-education/README.md` |  | fleets/bcit-education/requirements-map.json |
| ED-039 | delivered | `company-fleets/fleets/bcit-education/README.md` |  | fleets/bcit-education/requirements-map.json |

### Education addendum: 5. Standards and scholarly references

| Row | Status | Deliverable | Blocker or missing part | Mapped by |
|---|---|---|---|---|
| ED-040 | delivered | `edu-standards-alignment/references/standards-registry.json` |  | fleets/bcit-education/requirements-map.json |
| ED-041 | delivered | `edu-standards-alignment/references/standards-registry.json` |  | fleets/bcit-education/requirements-map.json |
| ED-042 | delivered | `edu-standards-alignment/references/standards-registry.json` |  | fleets/bcit-education/requirements-map.json |
| ED-043 | delivered | `edu-standards-alignment/references/standards-registry.json` |  | fleets/bcit-education/requirements-map.json |
| ED-044 | delivered | `edu-learning-progression/SKILL.md` |  | fleets/bcit-education/requirements-map.json |
| ED-045 | delivered | `edu-standards-alignment/references/standards-registry.json` |  | fleets/bcit-education/requirements-map.json |
| ED-046 | delivered | `edu-research-review/references/evidence-hierarchy.md` |  | fleets/bcit-education/requirements-map.json |

### Education addendum: 6. Professional organizations and communities

| Row | Status | Deliverable | Blocker or missing part | Mapped by |
|---|---|---|---|---|
| ED-047 | delivered | `edu-standards-alignment/references/organizations.json` |  | fleets/bcit-education/requirements-map.json |
| ED-048 | delivered | `edu-standards-alignment/references/organizations.json` |  | fleets/bcit-education/requirements-map.json |
| ED-049 | delivered | `edu-standards-alignment/references/organizations.json` |  | fleets/bcit-education/requirements-map.json |

### Education addendum: 7. Additional acceptance checks

| Row | Status | Deliverable | Blocker or missing part | Mapped by |
|---|---|---|---|---|
| ED-050 | delivered | `company-fleets/fleets/bcit-education/evidence/edu-research-review/critique-kazemitabaar-2023.md` |  | fleets/bcit-education/requirements-map.json |
| ED-051 | delivered | `company-fleets/fleets/bcit-education/fixtures/cs-classroom-instruction/lesson-accumulator.json` |  | fleets/bcit-education/requirements-map.json |
| ED-052 | delivered | `company-fleets/fleets/bcit-education/evals.json` |  | fleets/bcit-education/requirements-map.json |
| ED-053 | delivered | `company-fleets/fleets/bcit-education/evals.json` |  | fleets/bcit-education/requirements-map.json |
| ED-054 | delivered | `edu-standards-alignment/references/organizations.json` |  | fleets/bcit-education/requirements-map.json |

### Education addendum: 8. Registry and vault additions

| Row | Status | Deliverable | Blocker or missing part | Mapped by |
|---|---|---|---|---|
| ED-055 | delivered | `company-fleets/fleets/bcit-education/evals.json` |  | fleets/bcit-education/requirements-map.json |
| ED-056 | blocked |  | Notes outside this repository are the integrator's step, not this build's. Resume: the integrator adds the four linked entries in its own notes location, with that location's existing frontmatter. | integration (coverage.py) |
| ED-057 | blocked |  | Same step as ED-056: the integrator writes the entries in its own notes location and keeps that location's existing frontmatter and records. | integration (coverage.py) |
| ED-058 | delivered | `company-fleets/fleets/bcit-education/README.md` |  | fleets/bcit-education/requirements-map.json |
