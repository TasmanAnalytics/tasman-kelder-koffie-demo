---
summary: "Subscription billing intervals: 2, 4, or 6 weeks (14, 28, or 42 days); MRR normalized to 30-day month"
usage_mode: auto
sort_order: 0
tags:
  - subscriptions
  - billing
sl_refs:
  - fct_subscriptions
---

## Subscription Billing Intervals

Kelder offers three subscription billing intervals:

**Interval Options**:
- **2 weeks** (14 days)
- **4 weeks** (28 days)
- **6 weeks** (42 days)

**Interval Storage**:
- Shopify subscription app: `billing_interval = 'WEEK'` with `billing_interval_count` (2, 4, or 6)
- Recharge: `interval_days` (14, 28, or 42)
- Unified model: `interval_days` in `fct_subscriptions`

**MRR Calculation**: Monthly Recurring Revenue (MRR) is calculated by normalizing the subscription price to a 30-day month:
- `mrr_eur = (price_eur / interval_days) * 30`
- Only active subscriptions contribute to MRR (paused, cancelled, and expired subscriptions have `mrr_eur = 0`)

**Quantity**: Subscriptions specify `quantity` (bags per shipment), typically 1 or 2

**Source of truth**: `fct_subscriptions.interval_days`, `fct_subscriptions.mrr_eur`
