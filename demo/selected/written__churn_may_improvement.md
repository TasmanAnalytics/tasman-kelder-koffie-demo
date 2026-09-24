<!-- written workspace, run 1 of 3, model claude-opus-5-5, 8 turns. All three runs reached the same outcome. Transcript: demo/runs/written/churn_may_improvement/1.json -->

> Churn improved in May 2026. What drove the improvement?

Churn didn't really improve in May 2026. The drop comes from a change in how churn is counted, not from customer behaviour. On a like-for-like basis, May churn was slightly worse than April.

| Month | Churn as reported | Definition | v1 (old definition) | v2 restated (like-for-like) |
|---|---|---|---|---|
| Mar 2026 | 3.30% adjusted (9.40% raw) | v1 | 3.30% | 2.77% |
| Apr 2026 | 2.80% | v1 | 2.80% | 2.33% |
| **May 2026** | **2.42%** | **v2** | **2.90%** | **2.42%** |
| Jun 2026 | 1.79% (provisional) | v2 | 2.80% | 1.79% (provisional) |

- **Why it looks better:** As reported, churn fell from 2.80% in April (v1) to 2.42% in May (v2). But the definition changed on 1 May 2026 (decision 0009, "Churn v2: 30-day dunning grace"). Under v2, a failed payment only counts as churn if it isn't recovered within 30 days, so the new series is lower by design. The business events table lists this change with the expected effect "down (definitional)".
- **Like-for-like, churn rose:** On the restated v2 series, churn went from 2.33% in April to 2.42% in May, up about 0.09 points. Under the old v1 definition it also rose, from 2.80% to 2.90%. So the whole reported drop, and more, is definitional.
- **The real improvement came earlier, in April:** On the restated series, churn fell from 2.77% in March to 2.33% in April. That matches the pause-instead-of-cancel campaign started on 28 March 2026 (Linear KEL-412), which added a pause option to the Recharge cancel flow. The timing lines up, but I haven't shown the campaign caused the drop. Checking pause rates and cancel-flow outcomes would test that.
- **March figures:** The raw March rate of 9.40% is inflated by the 12 March billing migration, which wrote about 1,900 paused subscriptions as cancelled (decision 0007). The adjusted 3.30% is the real number, and it's what the table uses.
- **Don't read June's 1.79% as a win yet:** June is provisional. Failed payments younger than 30 days don't count yet, so it will be revised upward. On the old v1 definition June is 2.80%, roughly flat.

If someone is presenting May as a churn improvement, they're comparing v1 to v2. Use `churn_rate_v2_restated` for that comparison.

I checked `metrics_subscriber_churn_monthly` (as-reported, v1 and restated v2 columns, and the provisional flag), the `context.business_events` table for March to June 2026, and the column caveats in `_marts__models.yml`.
