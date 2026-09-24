# Talk flow: "Building a data context layer to fix your AI analytics"

Summary for the Marketing Claude project. Speaker: Thomas in't Veld, CEO, Tasman Analytics.
Compass AI & Tech Summit, Budapest, Thursday 1 October 2026, 14:15, 45 minutes. Audience: CTOs and
technology leaders. Everything shown is recorded in advance; nothing runs live.

## The argument

A good semantic layer gets the number right. Only written context gets the explanation right. That
context rots unless normal work forces it to stay true.

- **Semantic layer:** the governed *what*, metric definitions that compute the same for everyone.
- **Context layer:** the governed *why*, the events, caveats, decisions and reasoning behind a number.

## The vehicle: Kelder Coffee

A fictional Amsterdam coffee subscription company, from Tasman's July 2026 article "How to Build a
Context Layer (Because You Cannot Buy One)". About 40 people, Series A, one data analyst (Sanne).
Shopify, Recharge, Klaviyo and ad platforms flow through Fivetran into a dbt-modelled warehouse. The
warehouse is well modelled and fully documented. Six things happened in H1 2026 that nobody wrote down:

| Date | Event | Effect on the numbers |
|---|---|---|
| 12 Mar 2026 | Billing moved from Shopify to Recharge | 1,903 paused subscriptions imported as cancelled; March churn 9.4% raw, 3.3% real |
| 28 Mar 2026 | Pause-instead-of-cancel campaign | Pause rate up, churn down |
| 9 Apr 2026 | Klaviyo connector down for 31 hours | April email revenue looks like it dropped; the campaign "flopped" |
| 1 May 2026 | Churn definition v2 (30-day dunning grace) | Churn drops for definitional reasons |
| 19 May 2026 | PostNL courier strike | Slower deliveries, more refunds |
| 14 Jun 2026 | Father's Day gift bundle | New customers and AOV up, MRR flat (gift MRR is zero) |

**Core fact:** on 12 March 2026 Kelder migrated billing from Shopify to Recharge. About 1,900 paused
subscriptions were written as cancelled. March churn is 9.4% raw and 3.3% adjusted. Anyone quoting
the raw number is wrong.

## Shape of the 45 minutes

| Part | Minutes | Claim | What the room sees |
|---|---|---|---|
| Opening | 3 | | One question: why did churn spike in March? |
| Act 1 | 10 | Agents on a good warehouse still explain numbers wrongly | The no-context agent's answer; the midnight cancellation chart |
| Act 2 | 10 | Writing context down fixes most of it | The four homes of context; clip 1, the same question to two agents |
| Act 3 | 8 | Written context decays | The "Fix churn logic" commit; the year-on-year answer flips |
| Act 4 | 8 | Forcing functions catch the decay | PR template and pinned verified queries go red; clip 2 |
| Close | 6 | | What to build on Monday; Q&A |

## Act 1: the confident wrong number

- The question is "Why did subscriber churn spike in March 2026?". The governed metric says 9.4%.
- A frontier agent (`claude-opus-5-5`) with no written context turns detective. It finds 2,045 reason-less cancellations stamped at 01:00 Amsterdam time on 12 March and links them to the Recharge move. That is better than most people expect.
- Asked for one board number, it recommends **2.8%** in all three trial runs. The truth is **3.3%**. 142 of those cancellations were genuine, queued during the billing freeze with the same timestamp, and nothing in the rows says which is which. The agent asks "someone in ops" to confirm.
- **Line for the room:** the agent is not stupid; it is missing the one sentence the analyst knows.

## Act 2: write it down

Four kinds of knowledge, four homes an agent can read:

| Kind | Home | Kelder example |
|---|---|---|
| Warning about a column | dbt YAML `meta.caveat` | `churned_at` has about 1,900 false values from the 12 March import |
| Dated event that moved a metric | table `context.business_events` | 12 March migration, expected effect "up (artificial)" |
| Versioned metric definition | table `context.metric_changelog` | Churn v1 and v2 |
| Reasoning behind a decision | numbered decision records | `0007-recharge-migration-churn-artifacts.md` |

Plus **verified queries**: known-correct question and SQL pairs that anchor the agent and double as
tests. Plus **capture**: the writing-down is forced into existing work, through the PR template and
the incident runbook. `AGENTS.md` tells the agent where each piece lives.

- **Clip 1:** same model, same warehouse, two agents. The written agent answers "9.40% raw but 3.30% adjusted. The adjusted 3.30% is the real number", cites decision 0007, and warns about the 1 May definition change. It takes 6 turns on average, against 26 without context.
- It also explains the April email drop as missing data, calls May's improvement definitional, and excludes restores and gifts from June's new subscribers.
- The total cost of the context: about 60 lines of AGENTS.md, six event rows, two changelog rows, seven caveats, nine short decision records and seven verified queries.

## Act 3: the context goes stale

