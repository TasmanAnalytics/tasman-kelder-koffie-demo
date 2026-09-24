---
summary: "Web order channels derived from UTM parameters and referrer: paid_social, paid_search, email, organic, referral, direct"
usage_mode: auto
sort_order: 0
tags:
  - marketing
  - attribution
sl_refs:
  - fct_orders
  - dim_customers
  - fct_subscriptions
  - metrics_cac_monthly
---

## Marketing Channel Attribution

Kelder attributes web orders to marketing channels based on UTM parameters and referrer from the landing site:

**Channel Values**:
- `paid_social`: Paid social media (Meta/Facebook/Instagram ads)
- `paid_search`: Paid search (Google Ads)
- `email`: Email marketing (Klaviyo)
- `organic`: Organic search
- `referral`: Referral from another site
- `direct`: Direct traffic (no referrer or UTM)

**Attribution Logic**:
- Derived from `utm_source`, `utm_medium`, `utm_campaign`, `landing_site`, and `referring_site` on the order
- Only applies to **web orders** (`source_name = 'web'`)
- Subscription renewals (`source_name = 'subscription_contract'` or `'recharge'`) have empty channel

**First Order Channel**: The channel of a customer's first web order is captured on `dim_customers.first_order_channel` and `fct_subscriptions.first_order_channel` for acquisition analysis

**CAC Calculation**: Customer acquisition cost is calculated per channel using ad spend and new subscribers whose first order came through that channel

**Sources of truth**: `fct_orders`, `dim_customers`, `fct_subscriptions`, `metrics_cac_monthly`
