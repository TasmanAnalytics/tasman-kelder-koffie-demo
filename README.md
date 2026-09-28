# Kelder Coffee: a data context layer demo

> Evidence for **"Building a data context layer to fix your AI analytics"**, by Thomas in't Veld
> (Tasman Analytics), Compass AI & Tech Summit, Budapest, 1 October 2026.

**New machine or new Claude Code session? Read [`START_HERE.md`](START_HERE.md) first** (`make setup`, `make all`, `make demo`, `make doctor`).

**Then open [`index.html`](index.html)** (or run `make index` first). It is a one-page map of
the evidence, the numbers, the commands and the files. Every number on it is read from the build.

Kelder Coffee is a fictional Amsterdam coffee subscription company from Tasman's July 2026 article
*How to Build a Context Layer (Because You Cannot Buy One)*. Its warehouse is well modelled. Six
things happened in the first half of 2026 that nobody wrote down, and an AI agent explains them
wrongly, with confidence. Write the context down and the agent gets them right. Then one ordinary
commit makes that written context false, and only a forcing function in CI notices.

| Claim | Evidence in this repo |
|---|---|
| 1. Agents on a good warehouse still explain numbers wrongly | `installed` workspace; `charts/out/cancellations_by_hour_feb_mar_2026`; trials |
| 2. Writing the context down fixes most of it | `kelder-dbt/` at `kelder/with-context`; `written` workspace; `charts/out/churn_monthly_2026_events` |
| 3. Written context decays | the `kelder/rot` commit; `rot` workspace; `charts/out/yoy_like_for_like_written_vs_rot` |
| 4. Forcing functions catch the decay | `make check STATE=rot PR_BODY=kelder-dbt/.pr/rot.md`; `.github/workflows/ci.yml` |

## Quick start

```
uv sync
make all                 # generate data, load, build all three states, run the tests, render charts and index.html
```

About three minutes on a recent MacBook. Needs [uv](https://docs.astral.sh/uv/) and git; Python 3.12
and every package are pinned in `uv.lock`.

## How it fits together

```
generator/  ──► data/raw/*.parquet ──► loader/ ──► kelder_raw.duckdb ──► dbt build (per state) ──► kelder_<state>.duckdb
   │                                                                                                   │
   └──► data/truth/kelder_truth.duckdb   (hidden ground truth: builder tests only)                     ▼
                                                                          ~/kelder-demo/<workspace>/ (agent sees only this)
```

- **Generator** (`generator/`): simulates every customer and subscription from launch (April 2023) to
  August 2026, pinned so monthly churn hits the calibration targets exactly. It renders the world
  through Shopify, Recharge, Klaviyo and the ad platforms, then applies the incidents as logged
  transformations. Deterministic from the seed in `generator/config.yaml`; no language model is involved.
- **Truth** (`data/truth/kelder_truth.duckdb`): what really happened. The with-context warehouse must
  equal it exactly, numerator and denominator. It never reaches a warehouse or a workspace.
- **Kelder's repo** (`kelder-dbt/`): a normal dbt project in three states, all git references:

| State | Reference | What changes |
|---|---|---|
| before-context | tag `kelder/before-context` | Competent, documented, no context layer. March 2026 churn reads 9.4%. |
| with-context | tag `kelder/with-context` | Caveats, `context.business_events`, `context.metric_changelog`, decision records, glossary, quirks, verified queries, `AGENTS.md`, pull request template. |
| rot | tag and branch `kelder/rot` | One commit, "Fix churn logic", points the restated series at the unadjusted events. The context is unchanged. |

`git log --oneline -- kelder-dbt/` reads as Kelder's own history (Sanne de Vries, January to June 2026).

## Everyday commands

| Command | Does |
|---|---|
| `make generate` | Parquet, truth DB, `data/profile_report.md` |
| `make load` | `data/warehouse/kelder_raw.duckdb` |
| `make build STATE=with_context` | one state (`before`, `with_context`, `rot`) from its git reference |
| `make test` | targets, realism, incidents, determinism, truth, verified queries |
| `make check STATE=rot PR_BODY=kelder-dbt/.pr/rot.md` | what CI runs: verified queries against pinned answers, plus the context capture check |
| `make freeze-verified APPROVED_BY="..."` | pin verified answers from with-context; refuses unless the truth tests pass |
| `make charts` / `make index` | slide charts / the start page |

Never re-freeze verified answers to make a failing check pass. Each freeze is logged in `BUILD_LOG.md`.

## Agents

The agent tooling is pinned and installed outside the repo, never globally:

```
tools/demo/setup.sh      # ~/kelder-demo/_tools/npm: Claude Code 2.1.281, ktx 0.16.0 (read-only patch), Node 22
```

Context is served to agents by **ktx**, Kaelio's open-source context layer. Each state was ingested
once (`scripts/ktx_build.py <state>`), and the output is stored in `demo/ktx/<state>/`. Ingest uses a
language model, so it is never regenerated casually. `demo/selected/ingest_before_summary.md`
describes what ktx derived from the before-context state without any written context.

```
make workspaces                                   # ~/kelder-demo/{installed,written,rot}
make serve                                        # one ktx MCP server per workspace (make serve-status, make serve-stop)
make leak-check                                   # fails if any workspace could see the answer
uv run python scripts/verify_isolation.py         # dry runs: tools, denied reads, AGENTS.md loads
make trials WORKSPACE=installed N=3               # needs ANTHROPIC_API_KEY in .env (see .env.example)
make summary                                      # demo/trial_summary.md and demo/labels/labels.csv
scripts/demo_terminal.sh side-by-side             # clip 1; `rot` for clip 2
```

Isolation, enforced and tested:

- The workspaces contain only Kelder's repo at one state, a warehouse copy and the ktx project. There is no truth DB, generator, brief, git history or pinned answers.
- The agent can use only Read, Grep, Glob and the ktx tools. Bash, web search and web fetch are removed. Reads of the build repo and of sibling workspaces are denied.
- SQL is read-only, and DuckDB file access is disabled, so `read_csv('/etc/hosts')` fails. The leak check probes this live.
- Runs use a dedicated Claude Code configuration directory and only project settings. No personal memory, instructions or MCP servers load.
- The model is pinned (`KELDER_MODEL`, default `claude-opus-5-5`). Every transcript is kept in `demo/runs/`.

## Where to read more

- [`TALK_FLOW.md`](TALK_FLOW.md): the talk's flow, numbers and trial findings in one file.

- [`BUILD_BRIEF.md`](BUILD_BRIEF.md): the full specification.
- [`BUILD_LOG.md`](BUILD_LOG.md): every deviation, judgement call and checkpoint.
- [`data/profile_report.md`](data/profile_report.md): a ten-minute sniff test of the generated data.
- [`thinking/`](thinking/): design notes (generator, git history, ktx findings).
