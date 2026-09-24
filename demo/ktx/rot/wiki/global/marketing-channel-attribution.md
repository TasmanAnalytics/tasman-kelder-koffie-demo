---
summary: "Marketing channel attribution: how web orders are attributed to paid_social, paid_search, email, organic, referral, or direct"
usage_mode: auto
sort_order: 0
tags:
  - marketing
sl_refs:
  - fct_orders
  - dim_customers
  - fct_subscriptions
  - metrics_cac_monthly
---

## Marketing Channel Attribution

### Channels
Web orders are attributed to one of six channels:
- **paid_social**: Paid social media (Meta Ads - Facebook and Instagram)
- **paid_search**: Paid search (Google Ads)
- **email**: Email marketing (Klaviyo)
- **organic**: Organic search
- **referral**: Referral traffic
- **direct**: Direct traffic

### Attribution logic
Channel is derived from UTM parameters and referrer on the landing site of the visit that led to the order:
- `utm_source` and `utm_medium` determine paid channels
- Referrer determines organic, referral, or direct

### Subscription renewals
Subscription renewal orders have **no channel** (`channel` is empty). They are created by the billing system, not by a customer visit.

### Related columns
- `fct_orders.channel`
- 
- 
- 
- 
- `fct_orders.is_subscription_renewal` (no channel for renewals)

### Related
- `fct_orders`
- `dim_customers.first_order_channel`
- `fct_subscriptions.first_order_channel`
- `metrics_cac_monthly` (CAC by channel)
