# Metric changelog

Generated from `seeds/context/metric_changelog.csv` by `scripts/render_metric_changelog.py`.
Do not edit by hand. The same rows are in the warehouse as `context.metric_changelog`.

## subscriber_churn_rate

| Version | Valid from | Definition | Reason for change |
|---|---|---|---|
| v1 | 2025-01-01 | Cancelled in month / active at month start. Failed payments count as churn on day one | Initial definition |
| v2 | 2026-05-01 | As v1, with a 30-day dunning grace before a failed payment counts as churn | Recharge dunning recovers a material share of failed payments; day-one counting overstated losses |
