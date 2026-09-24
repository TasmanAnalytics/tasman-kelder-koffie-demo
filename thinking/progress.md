# Progress

## Done (2026-09-24)
- Scaffold, uv env, git.
- ktx smoke test (subagent): see ktx_findings.md. Blocked on an LLM key for ingest.
- Generator complete: world, commerce, Shopify/Recharge/Klaviyo/ads rendering, incidents with manifest, truth DB, profile report.
  `uv run python -m generator.generate` ~55 s. All targets pass.
- Tests: targets (28+), realism (9), incidents (12, diff clean vs damaged == manifest), determinism (hash equality).

## Next
- loader/load_raw.py -> kelder_raw.duckdb
- kelder-dbt before-context, then with-context, then rot; in-universe commits as Sanne.
- scripts/build_state.py, Makefile.
- truth tests on the warehouse; verified queries; capture check; CI.
- Workspaces, leak check, MCP server (own read-only DuckDB server with external access off?), charts.

## Dev tips
- KELDER_BUILD_CACHE=<scratchpad>/build.pkl caches the in-memory build for the incident tests.
