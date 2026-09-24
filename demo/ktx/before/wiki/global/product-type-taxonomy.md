---
summary: "Kelder product types: single_origin, blend, decaf, equipment, gift_box, gift_subscription, bundle"
usage_mode: auto
sort_order: 0
tags:
  - products
  - taxonomy
sl_refs: []
---

## Product Type Taxonomy

Kelder's product catalogue uses these product types:

**Coffee Products**:
- `single_origin`: Single-origin coffee beans
- `blend`: Coffee blends
- `decaf`: Decaffeinated coffee

**Non-Coffee Products**:
- `equipment`: Coffee brewing equipment
- `gift_box`: Gift boxes (e.g., Christmas gift boxes)
- `gift_subscription`: Prepaid gift subscription products
- `bundle`: Product bundles (e.g., Vaderdag Bundel)

**Source**: Shopify product metadata, captured in `stg_shopify__products.product_type` and joined to variants and orders

**Usage**: Product type is available on `fct_orders` via line items and on `fct_subscriptions` via the subscribed variant
