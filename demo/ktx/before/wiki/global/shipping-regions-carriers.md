---
summary: Kelder ships to Benelux, DACH, and Other EU; PostNL for Netherlands, DHL elsewhere
usage_mode: auto
sort_order: 0
tags:
  - operations
  - geography
sl_refs:
  - fct_orders
  - dim_customers
---

## Shipping Regions and Carriers

**Supported Countries**: Kelder ships to 5 countries (ISO 3166-1 alpha-2):
- `NL`: Netherlands
- `BE`: Belgium
- `DE`: Germany
- `LU`: Luxembourg
- `FR`: France

**Reporting Regions**:
- **Benelux**: Netherlands, Belgium, Luxembourg
- **DACH**: Germany (Österreich and Schweiz not currently supported)
- **Other EU**: France and any other EU countries

**Carrier Assignment**:
- **PostNL**: Netherlands
- **DHL**: All other countries (Belgium, Germany, Luxembourg, France)

**Delivery Tracking**: `fct_orders` includes `carrier`, `shipped_at`, `delivered_at`, `has_failed_delivery`, and `delivery_days` (local calendar days from shipping to delivery)

**Source**: `seeds/countries` seed file defines country-to-region mapping and default carrier
