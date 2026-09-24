"""The one place that defines how a demo agent is launched, for trials and recordings alike."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parent.parent
DEMO = Path(os.environ.get("KELDER_DEMO_DIR", Path.home() / "kelder-demo"))
NPM_BIN = DEMO / "_tools" / "npm" / "node_modules" / ".bin"  # pinned Claude Code, ktx and Node 22
CLAUDE = str(NPM_BIN / "claude")
TOOLS = ["mcp__warehouse__execute_query", "mcp__warehouse__list_tables", "mcp__warehouse__list_columns",
         "mcp__warehouse__list_databases"]


def env_file() -> dict:
    return {k: v for k, v in dotenv_values(ROOT / ".env").items() if v}


def model() -> str:
    return env_file().get("KELDER_MODEL", "claude-opus-5-5")


def agent_env() -> dict:
    """A clean environment: the dedicated config dir, the API key, no telemetry, nothing else of Thomas's."""
    e = env_file()
    cfg = Path(os.path.expanduser(e.get("KELDER_CLAUDE_CONFIG_DIR", str(DEMO / ".claude-config"))))
    env = {
        "PATH": f"{NPM_BIN}:/usr/bin:/bin:/usr/sbin:/sbin",
        "HOME": os.environ["HOME"],
        "TERM": os.environ.get("TERM", "xterm-256color"),
        "LANG": "en_GB.UTF-8",
        "CLAUDE_CONFIG_DIR": str(cfg),
        "DISABLE_TELEMETRY": "1",
        "DISABLE_ERROR_REPORTING": "1",
        "DISABLE_AUTOUPDATER": "1",
        "CLAUDE_CODE_DISABLE_NONESSENTIAL_TRAFFIC": "1",
        "DO_NOT_TRACK": "1",
        "CLAUDE_CODE_DISABLE_AUTO_MEMORY": "1",
    }
    if e.get("ANTHROPIC_API_KEY"):
        env["ANTHROPIC_API_KEY"] = e["ANTHROPIC_API_KEY"]
    return env


def mcp_tools(workspace: Path) -> list[str]:
    import json
    import make_workspace

    server = next(iter(json.loads((workspace / ".mcp.json").read_text())["mcpServers"]))
    return make_workspace.allowed_mcp_tools(server)


def base_args(workspace: Path) -> list[str]:
    """Flags shared by headless trials and interactive recordings."""
    return [
        "--model", model(),
        "--mcp-config", str(workspace / ".mcp.json"), "--strict-mcp-config",
        "--tools", "Read,Grep,Glob",
        "--allowedTools", " ".join(["Read", "Grep", "Glob", *mcp_tools(workspace)]),
        "--disallowedTools", "Bash WebSearch WebFetch Edit Write NotebookEdit Task",
        "--setting-sources", "project",
        "--permission-mode", "dontAsk",
        "--disable-slash-commands",
    ]


def headless(workspace: Path, prompt: str, max_turns: int = 30, budget_usd: float = 5.0) -> list[str]:
    return [CLAUDE, "-p", prompt, *base_args(workspace), "--output-format", "stream-json", "--verbose",
            "--max-turns", str(max_turns), "--no-session-persistence", "--max-budget-usd", str(budget_usd)]


def interactive(workspace: Path) -> list[str]:
    return [CLAUDE, *base_args(workspace)]
