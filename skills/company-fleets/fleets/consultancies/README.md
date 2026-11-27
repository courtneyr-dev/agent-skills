# Consultancies fleet runbook

The consultancies fleet runs seven specialist practices: accessibility, rebrand, internationalization, compliance, ecommerce, SEO and AI search, and email and lifecycle. It has 20 roles, 7 workloads, 4 original skills and 51 eval cases. Every client, contact and record here is a labeled Fixture Co fixture.

`consultancies.practice-coordinator` is the only coordinator and never dispatches. `consultancies.independent-reviewer` reviews every practice deliverable it did not produce. A named human (`human:engagement-owner`) accepts deliverables for the client.

## Run a practice

```bash
cd skills/company-fleets
bin/fleet resolve --profile agency --workload consultancies.workload.compliance-engagement
```

| Workload | Profiles | Lead | Practitioners |
|---|---|---|---|
| `accessibility-engagement` | agency, product, enterprise | a11y-lead | a11y-auditor, a11y-remediation |
| `rebrand` | agency, product | rebrand-lead | rebrand-researcher, rebrand-designer |
| `localization` | agency, product | i18n-lead | localization-qa; translators and locale reviewers are human |
| `compliance-engagement` | agency, product, enterprise | compliance-lead | compliance-engineer; control owners are human |
| `ecommerce-engagement` | agency, product | commerce-lead | commerce-engineer, commerce-operations |
| `search-engagement` | agency, product | search-lead | technical-seo |
| `lifecycle-email` | agency, product | lifecycle-lead | email-practitioner, consent-steward |

Every workload also lists the coordinator and the independent reviewer.

## Gates the practices run

| Practice | Command (from `skills/`) | Stops |
|---|---|---|
| Compliance | `python3 consult-compliance-engagement/scripts/engagement_check.py --engagement E --evidence-root DIR --selector S` | Six stages: applicability, control owners, evidence (rehashed from `DIR/<tenant>/`), gaps, independent review, authorized report; claim categories come from the text, not the label |
| Localization | `python3 consult-i18n-check/scripts/i18n_check.py --source S --target T` (JSON catalogs); `agency-i18n-check` for gettext | Placeholder, plural, bidi, RTL, length, glossary, untranslated, stale defects; linguistic review always required |
| Email | `python3 consult-email-send-gate/scripts/send_gate.py --campaign C --ledger L --sender-auth A --now T` | Suppression wins on the mailbox key (plus-tags and trailing dots removed); the approval binds kind, sender, subject, headers, content and recipients; `sends_performed` is always 0 |
| SEO and AI search | `python3 consult-search-claims-check/scripts/claims_check.py --claims R --sources G` | Unregistered citations, misquotes, quotes under 4 words or unrelated to the claim, edited captures, listed placement-guarantee wordings, ranking factors without a primary source a second human verified. It cannot prove a registered source is accurate |
| Ecommerce | `python3 product-payment-events/scripts/payment_events.py process ...` (product fleet skill) | Duplicate events cannot double a capture or fulfillment |

## Skills attached

Written by this workstream: [consult-compliance-engagement](../../../consult-compliance-engagement/SKILL.md), [consult-i18n-check](../../../consult-i18n-check/SKILL.md), [consult-email-send-gate](../../../consult-email-send-gate/SKILL.md), [consult-search-claims-check](../../../consult-search-claims-check/SKILL.md). Each has SKILL.md, scripts, fixtures, references with rights, unit tests and positive, negative and boundary evals. The i18n, email and search-claims skills were started by helper agents that were stopped mid-run; their code, fixtures and tests were reviewed and rerun here, and consult-search-claims-check's SKILL.md and evals were written here.

Adopted, installed upstream (attached by id, not copied):

