# ktx smoke test findings (2026-09-24)

Run by a subagent in a throwaway folder outside the repo
(`$SCRATCHPAD/ktx-smoke/`: env.sh, mcpcall.sh, mcp.json, tools.json, logs, ktxproj/).

## Verdict

The path works except `ktx ingest`, which needs a working LLM. There is no offline mode.
No ANTHROPIC_API_KEY in the environment; the keyless `claude-code` backend strips
ANTHROPIC_BASE_URL/ANTHROPIC_API_KEY and needs a plain-terminal `claude /login`.
Headless Claude reached the ktx MCP server, then got a 401 (expired OAuth token). Cost $0.

## Facts

- Package `@kaelio/ktx@0.16.0` (released 2026-07-03, adds DuckDB). No release since; last commit 2026-07-07.
  The unscoped npm `ktx` is unrelated.
- Needs Node 22+. Node 20.11.1 (installed) crashes. Local `node@22` from npm plus
  `npm install --save-exact @kaelio/ktx@0.16.0` works without a global install.
- Ingest LLM providers: `anthropic` (ANTHROPIC_API_KEY), `vertex`, `gateway`, `claude-code` or `codex` (local login).
  Embeddings: `openai` (OPENAI_API_KEY) or local `sentence-transformers`.
  Only no-LLM path: `ktx ingest --file x.md --verbatim` for wiki pages.
- Wiki location fixed at `<project>/wiki/`, no config key. Symlinks ignored. So `wiki/` must be generated
  from `context/` (make step + test that they match).
- ktx runs `git init` and auto-commits in its project dir: nested `.git` inside a dbt repo.
  Workspaces must not contain `.git` (leak check), so strip it or keep ktx state outside the extracted repo.
- Read-only: DuckDB opened read-only, parser allows one read-only statement. Writes rejected.
  **But `select * from read_csv('/etc/hosts')` succeeded: agents can read arbitrary local files through SQL.**
  That is a leak path to the build repo (BUILD_BRIEF.md, truth DB). Must be closed or mitigated.
- Telemetry on by default. Off: `KTX_TELEMETRY_DISABLED=1` or `DO_NOT_TRACK=1`. Also `KTX_NO_UPDATE_CHECK=1`,
  `KTX_RUNTIME_ROOT=<dir>` (else writes `~/.ktx`).
- MCP: `ktx mcp start --port 7979` -> `http://127.0.0.1:7979/mcp` (default 7878). Stop: `ktx mcp stop`, `ktx admin runtime stop`.
  Tools: connection_list, wiki_search, wiki_read, sl_read_source, sl_query, entity_details, dictionary_search,
  discover_data, sql_execution, sql_dialect_notes (+ memory_ingest* with an LLM).
- `ktx setup --agents --target claude-code --install-dir <dir>` writes `.mcp.json` and a skill file.
- Layout: ktx.yaml, semantic-layer/, wiki/, raw-sources/, .ktx/. Commit first three; ignore .ktx/ (and raw-sources/).

## Gotchas

1. DuckDB connector only reads the `main` schema; 0 tables found elsewhere, no warning.
2. DECIMAL results fail with `Do not know how to serialize a BigInt`. Cast money columns to DOUBLE.
3. `claude -p` hangs without `< /dev/null`.
4. `ktx setup --no-input` needs an explicit `--llm-backend`.

## Commands that worked

```
ktx setup --project-dir ./ktxproj --no-input --yes --skip-llm --skip-embeddings --database duckdb \
  --database-connection-id shop --database-url $PWD/data/shop.duckdb --source dbt --source-connection-id dbt_shop \
  --source-path $PWD/shop_dbt --source-profiles-path $PWD/shop_dbt --source-target dev --source-warehouse-connection-id shop
ktx ingest --file ../shop_dbt/context/revenue.md --verbatim --connection-id shop
ktx admin reindex; ktx status; ktx mcp start --port 7979
claude -p "..." --mcp-config mcp.json --strict-mcp-config --output-format json --max-turns 10 --allowedTools "mcp__ktx__*" < /dev/null
```

## Fallback

`uvx mcp-server-motherduck` (v1.0.8): read-only by default for local files; `--read-write` to write;
`--ephemeral-connections` keeps the file unlocked. Example:
`uvx mcp-server-motherduck --db-path /abs/shop.duckdb --ephemeral-connections`.
Need to check whether it also allows read_csv of arbitrary files (probably yes).

## Consequences for the build

- Marts that ktx should discover must live in `main` (or ktx sees nothing). Plan: dbt writes marts and
  context models to schemas as normal, and the workspace warehouse copy gets `main` views over them? Decide
  when wiring ktx. The `context.business_events` table is still queryable through sql_execution.
- Money columns as DOUBLE in marts.
- Close the file-read leak: a DuckDB MCP server that opens the file with `enable_external_access = false`
  (our own minimal server, or check whether ktx accepts DuckDB config), and a leak test that tries
  `read_csv`/`read_text`/`glob` through the served tool and expects failure.
- Keys: ktx ingest needs ANTHROPIC_API_KEY (or claude login); trials need the same. Ask Thomas.
