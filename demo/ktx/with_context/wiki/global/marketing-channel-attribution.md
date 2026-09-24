---
summary: Web orders are attributed to marketing channels based on UTM parameters and referrer
usage_mode: auto
sort_order: 0
tags:
  - marketing
  - attribution
sl_refs:
  - fct_orders
  - fct_subscriptions
  - metrics_new_subscribers_monthly
  - metrics_cac_monthly
---

## Marketing Channel Attribution

### Channels
Web orders (not subscription renewals) are attributed to one of six channels:
- `paid_social`: Paid social media (Meta/Facebook/Instagram)
- `paid_search`: Paid search (Google Ads)
- `email`: Email marketing (Klaviyo)
- `organic`: Organic search
- `referral`: Referral from another site
- `direct`: Direct traffic

### Attribution Logic
Channel is determined from the order's `landing_site`, `referring_site`, and UTM parameters (`utm_source`, `utm_medium`, `utm_campaign`).

### Subscription Renewals
Subscription renewal orders have **empty channel** because they are created by the billing system, not a customer visit.

### Data Model
- `fct_orders.channel`: Marketing channel for web orders
- `fct_orders.is_subscription_renewal`: True for renewals (empty channel)
- `fct_subscriptions.first_order_channel`: Channel of the checkout order that started the subscription

### Acquisition Metrics
New subscriber acquisition is attributed to the channel of the first order:
- `metrics_new_subscribers_monthly`: Breaks down new subscribers by paid vs unpaid channels
- `metrics_cac_monthly`: Customer acquisition cost for paid channels (paid_social, paid_search)

### Source
See `stg_shopify__orders` for the channel attribution logic.
