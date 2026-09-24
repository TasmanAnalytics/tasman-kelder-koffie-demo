---
summary: "Gift subscriptions: prepaid 3-shipment subscriptions excluded from subscriber metrics and MRR"
usage_mode: auto
sort_order: 0
tags:
  - subscriptions
  - finance
sl_refs:
  - fct_subscriptions
  - fct_subscription_events
  - fct_orders
  - metrics_subscriber_churn_monthly
  - metrics_new_subscribers_monthly
---

## Gift Subscriptions

### Definition
Prepaid gift subscriptions are 3-shipment subscriptions paid once at purchase. They sit outside regular subscriber metrics.

### Key characteristics
- **Prepaid**: Paid once at purchase, not recurring billing.
- **Fixed duration**: Three shipments, then expired.
- **Flagged**: `is_gift = true` in `fct_subscriptions`, `fct_subscription_events`, and `fct_orders`.
- **Zero MRR**: `mrr_eur = 0` by design in `fct_subscriptions`. Gifts are not recurring revenue.

### Impact on metrics
- **Subscriber counts**: Exclude gifts from base subscribers, new subscribers, churn, and pause metrics.
- **MRR**: Gifts contribute zero to MRR.
- **Orders**: Gift subscription purchases and shipments are flagged with `is_gift = true` in `fct_orders`.
- **Filter**: `WHERE is_gift = false` when analyzing subscriber behavior or recurring revenue.

### Related
- `fct_subscriptions.is_gift`
- `fct_subscriptions.mrr_eur` (zero for gifts)
- `fct_subscription_events.is_gift`
- `fct_orders.is_gift`
- `metrics_subscriber_churn_monthly` (base excludes gifts)
- `metrics_new_subscribers_monthly` (excludes gifts)
