---
summary: "context_metric_changelog table: versioned metric definitions tracking when and why definitions changed"
usage_mode: auto
sort_order: 0
tags:
  - conventions
  - finance
sl_refs:
  - metrics_subscriber_churn_monthly
---

## context.metric_changelog

### Purpose
Tracks versioned metric definitions. When a metric's definition changes, a row is added here along with a decision record.

### Structure
One row per metric version with:
- `metric`: Metric name
- `version`: Definition version (v1, v2, etc.)
- `valid_from`: First month the definition applies to in the as-reported series
- `valid_to`: Day before the next version starts (empty for current version)
- `definition`: The definition in words
- `reason_for_change`: Why the definition changed
- `is_current`: True for the version in force now

### Example: Churn definition
- **v1**: Used before May 2026
- **v2**: Used from May 2026 onward (decision 0009)
- **Reason**: v2 counts payment failures that remain unrecovered after 30 days; v1 counted all voluntary cancellations

### How to use
1. Query `context_metric_changelog` to understand metric definition history
2. Check `valid_from` and `valid_to` to see which version applies to a given period
3. Use restated columns (e.g., `churn_rate_v2_restated`) for like-for-like comparisons across definition changes
4. Follow decision records for full context

### Source
Loaded from `seeds/context/metric_changelog.csv` and rendered to `context_metric_changelog` model.

### Related
- `context_business_events` (definition_change events)
- `metrics_subscriber_churn_monthly` (v1 vs v2 columns)
- Wiki page: churn-definition-versions
