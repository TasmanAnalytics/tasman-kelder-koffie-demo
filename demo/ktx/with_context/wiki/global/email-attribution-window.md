---
summary: Email-attributed revenue uses a 5-day attribution window from click to order
usage_mode: auto
sort_order: 0
tags:
  - email
  - attribution
refs:
  - klaviyo-outage-april-2026
sl_refs:
  - metrics_email_attribution_daily
---

## Email Attribution Window

### Attribution Logic
An order is **email-attributed** if the same Klaviyo profile clicked an email within the **five days** before placing the order.

### Data Source
- **Klaviyo events**: `Clicked Email` and `Placed Order` events per profile
- **Attribution**: Klaviyo's own `attributed_message_id` field
- **Window**: 5 days before the order

### Metrics
`metrics_email_attribution_daily` tracks:
- `attributed_orders`: Placed Orders with a click in the previous 5 days
- `attributed_revenue_eur`: Revenue from those orders

### Data Quality
See the klaviyo-outage-april-2026 page for the April 2026 connector outage that caused incomplete attribution data through 15 April.

### Source
See `metrics_email_attribution_daily` model for the attribution logic.
