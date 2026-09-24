---
summary: Defines that paused subscriptions are not counted as churn and remain in the subscriber base; churn is only recorded when a subscriber cancels after a pause.
usage_mode: auto
tags:
  - subscriptions
  - churn
  - pause
  - retention
  - metrics
connections:
  - kelder
---

# 0003: A pause is not churn

Date: 2025-02-11 · Status: accepted · Owner: Sanne (data)

Paused subscriptions stay in the base and never count as churned. A subscriber who cancels after a
pause churns in the month of the cancellation.
