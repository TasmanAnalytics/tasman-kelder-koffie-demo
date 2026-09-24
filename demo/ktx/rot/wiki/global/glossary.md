---
summary: A glossary defining key subscription and revenue metrics including base, churn (with versioned definitions), MRR, pause, gift subscriptions, restores, and email-attributed revenue, with notes on data adjustments and calculation methodologies.
usage_mode: auto
tags:
  - subscription metrics
  - churn
  - MRR
  - glossary
  - definitions
  - billing
  - Recharge
  - Klaviyo
connections:
  - kelder
---

# Glossary

Owner: Sanne (data). Metric definitions live in `metric_changelog.md`; this page explains the terms.

**Base.** Subscriptions in status active or paused at 00:00 Amsterdam time on the first day of the
month. Gift subscriptions are never in the base.

**Churn.** Churned in the month divided by the base. Churned means voluntary cancellations in the
month plus failed payments, counted per the definition version:

- **v1** (to April 2026): a subscription whose payment first failed in the month counts as churned
  on the day of failure, whether or not a retry later recovers it.
- **v2** (from May 2026): a failed payment counts only if it is not recovered within 30 days. It is
  attributed to the month of the first failure. For the latest month, failures younger than 30 days
  at the as-of date do not count yet, so the latest month is provisional and will be revised upward.

**As reported versus restated.** The as-reported series is what we publish: v1 up to April 2026 and
v2 from May 2026. The restated series is v2 for every month. Compare months across 1 May 2026 only
with the restated series (`churn_rate_v2_restated`), otherwise you compare two definitions.

**Raw versus adjusted.** Raw counts the cancellations written by the 12 March 2026 billing migration
(about 1,900 paused subscriptions imported as cancelled). Adjusted excludes them and treats the
affected subscriptions as still paused until their restore. Adjusted is the real number. Raw exists
so finance can reconcile against Recharge exports (decision 0007).

**Pause.** A subscriber can pause for one, two, three or six months. A paused subscription is still
in the base and is not churn. Recharge has no paused status: paused means `active` with
`paused_until` set. From 28 March 2026 the cancel flow offers a pause first, so the pause rate rises.

**Gift subscription.** Prepaid for three shipments, then `expired`. Outside the base and outside
churn. MRR is zero by design (decision 0006).

**Restore.** A new Recharge subscription that operations created for a customer whose pause was wiped
by the migration (`restore_source = legacy_pause`). A restore continues the original subscription's
key and tenure. It is not a new subscriber (decision 0008).

**MRR.** Price per shipment, normalised to a month (x 365.25 / 12 / interval days), for active
subscriptions. Paused and ended subscriptions contribute zero. Gifts contribute zero.

**Email-attributed revenue.** Value of Klaviyo Placed Order events where the same profile clicked an
email in the five days before the order (decision 0004). There is no Klaviyo data from
2026-04-09 06:00 UTC to 2026-04-10 13:00 UTC, so 9 to 15 April 2026 are understated.

**New subscribers.** Subscriptions started in the month, excluding gifts and restores.

**CAC.** Paid channel ad spend in the month divided by new subscribers whose first order came through
that channel.
