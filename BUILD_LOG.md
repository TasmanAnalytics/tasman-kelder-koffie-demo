# Build log

Decisions, deviations from `BUILD_BRIEF.md`, judgement calls and open questions.
Newest checkpoint at the bottom of each section.

## Deviations and judgement calls

| Date | Area | Decision | Reason |
|---|---|---|---|
| 2026-09-24 | Repo | The build repository is this folder (`tasman-kelder-koffie`), standing in for `kelder-coffee/`. `initial-brief.md` renamed to `BUILD_BRIEF.md`. | The brief names the brief file `BUILD_BRIEF.md`; the leak check looks for that name. |
| 2026-09-24 | Calibration | The article chart (labelled illustrative) reads Jan 3.0, Feb 3.1, Mar 9.4/3.3, Apr 3.4, May 2.6, Jun 2.7 by pixel measurement. Jan and Apr differ from the calibration table by more than 0.2 points. Thomas chose to keep the brief's table. | Brief section 3.5 requires stopping to ask. |
| 2026-09-24 | Generator | Time is kept internally as local Amsterdam wall seconds; a small DST converter replaces pandas tz handling and is checked against zoneinfo. | Keeps "05:00 local" stable across daylight saving changes; deterministic and fast. |
| 2026-09-24 | Generator | Retail orders, email engagement and ads live in `generator/world_commerce.py`, beside `world.py`. | Keeps `world.py` about subscriptions. The layering is unchanged. |
| 2026-09-24 | Generator | Some incidents are world-level (billing freeze moves charges, PostNL strike delays parcels and causes refunds, restores decide when artefact subscribers resume). Rendering-level incidents (Recharge import damage, Klaviyo outage) are applied to clean rendered tables. Both kinds are written to the incident manifest; the incident tests diff clean and damaged tables against it. | Customers experienced the first kind, so it must change behaviour; only the data is wrong in the second. |
| 2026-09-24 | Generator | Queued genuine cancellations: the Shopify app stopped processing cancellations from 2026-03-05 00:00 local; every voluntary cancellation requested from then until the import is queued. Result: 142 (target 120 to 180). | Needs a window of about a week to reach the target at Kelder's cancellation rate. |
| 2026-09-24 | Generator | Freeze snapshot = the Shopify connector's last sync, 2026-03-11 21:30 UTC. Paused at that instant = migration artefact. Shopify pauses can start until 2026-03-11 20:00 local; sign-ups during the freeze arrive after it. | Makes "PAUSED at the last sync" exact. |
| 2026-09-24 | Generator | Artefact subscribers resume in the world at their restore time (weekday 09:15 on or after the original pause end, from 16 March). | Lets the adjusted warehouse logic equal the truth exactly. |
| 2026-09-24 | Generator | The paused count at the freeze is pinned by boosting February 2026 pause starts with a solved multiplier and setting the exact number of 1 to 11 March Shopify pauses. February's pause rate is therefore high (3.1%). | Brief step 8. The natural paused stock was about 1,550; the solver needs 1,903. |
| 2026-09-24 | Generator | July and August 2026 are simulated with pinned counts at June's 2.8%. | This is how "June 2026 hazard levels" is implemented. |
| 2026-09-24 | Generator | Warm-up applies the recurring seasonal multipliers every year (November x1.7, December x1.2, July and August x0.85); January 2026 x1.4 and June 2026 x1.15 apply once. | The brief lists the 2025 to 2026 curve; warm-up needs a seasonal shape too. |
| 2026-09-24 | Generator | A subscription with an open dunning episode at month start gets no new events that month. | Simplification; keeps one open episode per subscription. |
| 2026-09-24 | Generator | Subscription price per shipment = bags x list price x 0.9, plus EUR 4.95 shipping for a single 250 g bag. Most shipments are EUR 15 to 30; 1 kg and three-bag plans sit above EUR 30. | Keeps prices tied to the catalogue. |
| 2026-09-24 | Generator | Klaviyo `Placed Order` events exist for web orders by profiles, not for subscription renewals. | Renewals would dominate volume and blur attribution. |
| 2026-09-24 | Generator | Data cutoff is 2026-07-01 00:00 Amsterdam time (2026-06-30 22:00 UTC). v2 "as of 1 July" counts a failed payment only if its day-30 cancellation happened before the cutoff. | Makes "knowable on 2026-07-01" exact. |
| 2026-09-24 | Generator | Shopify contracts carry `origin_order_id` (a real Shopify field) so the first-order channel can be attributed. Contracts from before 2025 point at order ids that were never synced. | CAC by channel needs a link from subscription to first order. |
| 2026-09-24 | Generator | Retail average order value is EUR 31.3 (target about 32). | Close enough; tuning further is not worth the time. |
| 2026-09-24 | ktx | Smoke test: `@kaelio/ktx@0.16.0` (released 2026-07-03, no later release). It needs Node 22+ (Node 20.11 is installed; a local node 22 works without a global install). Ingest needs an LLM: ANTHROPIC_API_KEY, Vertex, a gateway, or a `claude-code`/`codex` login. Embeddings: OPENAI_API_KEY or local sentence-transformers. The wiki location is fixed at `<project>/wiki/`. Warehouse access is read-only, but `read_csv('/etc/hosts')` works through `sql_execution`. Telemetry off: `KTX_TELEMETRY_DISABLED=1` or `DO_NOT_TRACK=1`, plus `KTX_NO_UPDATE_CHECK=1` and `KTX_RUNTIME_ROOT`. The DuckDB connector only reads the `main` schema, and DECIMAL results fail to serialise. Full notes: `thinking/ktx_findings.md`. | Brief 7.1. Ingest is blocked on a key Thomas must supply. |
| 2026-09-24 | dbt | Marts materialise in the `main` schema. Context tables go in `context`, seeds in `context_seeds`/`reference`, staging in `staging`, intermediate models in `intermediate`. Money columns are DOUBLE. | ktx's DuckDB connector only sees `main` and cannot serialise DECIMAL. |
| 2026-09-24 | dbt | Context seeds are named `business_events` and `metric_changelog`. The models are `context_business_events` and `context_metric_changelog`, aliased to `context.business_events` and `context.metric_changelog`. | dbt forbids a seed and a model with the same name. |
| 2026-09-24 | dbt | The before-context source description does not say when the Shopify connector stopped. It says "current state as of the connector's last sync (see _fivetran_synced)". | A stated pause date would hint at the migration in the before-context state. |
| 2026-09-24 | dbt | Terminal status comes from current-state rows (Shopify contract, Recharge subscription), not from the webhook logs. Payment episodes are keyed by billing cycle date, parsed from the Shopify idempotency key and from Recharge `scheduled_at`. | Exact month attribution, including episodes that began before the data starts and episodes carried across the migration. |
| 2026-09-24 | Git | `kelder/before-context` is a tag on a side branch off the initial models, with one commit adding the plain 30-day rule from May (dated 2026-04-28). Main carries the with-context history (C3 to C10, 2026-03-14 to 2026-06-19, release tag `v2026.03.2`). `kelder/rot` is one commit on top of `kelder/with-context`. See `thinking/git_history_plan.md`. | Before-context must contain the May switch, which in Kelder's history arrived after context work began. |
| 2026-09-24 | Git | In-universe commits (author Sanne de Vries, backdated) carry no Co-Authored-By trailer; builder commits do. | They must read as Kelder's own history on stage. |
| 2026-09-24 | Git | A dbt singular test, "restated v2 never above v1", was removed from in-universe history with `filter-branch`, and the tags were rewritten. Nothing had been pushed. | It caught the rot on its own. The brief requires the rot to fail exactly the verified queries and the capture check, and to pass everything else. |
| 2026-09-24 | Rot | The rot commit also adds `kelder-dbt/.pr/rot.md` (the pull request body). Its model diff touches only `metrics_subscriber_churn_monthly.sql`: 6 lines removed and 1 line changed. | The brief asks for the body at that path. |
| 2026-09-24 | Verified | `verified_queries.yml` names the adjustment and the fact behind it, but contains no numbers. `AGENTS.md` states the core fact without the 9.4% and 3.3% figures, which live in decision 0007 (verbatim). | Keeps expected results out of workspaces. |
| 2026-09-24 | Verified | Expected results are NOT frozen yet. The check tooling was exercised against a scratch copy in the session scratchpad, not `tests/verified/expected/`. | Freezing needs Thomas's go-ahead. |
| 2026-09-24 | AGENTS.md | Draft written (62 lines, `kelder-dbt/AGENTS.md`, committed in C10). It must be rewritten by Thomas before any trial. | Brief 6.3. |
| 2026-09-24 | Serving | Trials and recordings use the fallback server for now: MotherDuck's `mcp-server-motherduck==1.0.8`, pinned in the project environment. It serves each workspace's DuckDB file read-only on one persistent connection (`--no-ephemeral-connections`), with `SET enable_external_access = false; SET lock_configuration = true` and FastMCP's update check off. The leak check probes each server live: plain queries work; `read_csv`, `read_text`, `glob`, `ATTACH`, writes and setting changes are refused. | ktx ingest is blocked on an LLM key, and ktx's `sql_execution` can read local files. Upstream gotcha: in the default ephemeral mode the server skips `--init-sql` for query connections, so `read_csv('/etc/hosts')` works. |
| 2026-09-24 | Isolation | Agents run with `--tools Read,Grep,Glob`, `--mcp-config <workspace>/.mcp.json --strict-mcp-config`, `--setting-sources project`, `--permission-mode dontAsk`, `--disable-slash-commands`, `--no-session-persistence`, a dedicated `CLAUDE_CONFIG_DIR` (`~/kelder-demo/.claude-config`) and a scrubbed environment (`scripts/agent_cmd.py`). A free dry run without credentials shows the init message lists exactly Glob, Grep, Read and the four warehouse tools, with the MCP server connected and no skills or plugins. Claude Code 2.1.25. | Brief section 8. `CLAUDE_CONFIG_DIR` may only redirect credentials, so user-level settings and MCP servers are also excluded by flags, and the leak check asserts there is no `~/.claude/CLAUDE.md` and no auto-memory for the workspaces. |
| 2026-09-24 | Workspaces | `kelder-dbt/.pr/` is not copied into workspaces. `written/` and `rot/` get a root `CLAUDE.md` containing only `@kelder-dbt/AGENTS.md`, because Claude Code reads AGENTS.md only from the working directory upwards and the agent runs from the workspace root. The `bare` workspace is not built. | The PR body is not normally part of a repository. `bare` is cut 4, and under the fallback it would be identical to `installed`. |
| 2026-09-24 | Charts | Charts are rendered with fallback fonts (Georgia, Menlo, Helvetica Neue) until EB Garamond and Roboto Mono are in `charts/fonts/`. Event labels are `<date> <event_type>`, read from `context.business_events`. The 9 April point in the email chart is a brick marker, because the bar is EUR 0. | Downloading the fonts needs Thomas's go-ahead. `business_events` has no short-label column. |
| 2026-09-24 | Working notes | A `thinking/` folder holds design notes and decisions. It is builder-only and never reaches a workspace. | Requested by Thomas. |

