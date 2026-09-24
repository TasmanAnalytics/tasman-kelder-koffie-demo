---
summary: "Email attribution uses 5-day lookback: orders attributed to email if profile clicked within 5 days before order"
usage_mode: auto
sort_order: 0
tags:
  - marketing
sl_refs:
  - metrics_email_attribution_daily
---

## Email Attribution Logic

### Attribution window
Email attribution uses a **5-day lookback window**. An order is attributed to email if the same Klaviyo profile clicked an email within the 5 days before placing the order.

### How it works
1. Klaviyo tracks email engagement events per profile: Received Email, Opened Email, Clicked Email
2. Klaviyo tracks Placed Order events with order value
3. An order is **attributed** if the profile has a Clicked Email event in the 5 days before the order
4. Klaviyo's own `attributed_message_id` field is also captured but not used for the 5-day attribution logic

### Metrics
- `metrics_email_attribution_daily.attributed_orders`: Orders with a click in the previous 5 days
- `metrics_email_attribution_daily.attributed_revenue_eur`: Revenue from attributed orders

### Data quality caveat
The Klaviyo connector outage (9-10 April 2026) created a gap in click events. Orders placed up to 5 days after the outage (through 15 April) lost the clicks that would have attributed them, so attributed revenue is understated for 9-15 April.

### Related
- `metrics_email_attribution_daily`
- `stg_klaviyo__events` (source events)
- Wiki page: klaviyo-outage-april-2026
