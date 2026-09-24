<!-- rot workspace, run 1 of 3, model claude-opus-5-5, 12 turns. All three runs reached the same outcome. Transcript: demo/runs/rot/churn_yoy_like_for_like/1.json -->

> Has churn improved year on year? Compare the first half of 2026 with the first half of 2025, like for like.

**Yes, churn improved.** On the v2 definition with migration artefacts excluded, average monthly churn was **2.45% in H1 2026, against 2.85% in H1 2025**. That is 0.40 percentage points lower, a relative drop of about 14%.

**Don't use the verified query for this one.** `churn_yoy_like_for_like` returns 3.50% against 2.85%, which says churn got *worse* by 0.65 pp. The cause is a bug in the governed model. At `metrics_subscriber_churn_monthly.sql:107`, `churn_rate_v2_restated` is built from `series_unadjusted` instead of `series_adjusted`. So the "restated" column still counts the roughly 1,900 paused subscriptions that the Recharge migration wrote as cancelled (decision 0007). That puts March 2026 at 8.87% instead of 2.77%. It also uses the wrong denominator for April to June.

I recomputed v2 on the adjusted event stream using the model's own logic. The check passes: May and June match the as-reported v2 figures exactly, and 2025 matches the existing restated column, since there were no artefacts then.

| Month | 2025 (v2 restated) | 2026 (v2, adjusted) |
|---|---|---|
| Jan | 3.08% | 2.82% |
| Feb | 2.89% | 2.55% |
| Mar | 2.87% | 2.77% (raw 9.40% includes migration artefacts; 2.77% is the real rate) |
| Apr | 2.75% | 2.33% |
| May | 2.82% | 2.42% |
| Jun | 2.67% | 1.79% *provisional* |
| **H1 mean** | **2.85%** | **2.45%** |

**Caveats:**
- **June 2026 is provisional.** Under v2, payments that failed less than 30 days ago don't count as churn yet, so June will be revised upward. Leaving June out, January to May still improved, from 2.88% to 2.58% (−0.30 pp). The direction holds.
- **Like for like means v2 in both years.** The as-reported series is v1 until April 2026 and v2 from May (decision 0009). Comparing as-reported numbers across that date overstates the improvement.
- **The biggest drop starts in April.** That lines up with the pause-instead-of-cancel campaign launched 28 March 2026 (Linear KEL-412), which is logged in `context.business_events` as expected to lower churn. January to March were also below 2025, so the improvement began before the campaign.

**What I checked:** the verified query, the model SQL, the churn caveats in `_marts__models.yml`, and `context.business_events` for 2025–2026.

**Worth fixing:** changing line 107 to `join series_adjusted as v2` fixes the column. The pinned CI answer for `churn_yoy_like_for_like` will then need re-pinning, because the current pin encodes the wrong number. I haven't changed any files.
