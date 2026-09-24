---
summary: dbt data tests document uniqueness, not-null constraints, accepted values, and relationships
usage_mode: auto
sort_order: 0
tags:
  - dbt
  - data-quality
---

## dbt Data Tests

### Test Types

#### Uniqueness and Not-Null
Primary keys are tested with `unique` and `not_null`:
- `dim_customers.customer_id`
- `fct_orders.order_id`
- `fct_subscriptions.subscription_key`
- `fct_subscription_events.subscription_event_id`
- All staging model primary keys

#### Accepted Values
Enum-like fields are tested with `accepted_values`:
- **Countries**: `['NL', 'BE', 'DE', 'LU', 'FR']`
- **Product types**: `['single_origin', 'blend', 'decaf', 'equipment', 'gift_box', 'gift_subscription', 'bundle']`
- **Order source**: `['web', 'subscription_contract', 'recharge']`
- **Channels**: `['paid_social', 'paid_search', 'email', 'organic', 'referral', 'direct']`
- **Subscription status**: `['active', 'paused', 'cancelled', 'expired']`
- **Event types**: `['started', 'paused', 'resumed', 'cancelled', 'expired', 'payment_failed', 'payment_recovered']`
- **Carriers**: `['PostNL', 'DHL']`
- **Financial status**: `['paid', 'refunded', 'partially_refunded']`

#### Relationships
Foreign keys are tested with `relationships`:
- `fct_orders.customer_id` → `dim_customers.customer_id`
- `fct_subscriptions.customer_id` → `dim_customers.customer_id`
- `fct_subscription_events.subscription_key` → `fct_subscriptions.subscription_key`
- Staging models have relationships to their parent tables

#### Unique Combinations
Composite keys are tested with `unique_combination`:
- `metrics_cac_monthly`: `[month, channel]`
- `stg_ads__ad_spend_daily`: `[spend_date, platform, campaign_id]`
- `int_charges_unified`: `[source_system, source_id]`
- `int_payment_episodes`: `[subscription_key, billing_cycle_date]`

### Test Metadata in Semantic Layer
The semantic layer overlays include test metadata in `constraints.dbt`:
- `not_null: true`
- `unique: true`

This metadata is visible to the query assistant and helps with data quality understanding.

### Source
See all `_models.yml` files for the full test suite.
