<!-- written workspace, run 1 of 3, model claude-opus-5-5, 6 turns. All three runs reached the same outcome. Transcript: demo/runs/written/churn_spike_why/1.json -->

> Why did subscriber churn spike in March 2026?

The March spike wasn't real churn. It came from the billing migration, not from customers leaving.

**March 2026 churn was 9.40% raw (2,932 churned) but 3.30% adjusted (1,029 churned out of a base of 31,194), both under the v1 definition. The adjusted 3.30% is the real number.**

**What caused it:** On 12 March 2026, billing moved from Shopify to Recharge (`context.business_events`, source `context/decisions/0007`). The old import had no "paused" state, so 1,903 paused subscriptions were written as cancelled at 2026-03-12 00:00 UTC. They are flagged `is_migration_artifact` and left out of adjusted churn. Those 1,903 records account for the entire gap between the raw 2,932 and the adjusted 1,029. The raw figure matches Recharge exports, which is probably why it's being quoted, but it should never be shown without the adjusted rate.

**Once adjusted, March looks like a normal month:**

| Month | Def. | Adjusted (as reported) | Raw | v2 restated |
|---|---|---|---|---|
| Dec 2025 | v1 | 3.10% | 3.10% | 2.58% |
| Jan 2026 | v1 | 3.40% | 3.40% | 2.82% |
| Feb 2026 | v1 | 3.00% | 3.00% | 2.55% |
| **Mar 2026** | v1 | **3.30%** | **9.40%** | **2.77%** |
| Apr 2026 | v1 | 2.80% | 2.94% | 2.33% |

On the like-for-like restated v2 series, March (2.77%) falls between January and February. There was no real rise in customer churn.

**If you compare with later months:**
- The definition changed to v2 on 1 May 2026 (decision 0009), so use the v2 restated column when comparing across that date.
- Churn fell from April onward. The likely reason is the pause-instead-of-cancel flow launched on 28 March 2026 (Linear KEL-412).
- June 2026 (1.79%) is provisional and will be revised upward, because failed payments younger than 30 days don't count yet.

**What I checked:** the `churn_march_2026` verified query, `metrics_subscriber_churn_monthly` for Dec 2025 to Jun 2026, and `context.business_events` for mid-February to mid-April 2026.
