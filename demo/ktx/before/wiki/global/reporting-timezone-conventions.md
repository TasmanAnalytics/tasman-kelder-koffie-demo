---
summary: All reporting uses Europe/Amsterdam timezone; month boundaries at 00:00 local time; fiscal year starts January
usage_mode: auto
sort_order: 0
tags:
  - conventions
  - data-model
sl_refs: []
---

## Reporting Timezone and Date Conventions

**Reporting Timezone**: `Europe/Amsterdam` (CET/CEST)

All date boundaries in Kelder's reporting use Amsterdam local time:
- Month boundaries: 00:00 Amsterdam time on the first of the month
- Day boundaries: 00:00 Amsterdam time
- Billing runs: 05:00 Amsterdam time

**Fiscal Year**: Starts January 1 (calendar year)

**Reporting Period**: Metrics cover full months before the `as_of_date` variable (currently `2026-07-01`), starting from `first_reporting_month` (`2025-01-01`)

**UTC Storage**: Raw event timestamps are stored in UTC but converted to Amsterdam time for reporting boundaries

**Sources**:
- `int_reporting_months`: Calendar months with start/end instants at 00:00 Amsterdam time
- dbt project vars: `as_of_date`, `first_reporting_month`, `reporting_timezone`
