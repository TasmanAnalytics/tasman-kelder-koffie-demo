<!-- installed workspace, run 1 of 3, model claude-opus-5-5, 27 turns. All three runs reached the same outcome. Transcript: demo/runs/installed/churn_spike_why/1.json -->

> Why did subscriber churn spike in March 2026?

The March spike isn't real customer churn. It comes from the Shopify → Recharge subscription migration.

**The numbers**

| Month | Base | Churned | Churn rate |
|---|---|---|---|
| Jan 2026 | 29,266 | 995 | 3.4% |
| Feb 2026 | 30,492 | 915 | 3.0% |
| **Mar 2026** | **31,194** | **2,932** | **9.4%** |
| Apr 2026 | 30,304 | 891 | 2.9% |

**What caused it**
- Every normal churn reason held steady in March: payment failures, max retries reached, too expensive, too much coffee, and so on. The entire excess is **2,045 cancellations with no cancellation reason**. That bucket appears in no other month.
- All 2,045 happened in the same minute: **12 March 2026, 01:00 Amsterdam time**. The raw Recharge event log shows the migration job creating each subscription (from its Shopify contract ID) and cancelling it in that same minute, with `cancellation_reason: null`.
- **1,903 of the 2,045 (93%) were paused** Shopify subscriptions. It looks like the migration couldn't carry paused subscriptions over, so it cancelled them.
- The pipeline records any cancellation with no reason as voluntary, so the governed metric counted all of these as voluntary churn.

**Most came back**
- 1,619 were later recreated in Recharge, marked `restore_source = "legacy_pause"` and linked to the original contract. Nearly all have the same coffee and delivery interval.
- These restores happened gradually from mid-March to June, which fits customers coming back when their pause ended. 1,532 are still active today.

**Corrected picture**
- Without the 2,045 migration cancellations, March churn was **887 / 31,194 ≈ 2.8%**. That's in line with the months on either side.

**Things to watch**
1. **About 426 may be real losses caused by the migration.** 284 were paused but never restored, and 142 weren't paused at all but were cancelled anyway (118 active, 20 recently resumed, 4 that had just recovered from a failed payment). It's worth checking whether they were contacted.
2. **Other metrics are also off.** The 1,619 restored subscriptions start as new Recharge subscriptions, so they probably inflate new-subscriber counts from March to June. They were also dropped from the base, which is part of why April's base fell to 30,304. That may flatter the churn rates for April to June.
3. **Pipeline fix.** Migration cancellations should be excluded from `metrics_subscriber_churn_monthly`, or given a system reason instead of being treated as voluntary. Each restored subscription should also be linked back to its original contract.

Two limits: I confirmed the batch job from the timestamps and event data, not from any migration notes or runbook. And "likely inflates new-subscriber counts" is an inference that I didn't check against `metrics_new_subscribers_monthly`.
