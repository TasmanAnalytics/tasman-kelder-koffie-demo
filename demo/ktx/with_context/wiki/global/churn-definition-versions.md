---
summary: "Subscriber churn metric definition versions: v1 (before May 2026) vs v2 (from May 2026)"
usage_mode: auto
sort_order: 0
tags:
  - finance
  - metrics
sl_refs:
  - metrics_subscriber_churn_monthly
---

## Subscriber Churn Definition Versions

Kelder's subscriber churn metric has two definition versions:

### v1 (before May 2026)
- **Base**: Subscriptions active or paused at 00:00 Amsterdam time on the first of the month, excluding gift subscriptions
- **Churned**: Voluntary cancellations in the month

### v2 (from May 2026)
- **Base**: Same as v1
- **Churned**: Voluntary cancellations in the month **plus failed payments that did not recover within 30 days**

### Using the Metrics
- **As-reported series** (`churn_rate_as_reported`): Uses v1 before May 2026, v2 from May 2026. The definition changes on 1 May 2026.
- **Like-for-like comparisons**: Use `churn_rate_v2_restated` which applies v2 consistently across all months.
- **Latest month**: Marked as `is_provisional = true`. v2 churn will be revised upward as failed payments pass 30 days.
- **Raw columns**: Include migration artifacts (see migration-artifacts page). Never report raw churn without the adjusted rate.

### Source
`metrics_subscriber_churn_monthly` table contains all versions. See `context_metric_changelog` for the full decision record.
