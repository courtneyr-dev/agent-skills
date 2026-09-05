---
name: site-health-audit
description: "Use when the user says 'site health', 'weekly health check', 'run the site health audit', or wants PageSpeed, accessibility, SEO, security headers, SSL, email authentication, social preview, carbon, and WordPress Site Health checked for a site described by a config; example.com is the default. Full UX audits go to website-audit."
---

# Site health audit

## Config

Read `config.yml` beside this file unless the caller names one. Every site-, host-, and plugin-specific step comes from it: URLs, cache steps and signals, dashboards, header owners, email baseline, `leave_as_is`, `report_only`. An empty or `none` key marks its check `n/a` and the run continues. When the site moves, swap the `host:`, `security_layer:`, and `cache_steps:` blocks.

## Run frame

Unattended: finish the run; the only stops are sending real email, changing DNS, or any write to the live site. Cache flushes in `cache_steps` are part of the run. Admin checks use the existing session; logging in is off-limits, so an expired session records "not readable this run" and the run continues. Narrate once before the first tool call and on a regression.

## State on disk

Before check 1, create the dated report in `report.dir` with one empty heading per check, and `.state/<date>.json` beside it: each check's status (`pending`, `done`, `n/a`, `not-read`), evidence pointers, SSL Labs start time, previous report path. Append each check's section and flip its status as it completes. Context gets compacted mid-run: on resume, read the JSON and continue at the first check not `done`. A compaction summary keeps the date, config path, previous report path, cache results, every recorded number with its source, and the open checks.

## Evidence

Every number cites the tool output it came from: URL or command plus the field read. Scores come from page text or the DOM, not pixels. Before judging any screenshot (layout, og:image shape, a gauge), zoom or crop the region and judge the enlarged image. A number without a source stays blank under "Not read this run".

## Checks

Method and record lists: `references/checks.md`; tool traps: `references/quirks.md`. A check is done when its values are in the report with sources, or it is marked `n/a` or `not-read` with the reason.

0. Previous report — newest dated file in `report.dir`; path into the state JSON.
1. Caches — `cache_steps` in order; signal observed or failure recorded; wait 30 s.
2. Frontend — console errors, regression-script count, zoomed layout check.
3. SSL Labs — start the API scan now, poll between checks, record only at `status: READY`.
4. PageSpeed — mobile and desktop, four scores each, failing audits named.
5–7. Accessibility, SEO, and AI-visibility dashboards from config.
8. Security headers — grade, missing or flagged headers, owner per config.
9. Email authentication — `dig` plus mxtoolbox: SPF qualifier and lookup count, chain covers the MX, DKIM, DMARC, blocklists. 9b live tests only with the user's go-ahead this session; otherwise "skipped — sends real mail".
10. Rich results and social previews — homepage and latest post; complete og set, image resolves via a real unfurler.
11–13. WAVE, carbon, Is It Agent Ready — record the categories the page shows today.
14. WordPress Site Health — critical, recommended, passed counts; `leave_as_is` items recorded, not acted on.
15. Report — Regressions and Action Items from the diff against the previous report.

## Report

Template in `references/checks.md`. One line per metric with its Δ and source; a check with nothing new is one line; Regressions and Action Items are the only prose; no filler sections, restated summaries, or boilerplate. Each action item carries a tier from `references/remediation.md` (fix on approval, fix with caution, leave as is, report only) and its owning admin URL or file. Live-site fixes run later, when the user says so, per remediation.md.

Done: no `pending` check in the state JSON, Regressions and Action Items present, and a final message giving regression count, top action items, checks not read, report path.
