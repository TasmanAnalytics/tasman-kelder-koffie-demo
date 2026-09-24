---
summary: "2026-03-12 Recharge migration artifacts: ~1,900 paused subscriptions incorrectly marked as cancelled"
usage_mode: auto
sort_order: 0
tags:
  - data-quality
  - subscriptions
refs:
  - churn-definition-versions
sl_refs:
  - fct_subscriptions
  - fct_subscription_events
  - metrics_subscriber_churn_monthly
---

## 2026-03-12 Recharge Migration Artifacts

### What Happened
During the 2026-03-12 Recharge backfill, approximately 1,900 subscriptions that were **paused** at the last Shopify sync arrived in Recharge as **cancelled** at 2026-03-12 00:00:00 UTC with no cancellation reason.

These subscriptions were not actually cancelled. They are migration artifacts.

### Identification
Rows with `is_migration_artifact = true` in:
- `fct_subscriptions`
- `fct_subscription_events`
- `metrics_subscriber_churn_monthly` (raw columns only)

### Impact on Metrics
- **Churn metrics**: Migration artifacts are **excluded** from adjusted churn metrics (`churn_rate_as_reported`, `churn_rate_v2_restated`).
- **Raw columns**: Include migration artifacts for finance reconciliation against Recharge exports. Never report raw churn without the adjusted rate.
- **Subscription counts**: Exclude `is_migration_artifact = true` when counting active/cancelled subscriptions.

### Legacy Pause Restores
Some affected customers had their subscriptions manually re-created by operations. These carry:
- `is_legacy_pause_restore = true`
- `continues_subscription_key` pointing to the original subscription

**Exclude restores from**:
- New subscriber counts (they continue an existing subscription)
- Acquisition metrics (they are not new acquisitions)

### Source
Decision 0007 in the context tables. See `context_business_events` for the full timeline.
