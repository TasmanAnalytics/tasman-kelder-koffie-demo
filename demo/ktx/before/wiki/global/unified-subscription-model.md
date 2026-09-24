---
summary: "Subscription key logic: stable identifiers across Shopify and Recharge migrations with unified status mapping"
usage_mode: auto
sort_order: 0
tags:
  - subscriptions
  - data-model
sl_refs:
  - fct_subscriptions
---

## Unified Subscription Model

Kelder tracks subscriptions across two billing systems (Shopify subscription app and Recharge) using a unified subscription key that remains stable across migrations.

**Subscription Key Format**:
- `shp-<contract_id>` for subscriptions that started in Shopify
- `rch-<subscription_id>` for subscriptions that started in Recharge without a Shopify contract

**Key Stability**: When a Recharge subscription continues a Shopify contract (via `external_contract_id`), it keeps the Shopify contract's key (`shp-<contract_id>`), ensuring continuity across the migration.

**Unified Status Mapping**:
The `int_subscriptions_unified` model maps platform-specific statuses to a unified status:
- **active**: Currently billing
- **paused**: Active subscription with `paused_until` set (Recharge has no paused status; paused subscriptions are 'active' with `paused_until`)
- **cancelled**: Customer-initiated cancellation or billing gave up (`max_retries_reached`)
- **expired**: Prepaid gift subscription completed

**Source Systems**:
- Shopify subscription app: `source_status` values are `ACTIVE`, `PAUSED`, `CANCELLED`, `FAILED`, `EXPIRED`
- Recharge: `source_status` values are `active`, `cancelled`, `expired` (no paused status)

**Sources of truth**: `int_subscriptions_unified`, `fct_subscriptions`
