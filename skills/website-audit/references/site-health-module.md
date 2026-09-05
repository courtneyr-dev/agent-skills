# Site health module

Load at Phase 7, alongside `audit-playbook.md`. Runs the same battery as the
`site-health-audit` skill, re-tiered so it stays inside the read-only contract.

## Why this is a module and not a skill call

Do **not** invoke `site-health-audit`. Their Phase 1
clears the site's caches and their Phase 15 auto-fixes post content and plugin settings — both
mutate, and you cannot opt out of a skill's phases once you call it. The one is also hardcoded
to example.com. The battery below is their Phases 2–14, reorganized by what each check
actually requires. Nothing was dropped except the two write phases.

## Tier A — always run, any site, no credentials

Every check is an external read. These work on a site you do not own and satisfy Standing
Rule 5 without qualification.

| # | Check | Where | Record | Evidence label |
| :-- | :--- | :--- | :--- | :--- |
| A1 | Frontend loads cleanly | the site | Console errors and warnings; broken layout, missing images, blocking overlays | **Observed** |
| A2 | PageSpeed Insights | `pagespeed.web.dev` | Performance / Accessibility / Best Practices / SEO, **mobile and desktop**. Expand diagnostics for anything under 100 and name the failing audits. Wait 60–90s. | **Measured** with CrUX field data, else **Observed** (lab only) |
| A3 | Security headers | `securityheaders.com` | Letter grade; missing or flagged CSP, Permissions-Policy, X-Content-Type-Options, X-Frame-Options, HSTS, Referrer-Policy | **Observed** |
| A4 | SSL/TLS | `ssllabs.com/ssltest` | Letter grade; cipher suites, protocol support, certificate expiry. Takes 2–3 min. | **Observed** |
| A5 | Rich results | `search.google.com/test/rich-results` | Valid items, warnings, errors — homepage **and** the most recent post or a deep content page | **Standards-based** |
| A6 | WAVE | `wave.webaim.org` | Errors, alerts, contrast errors, structural issues | **Standards-based**, scan depth stated |
| A7 | Website Carbon | `websitecarbon.com` | Rating, CO₂ per visit, percentile | **Measured** |
| A8 | Agent readiness | `isitagentready.com/<bare-domain>` | Overall score, per-check pass/fail/warning, recommendations. Re-run if the result looks cached. Its page structure changes over time — capture the layout if it differs from the last run. | **Observed** |

Two standing cautions:

- **Each of these sends the audited URL to a third-party service.** Confirm at intake before
  running them against a pre-launch, staging, private, or client site.
- **A score is not a finding.** Standing Rule 10 still applies: connect every number to a user
  consequence, or leave it in the appendix. "Performance 82" is data. "The largest contentful
  paint is a 1.4 MB uncompressed hero, so the headline lands 4.2s in on a throttled 4G
  connection" is a finding.

## Tier B — owned site with authorized credentials only

Gated on the intake answer *"do you own this site, and were credentials supplied through an
authorized channel?"* If no, **skip and record as a limitation** — do not attempt, and do not
treat the gap as a pass.

| # | Check | Record |
| :-- | :--- | :--- |
| B1 | Accessibility plugin dashboard | Total open issues by severity; per issue: check type, severity, WCAG level, count. Skip if none installed. |
| B2 | SEO plugin dashboard | Search Console 28-day impressions, clicks, avg CTR, avg position with deltas; top 5 content and top 5 queries; SEO score breakdown (Good / OK / Needs Improvement / Not Analyzed); readability breakdown. Skip if none installed. |
| B3 | AI visibility / brand insights | Whatever the configured tool reports — visibility index, brand mentions, sentiment, competitor rank. Note "requires manual login" if auto-login is not possible. Skip if none configured. |
| B4 | CMS Site Health | WordPress: `<admin>/site-health.php?tab`. Wait for results to finish loading. Record critical count (target 0), recommended count, passed count. Per critical: title, category, description. Watch specifically for **late scheduled events, Consent API non-conformance, autoloaded options over 1 MB, PHP version, and database / loopback / REST-API warnings.** |

Tier B needs stack details — CMS, theme, hosting, performance plugin, SEO plugin,
accessibility plugin, security/CDN layer, object cache, AI visibility tool. Collect them in
intake batch 2 when Tier B is in scope. The shape in
`~/.claude/skills/site-health-audit/config.example.yml` is a good checklist.

## Tier C — cache clear, opt-in, owned sites only

**Excluded by default.** A stale CDN or page cache produces false performance findings, so on
a site the user owns this is a *measurement precondition* rather than a change to the site.
It is still a write, so it requires **both** `--own-site` **and** explicit confirmation in the
brief. Never on a site not confirmed owned. Never silently.

When authorized, clear in this order, 3s between actions: host cache → performance plugin
"clear used CSS" → performance plugin "clear minified JS/CSS" → object cache → CDN/WAF full
cache and path `/` → host cache again. Wait 30s before measuring. If a CDN API connection
fails, note it and continue.

If not authorized, run Tier A anyway and **label the performance results
"cache state unknown"** — an uncontrolled variable stated is better than a clean-looking
number that is wrong.

## Never — remediation

The source skill's Phase 15 tiered remediation (auto-fix / with-caution / never-touch /
report-only) is **out of scope for this skill entirely**, including its "auto-fix without
asking" category. This is an audit. Fixes are a separate, later pass the user authorizes
knowing what the audit found.

Its `never_touch_items` and `report_only_items` concepts do carry over, as *reporting*
categories: ask at intake for known intentional choices (inactive plugins kept on purpose,
host-cron scheduled-event warnings, WAF-controlled headers) and mark those findings
**"intentional — recorded, not actioned"** rather than reporting them as defects. An audit
that flags a deliberate decision as a bug loses the reader's trust for the findings that matter.

## Week-over-week comparison

Look for prior health reports and diff against the most recent:

1. the audit's notes location, `<notes>/`
2. `$VAULT_DIR/Areas/Site Health/` — dated `YYYY-MM-DD-site-health-report.md`
   files, which is where the standing weekly audit writes for example.com

Report **regressions explicitly**, and say so plainly when there are none. A first run has no
baseline — say that rather than implying stability.

## How this lands in the report

Health results are **evidence feeding the UX audit**, not a parallel report. Two placements:

- A finding a health check *explains* goes in the main findings, with the check as its
  evidence. A slow LCP that pushes the primary call to action past a user's patience is a UX
  finding with **Measured** support — not a performance appendix line.
- Everything else goes in a **Site health** appendix section, in the table shape below, so the
  numbers are on record without diluting the findings.

```
## Site health

| Check | Result | Δ vs <date> |
|---|---|---|
| PageSpeed mobile | P / A / BP / SEO | +/- |
| PageSpeed desktop | P / A / BP / SEO | +/- |
| Security headers | grade — missing: … | — |
| SSL/TLS | grade — issues: … | — |
| Rich results | home: … · latest: … | — |
| WAVE | errors / alerts / contrast | +/- |
| Carbon | rating · g CO₂/visit · percentile | +/- |
| Agent readiness | score — failing: … | +/- |
| CMS Site Health | critical / recommended / passed | +/- |

**Cache state:** cleared (authorized) | unknown — results may reflect cached assets
**Tier B:** run | skipped — no authorized credentials
**Regressions:** … | none | no baseline (first run)
```
