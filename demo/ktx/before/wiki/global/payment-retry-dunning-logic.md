---
summary: Failed payments retry on days 1, 3, 7, 14, 21, 28; billing gives up on day 30 with max_retries_reached cancellation
usage_mode: auto
sort_order: 0
tags:
  - subscriptions
  - billing
sl_refs:
  - fct_subscription_events
---

## Payment Retry and Dunning Logic

Kelder's subscription billing follows this retry schedule for failed payments:

**Billing Schedule**:
- Initial billing: 05:00 Amsterdam time on the scheduled billing date
- Retries on days: 1, 3, 7, 14, 21, 28 after the first failure
- Final attempt: Day 30

**Dunning Episode**: A billing cycle with a failed payment is tracked as a "dunning episode" in `int_payment_episodes`

**Recovery Window**: A payment is considered "recovered within 30 days" if any retry succeeds within 30 days of the first failure

**Cancellation**: If all retries fail, billing gives up on day 30 and cancels the subscription with reason `max_retries_reached`

**Event Types**:
- `payment_failed`: First failed payment of a billing cycle
- `payment_recovered`: A retry succeeded after a failure

**Churn Impact**: Subscriptions whose payment failed in a month (and did not recover) count as churned in that month, even if the formal cancellation happens later

**Sources of truth**: `int_payment_episodes`, `int_charges_unified`, `fct_subscription_events`
