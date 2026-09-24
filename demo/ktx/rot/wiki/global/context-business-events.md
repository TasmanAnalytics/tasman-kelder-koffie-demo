---
summary: "context_business_events table: dated events that moved metrics (migrations, promos, outages, definition changes, logistics)"
usage_mode: auto
sort_order: 0
tags:
  - conventions
  - data-quality
---

## context.business_events

### Purpose
Tracks dated events that moved a metric: migrations, promotions, outages, definition changes, and logistics events.

**Check this table before explaining any anomaly in a metric.**

### Structure
One row per event with:
- `event_date`: Date the event started (local date)
- `event_type`: migration, promo, outage, definition_change, or logistics
- `title`: Short title
- `description`: What happened and what it does to the numbers
- `affected_metrics`: Metrics the event moves (array of metric names)
- `expected_effect`: Expected direction (up, down, gap, none) with qualifier
- `owner`: Person who owns the event record
- `source_link`: Decision record, Linear ticket, Slack thread, or Notion page

### Event types
- **migration**: Data migration or system change (e.g., Recharge migration 2026-03-12)
- **promo**: Promotional campaign or discount
- **outage**: System outage or data gap (e.g., Klaviyo connector outage)
- **definition_change**: Metric definition change (e.g., churn v1 → v2)
- **logistics**: Logistics event (e.g., PostNL strike)

### How to use
1. Query `context_business_events` when investigating a metric anomaly
2. Check `affected_metrics` to see which metrics the event impacts
3. Follow `source_link` for full context and resolution
4. State the caveat explicitly when reporting affected periods

### Source
Loaded from `seeds/context/business_events.csv` and rendered to `context_business_events` model.

### Related
- `context_metric_changelog` (metric definition versions)
- Wiki pages for specific events (Recharge migration, PostNL strike, Klaviyo outage)
