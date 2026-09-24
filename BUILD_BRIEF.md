# Kelder Coffee: build brief for a context layer demo

Read this whole document before writing any code. It is self-contained and assumes no prior conversation.

"Must" is a hard requirement. "Should" means do it unless it threatens the schedule. "Could" means only if time allows. When a Kelder fact is in doubt, the published article wins; where the article is silent, this brief wins; where both are silent, choose the most realistic option and record the choice in `BUILD_LOG.md`.

---

## 1. What you are building and why

Tasman Analytics (tasman.ai) is a senior-led data consultancy in Amsterdam and London. Its CEO, Thomas in't Veld, is giving a 45-minute talk, "Building a data context layer to fix your AI analytics", at the Compass AI & Tech Summit in Budapest on Thursday 1 October 2026 at 14:15. The audience is CTOs and other technology leaders. Thomas is the person working with you on this build and the person you report to.

The talk makes four claims. This build must produce honest evidence for each one:

1. AI agents on a well-modelled warehouse still give confidently wrong explanations, because the reasons behind the numbers were never written down. They mistake data artefacts for customer behaviour, data gaps for real drops, and definition changes for business improvements.
2. Writing that context down, in plain files and warehouse tables an agent can read, fixes most of it without a better model.
3. Written context then decays. A later code change can make the context false while it still reads as authoritative, and the agent inherits the error with full confidence.
4. Forcing functions inside normal work, a pull request template and automated checks against pinned correct answers, catch that decay before it reaches anyone.

The vehicle is Kelder Coffee, a fictional Amsterdam coffee subscription company introduced in Tasman's article of July 2026, "How to Build a Context Layer (Because You Cannot Buy One)": https://www.tasman.ai/news/how-to-build-a-context-layer. Read it if you have network access. Everything you need from it is reproduced in the appendix, so you can work without it.

Kelder has no real data. You will generate it.

### Deliverables

- A deterministic synthetic data generator that reproduces every Kelder number and event in the article.
- A DuckDB warehouse loaded from that data in the shape Fivetran would produce, modelled with dbt.
- The Kelder analytics repository, `kelder-dbt/`, in three states:
  - **before-context**: a competent, documented dbt project with no context layer;
  - **with-context**: the article's end state, with all four homes of context, verified queries and the pull request template;
  - **rot**: the with-context state plus one later commit that silently breaks part of the logic while the context still claims otherwise.
- The context served to an agent through ktx, an open-source context layer, with a documented fallback.
- Isolated agent workspaces, a trial harness that asks the same questions many times and summarises the answers honestly, and scripts to record two short screen clips.
- Brand-styled charts for the slides.

Everything is recorded in advance. Nothing runs live on stage.

---

## 2. Definition of done

- [ ] `make all` on a clean clone regenerates data, builds all three warehouse states and runs every test in under 15 minutes on a recent MacBook.
- [ ] The same seed produces byte-identical raw files. A test proves it.
- [ ] Every number in "Numbers that must reconcile" is produced by the data and asserted by a test.
- [ ] In the with-context state, adjusted metrics equal the hidden ground truth exactly, numerator and denominator.
- [ ] The rot state fails exactly the checks it should fail and passes all others.
- [ ] The leak check passes for every agent workspace.
- [ ] Trials have run at least ten times per question per workspace on one pinned model. A summary table exists and every raw transcript is kept.
- [ ] Two recorded clips of at most 90 seconds each, and clean text of the final answers used on slides.
- [ ] Charts exist as SVG and as PNG at 2400×1350, each with a JSON file of the plotted values.
- [ ] `README.md` explains how to reproduce everything from scratch.
- [ ] `BUILD_LOG.md` records every deviation from this brief and every judgement call.

---

## 3. Background

### 3.1 What a context layer is

A **semantic layer** is the governed *what*: metric definitions that compute the same for everyone. A **context layer** is the governed *why*: the events, caveats, decisions and reasoning that explain why a number is what it is. An agent on a good semantic layer gets the number right and the explanation wrong.

Context comes in four shapes, and each has a natural home:

| Kind of knowledge | Home | Example at Kelder |
|---|---|---|
| Static warning about a column or model | dbt YAML, `meta.caveat` | `churned_at` carries false values from the 12 March import |
| Dated event that moved a metric | Warehouse table `context.business_events` | 12 March billing migration |
| Versioned metric definition | Warehouse table `context.metric_changelog`, plus a markdown rendering | Churn v1 and v2 |
| Reasoning behind a decision | Numbered, immutable markdown decision records in the repo | `0007-recharge-migration-churn-artifacts.md` |

Two further pieces complete it. **Verified queries** are known-correct question and SQL pairs; they anchor the agent and double as a test suite. **Capture** means the writing-down is forced inside work that already happens: the pull request template and the incident runbook.

### 3.2 Kelder Coffee facts

These must stay consistent everywhere:

- Amsterdam. Single-origin coffee on subscription, plus one-off retail.
- About 40 people, Series A. One data analyst, **Sanne**. No data engineer.
- Shopify, Recharge, Klaviyo and the ad platforms flow through Fivetran into the warehouse, modelled in dbt. Notion holds docs, Slack the chat, Linear the tickets. No BI tool.
- Before 12 March 2026, subscriptions were billed through Shopify subscription contracts. From 12 March 2026, billing runs on Recharge.
- Currency EUR. Customers mostly in the Netherlands, with Belgium and Germany.

The article used Snowflake. This build uses DuckDB on purpose: the context files should move to a different warehouse without edits. Keep context files warehouse-agnostic wherever possible.

**Data window:** 1 January 2025 to 30 June 2026. **As-of date for every question:** 1 July 2026. All raw timestamps are stored in UTC. Customer behaviour follows Europe/Amsterdam local time (CET, CEST from 29 March 2026).

### 3.3 The six events of the first half of 2026

The analyst knows all six. Nothing in the before-context warehouse records any of them explicitly, but each one leaves a realistic fingerprint in the raw data.

| Date | Day | Type | Title | Affected metrics | Expected effect | Fingerprint in the data |
|---|---|---|---|---|---|---|
| 2026-03-12 | Thu | migration | Shopify to Recharge billing migration | subscriber_churn_rate, mrr | up (artificial) | About 1,900 paused subscriptions imported into Recharge as cancelled, stamped `2026-03-12 00:00:00 UTC` |
| 2026-03-28 | Sat | promo | Pause-instead-of-cancel campaign | subscriber_churn_rate, pause_rate | down | Recharge cancel flow starts offering a pause; 35% of would-be cancellers pause instead |
| 2026-04-09 | Thu | outage | Fivetran Klaviyo connector down 31h | email_attributed_revenue | gap | No Klaviyo events from 2026-04-09 06:00 UTC to 2026-04-10 13:00 UTC; the 9 April campaign appears to flop |
| 2026-05-01 | Fri | definition_change | Churn v2: 30-day dunning grace | subscriber_churn_rate | down (definitional) | The churn model switches definition on this date |
| 2026-05-19 | Tue | logistics | PostNL courier strike | refund_rate, delivery_days | up | Dutch PostNL shipments sent 18 to 24 May take 3 to 7 days; refunds for late delivery rise |
| 2026-06-14 | Sun | promo | Father's Day gift bundle | aov, new_customers | up | Gift bundle and prepaid gift subscriptions sold 14 to 21 June; gift MRR is zero by design |

Father's Day in the Netherlands is Sunday 21 June 2026.

### 3.4 The core fact

> On 12 March 2026 Kelder migrated billing from Shopify to Recharge. About 1,900 paused subscriptions were written as cancelled. March churn is 9.4% raw and 3.3% adjusted. Anyone quoting the raw number is wrong.

In the with-context state this fact must be findable in each of: the dbt caveat on `churned_at`, the `business_events` row, decision record 0007, the verified query for March churn, and `AGENTS.md`.

### 3.5 Numbers that must reconcile

Churn definitions (full detail in the appendix):

- **Base**: subscriptions in status active or paused at 00:00 Europe/Amsterdam on the first day of the month. Gift subscriptions are excluded from the base and from churn in every state.
- **v1**: churned in month = voluntary cancellations in the month plus subscriptions whose payment first failed in the month, counted on the day of failure whether or not it is later recovered. Churn rate = churned in month / base.
- **v2**: as v1, except a failed payment counts only if it is not recovered within 30 days. The churn is attributed to the month of the first failure. For the latest month, failures younger than 30 days at the as-of date count as not churned, so the latest month is provisional and will be revised upward.
- **As-reported series**: v1 up to April 2026, v2 from May 2026.
- **Restated v2 series**: v2 for every month, used for like-for-like comparisons.
- **Raw**: counts the migration artefacts as churn. **Adjusted**: excludes them and treats the affected subscriptions as still paused.

