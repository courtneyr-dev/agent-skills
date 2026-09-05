---
name: job-search
description: Run a repeatable job-search scan across job boards, company ATS pages, email alerts, LinkedIn, and community chat; diff against the previous run to separate NEW from STILL OPEN and CLOSED, score each role against your own criteria, and write a dated report. Use for "run the job scan", "job search scan", "what's new in my search", or a scheduled daily/weekly run. Read-only — it never applies, messages, or replies on your behalf.
---

# Job search scan

A search that runs on a schedule beats one you remember to do. This skill turns a scattered search
into one repeatable pass: same sources, same rubric, same report shape, diffed against last time so
you only read what changed.

**Everything personal lives in `config.yml`, not in this skill.** Copy `config.example.yml` to
`config.yml`, fill it in, and never commit it. This skill ships with no profile, no employer names,
and no target list.

## Setup (once)

1. Copy `config.example.yml` to `config.yml` in this skill's directory.
2. Fill in: your tracks, must-haves, sources, excluded companies, and where reports get written.
3. Connect whichever integrations you want — see `references/integrations.md`. None are required;
   the scan degrades to whatever is available and says so in the report.

## Workflow

1. **Load config.** Read `config.yml`. If it is missing, stop and say so — do not guess a profile
   or invent target companies.

2. **Scan sources** (`references/sources.md`). Work through each configured source. Prefer a
   company's own ATS posting over an aggregator — aggregator URLs rot and often lag the real board.

3. **Sweep email**, if configured. Job alerts and direct recruiter outreach. Recruiter mail
   outranks any board listing: a human already thinks you fit. Read-only — never reply or label.

4. **Check community channels**, if configured. Roles get posted in Slack and Discord days before
   they hit a board, and some never hit one at all.

5. **Diff against the previous report.** Classify every role NEW / STILL OPEN / CLOSED. The diff is
   the point: a scan you have to re-read end to end will not survive a week.

6. **Score** against `references/scoring.md` and your config's must-haves. Drop anything on the
   applied list or the excluded-companies list.

7. **Write the report** (`references/report-format.md`) to the configured output path, dated.

## Rules

- **Read-only.** Never submit an application, send a message, accept a connection request, or reply
  to a recruiter. Surface and rank; the human decides and acts.
- **Never invent a listing.** If a source fails, record it as a coverage gap in the report. A scan
  that quietly skips a broken source looks identical to one that found nothing — and that mistake
  compounds every day it goes unnoticed.
- **Respect the excluded list** without exception, however good the role looks.
- **Deduplicate by company plus normalized title**, not by URL. Ignore Senior/Staff/Lead/Principal
  prefixes — the same role is often posted several times with different seniority wording.
- **Record why**, not just what. A one-line "why it fits" per role is what makes the report useful
  a week later when you have forgotten the listing.

## Reading map

- Configuring sources and what each type is good for → `references/sources.md`
- The scoring rubric and how to adapt it → `references/scoring.md`
- Wiring up Firecrawl, email, LinkedIn, chat, ATS → `references/integrations.md`
- Report structure → `references/report-format.md`
