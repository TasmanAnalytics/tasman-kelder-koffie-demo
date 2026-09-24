---
summary: "Unified subscription status: how Shopify and Recharge statuses map to active/paused/cancelled/expired"
usage_mode: auto
sort_order: 0
tags:
  - subscriptions
sl_refs:
  - fct_subscriptions
  - fct_subscription_events
---

## Unified Subscription Status

### Source systems
Kelder subscriptions come from two systems:
- **Shopify subscription app**: Uses statuses ACTIVE, PAUSED, CANCELLED, FAILED, EXPIRED
- **Recharge**: Uses statuses active, cancelled, expired (no explicit paused status - paused subscriptions are 'active' with `paused_until` set)

### Unified mapping
The `int_subscriptions_unified` intermediate model maps both systems to a single status vocabulary:
- **active**: Subscription is billing and shipping
- **paused**: Subscription is paused (Shopify PAUSED, or Recharge active with `paused_until` set)
- **cancelled**: Subscription was cancelled (Shopify CANCELLED or FAILED, Recharge cancelled)
- **expired**: Subscription expired (Shopify EXPIRED, Recharge expired)

### Current status only
The unified status in `fct_subscriptions` is the **current** status as of the last sync. For status at a point in time, use the event stream in `fct_subscription_events`.

### Related
- `fct_subscriptions.status` (unified)
- `int_subscriptions_unified` (mapping logic)
- `fct_subscription_events` (status history)
