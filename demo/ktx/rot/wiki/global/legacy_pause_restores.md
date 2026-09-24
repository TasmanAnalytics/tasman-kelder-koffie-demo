---
summary: Documents the legacy pause restoration process following the 12 March billing migration, which converted paused Shopify subscriptions to cancelled Recharge subscriptions, and describes how operations re-creates these subscriptions and how they should be treated in analytics.
usage_mode: auto
tags:
  - billing migration
  - pause restoration
  - Recharge subscriptions
  - data lineage
  - subscription events
sl_refs:
  - fct_subscriptions
  - int_subscription_events_adjusted
  - metrics_new_subscribers_monthly
  - metrics_cac_monthly
connections:
  - kelder
---

# Legacy pause restores

Owner: Sanne (data). Written 2026-03-17.

## What happened

The 12 March billing migration wiped every pause: subscriptions that were paused at the last
Shopify sync arrived in Recharge as cancelled (decision 0007). Those customers still expected
coffee when their pause ended.

From 16 March an operations job re-creates each affected subscription on the original
`pause_until` date, as a new Recharge subscription:

- same customer, plan and product;
- status `active`, `created_at` at the job's run time, 09:15 Amsterdam time on weekdays;
- `properties` contains `{"restore_source": "legacy_pause", "legacy_contract_id": "<Shopify contract id>"}`;
- first charge at the next 05:00 billing run.

Subscriptions whose pause ends after the end of the data are not restored yet.

## How to treat them

- A restore is a continuation, not a new subscriber. `fct_subscriptions.is_legacy_pause_restore`
  flags it and `continues_subscription_key` points at the original subscription.
- The adjusted event stream (`int_subscription_events_adjusted`) moves the restore's events to the
  original key. The original subscription counts as paused from its Shopify pause until the
  restore is created.
- `metrics_new_subscribers_monthly` and `metrics_cac_monthly` exclude restores.
- A naive count of Recharge subscriptions created in March to June counts restores as new
  subscribers. That overstates acquisition by roughly 1,600 subscriptions.
