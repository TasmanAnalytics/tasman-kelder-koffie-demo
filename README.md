# Kelder Coffee: a data context layer demo

Evidence for the talk "Building a data context layer to fix your AI analytics" (Thomas in't Veld,
Tasman Analytics, Compass AI & Tech Summit, 1 October 2026). Kelder Coffee is a fictional
Amsterdam coffee subscription company from Tasman's article "How to Build a Context Layer
(Because You Cannot Buy One)", July 2026.

The repository holds a deterministic data generator, a DuckDB warehouse modelled with dbt in three
states, agent workspaces, a trial harness and the slide charts. `BUILD_BRIEF.md` is the full
specification; `BUILD_LOG.md` records every deviation and judgement call.

## What is where

| Path | What |
|---|---|
| `generator/` | World simulation, source-system rendering (Shopify, Recharge, Klaviyo, ads), incidents, truth DB. All parameters and the seed are in `config.yaml`. |
| `loader/load_raw.py` | Parquet into `data/warehouse/kelder_raw.duckdb` (`raw_*` schemas, Fivetran columns). |
| `kelder-dbt/` | Kelder's own analytics repository. Its three states are git references (below). |
| `scripts/` | Build a state from a git ref, checks, workspaces, trials, recordings. |
| `tests/` | Targets, realism, incidents, determinism, warehouse truth, verified queries, leak check. |
| `charts/` | `render.py` and the rendered charts (`charts/out/`: SVG, PNG 2400x1350, JSON of the values). |
| `demo/` | Prompts, trial runs (git-ignored), labels, selected answers. |
| `thinking/` | Working notes and design decisions. Builder-only. |
| `data/` | Generated data and warehouses (git-ignored). |

## The three states of `kelder-dbt/`

| State | Git reference | What it is |
|---|---|---|
| before-context | tag `kelder/before-context` | A competent, documented dbt project with no context layer. March 2026 churn reads 9.4%. |
| with-context | tag `kelder/with-context` | The article's end state: caveats, `context.business_events`, `context.metric_changelog`, decision records, glossary, quirks, verified queries, `AGENTS.md`, pull request template. |
| rot | tag and branch `kelder/rot` | One commit on top of with-context ("Fix churn logic") that points the restated churn series at the unadjusted events. Every piece of context still claims otherwise. |

`git log --oneline -- kelder-dbt/` shows Kelder's own history (author Sanne de Vries, backdated
January to June 2026). `scripts/build_state.py <state>` extracts `kelder-dbt/` at the reference with
`git archive` and builds that state's warehouse with the current generator, loader and tests.

## Reproduce everything

Requirements: macOS or Linux, [uv](https://docs.astral.sh/uv/), git. Python 3.12 and every package
are pinned in `uv.lock`.

```
uv sync
make all          # generate, load, build all three states, run the tests, render the charts
```

Individual steps:

```
make generate                 # data/raw/*.parquet, data/truth/kelder_truth.duckdb, data/profile_report.md
make load                     # data/warehouse/kelder_raw.duckdb
make build STATE=with_context # or before, rot
make test                     # data and warehouse tests
make check STATE=rot PR_BODY=kelder-dbt/.pr/rot.md   # verified queries + context capture check, as CI runs them
make charts
```

`make check` compares verified-query results with pinned answers in `tests/verified/expected/`.
They are written by `make freeze-verified APPROVED_BY="..."`, which refuses unless every truth test
passes. Never re-freeze to make a failing check pass.

## Agent workspaces

```
make workspaces   # ~/kelder-demo/{installed,written,rot}
make leak-check   # fails if any workspace could see the answer
```

Each workspace holds only what a Kelder employee's agent would see: `kelder-dbt/` at one state (no
`.git`), a copy of that state's warehouse, one MCP server serving it read-only with file-system
access disabled, and settings that allow only Read, Grep, Glob and the warehouse tools. Agents run
with a dedicated Claude Code configuration directory, so no personal memory, instructions or MCP
servers load. The launch command for trials and recordings is defined once, in
`scripts/agent_cmd.py`.

Trials (need `ANTHROPIC_API_KEY` in `.env`; see `.env.example`):

```
uv run python scripts/verify_isolation.py        # dry runs: tools, denied reads, AGENTS.md loads
make trials WORKSPACE=installed PROMPTS=all N=3
make summary                                     # demo/trial_summary.md and demo/labels/labels.csv
```

Recordings: `scripts/demo_terminal.sh setup`, then `side-by-side` (clip 1) or `rot` (clip 2).

## Honesty rules

The generator never calls a language model. The truth database never reaches a warehouse or a
workspace. Every trial run is kept and counted. See `BUILD_BRIEF.md` section 9.3.
