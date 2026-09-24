# What ktx derived unaided: before-context ingest

ktx 0.16.0 was pointed at the before-context warehouse and the before-context dbt project, with no
written context. The ingest ran on 24 September 2026 from 16:14 to 16:20, with LLM enrichment
(`claude-sonnet-4-5`, `claude-opus-4-5`, `claude-haiku-4-5`) and local embeddings (`all-MiniLM-L6-v2`).
The output is stored in `demo/ktx/before/` and reused by the `installed` workspace.

## What it produced

- A semantic-layer source for each of the nine marts in `main` (`semantic-layer/kelder/*.yaml`). The
  descriptions are the dbt descriptions, carried over.
- Ten wiki pages (`wiki/global/`), written by the LLM from the dbt project:
  email attribution, gift subscription exclusions, channel attribution, payment retries and dunning,
  product types, reporting time zone, shipping regions and carriers, subscriber churn definition,
  billing intervals, and the unified subscription model.

## Search for the six events

Searched every file for 12 March, the migration, midnight clustering, restores, artefacts, backfills,
the outage, the strike and the 1 May definition change.

| Looked for | Found |
|---|---|
| "migration" | **Yes, as a correct inference.** `unified-subscription-model.md` says keys stay "stable across Shopify and Recharge migrations" and "continuity across the migration". It inferred from the key logic (a Recharge subscription carrying a Shopify contract id continues that key) that subscriptions moved between systems. |
| 12 March 2026 | No |
| Midnight clustering of cancellations, null reasons | No. "00:00" appears only as the Amsterdam month boundary. |
| Paused subscriptions written as cancelled; artefacts; backfill | No |
| Restores, legacy pause | No |
| Klaviyo outage, PostNL strike | No |
| 1 May 2026 switch to the 30-day rule | No |

Both inferences are kept exactly as ktx wrote them. The leak check reports them and does not fail on them.

## A plausible but wrong statement

`subscriber-churn-definition.md` says churn counts "subscriptions whose payment failed in the month
(dunning episodes that did not recover)", and `payment-retry-dunning-logic.md` repeats "failed in a
month (and did not recover)". That is only true from May 2026. Before May, every failed payment counts
on the day it fails, recovered or not. The SQL shows both rules; the tool generalised the newer one.

So the tool gets the definition half right and states it with confidence. It knows that a migration
happened, but not when, and not that it broke March.
