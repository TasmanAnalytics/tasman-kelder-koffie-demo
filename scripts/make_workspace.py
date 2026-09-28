"""Create agent workspaces under ~/kelder-demo/, outside the build repository, from scratch.

    uv run python scripts/make_workspace.py --all
    uv run python scripts/make_workspace.py --name written

Each workspace holds only what a Kelder employee's agent would see in one state: kelder-dbt/ at
that state (no .git, no build output), a copy of that state's warehouse as warehouse.duckdb, one
MCP configuration (.mcp.json) serving that file read-only, and .claude/settings.json allowing only
Read, Grep, Glob and the warehouse tools. written/ and rot/ also get a CLAUDE.md that imports
AGENTS.md and nothing else.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import stat
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEMO = Path(os.environ.get("KELDER_DEMO_DIR", Path.home() / "kelder-demo"))
TOOLS = DEMO / "_tools"
CONFIG_DIR = DEMO / ".claude-config"
WORKSPACES = {"installed": "before", "written": "with_context", "rot": "rot"}
SERVER_NAME = "warehouse"  # fallback server name
KTX_TOOLS = ["connection_list", "wiki_search", "wiki_read", "sl_read_source", "sl_query", "entity_details",
             "dictionary_search", "discover_data", "sql_execution", "sql_dialect_notes"]
KTX_PORTS = {"installed": 7801, "written": 7802, "rot": 7803}
# ktx 0.16 git-inits its project directory, and a workspace must not contain .git, so each
# workspace's ktx project lives beside it (outside the agent's reach); ktx reads the workspace's
# kelder-dbt/ and warehouse from there and serves the semantic layer and wiki over MCP.
KTX_PROJECTS = TOOLS / "ktx-projects"
FALLBACK_TOOLS = ["execute_query", "list_tables", "list_columns", "list_databases"]
# never copied into a workspace even though they are part of the Kelder repo at that state
EXCLUDE = {".pr", "target", "logs", "dbt_packages", ".ktx", ".user.yml", ".git"}


def server_launcher() -> Path:
    """A launcher outside every workspace, so no workspace file points into the build repository."""
    TOOLS.mkdir(parents=True, exist_ok=True)
    (TOOLS / "duckdb-home").mkdir(exist_ok=True)
    launcher = TOOLS / "warehouse-mcp"
    binary = ROOT / ".venv" / "bin" / "mcp-server-motherduck"
    if not binary.exists():
        sys.exit("mcp-server-motherduck missing from the project environment: run `uv sync`")
    launcher.write_text(f'#!/bin/sh\nexec "{binary}" "$@"\n')
    launcher.chmod(launcher.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
    return launcher


def mcp_config(ws: Path, launcher: Path) -> dict:
    return {"mcpServers": {SERVER_NAME: {
        "command": str(launcher),
        "args": [
            "--db-path", str(ws / "warehouse.duckdb"),
            "--home-dir", str(TOOLS / "duckdb-home"),
            # one persistent read-only connection; no file system access from SQL
            "--no-ephemeral-connections",
            "--init-sql", "SET enable_external_access = false; SET lock_configuration = true;",
            "--max-rows", "500",
            "--query-timeout", "120",
        ],
        "env": {"FASTMCP_CHECK_FOR_UPDATES": "off", "FASTMCP_SHOW_SERVER_BANNER": "false", "DO_NOT_TRACK": "1"},
    }}}


def allowed_mcp_tools(server: str) -> list[str]:
    names = KTX_TOOLS if server == "ktx" else FALLBACK_TOOLS
    return [f"mcp__{server}__{t}" for t in names]


def ktx_config(ws: Path, state: str) -> str:
    """The stored ingest config, pointed at this workspace only, with the LLM off (read-only tools)."""
    s = (ROOT / "demo" / "ktx" / state / "ktx.yaml").read_text()
    s = re.sub(r"(\n    path: ).*", rf"\g<1>{ws / 'warehouse.duckdb'}", s)
    s = re.sub(r"(\n    source_dir: ).*", rf"\g<1>{ws / 'kelder-dbt'}", s)
    s = re.sub(r"(\n    profiles_path: ).*", rf"\g<1>{ws / 'kelder-dbt'}", s)
    s = re.sub(r"llm:\n  provider:\n    backend: anthropic\n    anthropic:\n      api_key: env:ANTHROPIC_API_KEY\n  models:\n(?:    .*\n)+",
               "llm:\n  provider:\n    backend: none\n  models: {}\n", s)
    return s


def settings(ws: Path, server: str = SERVER_NAME) -> dict:
    home = Path.home()
    others = [DEMO / n for n in WORKSPACES if DEMO / n != ws] + [DEMO / "bare"]
    outside = [ROOT, ROOT.parent, Path("/private/tmp"), Path("/tmp"), home / ".claude", home / "Documents", home / "Desktop",
               home / "Downloads", home / "Library", TOOLS, CONFIG_DIR, *others]
    # never deny a directory that contains this workspace (for example a demo folder placed under /tmp)
    outside = [p for p in outside if not str(ws.resolve()).startswith(str(p.resolve()) + "/")]
    deny_paths = [f"{tool}(/{p}/**)" for p in outside for tool in ("Read", "Grep", "Glob")]
    deny_paths += [f"Read(/{home / '.claude.json'})"]
    return {
        "permissions": {
            "allow": ["Read", "Grep", "Glob", *allowed_mcp_tools(server)],
            "deny": ["Bash", "WebSearch", "WebFetch", "Edit", "Write", "NotebookEdit", "Task", "Agent", "Skill",
                     "SlashCommand", *deny_paths],
            "defaultMode": "dontAsk",
        },
        "enableAllProjectMcpServers": False,
        "enabledMcpjsonServers": [server],
        "includeCoAuthoredBy": False,
        "autoMemoryEnabled": False,
        "cleanupPeriodDays": 30,
    }


def make(name: str, launcher: Path, server: str = "ktx") -> Path:
    state = WORKSPACES[name]
    src = ROOT / "build" / state / "kelder-dbt"
    db = ROOT / "data" / "warehouse" / f"kelder_{state}.duckdb"
    if not src.exists() or not db.exists():
        sys.exit(f"state {state} not built: run `make build STATE={state}`")
    ws = DEMO / name
    if ws.exists():
        shutil.rmtree(ws)
    ws.mkdir(parents=True)
    shutil.copytree(src, ws / "kelder-dbt", ignore=lambda d, names: [n for n in names if n in EXCLUDE])
    shutil.copyfile(db, ws / "warehouse.duckdb")
    (ws / ".claude").mkdir()
    (ws / ".claude" / "settings.json").write_text(json.dumps(settings(ws, server), indent=2) + "\n")
    if server == "ktx":
        stored = ROOT / "demo" / "ktx" / state
        if not stored.exists():
            sys.exit(f"no ktx ingest output for {state}: run scripts/ktx_build.py {state}")
        proj = KTX_PROJECTS / name
        if proj.exists():
            shutil.rmtree(proj)
        proj.mkdir(parents=True)
        for d in ("semantic-layer", "wiki"):
            shutil.copytree(stored / d, proj / d)
        (proj / "ktx.yaml").write_text(ktx_config(ws, state))
        mcp = {"mcpServers": {"ktx": {"type": "http", "url": f"http://127.0.0.1:{KTX_PORTS[name]}/mcp"}}}
    else:
        mcp = mcp_config(ws, launcher)
    (ws / ".mcp.json").write_text(json.dumps(mcp, indent=2) + "\n")
    if (ws / "kelder-dbt" / "AGENTS.md").exists():
        (ws / "CLAUDE.md").write_text("@kelder-dbt/AGENTS.md\n")
    print(f"workspace {name}: {ws} (state {state})")
    return ws


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", choices=sorted(WORKSPACES))
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--server", choices=["ktx", "fallback"], default="ktx")
    a = ap.parse_args()
    if not (a.all or a.name):
        ap.error("--all or --name")
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    launcher = server_launcher()
    for n in (sorted(WORKSPACES) if a.all else [a.name]):
        make(n, launcher, a.server)


if __name__ == "__main__":
    main()
