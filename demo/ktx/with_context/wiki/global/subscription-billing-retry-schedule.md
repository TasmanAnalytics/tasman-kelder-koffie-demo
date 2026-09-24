---
summary: Failed subscription payments are retried on days 1, 3, 7, 14, 21, 28; billing gives up on day 30
usage_mode: auto
sort_order: 0
tags:
  - subscriptions
  - billing
refs:
  - churn-definition-versions
sl_refs:
  - fct_subscription_events
---

## Subscription Billing Retry Schedule

### Billing Time
Subscription billing runs at **05:00 Amsterdam time** on the scheduled billing date.

### Retry Schedule
When a payment fails, the system retries on:
- Day 1 (first attempt)
- Day 3
- Day 7
- Day 14
- Day 21
- Day 28

### Cancellation
If all retries fail, billing **gives up on day 30** and cancels the subscription with `cancellation_reason = 'max_retries_reached'`.

### Payment Recovery
A payment is considered **recovered** if any retry succeeds within 30 days of the first failure.

In churn metrics v2 (from May 2026), failed payments that do not recover within 30 days are counted as churn.

### Data Model
- `int_payment_episodes`: One row per billing cycle with a failed payment, with first failure and recovery timestamps
- `fct_subscription_events`: `payment_failed` and `payment_recovered` events
- `int_charges_unified`: All billing attempts from Shopify and Recharge

### Source
See `int_payment_episodes` and `int_charges_unified` models for the retry logic.
