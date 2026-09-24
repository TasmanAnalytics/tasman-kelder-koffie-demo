<!-- written workspace, run 1 of 3, model claude-opus-5-5, 6 turns. All three runs reached the same outcome. Transcript: demo/runs/written/churn_board_number/1.json -->

> What was subscriber churn in March 2026? I need one number for the board deck.

**For the board deck, March 2026 churn was 3.3%** (v1 definition, excluding migration artefacts). 1,029 of 31,194 base subscribers churned.

- **Raw vs. adjusted:** The raw figure is 9.4% (2,932 churned), and it matches the Recharge exports. It is inflated because the billing move from Shopify to Recharge on 12 March 2026 wrote 1,903 paused subscriptions as cancelled. They weren't real cancellations, so they are excluded under decision 0007 (`context/decisions/0007`). The real rate is 3.3%. If anyone brings up the 9.4% from Recharge, this is the explanation.
- **Definition version:** 3.3% uses the v1 definition, which applied before 1 May 2026. If the same slide shows May or June 2026 (v2), use the v2 restated figure for March, **2.8%**, so the months are comparable (decision 0009). If March appears on its own, 3.3% is the right number.

**What I checked:** the governed `metrics_subscriber_churn_monthly` model, using the `churn_march_2026` verified query; the 2026-03-12 migration event in `context.business_events`; and the caveats on `churned_at` and the churn metric in `_marts__models.yml`.
