---
name: hosting-metering-reconcile
description: Meter hosting usage and check the money against it. Dedupes meter events so a retried delivery counts once (same id, or a new id with the same tenant, meter, quantity and timestamp instant, which also fails for a human to settle), enforces and checks published customer-visible quotas, reconciles invoices against metered usage (overbilled, underbilled, unbilled, billed-but-unmetered), splits shared costs across tenants so allocations sum to the cent, reconciles affiliate commissions against an upstream provider's payouts and flags payouts made without disclosure, and forecasts infrastructure capacity headroom with stated assumptions. Use whenever someone asks whether an invoice is right, a tenant is near or over quota, how to split a shared cost, whether affiliate payouts are correct, or when a resource will hit its utilization threshold.
license: MIT
disable-model-invocation: true
---

# Hosting metering and reconciliation

This skill compares what was metered, what was billed and what was paid, and says how sure it is. Every number comes from a script that uses `decimal.Decimal` with ROUND_HALF_UP to cents, and every result lists the assumptions behind it. Duplicate meter events count once, shared-cost allocations sum to the pool exactly, and a capacity forecast refuses to run on too few days. It reads files and calls nothing.

## When to use

- An invoice looks high or low and someone wants to know by how much and why.
- A tenant is approaching or over a quota, or a quota's published value is missing or wrong.
- A shared pool (egress, observability) needs splitting across tenants by a usage driver.
- Affiliate commissions need checking against the upstream provider's payout report.
- Someone asks when a shared resource reaches 80 percent utilization.

## When not to use

- Sizing a support or ops team (Erlang C, headcount): the installed `capacity-planner` skill (MIT, Alireza Rezvani) answers that queue question. This skill answers infrastructure headroom only.
- Partner channel cost, ROI or channel mix: the installed `channel-economics` skill (MIT, Alireza Rezvani).
- Setting prices, discounts or tiers, or issuing credits and refunds: a human with billing authority.
- Downtime credits and SLO checks: `hosting-incident-response`.
- Tax, revenue recognition or legal disclosure wording: finance or legal review.

## Inputs and prerequisites

- Usage events JSONL: `event_id`, `tenant_id`, `meter`, `quantity`, optional `ts` (ISO 8601 with an offset or Z). A first line holding only `label` is skipped. Ids are compared with whitespace stripped; a new id with the same tenant, meter, quantity and `ts` instant as an earlier event (10:00:00Z and 11:00:00+01:00 are one instant) counts once and fails as `same-payload-new-id`.
- Quotas JSON: `quotas[]` with `tenant_id`, `meter`, `limit`, `unit`, `customer_visible`, `published_limit`.
- Fixture Co's owner files at fixed paths in `company-fleets/fleets/hosting/fixtures/metering/`: `prices.json` (`currency`, `prices[]` with `meter` and `unit_price`, and `max_tolerance`), `terms.json` (`rate`, `clawback_days`) and `disclosure-log.json` (`shown[]` with `referral_id`, `page` and `rendered_at`, written by Fixture Co's site, not by the affiliate). `--prices`, `--terms` and `--disclosures` are refused by name (`prices-not-owner-file`, `terms-not-owner-file`, `disclosures-not-owner-file`) unless they name those same files. Invoices JSON: `invoices[]` with `invoice_id`, `tenant_id`, `currency`, optional `total`, `lines[]` (`meter`, `amount` in whole cents, optional `quantity`).
- Costs JSON: `pools[]` with `pool_id`, `amount` in whole cents. Referrals and payouts JSON for commissions. A referral id or a tenant-and-meter quota listed twice refuses the file. Utilization series JSON: `points[]` with `date`, `utilization` from 0 to 1.
- One billing period of events per run. Each tenant's figures stay in the operator's view; give a tenant-facing agent only that tenant's rows.

## Method