Hard targets, each asserted by a test:

| Quantity | Target |
|---|---|
| Base on 1 March 2026 | 31,200 ± 150 |
| Migration artefacts (paused subscriptions imported as cancelled) | 1,880 to 1,920, exact count solved so both March rates round correctly |
| March 2026 v1 churn, raw | rounds to 9.4% (keep within 9.37% to 9.43%) |
| March 2026 v1 churn, adjusted | rounds to 3.3% (keep within 3.27% to 3.33%) |
| Mean of v1 adjusted churn, September 2025 to February 2026 | rounds to 3.1% |
| Genuine cancellations queued during the billing freeze and imported with the same midnight stamp | 120 to 180 |
| v1 minus restated v2, mean over January to March 2026 | 0.4 to 0.7 percentage points |
| As-reported churn, May 2026 | lower than April 2026 |
| Restated v2 mean churn, January to June 2026, versus January to June 2025 | lower by 0.3 to 0.8 points (churn improved) |
| Same comparison in the rot state | higher (the conclusion flips) |

Monthly v1 adjusted churn targets, the calibration anchor. Hit each to within ±0.02 points:

| Month | Target | Month | Target | Month | Target |
|---|---|---|---|---|---|
| 2025-01 | 3.7% | 2025-07 | 3.4% | 2026-01 | 3.4% |
| 2025-02 | 3.5% | 2025-08 | 3.4% | 2026-02 | 3.0% |
| 2025-03 | 3.4% | 2025-09 | 3.1% | 2026-03 | 3.3% |
| 2025-04 | 3.3% | 2025-10 | 3.0% | 2026-04 | 2.8% |
| 2025-05 | 3.3% | 2025-11 | 3.0% | 2026-05 | 2.9% |
| 2025-06 | 3.2% | 2025-12 | 3.1% | 2026-06 | 2.8% |

The article contains a chart of monthly churn for January to June 2026: https://cms.tasman.ai/uploads/2026/07/image-70-1000x563.png. If you can download it, read the approximate values off it. If they differ from the table above by more than 0.2 points in any month, stop and tell Thomas before continuing. March must stay 9.4% raw and 3.3% adjusted regardless.

---

## 4. Architecture and repository layout

There are two separate environments. Keeping them separate is essential to the honesty of the demo.

1. **The build repository**, `kelder-coffee/`, contains the generator, loader, tests, harness, charts and this brief. It contains the ground truth.
2. **Agent workspaces**, created under `~/kelder-demo/`, outside the build repository. Each contains only what a Kelder employee's agent would see in one state. They never contain the ground truth, the generator, this brief, trial runs or git history.

```
kelder-coffee/
├── BUILD_BRIEF.md              # this document; never copied into a workspace
├── BUILD_LOG.md                # decisions, deviations, open questions
├── README.md
├── Makefile
├── pyproject.toml, uv.lock
├── .env.example                # ANTHROPIC_API_KEY etc.; real .env is git-ignored
├── generator/
│   ├── config.yaml             # every parameter, target, date and the seed
│   ├── world.py                # entity simulation
│   ├── calibrate.py            # solvers for scale and pinned counts
│   ├── catalogue.py            # products, prices, VAT
│   ├── systems/
│   │   ├── shopify.py
│   │   ├── recharge.py
│   │   ├── klaviyo.py
│   │   └── ads.py
│   ├── incidents.py            # explicit, logged transformations of rendered data
│   ├── truth.py                # writes the ground truth database
│   └── write.py                # Parquet output
├── loader/
│   └── load_raw.py             # Parquet into raw_* schemas with Fivetran columns
├── kelder-dbt/                 # the Kelder analytics repo; the thing shown on stage
│   ├── dbt_project.yml
│   ├── profiles.yml            # DuckDB path from env var
│   ├── models/
│   ├── seeds/
│   ├── tests/
│   └── (with-context only) AGENTS.md, context/, .github/pull_request_template.md
├── tests/
│   ├── targets/                # generated data hits the reconciliation targets
│   ├── truth/                  # warehouse metrics equal ground truth
│   ├── realism/                # distribution shape checks
│   ├── incidents/              # each incident leaves exactly its fingerprint
│   ├── determinism/
│   ├── verified/               # runs verified queries against a built state
│   │   └── expected/           # frozen expected results; never in a workspace
│   └── leaks/                  # workspace leak checks
├── scripts/
│   ├── build_state.py          # builds one warehouse state from a git ref
│   ├── make_workspace.py
│   ├── check_context_capture.py
│   ├── run_trials.py
│   ├── summarise_trials.py
│   └── demo_terminal.sh
├── charts/
│   ├── render.py
│   ├── fonts/
│   └── out/
├── demo/
│   ├── prompts.yaml
│   ├── runs/                   # git-ignored raw transcripts
│   ├── labels/                 # Thomas's manual labels of runs
│   └── selected/               # final answers used on slides
└── data/                       # git-ignored
    ├── raw/<system>/<table>.parquet
    ├── truth/kelder_truth.duckdb
    └── warehouse/kelder_{raw,before,with_context,rot}.duckdb
```

### The three states as git references

- Tag `kelder/before-context`
- Tag `kelder/with-context`
- Branch `kelder/rot`, one commit on top of `kelder/with-context`, also tagged `kelder/rot`

Only `kelder-dbt/` differs between states. `scripts/build_state.py <ref>` must extract `kelder-dbt/` at that reference (`git archive <ref> kelder-dbt`), copy `kelder_raw.duckdb` to the state's warehouse file, and run `dbt build` there, always using the current generator, loader and tests. This keeps the states reproducible while the tooling evolves.

### Make targets

| Target | Does |
|---|---|
| `make generate` | Runs the generator; writes Parquet and the truth database |
| `make load` | Builds `kelder_raw.duckdb` from Parquet |
| `make build STATE=before\|with_context\|rot` | Builds one warehouse state |
| `make build-all` | All three states |
| `make test` | Targets, truth, realism, incidents, determinism, dbt tests |
| `make check STATE=... PR_BODY=...` | Verified queries plus the context capture check, as CI would run them |
| `make freeze-verified` | Writes expected verified-query results from the with-context state; refuses unless truth tests pass |
| `make charts` | Renders all charts |
| `make workspaces` | Creates or refreshes every agent workspace |
| `make leak-check` | Leak tests across all workspaces |
| `make trials WORKSPACE=... PROMPTS=... N=...` | Runs trials |
| `make all` | generate, load, build-all, test, charts |

### Tooling

- Python 3.12 managed with `uv`; numpy, pandas or polars, pyarrow, duckdb, faker, pyyaml, pytest, matplotlib, dbt-core with dbt-duckdb. Pin everything in `uv.lock`.
- Node 20 or later for ktx.
- A single fixed seed in `generator/config.yaml`: `20260312`.
- Thomas works on macOS. Do not install anything globally without asking.

---

## 5. Data generation

This is the hardest part. Realism and exact reconciliation pull in opposite directions. The method below resolves that tension; follow it.

### 5.1 Principles

1. **Three layers.** Generate the **world** first: what actually happened to every customer and subscription. Then **render** the world through each source system, with that system's schemas, identifiers and quirks. Then apply **incidents** as explicit transformations of the rendered data. Each layer is a separate module.
2. **Hidden truth.** The world is written to `data/truth/kelder_truth.duckdb`. It is used only by the builder's tests and never reaches a workspace. It gives an exact correctness test: the adjusted metrics in the with-context state must equal the truth.
3. **Every incident is logged.** `incidents.py` writes a manifest of every row it creates, alters or removes, with before and after values.
4. **Determinism.** One seeded `numpy.random.Generator` per module, derived from the master seed. No wall-clock time, no unordered iteration over sets or dicts where order affects output, sorted output rows.
5. **No LLM-generated rows.** Language models may help write flavour text once (product names, campaign subject lines, cancellation reason texts, refund notes). That text is committed to `generator/` as plain files and read at generation time. Nothing in the generator calls a model.
6. **Fake identities only.** Names and addresses from Faker with `nl_NL`, `nl_BE` and `de_DE` locales. Every email address ends in `@example.com`.

