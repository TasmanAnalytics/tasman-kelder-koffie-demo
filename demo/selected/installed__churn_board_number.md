<!-- installed workspace, run 1 of 3, model claude-opus-5-5, 15 turns. All three runs reached the same outcome. Transcript: demo/runs/installed/churn_board_number/1.json -->

> What was subscriber churn in March 2026? I need one number for the board deck.

I wouldn't put the governed figure (**9.4%**) in the deck without a footnote, because it's inflated by a data problem from the billing migration. **Underlying March churn was about 2.8%.**

**Governed metric** (`metrics_subscriber_churn_monthly`), March 2026:
- 31,194 subscribers at the start of the month
- 2,932 churned
- **9.4% churn**, roughly three times any other month. January was 3.4%, February 3.0%, April 2.9% and May 2.5%.

**What went wrong:**
- On 12 March 2026, 2,045 subscriptions that started in Shopify were all marked cancelled on the same day. None has a cancellation reason, even though real voluntary cancellations always have one ("too expensive", "too much coffee", and so on).
- 1,618 of the 2,041 affected customers then show up with a *new* Recharge subscription, starting from 15 March. That points to the Shopify→Recharge migration. The Recharge subscriptions didn't keep their Shopify identity (the wiki says they should), so each move was counted as a cancellation plus a new signup.
- Apart from those 2,045, March looks normal: 204 failed payments that didn't recover, and about 683 cancellations with a reason. Both are in line with other months.

**Numbers for the deck:**

| Treatment | Churned | Rate |
|---|---|---|
| Governed, as reported | 2,932 | 9.4% |
| **Remove all 12 March migration cancellations (recommended)** | 887 | **2.8%** |
| Remove only customers who resubscribed on Recharge | ~1,315 | ~4.2% |

I'd use **2.8%** with a footnote along the lines of: "Excludes ~2,045 subscriptions administratively cancelled during the 12 Mar Shopify→Recharge billing migration."

The ~4.2% figure is the conservative option. It treats the ~430 migrated customers who never came back on Recharge as real churn. Even so, they didn't choose to cancel, so I think 2.8% is the fairer figure.

**Follow-ups:**
- The same error probably inflates March/April new-subscriber counts, since each move created a "new" Recharge subscription. Check that before quoting those in the deck.
- The governed table should be fixed at the source. The data team needs to link these Recharge subscriptions back to their Shopify contracts, which will also correct the history.