## Open questions (waiting for Thomas)

1. `ANTHROPIC_API_KEY` in `.env`: needed for trials, for `scripts/verify_isolation.py`, and for ktx ingest.
2. `AGENTS.md`: rewrite `kelder-dbt/AGENTS.md` by hand (draft at tag `kelder/with-context`). The rewrite then gets committed in-universe before the with-context tag, and the rot commit is replayed on top.
3. Freeze verified results: `make freeze-verified APPROVED_BY="Thomas, <date>"`. Until then `make check` reports "no frozen expected result" and two verified tests skip.
4. Download EB Garamond and Roboto Mono (Google Fonts, OFL, about 1 to 2 MB) into `charts/fonts/`.
5. `brew install tmux` for the side-by-side clip.
6. ktx or the fallback for trials. ktx needs Node 22 (local install), an LLM key for ingest, and a fix for file reads through `sql_execution`.
7. A private GitHub repository and a pull request from `kelder/rot` for the red-check screenshot. Nothing has been pushed.

## Checkpoints

### 2026-09-24, workspaces, leak check, charts, harness

- `make all` on the current checkout takes 3 minutes. All tests pass: 52 data, 26 truth and verified (3 skipped until the freeze), 23 leak.
- Workspaces `installed`, `written` and `rot` are in `~/kelder-demo/`, and the leak check passes, including live MCP probes.
- Five charts are in `charts/out/` (SVG, 2400x1350 PNG, JSON).
- Trial harness, summariser, isolation dry run and terminal script are written. No trial has run: there are no credentials, and AGENTS.md is still a draft.