### 5.2 Method: entity simulation with pinned monthly counts

Simulate every subscription as an individual with its own attributes and hazards. The simulator decides *how many* events happen each month from the targets, and *who* experiences them by weighted sampling on individual hazards. Aggregates therefore hit the targets exactly, while individual behaviour keeps realistic structure: cohort curves, tenure effects, payment-method differences, weekday and time-of-day rhythms.

**Warm-up.** Simulate from Kelder's launch on 2023-04-01 to 2024-12-31 without pinning, using the hazards below and a gently rising new-subscriber curve. Scale warm-up acquisition so the base on 2025-01-01 is 20,000 ± 300. This produces a realistic tenure mix at the start of the window. Emit the warm-up subscriptions into the Shopify contracts tables with their original dates. Order and event history before 2025-01-01 is not emitted; Kelder set up its Fivetran Shopify connector in January 2025.

**Pinned months, January 2025 to June 2026.** For each month:

1. Compute the base as defined above.
2. Target churn events = round(v1 target × base). These are true adjusted events; artefacts are added at the incident stage.
3. **First payment failures** = round(involuntary share × target churn events). Default involuntary share 0.36, in config. Choose which scheduled charges fail, weighted by payment-method multiplier × individual frailty. A subscription can have only one open dunning episode. Retries happen on days 1, 3, 7, 14, 21 and 28 after the first failure. Each episode is recovered with probability 0.52 for SEPA or iDEAL mandates, 0.40 for cards and 0.45 for PayPal; if recovered, the recovery day is drawn from the retry days, weighted towards early retries. Unrecovered episodes end in cancellation on day 30 with reason `max_retries_reached`.
4. **Voluntary cancellations** = target churn events minus first failures. Candidates are active subscriptions with no failure that month, plus paused subscriptions whose pause ends that month. Weight = tenure hazard × promo-cohort multiplier × frailty, with a × 4 multiplier during the seven days after a pause ends. Sample without replacement.
5. **Timing.** Place 40% of voluntary cancellations within three days after the subscriber's most recent shipment and the rest across the month, both weighted by the day-of-week profile. Draw the local time of day from the human cancellation profile.
6. **Pause diversion.** From 2026-03-28, the cancel flow offers a pause. For every month from then on, also create round(voluntary cancellations × 0.35 / 0.65) pauses from the same weighted pool, so that the pinned number of cancellations still lands exactly.
7. **Self-serve pauses.** Pauses start at the base pause hazard, with a × 1.8 summer multiplier for July and August. Pauses are available through Shopify until 2026-03-11 and through the Recharge portal from 2026-03-28. No pauses start between 2026-03-12 and 2026-03-27. Duration: 1 month 35%, 2 months 30%, 3 months 20%, 6 months 15%. At the end of a pause the subscription resumes; the elevated post-pause hazard in step 4 produces the cancellations that follow some pauses.
8. **Pin the paused count at the freeze.** After simulating up to 2026-03-11 23:59 local time, adjust recent pause starts (February and early March, hazard-weighted) so the number of paused subscriptions equals the artefact count the solver requires.
9. **New subscriptions** = round(scale × curve for the month). The curve shape is fixed in config and the scale is solved by bisection so the base on 2026-03-01 hits 31,200 ± 150. Curve multipliers: Black Friday (November 2025) × 1.7, January 2026 × 1.4, December × 1.2, June 2026 × 1.15, July and August × 0.85. Subscribers from Black Friday, January 2026 and other first-box-discount months carry a promo-cohort flag.
10. **Charges.** Every active, non-paused subscription is charged on its schedule at 05:00 Europe/Amsterdam. Each successful charge creates an order.
11. **Gift subscriptions** run as a separate process: prepaid for three shipments, then status expired. About 300 are sold in December 2025 and about 450 in the Father's Day week. They carry zero MRR by design and sit outside the churn base.

**Beyond June 2026.** Continue unpinned at June 2026 hazard levels until 2026-08-31, so every dunning episode that starts before 1 July resolves in the truth. The truth database stores both the final v2 values and the values knowable on 2026-07-01.

**Fallback, only if pinned sampling will not converge by the Friday checkpoint:** generate monthly aggregates straight from the targets and assign events to individuals with simple tenure weights. It hits the numbers but looks flatter. Tell Thomas before switching.

### 5.3 World parameters (defaults; all in `config.yaml`)

| Parameter | Default |
|---|---|
| Country mix | NL 72%, BE 13%, DE 12%, LU and FR 3% |
| Plan frequency | every 2 weeks 35%, 4 weeks 55%, 6 weeks 10% |
| Bags per shipment | 1: 70%, 2: 25%, 3: 5% |
| Bag size | 250 g 85%, 1 kg 15% |
| Grind | whole bean 55%, filter 25%, espresso 12%, French press 8% |
| Payment method | SEPA or iDEAL mandate 62%, card 30%, PayPal 8% |
| Payment failure multiplier | mandate 0.7, card 1.6, PayPal 1.0 |
| Frailty | gamma, mean 1, shape 2 |
| Voluntary hazard by tenure month | 1: 7.0%, 2: 5.0%, 3: 4.0%, 4: 3.2%, 5: 3.0%, 6: 2.8%, 7 to 18: 2.0% falling to 1.6% |
| Promo-cohort multiplier | × 1.5 for the first four months |
| Base pause hazard | 2.0% per month |
| Subscription price | €15 to €30 per shipment, 10% subscriber discount |
| VAT | coffee 9%, equipment 21%, prices include VAT |
| Retail orders | about 3,500 a month; December × 2.2, Black Friday week × 1.6; average order value about €32 |
| Father's Day bundle | €49, "Vaderdag Bundel" (two bags and a mug) |
| Refunds | 1.1% of orders at baseline; 6% of affected orders during the strike, reason `late_delivery` |
| Delivery | PostNL for NL, about 1.2 days; DHL for BE and DE, 2 to 3 days; no Sunday delivery |
| Klaviyo list | subscribers and customers with marketing consent |
| Klaviyo campaigns | weekly, Thursday 10:00 local; open 42%, click 2.8%, attributed order 0.35% of recipients within 5 days of a click |
| Klaviyo flows | welcome, post-purchase, win-back, abandoned checkout |
| Ad spend | Meta about €1,100 a day, Google about €550 a day; Black Friday × 1.8, January × 1.3, bundle week × 1.5, summer × 0.8 |
| Channels | paid social, paid search, email, organic, referral, direct, from UTM parameters on the first order |

**Time-of-day profiles**, local time:

- Human activity (retail orders, sign-ups, voluntary cancellations): peaks 07:00 to 09:00, 12:00 to 13:00 and 19:00 to 22:00; trough 02:00 to 05:00.
- Subscription charges and the orders they create: 05:00 to 05:30.
- Operations jobs: weekday office hours.

**Day-of-week profile** for human activity: Sunday 1.25, Monday 1.20, Tuesday 1.00, Wednesday 0.95, Thursday 0.95, Friday 0.80, Saturday 0.85.

**Product catalogue.** About 14 single-origin coffees with seasonal availability (for example Ethiopia Guji, Colombia Huila, Kenya Nyeri, Brazil Cerrado, Guatemala Huehuetenango, Rwanda Nyamasheke), three house blends, one decaf, equipment (grinders, drippers, filters, scales), a Christmas gift box, prepaid gift subscriptions, and the Vaderdag Bundel. Use invented names for everything except real origins.

### 5.4 Source systems and raw tables

Every raw table carries `_fivetran_synced` (timestamp) and `_fivetran_deleted` (boolean). All timestamps are UTC.

**`raw_shopify`**, synced from 2025-01-01:

- `customers`: id, email, first_name, last_name, country_code, created_at, accepts_marketing, tags
- `products`, `product_variants`: id, product_id, sku, title, price, grams, taxable
- `orders`: id, name (like `#K10234`), customer_id, created_at, processed_at, financial_status, fulfillment_status, currency, subtotal_price, total_tax, total_discounts, total_price, source_name (`web`, `subscription_contract` before 12 March, `recharge` from 12 March), tags, landing_site (with UTM parameters), referring_site, discount_codes (JSON), cancelled_at
- `order_lines`: id, order_id, variant_id, sku, quantity, price, total_discount
- `refunds`: id, order_id, created_at, amount, note
- `fulfillments`: id, order_id, created_at, tracking_company (`PostNL`, `DHL`), status, delivered_at
- `subscription_contracts`: id, customer_id, status (`ACTIVE`, `PAUSED`, `CANCELLED`, `EXPIRED`, `FAILED`), created_at, updated_at, next_billing_date, billing_interval (`WEEK`), billing_interval_count, line_variant_id, line_quantity, paused_at, pause_until, cancelled_at, cancellation_reason, custom_attributes (JSON, including `is_gift`). Current state only. The connector was paused after the migration, so every row reflects status at the last sync, 2026-03-11 21:30 UTC.
- `subscription_contract_events`: id, contract_id, event_type (`created`, `paused`, `resumed`, `cancelled`, `expired`, `billing_failed`, `billing_succeeded`), occurred_at, detail (JSON). Status history from the subscription app's webhook log, up to the freeze.
- `subscription_billing_attempts`: id, contract_id, created_at, completed_at, error_code, error_message, order_id, idempotency_key.

