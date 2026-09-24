---
summary: Subscription key is a stable identifier that follows a subscription across Shopify and Recharge systems
usage_mode: auto
sort_order: 0
tags:
  - subscriptions
  - data-modeling
refs:
  - migration-artifacts-2026-03-12
  - subscription-status-unified
sl_refs:
  - fct_subscriptions
  - fct_subscription_events
---

## Subscription Key

### Purpose
The **subscription key** is a stable identifier that follows a subscription for its entire lifecycle, even when it moves between Shopify and Recharge systems.

### Format
- **Shopify contracts**: `shp-<contract_id>`
- **Recharge subscriptions**: `rch-<recharge_subscription_id>` (when no Shopify contract exists)
- **Recharge continuations**: Use the Shopify contract's key when `external_contract_id` is set

### Lifecycle
A subscription keeps its key for its whole life:
1. Starts in Shopify → gets `shp-<contract_id>` key
2. Migrates to Recharge → keeps the same `shp-<contract_id>` key (via `external_contract_id`)
3. New Recharge subscription (no Shopify history) → gets `rch-<subscription_id>` key

### Usage
- `fct_subscriptions.subscription_key`: Primary key for subscriptions
- `fct_subscription_events.subscription_key`: Links events to subscriptions
- `int_charges_unified.subscription_key`: Links billing attempts to subscriptions

### Legacy Pause Restores
When operations manually re-created a subscription after the 2026-03-12 migration, the restore:
- Gets a new `rch-<id>` key
- Has `continues_subscription_key` pointing to the original subscription's key
- Has `is_legacy_pause_restore = true`

See migration-artifacts-2026-03-12 for details.

### Source
Defined in `int_subscriptions_unified` and used throughout the marts layer.
