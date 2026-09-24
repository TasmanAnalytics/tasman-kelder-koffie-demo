---
summary: Gift subscriptions are prepaid for three shipments and excluded from subscriber metrics
usage_mode: auto
sort_order: 0
tags:
  - subscriptions
  - metrics
sl_refs:
  - fct_subscriptions
  - fct_subscription_events
---

## Gift Subscriptions

### Definition
Gift subscriptions are **prepaid** subscriptions purchased as gifts. They:
- Are paid once at purchase for three shipments
- Have `is_gift = true` in `fct_subscriptions` and `fct_subscription_events`
- Have `mrr_eur = 0` by design (no recurring revenue)

### Exclusion Rules
**Always exclude gift subscriptions from**:
- Subscriber base counts (active, paused, cancelled)
- Churn metrics
- MRR calculations
- New subscriber counts
- Acquisition metrics (CAC, channel attribution)

### Identification
Filter with `is_gift = false` or use the `non_gift` segment on `fct_subscriptions`.

### Source
See `context/quirks/gift_subscriptions.md` for the full business logic.
