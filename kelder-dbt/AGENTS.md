# AGENTS.md: Kelder analytics

You are answering questions about Kelder Coffee's numbers: an Amsterdam coffee subscription
company (single-origin coffee on subscription, plus one-off retail). The warehouse holds Shopify,
Recharge, Klaviyo and ad platform data, modelled by this dbt project.

## As-of date

Answer as of **2026-07-01**. The data ends on 30 June 2026. "Last month" means June 2026.
Months start at 00:00 Amsterdam time. Raw timestamps are UTC.

## Where context lives

| Kind of knowledge | Where |
|---|---|
| Warnings about a column or model | `meta.caveat` in the dbt YAML (`models/**/_*.yml`) |
| Dated events that moved a metric | warehouse table `context.business_events` |
| Metric definitions and versions | `context.metric_changelog`, rendered in `context/metric_changelog.md` |
| Reasoning behind decisions | `context/decisions/NNNN-*.md` |
| Terms | `context/glossary.md` |
| Data quirks | `context/quirks/*.md` |
| Known-correct SQL | `context/verified_queries.yml` |

## Rules

1. **Check `context.business_events` before explaining any anomaly.** A spike, drop or gap may be
   a migration, an outage, a definition change, a promotion or a logistics problem, not customer
   behaviour. Name the event and its source link if one explains the anomaly.
2. **Use the governed metrics** (`metrics_*` models) for reported numbers. Do not recompute churn,
   new subscribers or email-attributed revenue from raw tables.
3. **Start from `context/verified_queries.yml`** when a question matches or is close to one there.
4. **Read the caveats** on every column you use.

## Churn

- On 12 March 2026 billing moved from Shopify to Recharge. The legacy import had no paused state,
  so about 1,900 paused subscriptions were written as cancelled at 2026-03-12 00:00 UTC. They are
  flagged `is_migration_artifact` and excluded from churn (decision 0007).
- **For March 2026, always report raw and adjusted churn together**, and say which is real
  (adjusted). Anyone quoting the raw number alone is wrong.
- The churn definition changed on 1 May 2026 (decision 0009): v1 before May, v2 from May.
  **Name the definition version** whenever you compare months across 1 May 2026, and use the
  restated series (`churn_rate_v2_restated`) for like-for-like comparisons. A drop in May 2026 in
  the as-reported series is mostly definitional.
- **The latest month is provisional** under v2 (`is_provisional`): failed payments younger than
  30 days do not count yet, so it will be revised upward. Say so.

## Subscribers and revenue

- **Gift subscriptions have zero MRR** by design and sit outside the churn base (decision 0006).
- **Restores are not new subscribers.** From 16 March 2026 operations re-created wiped pauses as new
  Recharge subscriptions (`is_legacy_pause_restore`). They continue the original subscription
  (decision 0008). `metrics_new_subscribers_monthly` already excludes them.
- **Email-attributed revenue** has a gap: no Klaviyo data from 2026-04-09 06:00 UTC to
  2026-04-10 13:00 UTC. Days 9 to 15 April 2026 are understated. Shopify orders are complete.
- **Delivery times and refunds** in the week of 18 to 24 May 2026 are affected by a PostNL strike.

## How to answer

- Give the number, the definition version and any adjustment in the same sentence.
- Say what you checked (tables, caveats, events) in one line.
- If the data cannot answer the question, say what is missing instead of guessing.
