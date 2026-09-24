---
summary: Fivetran syncs Shopify, Recharge, Klaviyo, and Ads data with _fivetran_synced timestamps
usage_mode: auto
sort_order: 0
tags:
  - data-pipeline
  - data-quality
refs:
  - klaviyo-outage-april-2026
  - migration-artifacts-2026-03-12
---

## Fivetran Sync Metadata

### Data Sources
Kelder uses Fivetran to sync data from four sources:
- **Shopify**: Store, orders, customers, subscription app (from January 2025)
- **Recharge**: Subscription billing
- **Klaviyo**: Email marketing
- **Ads**: Meta Ads (Facebook/Instagram) and Google Ads

### Sync Timestamps
All raw source tables have a `_fivetran_synced` column that records when Fivetran last synced the row. This is the `loaded_at_field` in dbt sources.

### Sync Freshness
- **Shopify subscription contracts**: `synced_at` column shows when Fivetran last synced the row (current state as of that timestamp)
- **Recharge subscriptions**: `synced_at` column shows when Fivetran last synced the row

### Known Outages
See klaviyo-outage-april-2026 for the April 2026 Klaviyo connector outage that caused incomplete data.

### Data Completeness
- **Shopify**: Complete from January 2025
- **Recharge**: Complete from the 2026-03-12 migration (see migration-artifacts-2026-03-12)
- **Klaviyo**: Complete except for the April 2026 outage
- **Ads**: Complete daily data

### Source
See all `_sources.yml` files for the `loaded_at_field` configuration.
