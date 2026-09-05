# Integrations

None of these are required. Connect what you have; the scan uses what is available and records the
rest as a coverage gap in the report. Every integration below is **read-only** in this skill.

## Firecrawl — web and ATS scraping

Best for career pages that render with JavaScript, which plain fetching returns empty.

- **Connect:** the Firecrawl MCP server, or the `firecrawl` API with a key in your environment.
- **Use `scrape`** for a single known career page; **`map`** to enumerate posting URLs under a
  careers domain without pulling every page; **`search`** for open-web discovery.
- **Cost discipline:** `map` first to find posting URLs, then `scrape` only the ones whose titles
  pass a keyword filter. Scraping every page of every board is how a daily scan gets expensive.
- **Failures:** record the source and the error in the report's coverage-gap list. Do not silently
  drop a source — an empty result and a broken scraper look identical in a finished report.

## Email — job alerts and recruiter outreach

Any mail integration (Gmail MCP, IMAP, a local client) works. Search the last 24 hours for:

- Mail from job boards you have alerts with — extract every role in each digest, not just the first.
- Subject or body matching your track keywords, plus recruiter language ("reaching out", "role",
  "opportunity"), excluding bulk promotional categories.
- Application status updates on roles you have already applied to.

Direct recruiter outreach ranks above any board listing and belongs at the top of the report.
**Never reply, draft, label, archive, or delete.** Reading the inbox is the whole job here.

## LinkedIn — browser, not API

LinkedIn's API will not give you job search. Drive a logged-in browser session instead (a browser
MCP, or a browser-automation tool your agent already has).

- Search URL pattern: `https://www.linkedin.com/jobs/search/?keywords=<terms>&f_TPR=r86400&f_WT=2`
  (`f_TPR=r86400` = last 24 hours, `f_WT=2` = remote).
- Read the result list; open a detail page only for roles that plausibly pass your must-haves.
- **Resolve to the company's own ATS URL** where you can. LinkedIn job URLs expire, and a report
  full of dead links is worthless a month later.
- **Never** click Apply or Easy Apply, send a message, or send a connection request.
- If the browser is not connected or the session is logged out, that is a coverage gap — say so and
  continue with the other sources rather than failing the whole run.

## Community chat — Slack and Discord

Roles appear in community channels before they hit boards, and some never leave. Use a chat
integration that can read your joined workspaces, scan the configured channels for the last 24
hours, and treat anything with an apply link as a candidate. Be careful with rate limits and page
sizes — a client that caps results per page will silently under-scan a busy channel.

## ATS boards — the highest-signal source

Greenhouse, Lever, Ashby, and Workable all expose a company's real, current openings, usually at a
predictable URL (`boards.greenhouse.io/<company>`, `jobs.lever.co/<company>`,
`jobs.ashbyhq.com/<company>`). When you find a role anywhere else, resolve it back to the ATS
posting: that is the listing that is actually current, and its URL survives.

Keep a list of target companies in `config.yml` under `sources.ats` and scan them directly. This is
the single highest-yield source in the whole scan and the one aggregators lag.

## Scheduling

Any scheduler works — cron, launchd, systemd timers, or your agent platform's own scheduled tasks.
Run daily if you are searching actively, weekly if you are watching passively. Run it at a time you
will actually read the output; a report nobody opens is not a search.
