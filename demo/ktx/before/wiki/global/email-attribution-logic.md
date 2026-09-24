---
summary: "Email attribution uses 5-day click window: orders attributed if profile clicked any email in previous 5 days"
usage_mode: auto
sort_order: 0
tags:
  - metrics
  - marketing
sl_refs:
  - metrics_email_attribution_daily
---

## Email Attribution Logic

Kelder attributes email revenue using a **5-day click window**:

**Attribution Rule**: A Klaviyo "Placed Order" event is attributed to email if the same profile clicked any email (campaign or flow) within the **five days before** the order.

**Metrics**:
- `attributed_orders`: Count of Placed Orders with a click in the previous 5 days
- `attributed_revenue_eur`: Sum of order values for attributed orders

**Data Source**: Klaviyo events (`Received Email`, `Opened Email`, `Clicked Email`, `Placed Order`)

**Attribution Model**: Last-click within 5 days (Klaviyo's own `attributed_message_id` is available but not used in the governed metric)

**Source of truth**: `metrics_email_attribution_daily`

**Note**: This is a simple last-touch attribution model. Orders may also be influenced by other channels (paid ads, organic, referral) not captured in this metric.