| Source | License | Skills |
|---|---|---|
| trailofbits/skills | CC BY-SA 4.0 | fp-check, differential-review (independent reviewer), supply-chain-risk-auditor (compliance engineer) |
| alirezarezvani/claude-skills | MIT | compliance-os (framework_selector.py feeds the compliance gate), soc2-compliance, isms-audit-expert, gdpr-dsgvo-expert, access-lifecycle, support-ops |
| coreyhaines31/marketingskills | MIT | ai-seo, seo-audit, schema, site-architecture, content-strategy, analytics, attribution, emails, marketing-loops, customer-research, competitor-profiling, product-marketing |
| zstvns/design-skills | MIT | brand, brand-strategy, creative-direction, art-direction, logo-design, design-system |
| magnus919/agent-skills | MIT | web-accessibility, verification-methodology |
| samber/developer-relations-skills | MIT | docs-localization-strategy |
| Automattic/claude-woocommerce-toolkit | GPL-2.0 | woocommerce-plugin-dev, woocommerce-upgrade-safety |
| Sibling fleets | agent-skills (MIT) | agency-keyboard-audit, agency-i18n-check (corporate-and-agency), product-payment-events (product), company-fleets (foundation) |

Overlap to consolidate: `agency-i18n-check` (gettext PO/POT, templates, CSS) and `consult-i18n-check` (JSON catalogs, CLDR 48 categories, glossary) check the same defect classes in different formats. Both SKILL.md files route by format today; the integrator can merge them later.

## Shared context records

The design and marketing skills write per-project records into the client project's `.agents/` folder. None exists rig-wide. One owner per artifact, per tenant:

| Record | Owner of record | Maintained during an engagement by |
|---|---|---|
| `.agents/brand.md` | `human:brand-owner` | consultancies.rebrand-lead |
| `.agents/design.md` | `human:brand-owner` | consultancies.rebrand-designer |
| `.agents/product-marketing.md` | the corporate fleet's product marketing owner | not this fleet; drafts only |

## Requirement map (section 7)

| Row | Deliverable or blocker |
|---|---|
| S07-001 lead, practitioners, independent reviewer, workflow | Workloads; test `each-practice-has-lead-practitioner-reviewer` |
| S07-002, S07-003 accessibility | Roles, web-accessibility, agency-keyboard-audit. Unverified here: the keyboard-defect case needs headless Chromium and runs in the agency fleet |
| S07-004, S07-005 rebrand | Roles and Zach Stevens's skills. Partial: asset-rights and token-consistency checks are manual |
| S07-006, S07-007 internationalization | consult-i18n-check and agency-i18n-check; human locale review stays required |
| S07-008, S07-009 compliance | consult-compliance-engagement |
| S07-010, S07-011 ecommerce | product-payment-events (webhooks, refunds, inventory races, reconciliation), WooCommerce skills. Not covered by a script: tax and shipping |
| S07-012, S07-013 SEO and AI search | consult-search-claims-check and Corey Haines's skills. Partial: observed visibility needs the tenant's exports |
| S07-014, S07-015 email | consult-email-send-gate |
| S07-016 keep conformance, applicability, certification and legal conclusions apart | Compliance claim kinds and `claim-category-overreach` |
| S07-017 applicability registry | `consult-compliance-engagement/references/applicability-registry.json`, seven frameworks. Editions were not re-fetched from publishers |
| S07-018 no unrelated medical or regulatory workflows | None installed; selector picks outside the registry are refused as `framework-unregistered` |
| S07-019 scanner is not conformance | a11y roles' limitations; agency-keyboard-audit pairs scan and keyboard walk |
| S07-020 translation accuracy separate | `linguistic_review: required` in every i18n result; eval `linguistic-review-not-fabricated` not run |
| S07-021 AIO claims as hypotheses | consult-search-claims-check |
| S07-022 Corey Haines and Zach Stevens canonical | Attachments above |
| S07-023 shared brand and context records | Table above |
| S07-024 bounded marketing loops | lifecycle-lead requires a stop and staged output per loop; no cadence enabled; sending stays with the tenant's system. Unverified: no loop run |

## Four states

- Roles: coverage 18 covered and 2 partial; installed `reference-only`; activated `not-activated`; behavioral `unverified`.
- Skills: coverage covered; installed `installed` for the Claude mount ([skills-installed.txt](evidence/skills-installed.txt)); activated `not-activated`; behavioral `verified` for deterministic script behavior only.