1. `usage --events E --quotas Q`: read `duplicates`, `totals`, each quota `status` (ok, warn at 80 percent or more, over above the limit) and `violations`.
2. `reconcile --events E --invoices I [--tolerance 0.00]`: expected = metered quantity x unit price per tenant and meter, from the owner's price list. A tolerance above its `max_tolerance` is refused (`tolerance-above-owner-max`). Read `overbilled`, `underbilled`, `unbilled_usage`, `billed_unmetered`, `amounts`, and the three invoice checks: `currency_mismatch` (invoice currency differs from the price file's), `total_mismatch` (a stated total differs from the sum of its lines) and `quantity_mismatch` (billed quantity differs from metered).
3. `attribute --costs C --events E --driver METER`: each pool splits by deduplicated driver usage. The cent remainder goes to the largest fractional cent, then tenant id.
4. `commission --referrals R --payouts Y`: a referral earns only if qualified, present in Fixture Co's disclosure log with an entry rendered on the `checkout` page on or before the day it converted, and not refunded within `clawback_days`. Any other log entry for it is flagged `disclosure-entry-invalid`. The row's own `disclosure_shown` is the affiliate's claim: a true claim with no log entry is flagged `disclosure-claim-unverified`. Read `paid_without_disclosure` first; those payouts need a human decision.
5. `capacity --series U --threshold 0.8 [--min-points 14]`: read `days_until_threshold`, `band_days`, `fit.r_squared` and `extrapolation_warning`.
6. State the assumptions to the reader with the number. Report an amount as expected or billed, never as owed, until a person with billing authority agrees.

## Stopping conditions

- Stop at the report. Don't edit invoices, send credits, change quotas or pay or claw back commissions.
- Stop when a command refuses (`no-driver-usage`, `insufficient-points`) and say what data would unblock it.
- A conflicting duplicate event (same id, different values) stops reconciliation work until the meter source is checked.

## Output contract

Stdout is JSON with sorted keys and an `assumptions` list. Money is a string with 2 decimals. `usage` returns `totals`, `duplicates`, `quotas`, `violations`. `reconcile` returns the six row groups plus `amounts`. `attribute` returns `pools[].allocations[]` and `tenant_totals`. `commission` returns `matched` and the flag groups. `capacity` returns `status` (projected, reached, not-reached; reached when the last observed point is at or over the threshold), a whole-day `days_until_threshold` or `not-reached`, a slope band and a fit summary.

## Failure states

- Exit 0: no mismatch or violation found.
- Exit 1: a quota violation or conflicting duplicate (`usage`); an overbilled, underbilled, unbilled or unmetered line above the tolerance (`reconcile`); a commission mismatch (`commission`); or a refusal: `no-driver-usage` (`attribute`), `prices-not-owner-file` and `tolerance-above-owner-max` (`reconcile`), `terms-not-owner-file` and `disclosures-not-owner-file` (`commission`), `insufficient-points` (`capacity`).
- Exit 2: invalid input, printed as `{"error": ...}`: bad JSON, a file that isn't UTF-8, a `ts` without an offset, missing file, negative quantity or amount, meter with usage but no price, pool with fractions of a cent, rate outside 0 to 1, non-increasing dates, utilization above 1, `--min-points` below 3.
- Exit 3: not produced; the script needs no external capability.
- Limit: a process running as the same OS user can rewrite `prices.json`, `terms.json` or `disclosure-log.json`. Only separate OS accounts or signed records stop that.

## Adapters and missing capability

No billing-system, meter-store or affiliate-provider adapter exists; export the data to the JSON shapes above. Without a payout report there's no commission check, only the expected-commission column. Without 14 daily points there's no forecast: collect more days or lower `--min-points` knowingly, never below 3.

## References

See `references/sources.md`.

## Tests

`cd skills/hosting-metering-reconcile/scripts && python3 -W ignore -m unittest discover -s tests`

## Evaluation cases

Fleet cases (merged into `fleets/hosting/evals.json`): `hosting.eval.metering-invoices-reconcile`, `hosting.eval.metering-overbilling-detected`, `hosting.eval.metering-duplicate-event-not-double-billed`, `hosting.eval.metering-undisclosed-referral-flagged`, `hosting.eval.metering-capacity-too-few-points`, `hosting.eval.metering-cost-attribution-sums-exactly`, `hosting.eval.metering-quota-unpublished-flagged`, `hosting.eval.metering-capacity-projects-threshold`. Model-run prompts live in `evals/evals.json`.

Cases that replay the 2026-11-26 independent review's probes: `hosting.eval.metering-forged-disclosure-flag-refused`, `hosting.eval.metering-invoice-currency-total-quantity-checked`, `hosting.eval.metering-capacity-already-over-is-reached`.

Cases that replay the hosting re-review's probes: `hosting.eval.metering-caller-disclosures-refused`, `-disclosure-after-conversion-refused`, `-tolerance-above-owner-max-refused`, `-retry-same-instant-counted-once`.
