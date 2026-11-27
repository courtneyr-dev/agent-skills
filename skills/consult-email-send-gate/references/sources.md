# Sources for consult-email-send-gate

As-of date: 2026-11-25. Cite-only entries: no text is copied into this skill. No URL was fetched while
building the skill (no network), so verify each at use.

| Rule in the script | Source | Version | Retrieved | Rights |
|---|---|---|---|---|
| `List-Unsubscribe` https URI plus `List-Unsubscribe-Post: List-Unsubscribe=One-Click` | RFC 8058, Signaling One-Click Functionality for List Email Headers, https://www.rfc-editor.org/rfc/rfc8058 | IETF, January 2017 | not fetched | IETF Trust legal provisions; cite only |
| SPF record present (`v=spf1`) | RFC 7208, https://www.rfc-editor.org/rfc/rfc7208 | IETF, April 2014 | not fetched | IETF Trust; cite only |
| At least one DKIM selector present | RFC 6376, https://www.rfc-editor.org/rfc/rfc6376 | IETF, September 2011 | not fetched | IETF Trust; cite only |
| DMARC record present, `p=none` warning | RFC 7489, https://www.rfc-editor.org/rfc/rfc7489 | IETF, March 2015. A DMARCbis revision is in progress; verify the current status at use. | not fetched | IETF Trust; cite only |
| Why marketing needs one-click unsubscribe and authentication | Gmail sender guidelines, https://support.google.com/a/answer/81126, and Yahoo sender best practices, https://senders.yahooinc.com/best-practices/ | Bulk-sender requirements announced for February 2024; provider policy, verify at use | not fetched | Provider policy; cite URL only |
| `img` needs an `alt` attribute | WCAG 2.2 success criterion 1.1.1 Non-text Content, https://www.w3.org/TR/WCAG22/#non-text-content | W3C Recommendation, 2023 | not fetched | W3C document license; cite only |

The consent, suppression, tenant and authorization rules are local policy of the fleet's email and
lifecycle practice, not external standards. Skill code and fixtures are original and synthetic.
