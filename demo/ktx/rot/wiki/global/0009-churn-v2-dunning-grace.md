---
summary: Defines Churn v2 methodology effective May 1, 2026, which counts failed payments as churn only if unrecovered within 30 days, replacing v1 which counted failures immediately, with parallel as-reported and restated historical series for comparison.
usage_mode: auto
tags:
  - churn
  - dunning
  - payment recovery
  - metrics definition
  - financial reporting
connections:
  - kelder
---

# 0009: Churn v2, 30-day dunning grace

Date: 2026-04-28 · Status: accepted · Owner: Sanne (data), agreed with Femke (finance)

## Context

Under v1 a failed payment counts as churn on the day it fails.
Recharge dunning retries recover a material share of failed
payments within 30 days, so v1 overstated losses.

## Decision

From 1 May 2026, a failed payment counts as churn only if it is
not recovered within 30 days, attributed to the month of the
first failure. The as-reported series keeps v1 for months before
May. A restated v2 series covers all months for like-for-like
comparisons.

## Rejected alternative

Silently restating all history under v2, because board decks had
already quoted v1 figures.

## Consequences

- Churn falls on 1 May for definitional reasons, by roughly half a
  percentage point on Q1 2026 recoveries.
- Comparisons across 1 May must use the restated series.
- The most recent month is provisional under v2 until 30 days have
  passed, and will be revised upward.
