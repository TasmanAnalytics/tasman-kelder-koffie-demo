<!-- installed workspace, run 1 of 3, model claude-opus-5-5, 24 turns. All three runs reached the same outcome. Transcript: demo/runs/installed/email_revenue_april/1.json -->

> Email-attributed revenue dropped in April 2026. What happened?

The drop comes from missing tracking data, not a real fall in email performance. Klaviyo sent no events into the warehouse for about 31 hours on 9–10 April, and that window included the weekly Thursday campaign. Almost none of that campaign's revenue got attributed to email.

**The gap in the raw data**
- `raw_klaviyo.events` has nothing between **9 Apr 07:34 and 10 Apr 15:01**.
- The 9 April campaign "Nieuwe oogst: Kenya Nyeri" (`000022`) was sent at 10:00 to 55,437 people and is marked "Sent" in `raw_klaviyo.campaigns`. It has **zero** "Received Email" events. The other campaigns have about 55k each.
- It only has 661 opens and 45 clicks, all recorded after tracking resumed. Normal campaigns get about 22k opens and 1.5k clicks.

**Effect on the metric (`metrics_email_attribution_daily`)**
The metric only credits an order to email if the same person clicked an email in the five days before it. With the 9 April clicks missing, orders over the next several days also lost their credit.

| Week | Email-attributed revenue |
|---|---|
| 2–8 Apr (normal campaign week) | €6,747 |
| **9–15 Apr (the gap)** | **€353** |
| 16–22 Apr | about €6,100 |

That's roughly **€6k–6.5k of missing attributed revenue**.

**The campaign itself worked normally.** Shopify's own UTM tracking in `fct_orders.channel` shows 164 email-channel orders on 9 April, against 174 on 2 April and 160 on 16 April. Customers bought as usual; Klaviyo just didn't record it.

**Why it looks like a drop even though April is up on March:** April reported €24.4k against €22.9k in March. But April had five campaign Thursdays and only four were recorded. With the missing week added back, April would be about **€30.5k**, the best month in the data. Every campaign-day number around it (€4.2k–5.2k each) is in the normal range, and nothing else changed: send volume, click rate (~2.8%) and the share of orders credited to email are all steady.

**Separate issue on the same day:** Shopify's 05:00 subscription-renewal batch on 9 April had only 172 orders instead of about 1,400. About 2,300 went through on 10 April instead. It doesn't affect email attribution, which is based on web orders, but it's probably worth asking whoever runs the store what happened that day.

**What to do**
1. Check the Fivetran Klaviyo connector's sync logs for 9–10 April and run a historical re-sync for that window. If Klaviyo still has the events, rebuilding the metric should fill in the missing revenue.
2. Add a check that flags when a campaign marked "Sent" has no "Received Email" events, or when a day has almost no events, so a gap like this gets caught.
3. Until the data is fixed, add a note to April reporting. Shopify's email-channel orders can serve as a rough stand-in for 9–10 April.
