---
summary: "Kelder product types: single_origin, blend, decaf, equipment, gift_box, gift_subscription, bundle"
usage_mode: auto
sort_order: 0
tags:
  - products
---

## Kelder Product Types

### Product type taxonomy
Kelder products are categorized into seven types:
- **single_origin**: Single-origin coffee
- **blend**: Coffee blends
- **decaf**: Decaffeinated coffee
- **equipment**: Coffee equipment (grinders, filters, etc.)
- **gift_box**: Gift boxes (e.g., Christmas gift boxes)
- **gift_subscription**: Prepaid gift subscriptions
- **bundle**: Product bundles (e.g., Vaderdag Bundel)

### Where used
- `stg_shopify__products.product_type`
- `stg_shopify__product_variants.product_type`

### Validation
Product types are validated with dbt `accepted_values` test to ensure data quality.

### Related
- `fct_orders.is_gift` (gift_box and gift_subscription orders)
- `fct_orders.contains_bundle` (bundle orders)
- `fct_subscriptions.is_gift` (gift_subscription subscriptions)
