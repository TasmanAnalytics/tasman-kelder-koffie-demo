---
summary: Documents a data quality issue where a Recharge subscription migration on March 12 incorrectly wrote false churn events for ~1,900 paused subscriptions, with the decision to flag affected rows and report both raw and adjusted churn metrics for March 2026.
usage_mode: auto
tags:
  - data quality
  - migration
  - churn metrics
  - Recharge
  - billing
sl_refs:
  - Recharge
connections:
  - kelder
---

# 0007: Recharge migration wrote false churn events

Date: 2026-03-14 · Status: accepted · Owner: Sanne (data)

## Context

The 12 March billing migration backfilled Recharge subscription
statuses. Recharge has no "paused" state in the legacy import path,
so ~1,900 paused subscriptions arrived as "cancelled", writing
churned_at timestamps that never happened.

## Decision

Flag affected rows with is_migration_artifact = true. Exclude
flagged rows from churn metrics. Report both raw and adjusted
churn for March 2026 in any board-facing number.

## Rejected alternative

Deleting the rows. Finance reconciles against Recharge exports,
so the raw record must match source.

## Consequences

March raw churn (9.4%) and adjusted churn (3.3%) will both exist.
Anyone quoting March churn without the adjustment is wrong.
