---
summary: Reporting timezone is Europe/Amsterdam; local dates and times for billing, events, and metrics
usage_mode: auto
sort_order: 0
tags:
  - conventions
---

## Reporting Timezone

### Timezone
All reporting uses **Europe/Amsterdam** timezone (CET/CEST).

### Local dates
- **Order dates**: `fct_orders.order_date` is the local date of the order in Amsterdam time.
- **Billing cycle dates**: `billing_cycle_date` columns are local dates in Amsterdam time.
- **Event months**: `event_month` columns are local calendar months in Amsterdam time.
- **Metrics**: Monthly metrics use calendar months starting at 00:00 Amsterdam time on the first of the month.

### UTC timestamps
Most timestamp columns (`created_at`, `occurred_at`, `shipped_at`, etc.) are stored in **UTC** but should be interpreted in Amsterdam time for reporting.

### Billing time
Subscription billing runs at **05:00 Amsterdam time** on the scheduled billing date.

### Configuration
Set in `dbt_project.yml`:
```yaml
vars:
  reporting_timezone: "Europe/Amsterdam"
```

### Related
- `int_reporting_months` (month boundaries at 00:00 Amsterdam time)
- All `*_at` timestamp columns (UTC)
- All `*_date` and `*_month` columns (local Amsterdam dates)