## Evals and evidence

```bash
cd skills/company-fleets
python3 fleets/product/tests/run_evals.py --fleet consultancies --write   # shared runner lives in the product fleet
python3 fleets/consultancies/tests/test_consultancies_fleet.py -v
bin/fleet validate --strict --fleet consultancies
```

Last run, 2026-11-26, after the review fixes: 49 pass, 0 fail, 2 not run (a human keyboard test and a model-judgment persona case). Raw outputs live in [evidence/](evidence/).

Acceptance rows and their evidence:

- Compliance engagement inputs: [compliance-report-may-issue.txt](evidence/compliance-report-may-issue.txt), [compliance-gaps-refused.txt](evidence/compliance-gaps-refused.txt), [compliance-evidence-at-age-limit.txt](evidence/compliance-evidence-at-age-limit.txt)
- Ecommerce: [duplicate-payment-events-no-duplicate-fulfillment.txt](evidence/duplicate-payment-events-no-duplicate-fulfillment.txt)
- Untrusted client content and tenant boundary: [untrusted-client-note-cannot-change-authority.txt](evidence/untrusted-client-note-cannot-change-authority.txt)
- Trail of Bits only where installed: [trail-of-bits-only-where-installed.txt](evidence/trail-of-bits-only-where-installed.txt)
- Localization, email and search: the `i18n-*`, `email-*` and `search-*` files in evidence/

## Recovery and rollback

Roll back with git on `skills/company-fleets/fleets/consultancies/` and the four `skills/consult-*` directories. Every gate reads files and writes nothing, so a rerun after a fix is safe.

## Review fixes, 2026-11-26

An independent review (product-consultancies.md, not published) found these defects in this fleet's skills. Each fix has a failing-first test and an eval in [evidence/](evidence/).

- Blocker 1: an email approval bound only the campaign id and content, so a campaign relabeled transactional, or one with an added recipient, stayed authorized. `send-authorization.v2` now carries `approval_sha256` over tenant, kind, sender domain, subject, headers, content and the resolved recipients; v1 files are refused. Eval `email-approval-binds-dispatch-fields`.
- Defect 2: `dee+news@example.com` and `dee@example.com.` escaped a suppression on `dee@example.com`. Suppression and dedupe now use the mailbox key stated in the skill. Eval `email-mailbox-variants-suppressed`.
- Defect 8: six common guarantee wordings passed. The pattern list is at version 2. Eval `search-guarantee-phrasings-rejected`.
- Defect 9: a one-word quote or a self-registered "primary" source supported a ranking factor. Now `quote-too-short`, `quote-unrelated`, and primary only with a second human's `verified_by`. Eval `search-weak-or-self-registered-evidence-rejected`.
- Defect 10: claim kinds were self-labeled. Text and framework now decide the category; WCAG claims are limited to evidenced criteria. Eval `compliance-claim-labels-cannot-soften`.
- Defect 11: evidence hashes and tenancy were format checks. The gate rehashes each artifact under `--evidence-root/<tenant_id>/` and refuses a run without it. Eval `compliance-evidence-rehashed-in-tenant`.

## Follow-ups

Not fixed in this round, by instruction:

- Minor 12: the email gate exits 0 without an authorization (only `authorized_for_dispatch` is false), and it accepts an `approved_at` later than `--now`. Resume: refuse a future `approved_at`, and add a `--require-authorization` flag that exits 1 when authorization is absent.
- Minor 15: the WooCommerce toolkit is recorded as GPL-2.0; its README says GPL v2 or later (`GPL-2.0-or-later`). Resume: correct the provenance strings in `roles.json` and the table above.
- The guarantee patterns still flag a negated promise such as "We cannot guarantee a ranking"; the pattern file says so.
- Foundation gaps: see the product runbook's Follow-ups (evidence reviewer identity is checked only inside product-release-gate; scanner misses two phrasings).
