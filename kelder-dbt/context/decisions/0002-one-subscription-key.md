# 0002: One subscription key, status unified in one model

Date: 2025-01-16 · Status: accepted · Owner: Sanne (data)

A subscription keeps one key for its whole life. Statuses from the billing systems are mapped to
active, paused, cancelled and expired in `int_subscriptions_unified` and nowhere else. Every other
model reads the unified status or the event stream.