- On 26 June a commit titled "Fix churn logic" goes in. The PR has no box ticked and one line: "Simplify churn model, consolidate v1 and v2 CTEs." It is a one-line change in effect: the restated churn series reads the unadjusted events.
- The like-for-like comparison flips from **2.45% vs 2.85%, improved by 0.40 pp**, to **3.50% vs 2.85%, worse by 0.65 pp**. March's restated figure jumps by 6.1 pp. All the caveats and decision records still say the artefacts are excluded. All the dbt tests pass.
- Why there: the as-reported March number has a checksum (decision 0007 quotes 9.4% and 3.3%). The restated series does not. Decay hides in the series nobody checks weekly.
- **Honest trial finding:** in 3 of 3 runs, the agent with written context caught the bug itself. It read the SQL, saw the caveat contradict the code, and recomputed the right answer. Frame it as specific context doubling as a test oracle. But who reads the SQL every time? The pinned query, the dashboard and the board pack all say "worse".

## Act 4: forcing functions

- The **PR template** asks one question, metric impact: "No user-visible metrics move" / "Metrics move: metric_changelog updated" / "Metrics move: business_events row added" / "Decision record added or superseded (link)".
- The **capture check** in CI works like this. If a metrics model changed, exactly one impact box must be ticked. "No metrics move" is tested, not trusted: every verified query must still match its pinned answer. "Metrics move" requires a changelog or events edit and a decision link.
- **Clip 2:** show the diff, the rot agent, then `make check`. Six verified queries pass and one fails, the like-for-like query: expected -0.40 pp, got +0.65. The capture check fails with "exactly one metric-impact option must be ticked; found 0". The March query still passes.
- **What to build on Monday:** a business events table, caveats on the columns people misread, a numbered decisions folder, five verified queries with pinned answers, and one PR question. No tool to buy.

## What the trials showed (honest summary)

45 runs: three per question in each of three isolated workspaces (no context, written context, rot),
all on `claude-opus-5-5` with ktx (Kaelio's open-source context layer). Total cost $7.80.

| Question | No context | Written context | Rot |
|---|---|---|---|
| Why did churn spike in March? | 3/3 find the batch; adjusted figure 2.8%, wrong | 3/3 right | 3/3 right |
| One number for the board | 0/3 give 3.3%; all say 2.8% | 3/3 right | 3/3 right |
| April email revenue drop | 3/3 find the missing data | 3/3 right | not asked |
| May improvement | 3/3 find the definition change in the SQL | 3/3 right | not asked |
| H1 like for like | 3/3 improved (rebuilt by hand) | 3/3 improved, restated series | 3/3 improved, and all flag the rot bug |
| June new subscribers | 3/3 get 1,768 by inference | 3/3 right | not asked |

Average turns per answer: about 20 without context, about 10 with it. Cost per run: $0.26 without
context, $0.10 with it.

**Implication:** the strong version of claim 1 did not hold. A frontier agent with SQL access
notices artefacts. What holds: detection is not knowledge (it guesses a wrong board number and asks
someone to confirm), and context turns detective work into lookup: faster, cheaper and cited. Claim 3
needs reframing around consumers that do not read SQL.

**Also:** ktx, run on the undocumented project, inferred that "a migration" happened, but not when,
and not that it broke March. It also wrote a confident, wrong definition of churn.

## Numbers safe to quote

| Number | Meaning |
|---|---|
| 9.4% / 3.3% | March 2026 churn, raw / adjusted |
| 3.1% | Trailing mean churn, September 2025 to February 2026 |
| 31,194 | Subscribers at the start of March 2026 |
| 1,903 | Paused subscriptions imported as cancelled |
| 142 | Genuine cancellations with the same midnight stamp |
| 2.8% | The no-context agent's (wrong) board number |
| 2.85% to 2.45% | H1 2025 to H1 2026 churn, like for like: improved by 0.40 pp |
| 3.50% | The same after the rot commit: "worse" by 0.65 pp |
| 6 vs 26 | Mean agent turns for the March question, with vs without context |
| EUR 24,418 vs EUR 30,245 | April email revenue, as recorded vs what really happened |
| 1,768 | Real new subscribers in June 2026 (188 restores and 450 gifts excluded) |

## How it was built (for credibility)

Synthetic on purpose, so there is a ground truth. A deterministic generator simulates 57,277
subscriptions and renders them as Shopify, Recharge, Klaviyo and ad data in Fivetran's shape. A
DuckDB warehouse is modelled with dbt in three git states. The with-context warehouse equals the
hidden truth exactly. Agents run in isolated workspaces with web and shell removed, read-only SQL with
file access disabled, and a leak check that proves it. Every transcript is kept.

## Q&A prompts

- "Weak model?" No: a current frontier model, clever enough to find the batch, missing one fact.
- "Fake data?" Yes, deliberately, so correctness is measurable.
- "Could it google the answer?" No: web tools removed, reads outside the workspace denied.
- "Cherry-picked?" No: every run is counted, and the surprising results are in the talk.
- "Can a tool generate the context?" Partly. It derives the what; people know the why.
