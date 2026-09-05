# Report format

Write to the configured output directory as `job-scan-YYYY-MM-DD.md`. One file per run, dated, so
the next run has something to diff against.

```markdown
# Job scan — YYYY-MM-DD

Sources scanned: N of M. Coverage gaps: <named sources that failed, or "none">.
New: N · Still open: N · Closed since last run: N

## Recruiter outreach
<Direct contact from a human. Highest priority regardless of score. Empty section if none.>

## New
### ★★★★★ Company — Role Title
- **Link:** <ATS URL, not an aggregator>
- **Comp:** <as printed, or "not listed">
- **Remote:** <as stated>
- **Posted:** <date or age>
- **Why it fits:** <one or two sentences, concrete, naming the gap if you applied a penalty>

## Still open
<One line each: Company — Role — stars — link. No detail; you have read these before.>

## Closed since last run
<One line each. Worth seeing: a role closing fast is a signal about that employer's urgency.>

## Coverage gaps
<Each failed source and why. Omit the section only when nothing failed.>
```

## Rules

- **Newest and highest-scoring first.** The top of the report is the only part guaranteed to be read.
- **Detail only in New.** Still-open roles get one line — repeating full detail every day is what
  makes a daily report unreadable by week two.
- **Keep Closed.** It is the cheapest signal in the report about how fast a market is moving.
- **Never write a report with no coverage-gaps section when a source failed.** That omission is the
  one error that makes every future report untrustworthy.
