---
summary: PostNL strike 18-24 May 2026 caused delivery delays and increased refund rates
usage_mode: auto
sort_order: 0
tags:
  - data-quality
  - logistics
sl_refs:
  - fct_orders
---

## PostNL Strike (18-24 May 2026)

### Event
PostNL strike from 18 to 24 May 2026 affected Dutch deliveries.

### Impact
- **Delivery times**: Dutch PostNL parcels shipped in that week took 3 to 7 days (vs normal 1-2 days)
- **Failed deliveries**: About 1% were never delivered
- **Refunds**: Late-delivery refunds rose to about 6% of those orders (vs normal ~1%)

### Analysis Guidance
When analyzing delivery times or refund rates:
- **Exclude the week** of 18-24 May 2026, OR
- **Call out the strike** when the week is included

The `delivery_days` column in `fct_orders` includes a caveat about this event.

### Source
See `context_business_events` for the full event record.
