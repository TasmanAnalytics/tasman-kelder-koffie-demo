---
summary: context_business_events table documents dated events that moved metrics (migrations, promotions, outages, definition changes, logistics)
usage_mode: auto
sort_order: 0
tags:
  - context
  - data-quality
refs:
  - migration-artifacts-2026-03-12
  - klaviyo-outage-april-2026
  - postnl-strike-may-2026
  - churn-definition-versions
---

## context.business_events

### Purpose
The `context_business_events` table documents **dated events that moved a metric**: migrations, promotions, outages, definition changes, and logistics events.

**Check this table before explaining any anomaly in a metric.**

### Schema
- `event_date`: Date the event started (local date)
- `event_type`: `migration`, `promo`, `outage`, `definition_change`, or `logistics`
- `title`: Short title
- `description`: What happened and what it does to the numbers
- `affected_metrics`: Metrics the event moves (array of metric names)
- `expected_effect`: Expected direction (`up`, `down`, `gap`, `none`), with a qualifier where the effect is not real
- `owner`: Person who owns the event record
- `source_link`: Decision record, Linear ticket, Slack thread, or Notion page with the detail

### Examples
- **2026-03-12 migration**: Recharge backfill created migration artifacts (see migration-artifacts-2026-03-12)
- **2026-04-09 outage**: Klaviyo connector outage (see klaviyo-outage-april-2026)
- **2026-05-18 logistics**: PostNL strike (see postnl-strike-may-2026)
- **2026-05-01 definition_change**: Churn metric v2 (see churn-definition-versions)

### Source
Seeded from `seeds/context/business_events.csv` and rendered to the `context_business_events` model.
