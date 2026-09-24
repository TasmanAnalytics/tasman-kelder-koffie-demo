---
summary: "Klaviyo connector outage 9-10 April 2026: incomplete email attribution data through 15 April"
usage_mode: auto
sort_order: 0
tags:
  - marketing
  - data-quality
sl_refs:
  - metrics_email_attribution_daily
---

## Klaviyo Connector Outage (9-10 April 2026)

### What happened
Fivetran Klaviyo connector outage from 2026-04-09 06:00 UTC to 2026-04-10 13:00 UTC. The data was never backfilled.

### Impact
- **Email events**: No Klaviyo data for 9 and 10 April. Email engagement metrics (received, opened, clicked) are incomplete for those days.
- **Attribution window**: Email attribution uses a 5-day lookback. Orders placed up to 5 days after the outage (through 15 April) lost the clicks that would have attributed them.
- **Attributed revenue**: Understated from 9 to 15 April.
- **Shopify orders**: Complete. Only Klaviyo events are missing.

### Affected days
- **9-10 April**: Email engagement metrics incomplete.
- **9-15 April**: Email-attributed revenue understated.

### How to handle
- **Exclude 9-15 April** when analyzing email attribution trends.
- **Or state the caveat** explicitly when including those days.
- **Flag**: `is_incomplete = true` in `metrics_email_attribution_daily` for 9-15 April.

### Related
- `metrics_email_attribution_daily.is_incomplete`
- `context_business_events` (event record)
