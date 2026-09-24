---
summary: Subscription status is unified from Shopify and Recharge source systems into a single status field
usage_mode: auto
sort_order: 0
tags:
  - subscriptions
refs:
  - migration-artifacts-2026-03-12
sl_refs:
  - fct_subscriptions
  - fct_subscription_events
---

## Unified Subscription Status

### Source Systems
Kelder subscriptions come from two systems:
- **Shopify subscription app**: Uses statuses `ACTIVE`, `PAUSED`, `CANCELLED`, `FAILED`, `EXPIRED`
- **Recharge**: Uses statuses `active`, `cancelled`, `expired` (no explicit paused status; paused subscriptions are `active` with `paused_until` set)

### Unified Status
`fct_subscriptions.status` unifies these into four values:
- `active`: Subscription is active
- `paused`: Subscription is paused (Shopify `PAUSED` or Recharge `active` with `paused_until`)
- `cancelled`: Subscription was cancelled (Shopify `CANCELLED` or `FAILED`, Recharge `cancelled`)
- `expired`: Subscription expired (both systems)

### Important Notes
- **Current status only**: `fct_subscriptions.status` shows the current state. For status at a point in time, use `fct_subscription_events`.
- **Unified in one place**: The unification happens in `int_subscriptions_unified` and nowhere else.
- **Migration artifacts**: See the migration-artifacts-2026-03-12 page for subscriptions incorrectly marked as cancelled.

### Source
See `int_subscriptions_unified` model for the unification logic.
