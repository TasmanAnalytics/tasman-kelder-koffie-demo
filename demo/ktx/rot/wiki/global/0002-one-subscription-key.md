---
summary: Establishes that subscriptions maintain a single key throughout their lifecycle, with billing system statuses unified into four states (active, paused, cancelled, expired) in the int_subscriptions_unified model, serving as the authoritative status source for all downstream models.
usage_mode: auto
tags:
  - subscriptions
  - status mapping
  - billing systems
  - data modeling
  - unified state
sl_refs:
  - int_subscriptions_unified
connections:
  - kelder
---

# 0002: One subscription key, status unified in one model

Date: 2025-01-16 · Status: accepted · Owner: Sanne (data)

A subscription keeps one key for its whole life. Statuses from the billing systems are mapped to
active, paused, cancelled and expired in `int_subscriptions_unified` and nowhere else. Every other
model reads the unified status or the event stream.
