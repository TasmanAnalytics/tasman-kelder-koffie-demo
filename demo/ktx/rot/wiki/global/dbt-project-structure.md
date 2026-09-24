---
summary: "dbt project structure: staging (views), intermediate (tables), marts (tables), context (tables)"
usage_mode: auto
sort_order: 0
tags:
  - conventions
---

## dbt Project Structure

### Layer structure
The Kelder dbt project follows a four-layer structure:

#### Staging (stg_*)
- **Schema**: `staging`
- **Materialization**: Views
- **Purpose**: Clean, renamed source data with minimal transformation
- **Naming**: `stg_{source}__{entity}` (e.g., `stg_shopify__orders`, `stg_recharge__subscriptions`)
- **Tests**: Column-level tests (not_null, unique, accepted_values, relationships)

#### Intermediate (int_*)
- **Schema**: `intermediate`
- **Materialization**: Tables
- **Purpose**: Business logic transformations, unifications, and derived datasets
- **Naming**: `int_{entity}` (e.g., `int_subscriptions_unified`, `int_payment_episodes`)
- **Key models**:
  - `int_subscriptions_unified`: Unified subscription status across Shopify and Recharge
  - `int_charges_unified`: Billing attempts from both systems
  - `int_payment_episodes`: Dunning episodes with recovery tracking
  - `int_subscription_events`: Unified event stream

#### Marts (dim_*, fct_*, metrics_*)
- **Schema**: `main`
- **Materialization**: Tables
- **Purpose**: Business-facing dimensional models and governed metrics
- **Naming**:
  - `dim_*`: Dimension tables (e.g., `dim_customers`)
  - `fct_*`: Fact tables (e.g., `fct_orders`, `fct_subscriptions`)
  - `metrics_*`: Pre-aggregated governed metrics (e.g., `metrics_subscriber_churn_monthly`)

#### Context (context_*)
- **Schema**: `context`
- **Materialization**: Tables
- **Purpose**: Metadata, business events, metric changelog
- **Key models**:
  - `context_business_events`: Dated events that moved metrics
  - `context_metric_changelog`: Versioned metric definitions

### Configuration
Set in `dbt_project.yml`:
```yaml
models:
  kelder:
    staging:
      +schema: staging
      +materialized: view
    intermediate:
      +schema: intermediate
      +materialized: table
    marts:
      +schema: main
      +materialized: table
    context:
      +schema: context
      +materialized: table
```

### Reporting date
Metrics cover full months before the as-of date:
```yaml
vars:
  as_of_date: "2026-07-01"
  first_reporting_month: "2025-01-01"
```

### Related
- Wiki pages for specific models and conventions
- `context_business_events` and `context_metric_changelog` for metadata
