# Shared corporate services fleet

The corporate fleet gives every business profile except `school` one set of shared services: executive direction, technology, product, finance, commercial, marketing, partnerships, customer operations, people, risk, internal operations, data and communications. It has 23 roles, 12 workloads and one coordinator, `corporate.chief-of-staff`. Every company record it touches is the Fixture Co fixture; nothing here is a real business.

## How work reaches it

The existing router (Claude Code plus credit-routing) picks a workload; factory-rig owns leases and contracts. Resolve the smallest role set, then load only the listed skills:

```bash
cd skills/company-fleets
bin/fleet resolve --profile agency --workload corporate.workload.proposal-and-pricing
```

The coordinator delegates inside the workload and never dispatches (`dispatch` is false on every role). Scope changes return through the PM layer.

## Workloads

| Workload | Roles beyond the coordinator | Profiles |
|---|---|---|
| strategy-decision | strategy-advisor, operations-advisor, finance-advisor | all corporate profiles |
| technology-decision | technology-advisor, security-lead, finance-advisor | all corporate profiles |
| finance-close | controller-workflow, finance-advisor, internal-auditor | all corporate profiles |
| proposal-and-pricing | revenue-lead, solutions-engineer, proposal-lead, deal-desk, contract-liaison | reseller, shared, managed, platform, enterprise, agency, product |
| campaign-staging | marketing-lead, lifecycle-marketer, data-analytics-lead, communications-lead | all corporate profiles |
| partner-program | partnerships-manager, finance-advisor, contract-liaison | affiliate, reseller, product, platform, agency |
| customer-onboarding | customer-success-lead, solutions-engineer | reseller, shared, managed, platform, enterprise, agency, product |
| capacity-plan | people-ops-advisor, operations-advisor, finance-advisor | all corporate profiles |
| risk-review | security-lead, privacy-compliance-analyst, contract-liaison, internal-auditor | all corporate profiles |
| vendor-review | internal-operations, security-lead, contract-liaison, controller-workflow | all corporate profiles |
| crisis-communications | communications-lead, contract-liaison, strategy-advisor, security-lead | all corporate profiles |
| metric-definition | data-analytics-lead, product-portfolio-lead | all corporate profiles |

"All corporate profiles" means affiliate, reseller, shared, managed, platform, enterprise, agency, product, devrel and community. Affiliate and reseller stay separate profiles. Each role's `purpose` names the titles it covers, for example `corporate.revenue-lead` covers CRO, business development, sales development, account executive and sales operations.

## Skills: adopted and written

Adopted (installed upstream, attached by id, never copied):

- alirezarezvani/claude-skills at `ea7b5ab8da93`, MIT, Alireza Rezvani: 9 c-level-advisor skills, 4 business-growth, 4 business-operations, 5 commercial, 2 finance, 1 product-team, compliance-os and 4 ra-qm-team skills.
- coreyhaines31/marketingskills at `8fd2fcade2fd`, MIT, Corey Haines: marketing-plan, product-marketing, ads, ad-creative, marketing-loops, emails, content-strategy, seo-audit, ai-seo, analytics, ab-testing, attribution, conversion-tracking, competitor-profiling, prospecting, sales-enablement, referrals, public-relations.
- magnus919/agent-skills at `6806511df28c`, MIT, Magnus Hedemark: technical-program-management, verification-methodology, agent-evals-and-observability, production-readiness.
- yysun/project-manager: brd-writer.

Written for this fleet (gaps no installed skill covered):

- `corporate-claims-check`: rejects guaranteed rankings or AI-answer placement, uncited outcomes and statistics, and fabricated citations, quotes and numbers. It checks the text a reader sees and reads the register's sign-off from the owner log of the instance the register names, never from the register. The SEO/AIO gate.
- `corporate-email-guard`: suppression at staging and at send, human approval bound to hashes, fake outbox only; the suppression list and the approval come from the campaign's owner log. The email gate.

## Evaluations

`run_evals.py` in this folder serves both this fleet and the agency fleet:

```bash
python3 fleets/corporate/run_evals.py run --fleet corporate        # every script case; writes evidence and outcomes
python3 fleets/corporate/run_evals.py expect --exit 1 --contains TEXT -- CMD ...   # one self-asserting check
```

Results on 2026-11-26 on the author's machine, with the upstream skills installed (`run_evals.py run --fleet corporate` in a copy of the skills tree, and `bin/fleet eval-run --fleet corporate` in the real tree): 39 script cases pass, 0 fail. From this repository alone, 16 pass and the 23 routing cases fail on `"installed": false`, because their roles attach upstream skills; `../../registry/eval-external-needs.json` lists them; 23 persona cases (model judgment) are recorded and not run. `evidence/run-evals-self-check.txt` shows the runner failing five wrong expectations and passing the control.