### 2026-09-24, generator, warehouse states and checks

- Generator: `uv run python -m generator.generate` takes about 50 s. Every target in "Numbers that must reconcile" passes (the truth table `targets`; `data/profile_report.md`).
  Base on 1 Jan 2025 is 19,987; base on 1 Mar 2026 is 31,194. There are 1,903 artefacts. March v1 is 9.40% raw and 3.30% adjusted. There are 142 queued genuine cancellations.
  The Sep to Feb mean is 3.10%. v1 minus restated v2 averages 0.52 pp over Jan to Mar 2026. Restated v2 improves by 0.40 pp from H1 2025 to H1 2026. As-reported May 2026 (v2, 2.42%) is below April (v1, 2.80%).
- Data tests: 9 targets, 9 realism, 12 incidents and determinism (byte-identical Parquet) all pass.
- Warehouse: `kelder_raw.duckdb` is loaded, and before, with_context and rot are built from their git refs. dbt build passes in all three states.
- Truth tests: 16 of 16 pass. With-context equals the truth exactly for base, v1, restated v2 as of 1 July, as-reported, new subscribers, pause starts, paused counts, daily email attribution and flag counts. Before-context shows 9.4% for March and counts restores as new.
  In rot, March restated v2 jumps 6.1 pp, the H1 comparison flips to "worse", and the as-reported series is unchanged.
- Check tooling: `make check STATE=rot PR_BODY=kelder-dbt/.pr/rot.md` fails `churn_yoy_like_for_like` and the capture check (0 boxes ticked); the other six verified queries pass. This ran against scratch expected results, because the real freeze is pending.
