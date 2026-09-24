---
summary: "Kelder dbt project structure: staging, intermediate, marts, and context layers with materialization strategy"
usage_mode: auto
sort_order: 0
tags:
  - dbt
  - data-modeling
---

## Kelder dbt Project Structure

### Project Configuration
- **Name**: kelder
- **Profile**: kelder
- **Reporting date**: 2026-07-01 (metrics cover full months before this date)
- **First reporting month**: 2025-01-01
- **Reporting timezone**: Europe/Amsterdam

### Layer Structure

#### Staging (`+schema: staging`, `+materialized: view`)
Raw source data cleaned and standardized:
- `stg_shopify__*`: Shopify store and subscription app (synced by Fivetran from January 2025)
- `stg_recharge__*`: Recharge subscription billing (synced by Fivetran)
- `stg_klaviyo__*`: Klaviyo email marketing (synced by Fivetran)
- `stg_ads__*`: Meta Ads and Google Ads daily performance (synced by Fivetran)

#### Intermediate (`+schema: intermediate`, `+materialized: table`)
Business logic and unification:
- `int_subscriptions_unified`: Unified subscription status across Shopify and Recharge
- `int_charges_unified`: Billing attempts from both systems
- `int_payment_episodes`: Dunning episodes with recovery tracking
- `int_subscription_events`: Unified event stream for governed metrics
- `int_reporting_months`: Calendar months for reporting

#### Marts (`+schema: main`, `+materialized: table`)
Analytics-ready fact and dimension tables:
- `dim_customers`: Customer master data
- `fct_orders`: Order transactions
- `fct_subscriptions`: Subscription contracts
- `fct_subscription_events`: Subscription lifecycle events
- `metrics_*`: Governed monthly and daily metrics

#### Context (`+schema: context`, `+materialized: table`)
Metadata and documentation:
- `context_business_events`: Dated events that moved metrics
- `context_metric_changelog`: Versioned metric definitions

#### Seeds (`+schema: reference`)
Reference data:
- `countries`: Countries Kelder ships to with regions and carriers
- `business_events`: Source CSV for context_business_events
- `metric_changelog`: Source CSV for context_metric_changelog

### Source
See `dbt_project.yml` for the full configuration.
