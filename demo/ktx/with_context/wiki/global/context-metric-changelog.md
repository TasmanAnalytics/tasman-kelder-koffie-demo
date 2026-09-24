---
summary: context_metric_changelog table documents versioned metric definitions and why they changed
usage_mode: auto
sort_order: 0
tags:
  - context
  - metrics
refs:
  - churn-definition-versions
---

## context.metric_changelog

### Purpose
The `context_metric_changelog` table documents **versioned metric definitions**. When a metric's definition changes, add a row here and a decision record.

### Schema
- `metric`: Metric name
- `version`: Definition version (`v1`, `v2`, etc.)
- `valid_from`: First month the definition applies to in the as-reported series
- `valid_to`: Day before the next version starts (empty for the current version)
- `definition`: The definition in words
- `reason_for_change`: Why the definition changed
- `is_current`: True for the version in force now

### Example: Subscriber Churn
- **v1** (valid_from 2025-01-01, valid_to 2026-04-30): Voluntary cancellations only
- **v2** (valid_from 2026-05-01, is_current = true): Voluntary cancellations + failed payments not recovered within 30 days

See churn-definition-versions for the full churn metric documentation.

### Source
Seeded from `seeds/context/metric_changelog.csv` and rendered to the `context_metric_changelog` model and `context/metric_changelog.md`.
