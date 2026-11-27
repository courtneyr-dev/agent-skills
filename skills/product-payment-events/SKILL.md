---
name: product-payment-events
description: Test-mode payment, entitlement and subscription webhook processing that proves duplicate or retried payment events cannot create a second charge capture, fulfillment, inventory decrement or refund. Use when building or reviewing a commerce, licensing, subscription or SaaS billing integration, a webhook handler, an entitlement or cancellation-and-export flow, or an inventory race. Not for live payments, real provider accounts, tax or chargeback rules.
disable-model-invocation: true
---

# Product payment events

`scripts/payment_events.py` is a disposable test integration. A fake provider's signed webhook events go in; a SQLite store the caller names comes out with at most one capture, fulfillment, inventory decrement and refund per order. The order id is the idempotency key the capture uses, so a provider replay (same event id) and a provider retry (new event id, same order) both land as no-ops. Live-mode events are always refused: this integration has no live mode.

## When to use

- A product or ecommerce engagement needs proof that webhook handling is idempotent before release.
- You are designing entitlements, refunds, cancellation and data export for a paid extension or SaaS plan.
- Two orders can race for the last unit of stock.

## Not for

- Real payment providers or accounts. Point the same fixture events at the provider's own test mode only with a human's approval and the provider's test credentials, outside this script.
- WooCommerce PHP integration tests: use the installed `woocommerce-plugin-dev` skill (Automattic/claude-woocommerce-toolkit), whose `woocommerce-plugin-dev/references/testing.md` has a PHPUnit idempotency pattern.
- Pricing decisions: installed `pricing-strategist` or `devtools-pricing-strategy`.

## Inputs

- Config `payment-config.v1`: `tenant_id`, `signing_key` (a published test value), `inventory` (sku to on-hand count). Example: `fixtures/config.json`.
- Events, one JSON object per line, schema `payment-event.v1`: `id`, `type`, `livemode`, `tenant_id`, `created` (ISO 8601 with a timezone; required), `data`, `signature`. Entitlement changes are ordered by `created`, not arrival: a cancel or refund only loses to a newer event, so a cancel that arrives before its checkout leaves the entitlement canceled. Types and required `data` fields:
  - `checkout.completed`: order_id, customer_id, sku, quantity, amount, currency
  - `charge.refunded`: order_id, amount
  - `subscription.canceled`: customer_id, sku
- Lines starting with `#` are comments. Unsigned authoring copies live in `fixtures/unsigned/`; `sign` produces the signed files.

## Method

1. Author events in `fixtures/unsigned/`, then `python3 scripts/payment_events.py sign --config C --events U > SIGNED`.
2. Process into a fresh temporary store: `python3 scripts/payment_events.py process --config C --events SIGNED --db TMP/store.db`.
3. Replay the same file again, and replay it from several processes at once. The store counts must not move.
4. Run `reconcile --db TMP/store.db`. Every capture needs a fulfillment or a hold; no refund may exceed or lack its capture.
5. Hand every `needs-human` hold to the commerce owner. The script never resolves one.

## Stopping conditions

- All events applied or refused, and reconcile ran.
- Any `refused-*` or `needs-human` outcome: stop and report; do not edit the store by hand.

## Output contract

`process` prints `mode` (`test`), per-event `events` outcomes, `outcomes` tally, `store` counts, `inventory`, `entitlements`, `live_calls` (always 0), `not_checked`, `status`. Outcomes: `fulfilled`, `refunded`, `canceled-export-offered`, `duplicate-event`, `duplicate-order`, `duplicate-refund`, `needs-human`, `refused-bad-signature`, `refused-live-mode`, `refused-tenant-mismatch`.

`reconcile` prints `mismatches` (`capture-without-fulfillment`, `fulfillment-without-capture`, `refund-without-capture`, `refund-exceeds-capture`), `holds_for_human`, totals and `status` (`reconciled` or `needs-attention`).

Exit 0 ok; 1 refused events, holds or mismatches; 2 invalid input (bad JSON, wrong schema tag, missing fields, missing signature).

## Failure states

- Bad signature, live mode or another tenant's event: refused, store unchanged.
- Stock exhausted: the capture is kept, fulfillment is held as `needs-human`, inventory never goes negative (a SQLite CHECK constraint).
- Refund for an order this store never captured: held as `needs-human`. One order can carry several holds (one per event), so a refund hold followed by a stockout on the same order holds twice instead of crashing.
- A store created by version 0.1.0 (holds keyed by order only, no `changed_at`) is not migrated; stores are disposable, so start a new one.
- Store file locked by another process: SQLite waits up to 30 seconds, then the run fails with the error; rerunning converges.

## Adapters and missing capability

Needs `python3` 3.9+ with the standard `sqlite3` module. The fake provider is the signed fixture file; there is no network code. Without a provider sandbox, real-provider behavior (retry schedules, signature headers, partial refunds) stays unverified and the output lists it under `not_checked`.

## References and rights

| Source | Version | Rights |
|---|---|---|
| RFC 2104, HMAC | February 1997 | IETF Trust; cite only |
| SQLite, "Transactions" (`BEGIN IMMEDIATE`) and `INSERT OR IGNORE` | SQLite 3 bundled with Python | SQLite is public domain |
| Stripe docs, "Idempotent requests" and "Receive Stripe events in your webhook endpoint" (pattern reference only) | verify at use; not pinned | Stripe site terms; cite the URL, do not copy |
| Automattic/claude-woocommerce-toolkit `woocommerce-plugin-dev`, woocommerce-plugin-dev/references/testing.md "Idempotency Tests" | installed copy, read 2026-11-25 | upstream license in that skill; not copied here |

## Tests

```bash
cd scripts/tests && python3 -m unittest -v
```
