---
summary: Gift subscriptions excluded from churn, pause rate, and CAC metrics; identified by is_gift flag
usage_mode: auto
sort_order: 0
tags:
  - subscriptions
  - metrics
sl_refs:
  - fct_subscriptions
  - fct_subscription_events
  - fct_orders
  - metrics_subscriber_churn_monthly
  - metrics_pause_rate_monthly
  - metrics_new_subscribers_monthly
---

## Gift Subscription Exclusions

Kelder tracks gift subscriptions separately and **excludes them from core subscription metrics**:

**Identification**: Gift subscriptions are identified by the `is_gift` flag, which comes from:
- Shopify subscription app: custom attribute `is_gift`
- Recharge: property `is_gift`
- Prepaid subscriptions (`is_prepaid = true`) are also gifts

**Metric Exclusions**:
- **Churn metrics**: Gift subscriptions excluded from both base and churned counts in `metrics_subscriber_churn_monthly`
- **Pause rate**: Excluded from base in `metrics_pause_rate_monthly`
- **New subscribers**: Excluded from `metrics_new_subscribers_monthly`
- **CAC**: Gift subscriptions not counted in customer acquisition cost

**Rationale**: Gift subscriptions have different lifecycle patterns (prepaid, fixed duration, no voluntary cancellation) and should not be mixed with regular recurring subscriptions in retention and acquisition metrics

**Order Tracking**: Orders are flagged as gift-related via `fct_orders.is_gift` (gift subscription purchase or shipment, or Christmas gift box)

**Sources of truth**: `fct_subscriptions.is_gift`, `fct_subscription_events.is_gift`, `fct_orders.is_gift`
