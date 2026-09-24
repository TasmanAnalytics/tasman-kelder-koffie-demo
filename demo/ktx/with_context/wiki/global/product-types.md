---
summary: "Kelder product types: single_origin, blend, decaf, equipment, gift_box, gift_subscription, bundle"
usage_mode: auto
sort_order: 0
tags:
  - products
refs:
  - gift-subscriptions
---

## Kelder Product Types

### Product Type Values
`stg_shopify__products.product_type` and `stg_shopify__product_variants.product_type` have seven values:

#### Coffee Products
- **`single_origin`**: Single-origin coffee beans
- **`blend`**: Coffee blends
- **`decaf`**: Decaffeinated coffee

#### Non-Coffee Products
- **`equipment`**: Coffee equipment (grinders, brewers, etc.)
- **`gift_box`**: Gift boxes (e.g., Christmas gift boxes)
- **`gift_subscription`**: Prepaid gift subscriptions (three shipments)
- **`bundle`**: Product bundles (e.g., Vaderdag Bundel)

### Usage
- Coffee products: `product_type IN ('single_origin', 'blend', 'decaf')`
- Gift products: `product_type IN ('gift_box', 'gift_subscription')`
- Subscription products: Coffee types + gift_subscription

### Related
See gift-subscriptions for how gift subscriptions are handled in metrics.

### Source
See `stg_shopify__products` for the product type field.
