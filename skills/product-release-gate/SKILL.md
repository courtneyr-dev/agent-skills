---
name: product-release-gate
description: Packaging gate for an extension, plugin, theme, module, browser extension, SDK, integration or SaaS release candidate. Checks the host, API and version compatibility matrix first and refuses an incompatible or untested version before any packaging stage, then checks SemVer and release channel, changelog, SBOM licenses and advisories, schema migration and rollback, the platform's own marketplace checklist, and that every input has fresh hash-bound evidence. Use before asking a human to approve packaging or distribution. Not for publishing, tagging or approving the release itself.
disable-model-invocation: true
---

# Product release gate

`scripts/release_gate.py gate` reads one release candidate and decides `ready-for-human-approval`, `refused` or `blocked`. It never approves. The approval owner in the output (`human:release-owner`) decides, through the existing PM and release process.

Compatibility runs first. When it fails, the gate stops and marks every packaging stage `not-run`, so an incompatible host or API version cannot reach packaging approval.

## When to use

- A product release is about to be packaged for a marketplace or direct download.
- You need a host/API/version compatibility matrix checked on its own: `release_gate.py compat --matrix M`.
- A review says "passed" and you need proof the evidence matches the current files and contract.

## Not for

- Writing the changelog or release notes: installed `changelog-writing`.
- Release process design, rollout strategy and DORA metrics: installed `release-engineering` (this gate calls its `semver_check.py` and `changelog_check.py`).
- Dependency advisory research: installed `supply-chain-risk-auditor` (Trail of Bits); feed its findings into `vulnerabilities`.
- WordPress.org policy review itself: installed `wordpress-org-compliance`; record its result as `marketplace_review`.
- Tagging, publishing or submitting anything.

## Inputs

Worked example: `fixtures/candidate-ok.json`. Paths inside a candidate are relative to its directory.

- Compatibility matrix `compat-matrix.v1`: `product {id, platform, version}`, `declares.hosts {host: {min, max}}`, `declares.apis {api: version}`, `platform_facts {source {ref, revision, retrieved}, host_versions, api_versions_served}`, `tests [{host, version, result}]`.
- Release candidate `release-candidate.v1`: `product {id, platform, version, previous_version}`, `public_api_change` (`none`, `additive`, `breaking`), `channel` (`stable`, `beta`, `nightly`), `distribution` (`marketplace`, `direct`), `compat_matrix`, `changelog` (Keep a Changelog or Release Please), `sbom` (CycloneDX JSON), `license_policy.allowed` (SPDX ids), `vulnerabilities [{id, component, severity, status, justification}]`, `migration {schema_from, schema_to, up, down, data_retention}` (required; equal schema numbers when nothing changes), `marketplace_review {platform, checklist, result}` or null, `support_boundary`, `evidence {handoff, contract, base}`.
- A company-fleets `handoff.v1` whose outputs include the candidate file itself, the matrix, the changelog and the SBOM, bound to a factory-rig contract. Each output has one review file with the lines `reviewed-by: <the handoff reviewer>`, `reviewed-sha256: <exact sha256 of the bytes reviewed>` and `verdict: pass`. The producer may not review its own output. `scripts/tests/fixture_handoff.py` shows the shape; its `write_reviews()` is a fixture stand-in for a reviewer and must never run over real inputs.

## Method

1. The compatibility engineer fills the matrix from real test runs and a sourced list of host and API versions, with its retrieval date.
2. The release engineer fills the candidate and binds it, its inputs and their review files in a handoff. Every claim in the candidate (migration results, license policy, advisory status, marketplace result) counts only because a reviewer read those exact bytes.
3. Run `python3 scripts/release_gate.py gate --candidate C`. Stages, in order: compatibility, semver-and-channel, changelog, supply-chain, migration-and-rollback, marketplace-policy, evidence-freshness.
4. Fix each refused stage at its source, get a new review of the changed file, then rebind. Rehashing without a new review fails: the old review still names the old bytes.
5. Hand a `ready-for-human-approval` result to the approval owner.

## Stopping conditions

- Compatibility fails: stop; later stages are `not-run`.
- All other stages ran: report the decision.

## Output contract

JSON: `product`, `channel`, `decision`, `approval_owner`, `support_boundary`, `stages [{stage, status (pass, fail, blocked, not-run), errors [{code, message}], note}]`, `not_checked`. `compat` prints `product`, `status`, `errors`. Exit 0 ready or compatible; 1 refused or blocked; 2 invalid input.

Error codes: `platform-facts-unsourced`, `matrix-product-mismatch`, `host-unknown`, `declared-version-unknown`, `no-hosts-declared`, `declared-range-inverted`, `host-untested`, `incompatible-host`, `untested-host-version`, `api-unknown`, `api-version-not-served`, `version-invalid`, `version-not-increasing`, `breaking-change-without-major`, `additive-change-without-minor`, `channel-prerelease-mismatch`, `changelog-invalid`, `changelog-missing-version`, `sbom-unreadable`, `license-unknown`, `license-not-allowed`, `vulnerability-unknown-component`, `open-vulnerability`, `vex-justification-missing`, `migration-undeclared`, `migration-untested`, `rollback-untested`, `retention-undefined`, `marketplace-platform-mismatch`, `marketplace-review-missing`, `marketplace-checklist-mismatch`, `marketplace-review-failed`, `evidence-unreadable`, `stale-or-invalid-evidence`, `review-not-bound-to-output`, `review-wrong-reviewer`, `review-not-passing`, `input-not-hash-bound`.

Residual limit: review files are not signed, so a producer who writes a review in the reviewer's name is caught only by the reviewer-identity line, not cryptographically.

## Failure states

- A review for one platform offered for another (for example a WordPress.org pass for a Shopify app): `marketplace-platform-mismatch`.
- A platform with no pinned checklist in `references/marketplace-checklists.json`: the marketplace stage is `blocked` and the decision is `blocked`, never `ready`.
- `release-engineering` or `company-fleets` missing beside this skill: that stage is `blocked` with the path it looked for.
- Bad JSON, wrong `schema`, missing field: `{"error": "..."}`, exit 2.

## Adapters and missing capability

Needs `python3` 3.9+, `../release-engineering/scripts/semver_check.py` and `changelog_check.py` (magnus919/agent-skills), and `../company-fleets/scripts/fleetlib` over `../factory-rig`. Test results and platform version lists come from the product's own CI and the platform's published support policy; the gate checks them, it does not run them.

## References and rights

| Source | Version | Rights |
|---|---|---|
| Semantic Versioning (via `semver_check.py`) | 2.0.0 | CC BY 3.0 |
| Keep a Changelog (via `changelog_check.py`) | 1.1.0 | MIT |
| magnus919/agent-skills `release-engineering` scripts | installed copy, revision 6806511df28c (sources ledger) | MIT |
| CycloneDX JSON (component and license fields only) | 1.5 | Apache-2.0 |
| SPDX license identifiers | list as used by the product's policy | CC BY 3.0 |
| `references/marketplace-checklists.json` (WordPress.org pinned through `wordpress-org-compliance`; Chrome Web Store, Mozilla Add-ons, Shopify, Drupal.org, Woo Marketplace and WordPress themes not pinned) | 2026-11-25 | URLs cited only |

## Tests

```bash
cd scripts/tests && python3 -m unittest -v
python3 scripts/tests/fixture_handoff.py   # fixtures only: rewrites fixture reviews and handoffs after editing a fixture
```
