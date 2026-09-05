# Standards and evidence modules

Load at Phase 7 alongside `audit-playbook.md`. This file is the **instrument panel**: what to
test with, and which published requirement a claim maps to. It does not decide *what* to
audit — the playbook's coverage modules do that.

## Standards

Default: **WCAG 2.2 Level AA**, unless intake set something else.

Never assert a standards claim from memory. Source it, and cite the specific criterion.

| Source | Use for |
| :--- | :--- |
| `specification-website` MCP — `get_checklist`, `list_topics`, `search`, `get_topic` | Web-platform contract items. Statuses map onto evidence: `required` and `recommended` support a **Standards-based** label; `optional` and `avoid` are context calls, not findings on their own. `get_checklist` and `list_topics` return all statuses unless you pass `status`. |
| WCAG 2.2 success criteria | Accessibility. Cite as `SC 1.4.3` etc., with the level. |
| ARIA Authoring Practices | Whether a custom widget's pattern is implemented correctly. |
| Sector rules named at intake | EAA, Section 508, and equivalents. Only when intake raised them. |

**Never write that the site conforms.** You can fail a criterion from evidence; you cannot pass
a standard from a sample. Standing Rule 12.

## Read-only instruments

These run as part of the site health battery — see **`site-health-module.md`**, which owns the
sequence, the credential tiers, and the reporting shape. Listed here as the instrument
reference. All are third-party services: **each one sends the audited URL to an external
host**, so confirm the user is comfortable with that for a non-public or pre-launch site.

| Instrument | Yields | Evidence label |
| :--- | :--- | :--- |
| PageSpeed Insights — `pagespeed.web.dev` | Lab + field Core Web Vitals, mobile and desktop; per-audit diagnostics | **Measured** when CrUX field data is present; **Observed** for lab-only |
| WAVE — `wave.webaim.org` | Accessibility errors, alerts, contrast errors, structural issues | **Standards-based**, scan depth stated |
| Rich Results Test | Structured-data validity | **Standards-based** |
| securityheaders.com | CSP, HSTS, Referrer-Policy, frame and content-type options | **Observed** |
| SSL Labs | TLS grade, protocol and cipher support, cert expiry | **Observed** |
| Website Carbon | CO₂ per visit, percentile | **Measured** |
| isitagentready.com | LLM/agent discoverability, `llms.txt`, crawler directives | **Observed** |

One caution that never stops applying: an automated score is **not** a usability finding. It
is an input you must connect to a user consequence before it earns a place in the report.

When the site under audit is example.com, the standing weekly audit's dated reports in
`Areas/Site Health/` are the **baseline to diff against** — read the most recent one, then
run the battery fresh so the comparison is like for like.

## In-session instruments

| Instrument | Use for |
| :--- | :--- |
| `read_page` (accessibility tree) | Heading order, landmarks, link and button names, form labels, focus order. **Preferred over screenshots** for anything textual or structural — it reads what assistive technology reads. |
| `resize_window` | Responsive passes. Test the breakpoints the site actually defines, not arbitrary widths. The mobile preset also emulates touch, which changes hover behavior — reload after switching so load-time device gates re-run. |
| `read_console_messages` | JS errors that break interaction; failures users never see reported. |
| `read_network_requests` | Payload weight, blocking requests, third-party load, failed assets. |
| Keyboard via `computer` `key` | Tab order, focus visibility, keyboard traps, skip links. Read-only — tabbing mutates nothing. **Do not press Enter on a submit control.** |
| `WebFetch` | Fast text and structure reads without a browser session. |

## What stays out

- Anything that submits, publishes, purchases, creates an account, or changes a setting.
- Authenticated areas without confirmed authorization from intake.
- Crawling at a rate or depth that `robots.txt` disallows.
- Personal data encountered in testing — redact it from evidence before it reaches the report
  (Standing Rule 18).

---

The coverage bar these instruments are measured against lives in
`audit-playbook.md` under **Coverage modules** — in particular module 8, which
requires a score be connected to a user consequence before it becomes a finding.