**`raw_recharge`**, from 2026-03-12:

- `customers`: id, shopify_customer_id, email, created_at
- `subscriptions`: id, customer_id, external_contract_id (the Shopify contract id for migrated subscriptions, otherwise null), shopify_variant_id, sku, quantity, price, order_interval_unit, order_interval_frequency, status (`active`, `cancelled`, `expired`), created_at, updated_at, cancelled_at, cancellation_reason, cancellation_reason_comments, next_charge_scheduled_at, paused_until (populated only for pauses from 2026-03-28), is_prepaid, properties (JSON: `is_gift`, and for restores `restore_source` and `legacy_contract_id`)
- `subscription_events`: id, subscription_id, verb (`created`, `activated`, `cancelled`, `paused`, `unpaused`, `expired`), created_at, payload (JSON)
- `charges`: id, customer_id, subscription_id, status (`success`, `error`, `refunded`, `skipped`), scheduled_at, processed_at, total_price, error_type, retry_date, number_times_tried, external_order_id (the Shopify order id)

Recharge has no paused *status*. A paused Recharge subscription is `active` with `paused_until` set. The unification model turns that into `paused`. This is a genuine quirk for the dbt layer, not an incident.

**`raw_klaviyo`**:

- `profiles`: id, email, shopify_customer_id, created_at
- `campaigns`: id, name, subject, send_time, status, audience_size
- `flows`: id, name
- `events`: id, metric_name (`Received Email`, `Opened Email`, `Clicked Email`, `Placed Order`, `Unsubscribed`), profile_id, timestamp, campaign_id, flow_id, value_eur, attributed_message_id, shopify_order_id

**`raw_ads`**:

- `meta_ads_daily`: date, account_id, campaign_id, campaign_name, spend, impressions, clicks
- `google_ads_daily`: date, customer_id, campaign_id, campaign_name, cost_micros, impressions, clicks

### 5.5 Incidents: exact mechanics

**Billing freeze and migration, 12 March 2026.**

- No charges run from 2026-03-11 20:00 to 2026-03-12 12:00 local time. Charges due in that window run at 05:00 on 13 March, producing a dip and then a spike in charge volume.
- At the freeze, every Shopify contract that is `ACTIVE` or `PAUSED` is imported into Recharge. `created_at` is date-only: the original contract date at 00:00:00 UTC. `external_contract_id` is set.
- `ACTIVE` contracts arrive as `active` and continue billing on their schedule. Open dunning episodes carry over and Recharge continues the retries.
- `PAUSED` contracts arrive as `cancelled`, with `cancelled_at = 2026-03-12 00:00:00 UTC` and a null `cancellation_reason`. The legacy import path has no paused state. These are the **migration artefacts**. They get a `cancelled` subscription event at the same timestamp.
- Between 120 and 180 **genuine** cancellation requests queued during the freeze are imported the same way: `cancelled`, `2026-03-12 00:00:00 UTC`, null reason. They are real churn. Nothing in Recharge distinguishes them from the artefacts. The only way to tell them apart is to join through `external_contract_id` to the last-synced Shopify contract and read its `PAUSED` status. That is exactly what the with-context flag does.
- Genuine live cancellations after the import have real timestamps and reasons.

**Restores.** Customers whose pauses were wiped still expect coffee when their pause ends. From 16 March, an operations job re-creates each affected subscription on the original `pause_until` date as a new Recharge subscription: same customer, plan and product; status `active`; `created_at` at the job's run time, 09:15 local on weekdays; `properties` containing `{"restore_source": "legacy_pause", "legacy_contract_id": "<id>"}`. First charge at the next 05:00 run. Subscriptions whose pause ends after 2026-06-30 are not yet restored when the data ends. In the world, these subscribers were paused throughout and resumed on schedule. A naive model counts restores as new subscribers.

**Klaviyo outage, 9 April 2026.** Delete every Klaviyo event with a timestamp from 2026-04-09 06:00 UTC to 2026-04-10 13:00 UTC, across all metric names. The Thursday campaign "Nieuwe oogst: Kenya Nyeri" is sent at 08:00 UTC on 9 April, inside the window, so most of its receipts, opens and clicks are missing. Late opens after 13:00 UTC on 10 April survive. Shopify orders are unaffected, so email-attributed revenue drops while total revenue does not.

**PostNL strike, 19 May 2026.** Dutch PostNL shipments sent from 18 to 24 May take 3 to 7 days to deliver, and about 1% are never delivered. Late-delivery refunds rise to about 6% of affected orders. A small uptick in voluntary cancellations is allowed but not required.

**Father's Day bundle, 14 to 21 June 2026.** Bundle orders and gift subscriptions spike; new customers and average order value rise; MRR does not, because gift MRR is zero by design.

**Churn v2, 1 May 2026.** This is not a data incident. It exists only in the dbt logic and in the context.

### 5.6 Truth database

`data/truth/kelder_truth.duckdb` must contain at least:

- `subscription_episodes`: world subscription id, customer id, true status, valid_from, valid_to (type 2 history)
- `id_map`: world subscription id to Shopify contract id to Recharge subscription ids, including restores
- `dunning_episodes`: first failure, retries, outcome, outcome date
- `metrics_monthly`: month; base; voluntary cancellations; first failures; unrecovered failures (final); unrecovered failures knowable on 2026-07-01; churn v1; churn v2 final; churn v2 as of 2026-07-01; paused count; pause rate; new subscribers excluding gifts and restores; gift subscriptions sold; retail orders; email-attributed revenue with and without the outage
- `incident_manifest`: incident, table, row id, change type, before value, after value
- `targets`: each target and the achieved value

### 5.7 Validation of the generated data

**Target tests** assert every value in "Numbers that must reconcile".

**Realism tests**, each a pytest with a clear threshold:

- Retail orders by local hour: the 07:00 to 09:00 and 19:00 to 22:00 bins each exceed twice the 02:00 to 05:00 mean.
- Subscription orders: more than 90% created between 05:00 and 05:30 local time.
- Voluntary cancellations in February 2026 by UTC hour: no single bin above 12% of the month's total.
- Cancellations stamped in March 2026: the 00:00 UTC bin holds more than 60% of the month's total. This is the artefact fingerprint.
- Retail orders by weekday: busiest day at least 15% above the quietest.
- Cohort survival curves are non-increasing, and the month-1 hazard is more than 1.8 times the month-6 hazard.
- December retail orders are at least 1.8 times the monthly median.
- Klaviyo: no events inside the outage window; each adjacent day within ±30% of the same weekday in the previous three weeks.
- Every email ends in `@example.com`.

**Incident tests** assert that each incident changes exactly the rows in the manifest and nothing else.

**Determinism test**: two runs produce identical SHA-256 hashes for every Parquet file.

**Profile report**: `make generate` writes `data/profile_report.md`, a readable summary with monthly tables, distributions and incident counts, so a human can sniff-test the data in ten minutes.

---

## 6. The Kelder analytics repository in three states

### 6.1 Loader

`loader/load_raw.py` creates `data/warehouse/kelder_raw.duckdb` with schemas `raw_shopify`, `raw_recharge`, `raw_klaviyo` and `raw_ads`, loaded from Parquet with correct types (TIMESTAMPTZ for timestamps, JSON for JSON columns). Never load truth tables into any warehouse file.

### 6.2 State one: before-context

This must be a competent project. The article's premise is that Kelder's semantic layer is in good shape, and the failure is missing context, not sloppy modelling. Every model and column has a clear description. Tests cover keys, relationships and accepted values. The churn definition is governed in one place.

Models:

