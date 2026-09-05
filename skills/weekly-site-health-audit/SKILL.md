---
name: weekly-site-health-audit
description: Use for "weekly site health", "run the weekly audit", or a scheduled weekly run — runs the site-health-audit skill against your configured site and diffs the results against last week's report. Thin scheduling wrapper; site-health-audit does the actual checks.
---

# Weekly site health audit

Runs [`site-health-audit`](../site-health-audit/) on a weekly cadence with one addition: a
week-over-week diff.

Use the config at `../site-health-audit/config.yml` (copy it from `config.example.yml` there if you
have not yet). The audit's run frame, state file, evidence rule, and report template all apply
unchanged — this skill adds nothing to them.

## The diff

Compare against the newest dated report in the config's `report.dir`. For every tracked metric,
report the previous value, the current value, and the direction of change.

When no previous report exists, say so plainly in the report header and record every value as the
new baseline. Do not silently present a first run as though it were a comparison — a baseline
labelled as a trend is worse than no trend at all.

## Why weekly

Site health moves on a scale of days, not hours. A daily run produces noise you learn to ignore,
and an ignored report is the same as no report. Weekly is frequent enough to catch a regression
while you can still connect it to what changed, and rare enough that you actually read it.

Schedule it with whatever your platform provides — cron, launchd, systemd timers, or your agent's
own scheduled tasks. Pick a time you will read the output.
