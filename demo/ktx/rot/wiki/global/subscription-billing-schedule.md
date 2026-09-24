---
summary: Subscription billing runs at 05:00 Amsterdam time; retry schedule for failed payments
usage_mode: auto
sort_order: 0
tags:
  - subscriptions
  - finance
sl_refs:
  - fct_subscription_events
  - fct_subscriptions
---

## Subscription Billing Schedule

### Billing time
Subscription billing runs at **05:00 Amsterdam time** on the scheduled billing date.

### Retry schedule for failed payments
When a payment fails, the system retries on:
- Day 1
- Day 3
- Day 7
- Day 14
- Day 21
- Day 28

### Max retries
Billing gives up on **day 30** and cancels the subscription with `cancellation_reason = 'max_retries_reached'`.

### Payment episodes
`int_payment_episodes` tracks each billing cycle with a failed payment (dunning episode), including:
- `first_failed_at`: First failed payment (05:00 Amsterdam time on the cycle date)
- `recovered_at`: When a retry succeeded, if one did
- `is_recovered_within_30_days`: Whether recovery happened within the 30-day window

### Related
- `int_payment_episodes`
- `fct_subscription_events` (payment_failed and payment_recovered events)
- `fct_subscriptions.cancellation_reason` (max_retries_reached)
