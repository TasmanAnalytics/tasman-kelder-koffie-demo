---
summary: "PostNL strike 18-24 May 2026: delivery delays and increased refund rates for Dutch orders"
usage_mode: auto
sort_order: 0
tags:
  - logistics
  - data-quality
sl_refs:
  - fct_orders
---

## PostNL Strike (18-24 May 2026)

### What happened
PostNL strike from 18 to 24 May 2026 caused delivery delays and failures for Dutch orders shipped during that week.

### Impact
- **Delivery times**: Dutch PostNL parcels shipped in that week took 3 to 7 days (vs normal 1-2 days).
- **Failed deliveries**: About 1% of parcels were never delivered.
- **Refunds**: Late-delivery refunds rose to about 6% of orders shipped that week (vs normal ~1%).

### How to handle
- **Exclude the week** when comparing delivery times or refund rates across periods.
- **Or state the caveat** explicitly when including the week in analysis.
- **Filter**: `WHERE shipped_at NOT BETWEEN '2026-05-18' AND '2026-05-24'` to exclude the strike week.

### Affected columns
- `fct_orders.delivery_days` (inflated for Dutch PostNL orders shipped 18-24 May)
- `fct_orders.has_failed_delivery` (elevated for that week)
- `fct_orders.refunded_eur` (elevated for late-delivery refunds)

### Related
- `fct_orders.delivery_days` (caveat in column description)
- `context_business_events` (event record)
