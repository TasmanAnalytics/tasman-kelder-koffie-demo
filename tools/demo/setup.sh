#!/usr/bin/env bash
# Install the pinned agent tooling into ~/kelder-demo/_tools/npm (never globally) and apply the
# ktx read-only patch. Idempotent.
#
# Patch: ktx 0.16.0 opens DuckDB with only access_mode=read_only, so SQL through its
# sql_execution tool can still read any local file (read_csv, read_text, glob). The patch adds
# enable_external_access=false and lock_configuration=true to that one DuckDBInstance.create call.
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
DEST="${KELDER_DEMO_DIR:-$HOME/kelder-demo}/_tools/npm"
command -v npm >/dev/null || { echo "npm not found: install Node.js 18 or newer first (for example: brew install node)" >&2; exit 1; }
mkdir -p "$DEST"
cp "$HERE/package.json" "$HERE/package-lock.json" "$DEST/"
(cd "$DEST" && npm ci --no-fund --no-audit --loglevel=error)
F="$DEST/node_modules/@kaelio/ktx/dist/connectors/duckdb/connector.js"
OLD="DuckDBInstance.create(this.dbPath, { access_mode: 'read_only' })"
NEW="DuckDBInstance.create(this.dbPath, { access_mode: 'read_only', enable_external_access: 'false', lock_configuration: 'true' })"
if grep -qF "$NEW" "$F"; then echo "ktx patch already applied"
elif grep -qF "$OLD" "$F"; then
  "$DEST/node_modules/.bin/node" -e 'const fs=require("fs");const [p,o,n]=process.argv.slice(1);fs.writeFileSync(p,fs.readFileSync(p,"utf8").replace(o,n))' "$F" "$OLD" "$NEW"
  echo "ktx patch applied"
else echo "ktx connector changed upstream: patch not applied" >&2; exit 1; fi
"$DEST/node_modules/.bin/claude" --version
"$DEST/node_modules/.bin/node" --version
KTX_TELEMETRY_DISABLED=1 DO_NOT_TRACK=1 KTX_NO_UPDATE_CHECK=1 PATH="$DEST/node_modules/.bin:$PATH" "$DEST/node_modules/.bin/ktx" --version
