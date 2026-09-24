---
summary: "2026-03-12 Recharge migration artifact: ~1,900 paused subscriptions incorrectly marked as cancelled"
usage_mode: auto
sort_order: 0
tags:
  - data-quality
  - subscriptions
sl_refs:
  - fct_subscriptions
  - fct_subscription_events
  - metrics_subscriber_churn_monthly
---

## Recharge Migration Artifact (2026-03-12)

### What happened
The 2026-03-12 Recharge backfill incorrectly wrote `churned_at` timestamps for approximately 1,900 subscriptions that were **paused** at the last Shopify sync. These subscriptions arrived in Recharge as **cancelled** at 2026-03-12 00:00:00 UTC with no cancellation reason.

### Impact on metrics
- **Churn metrics**: These subscriptions were not actually cancelled. They are flagged with `is_migration_artifact = true` in `fct_subscriptions` and `fct_subscription_events`.
- **Adjusted vs raw**: The adjusted churn metrics (`churn_rate_as_reported`, `churn_rate_v2_restated`) exclude migration artifacts. The `_raw` columns include them for reconciliation with Recharge exports.
- **Decision**: See decision 0007 for the full context and resolution.

### How to handle
- **Always use adjusted metrics** (`base_subscribers`, `churned_subscribers`, `churn_rate_as_reported`, `churn_rate_v2_restated`) for reporting.
- Use `_raw` columns **only** for finance reconciliation against Recharge exports.
- Filter: `WHERE is_migration_artifact = false` when querying `fct_subscriptions` or `fct_subscription_events` for churn analysis.

### Related
- `fct_subscriptions.is_migration_artifact`
- `fct_subscription_events.is_migration_artifact`
- `metrics_subscriber_churn_monthly` (adjusted vs raw columns)