- **Staging**: one model per raw table used; rename, type, convert to UTC, parse UTM parameters into a channel, parse `properties` and `custom_attributes`. Staging parses `is_gift`. It does not parse `restore_source`.
- **`int_subscriptions_unified`**: one row per subscription key. Shopify contracts provide history up to the freeze. Migrated Recharge subscriptions continue their Shopify key through `external_contract_id`. Native Recharge subscriptions, including restores, get new keys. Status is unified to `active`, `paused`, `cancelled` or `expired`, including the `paused_until` quirk.
- **`int_subscription_events`**: a unified event stream (started, paused, resumed, cancelled, expired, payment_failed, payment_recovered) from both systems.
- **`int_charges_unified`**: Shopify billing attempts and Recharge charges.
- **Marts**:
  - `dim_customers`
  - `fct_orders`: channel, is_subscription_order, is_gift, delivery_days, is_refunded
  - `fct_subscriptions`: key, customer, plan, started_at, `churned_at`, status, `mrr_eur` (zero for gifts), is_gift
  - `fct_subscription_events`
  - `metrics_subscriber_churn_monthly`: month, base_subscribers, churned_subscribers, churn_rate. The as-reported logic applies v1 before 2026-05-01 and v2 from then, in plain SQL with no comment explaining why. The switch is visible to anyone who reads the SQL, which is realistic.
  - `metrics_new_subscribers_monthly`: excludes gifts; counts restores as new
  - `metrics_pause_rate_monthly`
  - `metrics_email_attribution_daily`: Klaviyo `Placed Order` value attributed within 5 days of a click
  - `metrics_cac_monthly`: ad spend by channel over new subscribers by first-order channel

Hard constraints for this state, enforced by the leak check:

- No `context` schema, no `business_events`, no `metric_changelog`, no `AGENTS.md`, no `context/` directory, no pull request template.
- No columns named `is_migration_artifact` or `is_legacy_pause_restore`.
- No comments or descriptions that mention the migration, artefacts, backfills, restores, the outage, the strike, definition versions or the reason for the May switch. Payment terms such as "dunning" are fine where the logic needs them.

### 6.3 State two: with-context

Everything from before-context, plus:

**Model changes.**

- `fct_subscriptions` gains `is_migration_artifact`: a Recharge subscription with `external_contract_id` whose last-synced Shopify contract status is `PAUSED`, with `cancelled_at = 2026-03-12 00:00:00 UTC` and a null reason.
- It also gains `is_legacy_pause_restore` (`properties.restore_source = 'legacy_pause'`) and `continues_subscription_key`, which links a restore to the original key.
- In the adjusted logic, a flagged subscription is treated as paused from 12 March until its restore's `created_at`, or until the end of the data. The restore then continues the original subscription's key and tenure.
- `metrics_subscriber_churn_monthly` gains these columns: `definition_version_as_reported` (`v1` or `v2`), `churn_rate_as_reported` (adjusted), `churn_rate_as_reported_raw` (artefacts included, for finance reconciliation against Recharge exports), `churn_rate_v2_restated` (adjusted), and `is_provisional` (true for the latest month).
- The restated v2 series reads from an adjusted events model. Structure the SQL so the adjustment enters through one clearly named CTE or model reference; the rot commit will bypass it.
- `metrics_new_subscribers_monthly` excludes restores.

**Caveats in dbt YAML** (`meta.caveat`):

- `fct_subscriptions.churned_at`: verbatim from the appendix.
- `fct_subscriptions.mrr_eur`: zero for gift subscriptions by design.
- `fct_subscriptions.status`: Shopify and Recharge use different source values; unified in one intermediate model.
- `fct_subscriptions.is_legacy_pause_restore`: restores are continuations, not new subscribers.
- `metrics_email_attribution_daily`: no Klaviyo data from 2026-04-09 06:00 UTC to 2026-04-10 13:00 UTC; figures for 9 and 10 April are incomplete.
- `fct_orders.delivery_days`: PostNL strike, 18 to 24 May 2026.
- `metrics_subscriber_churn_monthly`: v1 before May 2026, v2 from May; use the restated series for comparisons across that date; the latest month is provisional.

**Context tables as dbt seeds**, materialised into the `context` schema:

- `seeds/context/business_events.csv`: the six rows from the appendix. Store `affected_metrics` as a semicolon-separated string in the CSV and expose it as `VARCHAR[]` in a `context.business_events` model.
- `seeds/context/metric_changelog.csv`: the two rows from the appendix.

**Context files** under `kelder-dbt/context/`:

- `glossary.md`: base, churn, raw versus adjusted, as-reported versus restated, pause, gift subscription, restore, MRR, email-attributed revenue.
- `metric_changelog.md`: generated from the seed by a script; a test fails if the two disagree.
- `decisions/0007-recharge-migration-churn-artifacts.md`: verbatim from the appendix.
- `decisions/0009-churn-v2-dunning-grace.md`: specified in the appendix.
- Could: short, dated stubs for 0001 to 0006 and 0008 on older decisions, so the numbering looks lived-in. Examples: currency EUR; gift MRR zero; status unification; attribution window; channel grouping; pause is not churn.
- `quirks/gift_subscriptions.md` and `quirks/legacy_pause_restores.md`.
- `verified_queries.yml`, specified below.

**`AGENTS.md`** at the root of `kelder-dbt/`. Write a draft of at most 150 lines, then stop and ask Thomas to rewrite it by hand before any trial runs. Hand-written instructions are part of the thesis. The draft covers:

- the as-of date, 2026-07-01;
- where each kind of context lives;
- check `context.business_events` before explaining any anomaly;
- use the governed metrics for reported numbers;
- report raw and adjusted together for March 2026;
- name the definition version when comparing across 1 May 2026, and use the restated series for like-for-like comparisons;
- the latest month is provisional under v2;
- gift MRR is zero;
- restores are not new subscribers.

**Pull request template** at `kelder-dbt/.github/pull_request_template.md`, verbatim from the appendix. Also copy it to the build repository's root `.github/pull_request_template.md` so GitHub uses it.

### 6.4 State three: rot

One commit on branch `kelder/rot`, on top of `kelder/with-context`.

- Commit message and pull request title: `Fix churn logic`. Pull request body: the template with no box ticked and one terse line under "What changed", for example "Simplify churn model, consolidate v1 and v2 CTEs." Store the body at `kelder-dbt/.pr/rot.md` for the local check.
- The diff touches only `metrics_subscriber_churn_monthly`, and at most about five lines. In consolidating the CTEs, the **restated v2 series** starts reading from the unadjusted events instead of the adjusted ones. The as-reported series is untouched.
- The caveats, decision records, changelog and `AGENTS.md` are all unchanged. They still say artefacts are excluded from churn metrics.

Expected consequences, each asserted by a test:

- March 2026 restated v2 churn jumps by about six points.
- The January-to-June 2026 restated mean now exceeds January-to-June 2025, so the year-on-year conclusion flips from "improved" to "worse".
- The verified queries for the year-on-year comparison fail. The March as-reported query still passes.
- The context capture check fails, because a metrics model changed without a ticked metric-impact box.

Why the rot sits in the restated series: decision 0007 quotes 9.4% and 3.3% for the as-reported series, so a careful agent could catch a break there against the written record. The restated series has no such checksum. Decay hides in the series nobody looks at every week.

### 6.5 Verified queries

`kelder-dbt/context/verified_queries.yml` lists, for each query: an id, the question, what it pins down, and canonical SQL against the marts and context tables. **It contains no expected results.** Expected results live in `tests/verified/expected/<id>.json` in the build repository and never reach a workspace, so an agent cannot copy the answer.

| id | Question | Pins down |
|---|---|---|
| `churn_last_month` | What was subscriber churn last month? | June 2026, v2, adjusted, provisional flag |
| `churn_march_2026` | What was real churn in March 2026? | Raw 9.4% and adjusted 3.3% both returned, adjustment named |
| `churn_yoy_like_for_like` | How did churn in the first half of 2026 compare with the first half of 2025, like for like? | Restated v2 series; June provisional noted |
| `cac_by_channel` | Which channel has the best CAC? | First half of 2026; channel grouping; restores and gifts excluded |
| `fathers_day_bundle` | How did the Father's Day bundle perform? | Bundle SKU list; date range from `business_events` |
| `email_revenue_april_2026` | What was email-attributed revenue in April 2026? | Value returned together with the missing-data window |
| `new_subscribers_june_2026` | How many new subscribers did we add in June 2026? | Restores and gifts excluded |

