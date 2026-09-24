---
summary: "Subscription key system: stable keys across Shopify and Recharge (shp-* and rch-*)"
usage_mode: auto
sort_order: 0
tags:
  - subscriptions
  - conventions
sl_refs:
  - fct_subscriptions
  - fct_subscription_events
---

## Subscription Key System

### Purpose
A subscription keeps its key for its whole life, even when it moves from Shopify to Recharge.

### Key format
- **shp-{contract_id}**: Shopify subscription app contracts (e.g., `shp-21400232`)
- **rch-{subscription_id}**: Recharge subscriptions that don't carry a Shopify contract (e.g., `rch-480000197`)

### Continuity across systems
When a Shopify subscription continues in Recharge:
- The Recharge subscription carries the Shopify contract id in `external_contract_id`
- The subscription keeps the **shp-** key from Shopify
- `fct_subscriptions.shopify_contract_id` and `recharge_subscription_id` are both populated

### New Recharge subscriptions
Subscriptions created directly in Recharge (no prior Shopify contract) get their own **rch-** key.

### Where to find it
- `fct_subscriptions.subscription_key` (primary key)
- `fct_subscription_events.subscription_key` (foreign key)
- `int_subscriptions_unified.subscription_key` (source of truth)
- `int_charges_unified.subscription_key` (billing events)
- `int_payment_episodes.subscription_key` (dunning episodes)

### Related
- `fct_subscriptions`
- `fct_subscription_events`
- `int_subscriptions_unified` (mapping logic)
