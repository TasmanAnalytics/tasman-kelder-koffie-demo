---
summary: "Churn metric definition changed on 2026-05-01: v1 vs v2 and how to compare across the change"
usage_mode: auto
sort_order: 0
tags:
  - subscriptions
  - finance
sl_refs:
  - metrics_subscriber_churn_monthly
---

## Churn Definition Versions

### Timeline
- **v1**: Used before May 2026
- **v2**: Used from May 2026 onward (decision 0009)

### The change
The churn definition changed on 2026-05-01. The as-reported series (`churn_rate_as_reported`) uses v1 before May 2026 and v2 from May 2026 onward.

### How to compare across the change
- **Do NOT compare** `churn_rate_as_reported` across May 2026 - the definition changed.
- **Use** `churn_rate_v2_restated` for like-for-like comparisons across the change. This column applies v2 to every month.

### Columns in metrics_subscriber_churn_monthly
- `definition_version_as_reported`: v1 or v2, shows which definition was used for the as-reported series in that month.
- `churn_rate_as_reported`: The as-reported churn rate (v1 before May 2026, v2 from May).
- `churn_rate_v1`: v1 churn for every month (restated).
- `churn_rate_v2_restated`: v2 churn for every month (restated). **Use this for comparisons across May 2026.**

### Provisional data
The latest month is provisional (`is_provisional = true`). v2 does not count payment failures younger than 30 days yet, so the churn rate will be revised upward as failures age.

### Related
- `metrics_subscriber_churn_monthly`
- `context_metric_changelog` (definition details)
- Decision 0009 (reason for change)
