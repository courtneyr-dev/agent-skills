---
name: consult-email-send-gate
description: Runs a deterministic pre-send gate on one email campaign for the company-fleets consultancy fleet. It keeps suppressed contacts suppressed, checks marketing permission, tenant, SPF/DKIM/DMARC fixtures, RFC 8058 one-click unsubscribe and accessible rendering, then stages the result and never sends. Use before a human approves dispatch of a marketing or transactional email. Not for sequence strategy, copy, recurring loops or sending.
disable-model-invocation: true
---

# Consult email send gate

`scripts/send_gate.py` reads one campaign, a consent ledger, a sender-authentication record and an
optional send authorization. It decides who is eligible, which defects block the send, and whether the
authorization is valid for this exact content. It never sends. A named human dispatches through the
tenant's existing authorized email system, and the consent steward is the only role that removes a suppression.

## When to use

- A campaign is ready for review and someone needs a repeatable go/no-go before dispatch.
- You need to prove a suppressed or cross-tenant contact stays out of the audience.
- A human approval must be bound to the exact content that was reviewed (SHA-256).

## Not for

- Sequence strategy and copy: use the installed `emails` skill (coreyhaines31/marketingskills).
- Recurring loops and scheduled programs: use the installed `marketing-loops` skill.
- Any actual sending, scheduling, list edits or suppression removal. The script has no network code and writes nothing.

## Inputs

Worked example: `fixtures/campaign-clean-marketing.json`, `fixtures/ledger-fixture-co.json`,
`fixtures/sender-auth-good.json`, `fixtures/authorization-clean.json`. Every file carries a `label`.

- Campaign `email-campaign.v1`: `campaign_id`, `tenant_id`, `kind` (`marketing` or `transactional`),
  `from_domain`, `subject`, `content` {`html`, `text`, `lang`}, `headers`, `audience` (contact ids).
- Ledger `consent-ledger.v1`: `tenant_id`, `contacts` [{`id`, `email`, `tenant_id`, `permission` {`marketing`, `source`, `at`}}],
  `suppressions` [{`email`, `reason`, `at`}].
- Sender auth `sender-auth.v1`: `domain`, `spf`, `dkim` [{`selector`, `present`}], `dmarc`. A fixture; no live DNS.
- Authorization `send-authorization.v2` (optional): `campaign_id`, `approval_sha256`, `approved_by` (`human:...`),
  `approved_at`, `expires_at`. `approval_sha256` is the value the gate prints for the campaign the human reviewed. It covers
  `campaign_id`, `tenant_id`, `kind`, `from_domain`, `subject`, `headers`, `content` and the sorted mailbox keys of the
  eligible recipients, so relabeling the kind, adding a recipient, or changing the sender, subject or headers after
  approval invalidates it. A `send-authorization.v1` file (content hash only) is refused with exit 2; re-approve.
- `--now` is required (ISO 8601, for example `2026-11-25T12:00:00Z`) so runs are repeatable.

## Method

1. Run `python3 scripts/send_gate.py --campaign C --ledger L --sender-auth A --now T [--authorization Z]`.
2. Suppression wins, matched on the mailbox key: the address trimmed and lowercased, trailing dots removed from the
   domain, and any `+tag` removed from the local part. A suppression on any variant (`dee+news@example.com`,
   `dee@example.com.`) suppresses every variant of that mailbox, even when permission says opted-in after the
   suppression time. Provider-specific rules (Gmail ignoring dots in the local part, other tag separators) are not
   applied. Marketing also needs `opted-in` with `source` and `at`.
   Transactional ignores marketing permission and `unsubscribed`, but honors `hard-bounce`, `complaint`, `legal-hold`.
3. A contact from another tenant is excluded and reported as error `tenant-mismatch`. Two addresses with the same mailbox key are sent once.
4. Sender auth gaps are error `sender-auth-missing`; `p=none` is warning `dmarc-policy-none`.
5. Marketing needs an https `List-Unsubscribe` URI and `List-Unsubscribe-Post` exactly `List-Unsubscribe=One-Click`.
6. Accessibility (`a11y-text-part-missing`, `a11y-lang-missing`, `a11y-img-alt-missing`, `a11y-image-only`).
7. Authorization is valid only for a `human:` approver, the same campaign id and `approval_sha256`, and `--now` before `expires_at`.
   `authorized_for_dispatch` is true only when it is valid and no error defect remains.
8. A human reads `human_review_required` and `not_checked`, then dispatches or not.

## Stopping conditions

Stop after one run. Exit 1 means fix the defects and rerun; any change to a bound field or the recipient set needs a new authorization.
Exit 2 means fix the input. Never dispatch, retry a send, or edit the ledger from this skill.

## Output contract

One JSON object: `campaign_id`, `mode` (`staged`), `eligible`, `excluded` [{`id`, `reason`}], `defects`
[{`code`, `severity`, `message`, `location`}], `approval_sha256`, `authorized_for_dispatch`, `sends_performed` (always 0),
`dispatch_route`, `human_review_required`, `not_checked`.
Exit 0 = no error-severity defect (correct exclusions are not defects). Exit 1 = at least one error.
Exit 2 = invalid input or usage, with `{"error": "..."}`.

## Failure states

- Bad JSON, wrong `schema` tag, missing field, bad timestamp, missing `--now`: exit 2 with the reason.
- Audience id missing from the ledger: excluded, error `contact-not-in-ledger`.
- Ledger tenant differs from campaign tenant: all contacts excluded, error `tenant-mismatch`.
- Sender-auth domain differs from `from_domain`: error `sender-auth-domain-mismatch`.
- Authorization present but invalid: one `authorization-invalid` error per reason; `authorized_for_dispatch` false.

## Adapters and missing capability

No adapter is needed: Python 3.9+ standard library only. The skill cannot read live DNS, the tenant's email
system or the rendered inbox; those appear in `not_checked`. It cannot send, and no adapter changes that.

## References and rights

| Source | Version | Rights |
|---|---|---|
| RFC 8058 one-click unsubscribe (IETF) | 2017 | IETF Trust; cite only |
| RFC 7208 SPF, RFC 6376 DKIM (IETF) | 2014, 2011 | IETF Trust; cite only |
| RFC 7489 DMARC (IETF) | 2015; DMARCbis in progress, verify at use | IETF Trust; cite only |
| Gmail and Yahoo bulk-sender requirements | Announced for February 2024; verify at use | Provider policy; cite URL only |
| WCAG 2.2 SC 1.1.1 alt text (W3C) | 2023 | W3C document license; cite only |

URLs and as-of dates: `references/sources.md`.

## Tests

```bash
cd scripts/tests && python3 -m unittest -v
```
