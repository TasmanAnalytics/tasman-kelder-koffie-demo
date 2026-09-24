---
summary: Klaviyo connector outage 9-10 April 2026 caused incomplete email attribution data through 15 April
usage_mode: auto
sort_order: 0
tags:
  - data-quality
  - email
sl_refs:
  - metrics_email_attribution_daily
---

## Klaviyo Connector Outage (April 2026)

### Event
Fivetran Klaviyo connector outage from 2026-04-09 06:00 UTC to 2026-04-10 13:00 UTC. Data was never backfilled.

### Impact
- **9-10 April**: Email activity figures (received, opened, clicked) are incomplete
- **9-15 April**: Email-attributed revenue is **understated**
  - Orders placed up to five days after the outage lost the clicks that would have attributed them
  - The 5-day attribution window means the impact extends through 15 April

### Data Completeness
- **Shopify orders**: Complete (not affected)
- **Klaviyo events**: Incomplete for 9-10 April
- **Email attribution**: Understated through 15 April

### Identification
`metrics_email_attribution_daily.is_incomplete = true` for 9-15 April 2026.

### Analysis Guidance
When analyzing email attribution or revenue:
- **Exclude 9-15 April 2026**, OR
- **Call out the outage** when those days are included

### Source
See `context_business_events` for the full event record.
