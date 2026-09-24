---
summary: A changelog documenting the evolution of the subscriber_churn_rate metric, tracking definition changes and their effective dates from January 2025 onwards, including adjustments to how failed payments are counted in churn calculations.
usage_mode: auto
tags:
  - metric
  - churn
  - changelog
  - subscriber
  - definition
  - versioning
sl_refs:
  - subscriber_churn_rate
connections:
  - kelder
---

# Metric changelog

Generated from `seeds/context/metric_changelog.csv` by `scripts/render_metric_changelog.py`.
Do not edit by hand. The same rows are in the warehouse as `context.metric_changelog`.

## subscriber_churn_rate

| Version | Valid from | Definition | Reason for change |
|---|---|---|---|
| v1 | 2025-01-01 | Cancelled in month / active at month start. Failed payments count as churn on day one | Initial definition |
| v2 | 2026-05-01 | As v1, with a 30-day dunning grace before a failed payment counts as churn | Recharge dunning recovers a material share of failed payments; day-one counting overstated losses |
