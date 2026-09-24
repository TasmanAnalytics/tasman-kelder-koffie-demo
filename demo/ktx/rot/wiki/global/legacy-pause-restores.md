---
summary: "Legacy pause restores: Recharge subscriptions re-created by operations after migration wiped pauses"
usage_mode: auto
sort_order: 0
tags:
  - data-quality
  - subscriptions
sl_refs:
  - fct_subscriptions
  - metrics_new_subscribers_monthly
---

## Legacy Pause Restores

### What they are
Recharge subscriptions re-created by the operations team for customers whose pause was wiped by the 2026-03-12 migration. These subscriptions have `restore_source = 'legacy_pause'` in Recharge properties.

### Key characteristics
- **Continuations, not new subscribers**: Restores continue the original subscription's key and tenure via `continues_subscription_key`.
- **Flagged**: `is_legacy_pause_restore = true` in `fct_subscriptions`.
- **Original subscription key**: The restore inherits the original subscription's `subscription_key` (e.g., `shp-21400232`).

### Impact on metrics
- **New subscriber counts**: Exclude restores from new subscriber metrics. They are continuations, not acquisitions.
- **Acquisition metrics**: Exclude restores from CAC and channel attribution. The original subscription already counted.
- **Filter**: `WHERE is_legacy_pause_restore = false` when counting new subscriptions or analyzing acquisition.

### Related
- `fct_subscriptions.is_legacy_pause_restore`
- `fct_subscriptions.continues_subscription_key`
- `metrics_new_subscribers_monthly` (already excludes restores)