| Acceptance row | Case | Evidence |
|---|---|---|
| SEO/AIO: ranking claims and fabricated citations rejected | claims-ranking-guarantee-rejected, claims-fabricated-citation-rejected, claims-uncited-statistic-rejected, claims-review-guarantee-phrasings-flagged, claims-register-sign-off-enforced, claims-hidden-text-checked, claims-cautionary-sentences-pass, claims-unclosed-fence-refused | `evidence/claims-*.txt` |
| Email: suppressed stay suppressed, no send without authority | email-suppressed-stay-suppressed, email-send-without-authority-refused, email-retry-and-tamper-boundary, email-malformed-suppression-refused | `evidence/email-*.txt` |
| Selective loading | unrelated-fleets-stay-unloaded, school-profile-excludes-corporate | `evidence/unrelated-fleets-stay-unloaded.txt` |

`evidence/claims-register-source-check.txt` confirms the two Google Search Central sentences in the claims register appear verbatim on the live page.

## The four states

- Coverage: 23 of 23 roles covered.
- Installed: every role is `reference-only`, like the sibling fleets: no native agent configuration exists, and each note cites the routing case that shows `fleet resolve` loading it with every attached skill present. Both local skills installed (`evidence/skill-unit-tests.txt`, 78 tests).
- Activated: nothing activated; no real router session has selected these roles.
- Behavioral: both local skills verified by script. Every role stays unverified, because its persona case needs a model run that hasn't happened.

## Review fixes (evidence/reviews/corporate-agency.md)

| Defect | Before | After |
|---|---|---|
| 3 Guarantee phrasings | 16 of the review's 25 passed, exit 0 | All 25 flagged by a phrase-class check (promise cue plus ranking or AI-answer target, either order); reporting sentences still pass |
| 4 The register accepted any source its author added | An invented analyst source backed a 310% claim | The register needs an author and a sign-off from a different named human bound to the sources hash; any later edit voids it |
| 5 Citation checks proved less than their names | `"ran"` matched inside "guarantee"; 42% borrowed from another fact; cited outcomes unchecked | Quotes need three or more words and whole-word matches; numbers need matching context; cited outcomes need an excerpt that states them |
| 11 Malformed suppression rows loaded silently | A trailing dot or zero-width character suppressed nothing | Both normalized on contacts and suppression rows alike; a row that still isn't an address exits 2 |
| 18 Minor: roles claimed `installed` | 23 installed | 23 `reference-only` |

The company margin policy lives here, at `policies/margin-policy.json` (owner `human:finance-owner`, floor 0.35, basis hypothesis). An agency engagement's coordinator pins it in the owner log of the engagement's instance, and the brief gate reads it from there; no flag or brief field sets or passes a floor, and a ledger of another tenant is refused. A same-user process can still write the owner root, read the claim token, or claim an instance first, including a new instance id written into its own brief (`../../references/authoring-guide.md`, Owner path and its limit).

## Re-review fixes (evidence/reviews/corporate-agency-rereview.md)

The re-review found that the register's own `sign_off` was a trusted value the draft's author could rewrite. The owner path (`../../references/authoring-guide.md`, Owner path and its limit) replaces it. Probes and their before and after output: `../../evidence/reviews/rereview-probes/`.

| Finding | Before | After |
|---|---|---|
| 6 The register's sign-off hash could be recomputed by whoever edits it | An invented S9 source with a recomputed `sources_sha256` backed a 310% claim, exit 0 | The sign-off is an owner-log record looked up by the sources hash. Any edit to the sources, or a `sign_off` field written into the register, gets `register-not-signed-off`; the author can't record one without the claim token (`not-the-lease-holder`) and can't sign their own (`register-self-signed`) |
| 7 Invisible and look-alike characters | 7 disguised guarantees exit 0 | HTML entities decoded, NFKC, format characters dropped, Cyrillic and Greek look-alikes folded, spaced letters rejoined; all 7 flagged |
| 8 The checker skipped text a reader sees | A fenced guarantee, an unclosed fence and footnote text exit 0 | Fenced and footnote text checked; an unclosed fence exits 2 |
| 9 Fabricated quotes passed outside straight double quotes | Single-quoted, „…“, «…», blockquote and uncited attributed misquotes exit 0 | These quote forms are compared with the cited excerpt (`quote-not-in-source`); an attributed quote with no citation gets `quote-without-citation`. The second re-review found four more forms; see below |
| 10 Cautionary and reporting sentences were blocked | 8 of 11 benign sentences, the verbatim S1 quote and the two-word "someone else" exit 1 | A promise counts only when the author makes it or makes it to the client; certified and warranted count only right after a position; a verbatim cited quote is the source's speech; quotes need two words. All 14 pass, and all 25 first-review phrasings stay flagged |
| 15 Minor: paraphrased promises | "You can count on a #1 ranking", "We make sure you rank #1", "We ensure first-page rankings", "Your site ranks #1 after our audit" exit 0 | All 4 flagged |

The cross-fleet demo `demos/03-extension-release` runs the claims check on a launch register that names no instance, so no owner ledger holds a sign-off for it, and its launch copy stays blocked only at `register-not-signed-off`, as before.

## Second re-review fixes (evidence/reviews/corporate-agency-rereview-2.md)

The second re-review found that each gate trusted whichever ledger folder the caller named, and that `fleet claim` made any caller an owner. Probe scripts and their raw before and after output: `../../evidence/reviews/rereview2-probes/`. Every after command below ran on 2026-11-26.

