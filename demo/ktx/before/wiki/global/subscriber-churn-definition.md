---
summary: "Governed monthly subscriber churn: voluntary cancellations + payment failures, over active/paused base at month start"
usage_mode: auto
sort_order: 0
tags:
  - metrics
  - subscriptions
sl_refs:
  - metrics_subscriber_churn_monthly
  - fct_subscriptions
  - fct_subscription_events
---

## Subscriber Churn Definition

Kelder's governed monthly subscriber churn metric follows this definition:

**Base**: Subscriptions that are active or paused at 00:00 Amsterdam time on the first of the month, **excluding gift subscriptions**.

**Churned**: Subscriptions counted as churned in the month include:
- Voluntary cancellations (customer-initiated)
- Subscriptions whose payment failed in the month (dunning episodes that did not recover)

**Churn Rate**: `churned_subscribers / base_subscribers`

**Key exclusions**:
- Gift subscriptions are excluded from both base and churned counts
- Paused subscriptions are included in the base (they are still active subscribers)
- Only voluntary cancellations and payment failures count as churn; expired subscriptions are handled separately

**Source of truth**: `metrics_subscriber_churn_monthly`

**Timezone**: All month boundaries use Europe/Amsterdam timezone (00:00 local time on the first of the month).
