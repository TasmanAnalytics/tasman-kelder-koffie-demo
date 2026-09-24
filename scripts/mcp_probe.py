"""Start a workspace's MCP server exactly as .mcp.json describes it and probe it.

Used by the leak check: the served warehouse must answer a plain query, and must refuse to read
local files, attach other databases or write.
"""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path

from contextlib import asynccontextmanager

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.streamable_http import streamable_http_client

PROBES = {
    "plain_query": "select count(*) as n from information_schema.tables",
    "read_local_file": "select * from read_csv('/etc/hosts')",
    "read_text_file": "select * from read_text('/etc/hosts')",
    "glob_files": "select * from glob('/Users/*')",
    "attach_other_db": "attach '/tmp/kelder_probe.duckdb' as other",
    "write_table": "create table main.probe_write as select 1 as x",
    "change_setting": "set enable_external_access = true",
}


@asynccontextmanager
async def _connect(spec: dict):
    if spec.get("type") == "http":
        async with streamable_http_client(spec["url"]) as streams:
            yield streams[0], streams[1]
    else:
        env = dict(spec.get("env") or {}, PATH="/usr/bin:/bin")
        params = StdioServerParameters(command=spec["command"], args=spec.get("args", []), env=env)
        async with stdio_client(params) as (read, write):
            yield read, write


async def _probe(mcp_json: Path) -> dict:
    cfg = json.loads(mcp_json.read_text())["mcpServers"]
    out = {"servers": sorted(cfg)}
    name, spec = next(iter(cfg.items()))
    async with _connect(spec) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await session.list_tools()
            out["tools"] = sorted(t.name for t in tools.tools)
            names = {t.name for t in tools.tools}
            if "sql_execution" in names:
                tool, arg = "sql_execution", lambda q: {"connectionId": "kelder", "sql": q}
            else:
                tool, arg = "execute_query", lambda q: {"sql": q}
            results = {}
            for key, sql in PROBES.items():
                r = await session.call_tool(tool, arg(sql))
                text = " ".join(getattr(c, "text", "") for c in r.content)
                low = text.lower()[:400]
                err = bool(getattr(r, "is_error", False)) or "error" in low or "not allowed" in low or "rejected" in low or "only read-only" in low
                results[key] = {"is_error": err, "text": text[:300]}
            out["probes"] = results
    return out


def probe(mcp_json: Path) -> dict:
    return asyncio.run(_probe(mcp_json))


if __name__ == "__main__":
    print(json.dumps(probe(Path(sys.argv[1])), indent=2))