`make freeze-verified` builds the with-context state, requires every truth test to pass, then writes the expected results. **Never re-freeze expected results to make a failing check pass.** Freeze only when Thomas asks, and log each freeze in `BUILD_LOG.md`.

### 6.6 CI and the context capture check

`scripts/check_context_capture.py` takes the list of changed files and the pull request body.

- If nothing under `kelder-dbt/models/marts/metrics_*`, `kelder-dbt/models/**/fct_subscription*` or the semantic layer definitions changed, it passes.
- Otherwise exactly one metric-impact option must be ticked.
- If "No user-visible metrics move" is ticked, the verified queries must all still match their expected results. The claim is tested, not trusted.
- If a "Metrics move" option is ticked, the change must include an edit to `metric_changelog.csv` or `business_events.csv`, and the body must link a decision record path when that option is ticked.

`make check STATE=rot PR_BODY=kelder-dbt/.pr/rot.md` runs the verified queries and this check locally, with clear red and green terminal output suitable for recording.

GitHub Actions (`.github/workflows/ci.yml`) runs on pull requests: `uv sync`, generate, load, build the head state, run the truth tests and `make check` with the real pull request body. Should: once Thomas has created the private repository, open a real pull request from `kelder/rot` so a red check exists to screenshot. Ask before pushing anything.

### 6.7 In-universe git history (should)

Commits that change `kelder-dbt/` should read as Kelder's own history, so that `git log --oneline -- kelder-dbt/` shows the capture loop working over time.

- Use the author `Sanne de Vries <sanne@example.com>` and backdated author and committer dates between January and June 2026.
- Tag in-universe releases where the article mentions them. The artefact flag ships in `v2026.03.2`.
- Suggested sequence: initial models; the 14 March flag and caveat with decision 0007 and the first `business_events` row; the 28 March pause campaign row; the 9 April outage row with its caveat; decision 0009 and the v2 logic before 1 May; the 19 May strike row; the 14 June bundle row. The rot commit is dated late June.
- Never mix builder changes and in-universe changes in one commit.

---

## 7. Serving context to an agent

### 7.1 ktx smoke test first, time-boxed to 90 minutes

ktx is Kaelio's open-source (Apache 2.0) context layer for data agents. It holds a YAML semantic layer and a markdown wiki in git and exposes them to agents such as Claude Code through a local MCP server with read-only warehouse access. The DuckDB connector arrived in v0.16.0 (July 2026). The project moves fast and has had breaking changes, so pin the version.

Before touching the Kelder data, in a throwaway folder outside the build repository:

1. Install the latest ktx release at v0.16.0 or later, following its README.
2. Create a tiny DuckDB file and a three-model dbt project.
3. Run `ktx setup` with the DuckDB connection and the dbt project as a context source, then `ktx ingest`, then `ktx status`.
4. Start the MCP server and connect a Claude Code session to it. Ask one question that needs a join.

Establish and record in `BUILD_LOG.md`:

- whether the whole path works;
- the exact version;
- which LLM and embeddings providers ingest requires, and which keys Thomas must supply;
- whether the wiki location can point at an existing directory such as `context/`;
- that warehouse access is read-only;
- how to turn off telemetry.

If the path does not work within 90 minutes, stop, use the fallback in 7.3 and tell Thomas.

### 7.2 ktx configuration for Kelder

- The ktx project lives at the root of `kelder-dbt/` (`ktx.yaml`, `semantic-layer/`, `wiki/`). Keep `.ktx/` git-ignored.
- `context/` stays the single canonical location for written context. Configure ktx to read it directly if possible. Otherwise generate `wiki/global/` from `context/` in a make step, and add a test that fails if they differ.
- Run `ktx ingest` once per state. Because ingest uses a language model, store each state's ingest output and never regenerate it casually. Record the model and version used.
- The ingest output for **before-context** is itself an artefact for the talk: it shows what a tool derives unaided. Write `demo/selected/ingest_before_summary.md` describing what it produced. Search it for any mention of 12 March, the migration, midnight clustering or restores, and report exactly what you find. A correct inference drawn from the data is legitimate and must be reported, never removed.
- Allow read-only SQL through ktx in every workspace, with identical tools in every state. The only intended difference between the installed and written workspaces is the written context.
- Turn telemetry off for all demo work.

### 7.3 Fallback without ktx

Serve the workspace's DuckDB file through a DuckDB MCP server in read-only mode (for example MotherDuck's `mcp-server-motherduck`, which supports local files; check its current flags). The agent reads `kelder-dbt/` and `context/` with Claude Code's native file tools. Everything else stays the same. Record in `BUILD_LOG.md` which path was used for each trial and recording.

---

## 8. Agent workspaces and isolation

`scripts/make_workspace.py` creates each workspace from scratch.

| Workspace | Contents |
|---|---|
| `~/kelder-demo/installed/` | `kelder-dbt/` extracted at `kelder/before-context` without `.git`; the before-context ktx ingest output; `warehouse.duckdb` copied from `kelder_before.duckdb` |
| `~/kelder-demo/written/` | `kelder-dbt/` at `kelder/with-context` with Thomas's hand-edited `AGENTS.md`; the with-context ingest output; `warehouse.duckdb` from `kelder_with_context.duckdb` |
| `~/kelder-demo/rot/` | `kelder-dbt/` at `kelder/rot`; the rot ingest output; `warehouse.duckdb` from `kelder_rot.duckdb` |
| `~/kelder-demo/bare/` (could) | before-context files, a DuckDB MCP server only, no ktx |

Isolation requirements. All must hold, and `make leak-check` must verify every one it can:

- **No web access for the demo agent.** The article describing Kelder's March migration is public, so a web search would hand the agent the answer. Deny WebSearch, WebFetch and any other network tools in each workspace's `.claude/settings.json`.
- **Deny Bash.** Data access goes through the MCP server only. Allow Read, Grep, Glob and the ktx (or fallback) MCP tools.
- **No inherited instructions.** Claude Code loads `CLAUDE.md` files from parent directories and from the user's configuration. Verify that no directory above `~/kelder-demo/` contains a `CLAUDE.md`. Run every demo session with a dedicated configuration directory, so Thomas's own memory, instructions and MCP servers never load. Check the current mechanism with `claude --help` and the docs; `CLAUDE_CONFIG_DIR` has been used for this.
- **AGENTS.md loads in written and rot.** If Claude Code does not read `AGENTS.md` automatically, add a `CLAUDE.md` in those two workspaces that imports it with `@AGENTS.md`, and nothing else. Verify it loads with a dry run in which the agent quotes a harmless marker line, then remove the marker.
- **Pinned model.** Use one current frontier model for every trial and recording, for example `claude-opus-5-5`, and record the exact string. A weak model would invite the objection that the failures are the model's fault.
- **One MCP configuration per workspace** (`.mcp.json`), listing only ktx or the fallback server, in read-only mode.

**Leak check**, `make leak-check`, fails the build if:

- any workspace contains the truth database, generator code, `BUILD_BRIEF.md`, `BUILD_LOG.md`, `demo/`, `tests/verified/expected/`, a `.git` directory, or the article URL;
- any text file in `installed` or `bare` contains, case-insensitively: `migration`, `artefact`, `artifact`, `backfill`, `legacy_pause`, `restore_source`, `is_legacy`, `0007`, `0009`, `business_events`, `metric_changelog`, `changelog`, `decision record`, `definition change`, `strike`, `outage`. **Exception:** ktx ingest output derived from the data. Report matches in it; do not fail on them and do not delete them.
- `installed.duckdb` or `bare.duckdb` contains a `context` schema or a column named `is_migration_artifact` or `is_legacy_pause_restore`;
- any workspace's settings allow web tools or Bash;
- a parent directory of `~/kelder-demo/` contains `CLAUDE.md`.

---

## 9. Trials and recordings

### 9.1 Prompts

`demo/prompts.yaml`, exact wording:

| id | Prompt |
|---|---|
| `churn_spike_why` | Why did subscriber churn spike in March 2026? |
| `churn_board_number` | What was subscriber churn in March 2026? I need one number for the board deck. |
| `email_revenue_april` | Email-attributed revenue dropped in April 2026. What happened? |
| `churn_may_improvement` | Churn improved in May 2026. What drove the improvement? |
| `churn_yoy_like_for_like` | Has churn improved year on year? Compare the first half of 2026 with the first half of 2025, like for like. |
| `new_subscribers_june` | How many new subscribers did we add in June 2026, and what drove it? |

