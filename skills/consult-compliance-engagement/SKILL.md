---
name: consult-compliance-engagement
description: "Workflow gate for a compliance consulting engagement (SOC 2, ISO/IEC 27001, PCI DSS, GDPR, NIST, WCAG or a client obligation). Checks six stages in order: applicability with edition, jurisdiction, scope, licensed-text rights and human owners; human control owners; fresh, hashed, same-tenant evidence; gap remediation and risk acceptance; independent review; and a human-authorized report whose claims keep technical conformance, regulatory applicability, certification and legal conclusions apart. Use when scoping, running or reporting a compliance or audit-readiness engagement. Not for issuing certifications, legal opinions or auditor attestations."
disable-model-invocation: true
---

# Consult compliance engagement

`scripts/engagement_check.py` reads one `compliance-engagement.v1` record and reports each stage's errors. A report may issue only when every stage passes and a named human authorized it. The practice prepares evidence; it never certifies, attests or gives a legal conclusion. Those come from the issuer each framework names in `references/applicability-registry.json`.

## When to use

- Starting an engagement: record which frameworks apply, at which edition, for which scope, and who owns the evidence.
- Before an independent review: confirm owners, evidence age and hashes, and that the reviewer produced nothing it reviews.
- Before a report leaves the practice: confirm authorization and claim wording.

## Not for

- Choosing candidate frameworks from a company profile: installed `compliance-os` (`compliance-os/scripts/framework_selector.py`); pass its JSON output with `--selector` so every pick gets resolved.
- Framework-specific methods: installed `soc2-compliance`, `isms-audit-expert` (ISO 27001), `gdpr-dsgvo-expert`, all alirezarezvani/claude-skills.
- Medical-device, AI Act or other regulatory workflows the selector can name: out of scope for this practice unless a client obligation names them; they stay unregistered and the check refuses them.
- Certifying, attesting or giving legal advice.

## Inputs

Worked example: `fixtures/engagement-ok.json` with `fixtures/selector-output.json` and `--evidence-root fixtures/evidence-store`.

- `engagement_id`, `tenant_id`, `as_of` (ISO date).
- `applicability [{framework, decision (applies, not-applicable, undetermined), edition, jurisdiction, scope, text_rights_status (obtained, public, not-obtained), evidence_owner, review_authority, rationale}]`. Framework ids come from the registry.
- `controls [{id, framework, owner, description}]`.
- `evidence [{control, ref, sha256, tenant_id, collected_by, collected_on, max_age_days}]`. `ref` is a relative path under `<evidence-root>/<tenant_id>/`; the gate rehashes the artifact there and refuses a mismatch, a missing artifact, a path naming another tenant, or any run without `--evidence-root`.
- `exceptions [{id, control, status (open, remediated, risk-accepted), retest_evidence, accepted_by, expires}]`.
- `review {reviewer, scope_covered, result (no-findings, findings-recorded)}`.
- `report {author, status (draft, authorized), authorized_by, claims [{id, kind, framework, text, basis {kind, ref, issued_by}}]}`. Claim kinds: `technical-conformance`, `regulatory-applicability`, `organizational-certification`, `legal-conclusion`.

## Method

1. Run compliance-os `compliance-os/scripts/framework_selector.py PROFILE --output json` when a company profile exists, and save the output.
2. Resolve every candidate: `applies` with edition and rights, or `not-applicable` with a rationale. Confirm each edition at the publisher before relying on it; the registry was not re-fetched.
3. Name a human owner per control; collect hashed evidence inside the tenant.
4. Remediate or have a human accept each gap; send to an independent reviewer who collected nothing.
5. Run `python3 scripts/engagement_check.py --engagement E --evidence-root DIR [--selector S]` at each stage boundary; fix errors at their source.

Claim categories come from the text and framework, not only the label. A claim that says certified, attested, or compliant with an attested or certifiable framework (SOC 2, ISO/IEC 27001, PCI DSS) is a certification claim. A claim that says lawful, legally, liability, or complies with a regulation (GDPR) is a legal conclusion. A label can make a claim stricter, never looser. A WCAG conformance claim may name only success criteria with evidenced controls (`WCAG-2.1.1`); a level or whole-standard claim needs a `full-evaluation` basis.

## Stopping conditions

- All six stages ran: report the decision (`report-may-issue`, `ready-for-human-authorization`, `not-ready`).
- Invalid input: stop at exit 2.

## Output contract

JSON: `engagement_id`, `stages [{stage, status, errors [{code, where, message}]}]`, `decision`, `human_decisions_required`, `not_checked`. Exit 0 for `report-may-issue` or `ready-for-human-authorization`, 1 for `not-ready`, 2 for invalid input.

Error codes by stage: applicability (`selector-framework-unresolved`, `framework-unregistered`, `applicability-undetermined`, `rationale-missing`, `applicability-incomplete`, `edition-mismatch`, `licensed-text-not-obtained`, `owner-not-human`); control owners (`control-framework-not-applicable`, `control-owner-not-human`); evidence (`evidence-stale`, `evidence-future-dated`, `evidence-unhashed`, `evidence-cross-tenant`, `evidence-ref-invalid`, `evidence-ref-names-other-tenant`, `evidence-hash-unverified`, `evidence-artifact-missing`, `evidence-hash-mismatch`, `collector-is-reviewer`, `control-without-evidence`); gaps (`exception-open`, `exception-acceptance-invalid`, `remediation-unverified`, `exception-status-unknown`); review (`review-missing`, `reviewer-not-independent`, `review-scope-incomplete`, `review-not-complete`); report (`certification-claim-without-attestation`, `legal-conclusion-without-counsel`, `claim-category-overreach`, `conformance-claim-exceeds-evidence`, `report-not-authorized-by-human`, `report-self-authorized`, `report-authorized-with-open-errors`).

## Failure states

- Licensed text (ISO, PCI DSS, AICPA) not obtained: `licensed-text-not-obtained`; do not paraphrase the standard from memory to fill the gap.
- A framework not in the registry: `framework-unregistered`; add it with edition, rights and attestation issuer first.
- Bad JSON, wrong schema, malformed date or a selector file without `applicable_frameworks`: exit 2.

## Adapters and missing capability

Needs `python3` 3.9+. Optional: `../compliance-os/scripts/framework_selector.py` for candidates. Evidence artifacts live in the tenant's own systems; the record holds their refs and hashes only. Without a human reviewer or authorizer the decision stays `not-ready` or `ready-for-human-authorization`.

## References and rights

| Source | Version | Rights |
|---|---|---|
| `references/applicability-registry.json` (WCAG 2.2, PCI DSS v4.0.1, ISO/IEC 27001:2022, SOC 2 TSC 2017, NIST CSF 2.0, NIST SP 800-53 Rev. 5, GDPR) | as of 2026-11-25, not re-fetched | Per framework in the file; only names, editions and URLs recorded |
| alirezarezvani/claude-skills `compliance-os` framework_selector.py | rig-upstream clone ea7b5ab8, 2026-11-23 | MIT, copyright 2025 Alireza Rezvani |

## Tests

```bash
cd scripts/tests && python3 -m unittest -v
```
