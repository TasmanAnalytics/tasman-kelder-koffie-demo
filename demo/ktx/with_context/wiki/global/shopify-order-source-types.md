---
summary: "Shopify orders have three source types: web, subscription_contract, and recharge"
usage_mode: auto
sort_order: 0
tags:
  - orders
  - subscriptions
refs:
  - marketing-channel-attribution
sl_refs:
  - fct_orders
---

## Shopify Order Source Types

### Source Name Values
`fct_orders.source_name` has three values:

#### `web`
Web checkout orders placed by customers on the Kelder website. These have:
- Marketing channel attribution (`channel` field)
- UTM parameters and referrer tracking
- May be the first order that starts a subscription (`is_subscription_first_order = true`)

#### `subscription_contract`
Subscription renewal orders created by the **Shopify subscription app** billing system. These have:
- Empty `channel` (no marketing attribution)
- `is_subscription_renewal = true`
- Created by scheduled subscription charges

#### `recharge`
Subscription renewal orders created by the **Recharge** billing system. These have:
- Empty `channel` (no marketing attribution)
- `is_subscription_renewal = true`
- Created by Recharge charges after the migration

### Usage
- Filter for web orders: `source_name = 'web'`
- Filter for renewals: `is_subscription_renewal = true` (includes both subscription_contract and recharge)
- Marketing analysis: Use `channel` field (only populated for web orders)

### Source
See `stg_shopify__orders` and `fct_orders` for the source_name logic.
