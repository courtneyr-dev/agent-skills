---
name: consult-search-claims-check
description: Check a draft SEO or AI-search report against a register of captured sources and reject fabricated citations, quotes missing from the capture, edited captures, guaranteed-placement promises, and ranking-factor or forecast claims stated as fact without primary evidence. Use before an SEO, AIO, AEO or GEO report, audit summary or pitch goes to a client or reviewer. Not for running the audit itself, live crawling or rank tracking.
disable-model-invocation: true
---

# Consult search claims check

`scripts/claims_check.py` reads one draft report (`search-claims.v1`) and one source register (`source-register.v1`). Every quote must appear in a hashed capture of a registered source. A ranking factor or forecast without a primary platform document or first-party measurement stays a hypothesis. Placement promises are rejected. The script decides whether each claim is supported, a labeled hypothesis, or rejected; whether a supported claim is wise advice stays with a human reviewer.

## When to use

- A search or AI-answer visibility report, audit summary or proposal is about to leave the practice.
- A claim cites a study, a platform doc or a measurement and you need proof the quote is real.
- A teammate or client asks for "guaranteed" placement wording and you need a repeatable refusal.

## Not for

- Running an SEO audit: installed `seo-audit` (coreyhaines31/marketingskills).
- AI-search strategy and content changes: installed `ai-seo`.
- Structured data: installed `schema`.
- Live crawling, rank tracking or reading AI answers. This script makes no network calls.

## Inputs

- Draft report: `schema` `search-claims.v1`, `label`, `report_id`, `tenant_id`, `claims` of `{id, text, kind, status_label, evidence}`. `kind` is `observation`, `recommendation`, `ranking-factor` or `forecast`. `status_label` is `observed`, `hypothesis`, `estimate` or `recommendation`. `evidence` is a list of `{source_id, quote}`.
- Source register: `schema` `source-register.v1`, `label`, `sources` of `{id, url, title, retrieved, kind, capture_path, sha256, registered_by, verified_by}`. A `primary-platform-doc` or `first-party-measurement` source counts as primary only when `verified_by` names a human (`human:...`) other than `registered_by`; an unverified one is treated like a secondary source. `kind` is `primary-platform-doc`, `first-party-measurement` or `secondary`. `capture_path` is relative to the register file and may not leave its directory.
- Worked example: `fixtures/report-clean.json` with `fixtures/register.json` and `fixtures/captures/`.

## Method

1. Capture each source you cite as text, hash it with SHA-256, and add it to the register. A capture is a record of what you read on `retrieved`, not proof the page still says it.
2. Run `python3 scripts/claims_check.py --claims REPORT --sources REGISTER`.
3. Fix every rejected claim: cite a registered source, quote it exactly, relabel an unproven ranking factor or forecast as `hypothesis` or `estimate`, or delete the promise.
4. Send the passing report and the register to the reviewer named in the handoff. Observed visibility claims also need the tenant's own Search Console or analytics export.

## Stopping conditions

- Every claim has a verdict: report the result.
- Invalid input: stop at exit 2 and fix the file.

## Output contract

One JSON object: `report_id`, `status` (`pass` or `defects`), `claims` of `{id, verdict, defects}` where `verdict` is `supported`, `hypothesis` or `rejected`, `counts`, `human_review_required`, `not_checked`. Each defect has `code`, `severity`, `claim_id`, `message`. Exit 0 with no errors, 1 with any error, 2 for invalid input or usage.

Defect codes: `citation-unknown-source` (source id not in the register), `capture-missing`, `quote-too-short` (fewer than 4 words), `quote-unrelated` (fewer than 2 content words shared with the claim), `capture-hash-mismatch` (capture edited after hashing), `quote-not-found`, `guaranteed-placement`, `ranking-factor-unsupported`, `forecast-unlabeled`, `observation-without-evidence`.

## Failure states

- Bad JSON, wrong `schema`, a missing field, a duplicate id or a capture path outside the register directory: `{"error": "..."}`, exit 2.
- A capture that changed after hashing: every claim quoting it is rejected with `capture-hash-mismatch`.
- A self-registered source with a self-written capture passes the hash check; it cannot make a ranking factor a fact unless a different human verified it. The script cannot tell whether a verified capture matches the live page.
- A promise worded outside `references/guarantee-patterns.json` passes the script. The pattern list is a heuristic; a human still reads every passed claim. A negated sentence ("we cannot guarantee a ranking") is flagged, because the script does not parse negation.

## Adapters and missing capability

Needs only `python3` 3.9+. Captures come from whatever fetch tool the practice uses (a browser, `curl`, a docs MCP); the script reads files only. Without the tenant's measurement export, observed-visibility claims stay unverified and the report says so.

## References and rights

| Source | Version | Rights |
|---|---|---|
| `references/guarantee-patterns.json` | 2, 2026-11-26 | Original to this rig |
| coreyhaines31/marketingskills `ai-seo` (method source for AI-search practice) | commit 8fd2fca, 2026-11-23 | MIT License, copyright 2025 Corey Haines |
| Google Search Central, "Creating helpful, reliable, people-first content" and "AI features and your website" | verify at use; not pinned here | Google site terms; cite the URL, do not copy |

## Tests

```bash
cd scripts/tests && python3 -m unittest -v
```