Run matrix: all six prompts in `installed` and `written`; `churn_yoy_like_for_like`, `churn_spike_why` and `churn_board_number` in `rot`.

### 9.2 Harness

`scripts/run_trials.py --workspace <name> --prompts <ids> --n <count>`:

- Runs Claude Code in headless mode (`claude -p`) from the workspace directory, with the dedicated configuration directory, the workspace MCP configuration, the pinned model and JSON output. Check the current flags with `claude --help`.
- Uses a fresh session for every run, a turn limit of 30 and a timeout of 10 minutes.
- Saves the full JSON to `demo/runs/<workspace>/<prompt_id>/<n>.json` and a readable rendering (final answer plus a list of tool calls) beside it.

**Cost guard.** Run `N=3` first. Report tokens used and the projected cost of the full matrix at `N=10`. Ask Thomas before any batch projected above €50.

`scripts/summarise_trials.py` writes `demo/trial_summary.md`. It proposes a class for every run using heuristics (percentages quoted, mentions of 12 March or the migration, mentions of the definition change, hedging), writes `demo/labels/labels.csv` for Thomas to confirm or correct, and tallies classes using Thomas's labels where they exist.

| Prompt | A | B | C | D |
|---|---|---|---|---|
| `churn_spike_why` | Names the 12 March migration or import as the cause and quantifies it | Notices an anomaly on 12 March, but cannot establish the cause or the adjusted figure | Attributes the spike to business causes without noticing the anomaly | Other |
| `churn_board_number` | Gives raw 9.4% and adjusted 3.3% with the reason | Adjusted only | Raw 9.4% as the board number | Other |
| `email_revenue_april` | Identifies missing data | Notices irregular data | Blames the campaign or customers | Other |
| `churn_may_improvement` | Identifies the definition change | Mentions both the definition change and business causes | Business causes only | Other |
| `churn_yoy_like_for_like` | "Improved", roughly the right size, uses the restated series | Compares across definitions without restating | "Worse" | Other |
| `new_subscribers_june` | Excludes restores and gifts, names the bundle | Partly right | Counts restores as new | Other |

### 9.3 Honesty rules

- Report every run. Never discard a run because it is inconvenient.
- Do not change data, context, prompts or settings to push results in a particular direction. If anything changes for any reason, rerun every affected trial and log the change.
- The recorded take must show the most common outcome for that workspace and prompt. If the best take differs from the most common outcome, tell Thomas; he decides and discloses.
- Keep raw transcripts until after the talk.
- If the installed agent often reaches class B, noticing the anomaly without resolving it, that is a legitimate and interesting result. Report it plainly; do not engineer it away.

### 9.4 Recordings

Two clips of at most 90 seconds each, recorded by Thomas from interactive Claude Code sessions that use exactly the trial settings.

- **"Same question, two agents".** `scripts/demo_terminal.sh side-by-side` opens a tmux split: `installed` on the left, `written` on the right, each with its isolated configuration. Ask `churn_spike_why` in both, then `churn_board_number`.
- **"The context goes stale".** In the build repository, show the rot diff with `git show kelder/rot -- kelder-dbt/models`. Then ask `churn_yoy_like_for_like` in the `rot` workspace. Then run `make check STATE=rot PR_BODY=kelder-dbt/.pr/rot.md` and show the failing verified query and capture check in red.

Terminal set-up, applied by `scripts/demo_terminal.sh setup`:

- 1920×1080, font size at least 20 pt;
- background as close to `#fff9eb` as the terminal allows, text `#526476`;
- a minimal prompt with no user name or home path visible;
- notifications off;
- ktx or the fallback server already running.

Also write the final answers of the selected runs to `demo/selected/*.md` as clean text for transcript slides.

---

## 10. Charts

`charts/render.py` uses matplotlib and reads only from warehouse state files, never from the truth database, so every chart is evidence about the warehouse.

**Brand.**

- Background Cream `#fff9eb`; text, axes and primary series Slate `#526476`; secondary and correct values Sage `#90b39d`.
- Brick `#a93427` is reserved for **exactly one element per chart**: the wrong number or the artefact.
- EB Garamond for any display text, Roboto Mono for labels and ticks, Helvetica Neue with Arial as fallback for body text.
- Download EB Garamond and Roboto Mono from Google Fonts (SIL Open Font License) into `charts/fonts/`.
- No large titles baked in; slides carry the headlines. A small Roboto Mono source line at the bottom (for example "Kelder Coffee warehouse, with-context state").

**Output.** For each chart: SVG, PNG at 2400×1350, and a JSON file of the plotted values, all in `charts/out/`.

| File stem | Source state | Content | Brick element |
|---|---|---|---|
| `cancellations_by_hour_feb_mar_2026` | before | Subscription cancellations by UTC hour, February and March 2026 side by side | The March 00:00 bar |
| `churn_monthly_2026_events` | with-context | As-reported churn, January to June 2026, raw March and adjusted March both shown; the six events marked on the time axis from `context.business_events` with short Roboto Mono labels; a dashed line at 1 May for the definition change; June drawn as provisional (hollow marker) | The raw March point, labelled 9.4% |
| `churn_v1_vs_v2_restated` | with-context | v1 and restated v2, January 2025 to June 2026, with a break marker at 1 May | None; mark the 1 May line only |
| `email_revenue_daily_april_2026` | with-context | Daily email-attributed revenue with the missing window shaded and labelled | The apparent drop on 9 April |
| `yoy_like_for_like_written_vs_rot` | with-context and rot | First-half 2025 versus first-half 2026 restated churn, one pair per state | The rot first-half 2026 bar |

Annotations for events must be read from `context.business_events`, not typed by hand. The table that serves the agent also serves the chart.

Could: an Evidence.dev page in the build repository over the with-context state, for people who clone the repository after the talk.

---

## 11. Schedule, checkpoints and cut lines

Today is Thursday 24 September 2026. Recordings must be finished by Monday 28 September. Thomas travels on Wednesday 30 September.

| When | Work | Checkpoint: stop and report to Thomas |
|---|---|---|
| Thu 24, evening | Repository scaffold; ktx smoke test; generator skeleton | ktx works or not, version, requirements, gotchas |
| Fri 25 | Generator complete; calibration; target, realism, incident and determinism tests; profile report | Monthly table (base; v1 raw and adjusted; restated v2; pause rate; new subscribers; artefacts) against targets; test summary; profile report path |
| Sat 26 | Loader; before-context; with-context (with `AGENTS.md` draft); rot; verified queries; capture check; CI | Truth tests and verified queries green in with-context; exact failures in rot; `AGENTS.md` draft handed to Thomas |
| Sun 27 | ktx wiring; workspaces; leak check; trials at N=3; charts | Leak check result; first answers from each workspace; cost projection; charts |
| Mon 28 | Trials at N=10; labelling with Thomas; select takes; recordings; transcript text | Trial summary table; selected takes |
| Tue 29 | Fixes only | |

Cut in this order if time runs short:

1. In-universe backdated history.
2. The `cac_by_channel` and `fathers_day_bundle` verified queries, with ad data kept minimal.
3. The email revenue chart.
4. The `bare` workspace.
5. ktx, switching to the fallback.

Never cut:

- calibration to the reconciliation targets;
- truth tests;
- the leak check and disabled web tools;
- the rot state and its failing check;
- honest trial reporting.

---

## 12. Working agreements

- **Ask Thomas before:**
  - installing anything outside the project environment;
  - creating or pushing any GitHub repository;
  - making anything public;
  - any API batch projected above €50;
  - deleting data, runs or ingest outputs;
  - changing any number in "Numbers that must reconcile";
  - freezing verified results.
- **Secrets.** Keys live in `.env`, which is git-ignored. Never print them or commit them.
- **Writing style.** All human-facing text (README, context files, decision records, glossary, `AGENTS.md`, caveats, chart labels) is in British English, in short, plain sentences, without em dashes. Code identifiers keep the article's spelling, for example `is_migration_artifact`.
- **Evidence.** Never state a number that a test or query has not produced. Report failures as plainly as successes.
- **Commits.** Commit small, after each passing step. Builder commits and in-universe commits never mix.
- **Log.** Update `BUILD_LOG.md` at every checkpoint: what was done, what deviated from this brief, open questions.

---

## 13. Public release checklist (after the talk, only when Thomas says so)