| Finding | Before | After |
|---|---|---|
| 1 Blocker: the sign-off came from a ledger the caller picked | A ledger minted with `fleet claim` signed an invented S9 source, and so did a copy of the fixture ledger claimed at epoch 3: `Gartner found Fixture Co clients saw 310% more organic traffic[^S9].` exit 0 | The register names its instance (`instance`, `tenant_id`) and the check reads only that instance's ledger at `owner/<instance>/`; `--owner-ledger` is a usage error (exit 2); a ledger of another tenant gets `ledger-not-for-this-work`. Claiming the fixture instance gets `ledger-exists`, a plain claim on its store gets `owner-ledger-lease-store`, and a token from any other lease can't record (`stale-epoch`). The S9 draft gets `register-not-signed-off` (probes K1-K6). Still possible, as documented: an author who writes a new instance id into the register and claims it first |
| 2 Owner logs were git-ignored | In a tracked-files-only copy, 6 of 48 claims tests failed, and `claims-register-sign-off-enforced`, `claims-cited-draft-passes` and `claims-cautionary-sentences-pass` failed | Renamed `owner-log.ndjson`, `owner-head.json` and `<key>.owner-seal.json`. In a copy of `git ls-files -co --exclude-standard` output: 56 of 56 claims tests, 22 of 22 email guard tests and 39 of 39 corporate eval cases pass |
| 3 Guarantees with a cue named in the limits passed | 13 of the reviewer's 29 forms flagged, among the misses `A #1 ranking on Google is guaranteed by our team.`, `Zero risk: you will outrank every competitor on Google.`, `Fixture Co clients are always shown first in AI Overviews.`, `Number one on Google, or we work for free.`, and `Guar**anteed**`, `<b>Guar</b>anteed`, combining marks and `guaran-` across a line break | 24 of 29 flagged. HTML tags, Markdown emphasis inside a word, combining marks and a hyphenated line break are removed before matching; an engine after a preposition ("on Google") no longer reads as the speaker; `outrank`, `shown`/`listed` with an AI-answer target, `or we ... free`, and Spanish, French and German guarantee words with a few position phrases and their basic negations are matched. The 5 still passing have no cue word and are named in the limits. All 12 of the reviewer's benign sentences, the 14 earlier ones and two negated German and Spanish sentences pass |
| 4 Quote forms escaped the source comparison | `> quote[^S1]`, a blockquote with a dashless `Google Search Central[^S1]` line, `<q>` and `<blockquote>` misquotes each exit 0 | A blockquote cited on itself, or by a short cited name line after it, is a quotation; `<q>` and `<blockquote>` become their Markdown forms; `「…」` and `『…』` are quotation marks. 11 of the reviewer's 14 quote forms are refused; the code span, italics and colon paraphrase are listed in the limits as not quotes |
| 6 The email guard took the suppression list and approval from the caller | An empty caller list and a caller-written `human:me` approval sent 6 messages, `carol@example.com` among them; `carol+news@example.com` and `v.ictim@gmail.com` staged with `suppressed: 0` | `--suppression` and `--approval` are usage errors (exit 2). The list is a pin named `suppression-list` and the approval a write-once `send-approval` entry, both in the campaign's owner ledger (`owner/<campaign_id>/`), recorded with `fleet owner-record`. Carol stays suppressed; a `+tag` on any domain and Gmail dots fold for matching, so both variants are suppressed. The fake outbox stays the only transport |
| 10 Minor: text overclaimed | This README said "neither a brief nor a caller can set or pass a floor", and the claims limits named only direct log writes and token reads | Restated here and in every gate's limits with the three same-user limits: writing the owner root, reading the token, claiming an instance first |

## Follow-ups (minors from the review, not fixed)

- 13 (closed by the second re-review's major 6): the suppression list and the approval now come from the campaign's owner log, and plus tags and Gmail dots fold for matching. Still true: any `human:` title the contract owner records counts as the approver, and an approval binds the campaign and recipient hashes, not the suppression list, which the guard re-reads at send.
- 19: `yysun/project-manager` (brd-writer) has no LICENSE upstream, and `company-fleets/sources/README.md` says it isn't redistributable as is.

## Recovery and rollback

- Registry files are plain JSON; `bin/fleet validate --strict --fleet corporate` must print `"ok": true` after any edit.
- Rerunning `run_evals.py run` rewrites evidence and outcomes; failing cases stay recorded as `fail`.
- Rolling back means restoring `roles.json`, `skills.json`, `evals.json` and the two skill folders from git; nothing outside them depends on this fleet except agency workloads that name `corporate.deal-desk`.

## Limits

- Advisor skills carry SaaS-style benchmarks; every role treats them as hypotheses for the actual business model.
- No role sends, publishes, buys, signs, files or decides employment; drafts go to named human owners (`human:company-owner`, `human:finance-owner`, `human:send-authority-owner` and others).
- `requirements-map.json` maps all 30 section 3 requirement rows to a deliverable for the integrator.
