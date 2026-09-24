---
summary: Defines gift subscriptions as three-shipment prepaid products (SKU GIFT-SUB-3) that expire rather than churn, with zero MRR by design and flagged via is_gift attribute, excluding them from churn calculations and revenue recognition.
usage_mode: auto
tags:
  - gift subscriptions
  - prepaid
  - churn exclusion
  - MRR
  - Shopify
  - Recharge
  - subscription lifecycle
sl_refs:
  - fct_subscriptions
connections:
  - kelder
---

# Gift subscriptions

Owner: Sanne (data). Written 2026-06-15.

- A gift subscription is prepaid for three shipments, four weeks apart. The buyer pays once at
  checkout (SKU `GIFT-SUB-3`); the three shipments are zero-value renewal orders.
- After the third shipment the subscription is `expired`, not cancelled. Expiry is not churn.
- Gift subscriptions are excluded from the churn base and from churn, in every definition version.
- `fct_subscriptions.mrr_eur` is zero for gifts by design (decision 0006). The revenue shows up once,
  in the purchase order.
- Gifts are flagged with `is_gift`: the Shopify contract custom attribute before March 2026, the
  Recharge property from then. Recharge gifts are also `is_prepaid`.
- Volumes: about 300 sold in December 2025 and about 450 in the Father's Day week, 14 to 21 June 2026
  (context.business_events). Expect new customers and average order value to rise in those weeks
  while MRR does not.