- Remove or keep private `BUILD_BRIEF.md`, `BUILD_LOG.md`, `demo/runs/` and `demo/labels/`. The default is to exclude them.
- Add an Apache 2.0 licence, confirm telemetry is off by default, and scan for secrets.
- README: what Kelder is; how to reproduce each state; how to run an agent against each workspace; a pointer to the article.
- Tag `v1.0`.

---

## Appendix: artefacts to reproduce verbatim or to specification

### Caveat on `churned_at` (verbatim)

```yaml
- name: churned_at
  description: Timestamp the subscription entered a terminal cancelled state.
  meta:
    caveat: >
      The 2026-03-12 Recharge backfill wrote churned_at for ~1,900
      paused subscriptions. These rows carry is_migration_artifact
      = true and are excluded from churn metrics as of v2026.03.2.
```

Other column caveats in the article:

| Column | What it is | What the agent needs to know |
|---|---|---|
| churned_at | Timestamp of terminal cancellation | ~1,900 false values from the 12 Mar backfill, flagged and excluded from churn |
| mrr_eur | MRR attributed to the subscription | Zero for gift subscriptions by design |
| status | Unified subscription status | Shopify and Recharge use different source values; unified in one intermediate model |

### `business_events` structure (article version, Snowflake types)

```sql
create table context.business_events (
    event_date        date,
    event_type        string,   -- migration | promo | outage | definition_change | logistics
    title             string,
    description       string,
    affected_metrics  array,
    expected_effect   string,   -- up | down | gap | none
    owner             string,
    source_link       string    -- decision record, Linear ticket, or Slack permalink
);
```

In DuckDB use `VARCHAR` and `VARCHAR[]`.

### `business_events` rows

`event_date`, `event_type`, `title`, `affected_metrics`, `expected_effect` and `source_link` are verbatim from the article. Descriptions and owners are new; keep them short and factual.

| event_date | event_type | title | affected_metrics | expected_effect | owner | source_link | description |
|---|---|---|---|---|---|---|---|
| 2026-03-12 | migration | Shopify to Recharge billing migration | subscriber_churn_rate, mrr | up (artificial) | Sanne (data) | context/decisions/0007 | Legacy import path has no paused state; about 1,900 paused subscriptions arrived as cancelled at 00:00 UTC. Flagged and excluded from churn. |
| 2026-03-28 | promo | Pause-instead-of-cancel campaign | subscriber_churn_rate, pause_rate | down | Joris (retention) | Linear KEL-412 | Recharge cancel flow now offers a pause. A rising pause rate is expected and healthy. |
| 2026-04-09 | outage | Fivetran Klaviyo connector down 31h | email_attributed_revenue | gap | Sanne (data) | a Slack permalink on a fictional workspace URL | No Klaviyo events from 06:00 UTC on 9 April to 13:00 UTC on 10 April. The 9 April campaign's results are incomplete. |
| 2026-05-01 | definition_change | Churn v2: 30-day dunning grace | subscriber_churn_rate | down (definitional) | Sanne (data) | context/decisions/0009 | Failed payments count as churn only if not recovered within 30 days. |
| 2026-05-19 | logistics | PostNL courier strike | refund_rate, delivery_days | up | Lotte (operations) | Linear KEL-467 | Dutch PostNL deliveries delayed 3 to 7 days for parcels shipped 18 to 24 May. |
| 2026-06-14 | promo | Father's Day gift bundle | aov, new_customers | up | Joris (retention) | Notion campaign page | Vaderdag Bundel and gift subscriptions, 14 to 21 June. Gift MRR is zero by design. |

### `metric_changelog` rows (verbatim)

| metric | version | valid_from | definition | reason for change |
|---|---|---|---|---|
| subscriber_churn_rate | v1 | 2025-01-01 | Cancelled in month / active at month start. Failed payments count as churn on day one | Initial definition |
| subscriber_churn_rate | v2 | 2026-05-01 | As v1, with a 30-day dunning grace before a failed payment counts as churn | Recharge dunning recovers a material share of failed payments; day-one counting overstated losses |

"Active at month start" means active or paused, excluding gift subscriptions, as defined in "Numbers that must reconcile".

### Directory layout inside `kelder-dbt/` (from the article)

```
kelder-dbt/
├── AGENTS.md                  # agent instructions, < 300 lines, hand-written
├── models/
└── context/
    ├── glossary.md
    ├── metric_changelog.md
    ├── decisions/
    │   ├── 0007-recharge-migration-churn-artifacts.md
    │   └── 0009-churn-v2-dunning-grace.md
    └── quirks/
        └── gift_subscriptions.md
```

### Decision record 0007 (verbatim)

```markdown
# 0007: Recharge migration wrote false churn events

Date: 2026-03-14 · Status: accepted · Owner: Sanne (data)

## Context

The 12 March billing migration backfilled Recharge subscription
statuses. Recharge has no "paused" state in the legacy import path,
so ~1,900 paused subscriptions arrived as "cancelled", writing
churned_at timestamps that never happened.

## Decision

Flag affected rows with is_migration_artifact = true. Exclude
flagged rows from churn metrics. Report both raw and adjusted
churn for March 2026 in any board-facing number.

## Rejected alternative

Deleting the rows. Finance reconciles against Recharge exports,
so the raw record must match source.

## Consequences

March raw churn (9.4%) and adjusted churn (3.3%) will both exist.
Anyone quoting March churn without the adjustment is wrong.
```

### Decision record 0009 (write to this specification, in the same format)

- Title: `0009: Churn v2, 30-day dunning grace`
- Date 2026-04-28 · Status: accepted · Owner: Sanne (data), agreed with Femke (finance)
- **Context:** under v1 a failed payment counts as churn on the day it fails. Recharge dunning retries recover a material share of failed payments within 30 days, so v1 overstated losses.
- **Decision:** from 1 May 2026, a failed payment counts as churn only if it is not recovered within 30 days, attributed to the month of the first failure. The as-reported series keeps v1 for months before May. A restated v2 series covers all months for like-for-like comparisons.
- **Rejected alternative:** silently restating all history under v2, because board decks had already quoted v1 figures.
- **Consequences:**
  - Churn falls on 1 May for definitional reasons, by roughly half a percentage point on Q1 2026 recoveries.
  - Comparisons across 1 May must use the restated series.
  - The most recent month is provisional under v2 until 30 days have passed, and will be revised upward.

Do not quote precise figures in 0009 beyond "roughly half a percentage point", because the record predates May's data. The target test for the v1 to v2 gap makes that statement true.

### Pull request template (verbatim)

```markdown
## What changed

## Why (business context, not implementation detail)

## Metric impact

- [ ] No user-visible metrics move
- [ ] Metrics move: metric_changelog updated
- [ ] Metrics move: business_events row added
- [ ] Decision record added or superseded (link)
```

### Verified questions in the article (keep this wording)

| Verified question | Pins down |
|---|---|
| What was subscriber churn last month? | v2 definition, artefacts excluded |
| What was real churn in March 2026? | Raw and adjusted both returned, adjustment named |
| Which channel has the best CAC? | Attribution window and channel grouping |
| How did the Father's Day bundle perform? | Bundle SKU list, promo date range from business_events |

### The answer the with-context agent should be able to give to "Why did subscriber churn spike in March 2026?" (from the article)

> Raw churn in March was 9.4 percent against a trailing average of 3.1 percent. The business_events table shows a billing migration on 12 March that wrote cancelled statuses to around 1,900 paused subscriptions (decision record 0007). Excluding flagged artefacts, adjusted churn was 3.3 percent, in line with trend. One caution for year-on-year comparisons: the churn definition changed on 1 May 2026, so pre-May figures use the old definition.

This is the reference for classifying answers in the written workspace. Do not put this text in any workspace.

### Calendar checks

| Date | Day | Note |
|---|---|---|
| 2025-11-28 | Friday | Black Friday |
| 2026-03-12 | Thursday | Migration; CET, so 00:00 UTC is 01:00 local |
| 2026-03-14 | Saturday | Decision 0007 written |
| 2026-03-28 | Saturday | Pause-instead-of-cancel campaign |
| 2026-03-29 | Sunday | Clocks change to CEST |
| 2026-04-09 | Thursday | Klaviyo outage; campaign at 10:00 CEST, 08:00 UTC |
| 2026-05-01 | Friday | Churn v2 |
| 2026-05-19 | Tuesday | PostNL strike |
| 2026-06-14 | Sunday | Bundle campaign starts |
| 2026-06-21 | Sunday | Father's Day, Netherlands |