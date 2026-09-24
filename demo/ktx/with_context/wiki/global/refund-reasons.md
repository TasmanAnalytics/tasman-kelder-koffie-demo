---
summary: Refund reasons are entered by customer service in the refund_note field
usage_mode: auto
sort_order: 0
tags:
  - refunds
  - customer-service
refs:
  - postnl-strike-may-2026
sl_refs:
  - fct_orders
---

## Refund Reasons

### Refund Note Field
When customer service issues a refund, they enter a reason in `stg_shopify__refunds.refund_note` and `fct_orders` (via the first refund).

### Common Reasons
Examples from the dbt documentation:
- **`late_delivery`**: Order arrived late
- **`wrong_grind`**: Wrong grind size shipped

### Usage
- Refund analysis: Group by `refund_note` to understand refund drivers
- Late delivery tracking: Filter for `refund_note = 'late_delivery'`
- Quality issues: Look for product-related reasons like `wrong_grind`

### Related Events
See postnl-strike-may-2026 for the May 2026 event that caused late-delivery refunds to spike to ~6% of orders in that week.

### Data Sources
- `stg_shopify__refunds.refund_note`: Reason entered by customer service
- `fct_orders.first_refunded_at`: Timestamp of first refund
- `fct_orders.refunded_eur`: Total refunded amount
- `fct_orders.is_refunded`: Boolean flag for any refund

### Source
See `stg_shopify__refunds` for the refund_note field.
