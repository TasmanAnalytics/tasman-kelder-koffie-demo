"""Check that this machine can run everything, and say what to run next.

    make doctor

Read-only: it inspects prerequisites and build state, and changes nothing.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import make_workspace  # noqa: E402

DEMO = make_workspace.DEMO
NPM_BIN = DEMO / "_tools" / "npm" / "node_modules" / ".bin"
G, R, Y, X = ("\033[32m", "\033[31m", "\033[33m", "\033[0m") if sys.stdout.isatty() else ("", "", "", "")
results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, fix: str = "", optional: bool = False):
    results.append((name, ok, fix))
    mark = f"{G}ok{X}  " if ok else (f"{Y}--{X}  " if optional else f"{R}NO{X}  ")
    print(f"  {mark}{name}" + ("" if ok or not fix else f"   ->  {fix}"))
    return ok


def run(cmd, **kw) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, timeout=60, **kw).stdout.strip()
    except Exception:  # noqa: BLE001
        return ""


def main():
    print("Prerequisites")
    check("uv", bool(shutil.which("uv")), "install uv: https://docs.astral.sh/uv/")
    check("git", bool(shutil.which("git")), "install git (xcode-select --install)")
    node = run(["node", "--version"])
    major = int(node.lstrip("v").split(".")[0]) if node.startswith("v") else 0
    check(f"Node.js 18+ with npm (found {node or 'none'})", major >= 18 and bool(shutil.which("npm")), "brew install node")
    check("tmux (only for the side-by-side clip)", bool(shutil.which("tmux")), "brew install tmux", optional=True)
    env = {}
    if (ROOT / ".env").exists():
        from dotenv import dotenv_values
        env = dotenv_values(ROOT / ".env")
    check(".env with ANTHROPIC_API_KEY (trials, verify_isolation, ktx ingest)", bool(env.get("ANTHROPIC_API_KEY")),
          "cp .env.example .env and add the key")

    print("\nRepository")
    tags = run(["git", "tag"], cwd=ROOT).split()
    check("git tags kelder/before-context, kelder/with-context, kelder/rot",
          {"kelder/before-context", "kelder/with-context", "kelder/rot"} <= set(tags), "copy the folder with its .git directory")
    check("Python environment (uv sync)", bool(run(["uv", "run", "--frozen", "python", "-c", "import duckdb, dbt, pandas; print(1)"], cwd=ROOT)),
          "make setup")
    check("verified answers frozen", len(list((ROOT / "tests" / "verified" / "expected").glob("*.json"))) == 7,
          "make freeze-verified APPROVED_BY=... (only with Thomas's approval)")
    check("ktx ingest output stored", all((ROOT / "demo" / "ktx" / s / "ktx.yaml").exists() for s in ("before", "with_context", "rot")),
          "scripts/ktx_build.py <state> (costs LLM calls; normally already in the repo)")

    print("\nBuild outputs")
    check("generated data (data/raw, truth)", (ROOT / "data" / "truth" / "kelder_truth.duckdb").exists(), "make all")
    states = all((ROOT / "data" / "warehouse" / f"kelder_{s}.duckdb").exists() and (ROOT / "build" / s / "kelder-dbt").exists()
                 for s in ("before", "with_context", "rot"))
    check("warehouse states built (before, with_context, rot)", states, "make all")
    check("charts rendered", (ROOT / "charts" / "out" / "churn_monthly_2026_events.png").exists(), "make charts")

    print(f"\nAgent tooling ({DEMO / '_tools'})")
    claude = run([str(NPM_BIN / "claude"), "--version"]) if (NPM_BIN / "claude").exists() else ""
    check(f"pinned Claude Code (found {claude or 'none'})", claude.startswith("2.1.281"), "make setup")
    conn = DEMO / "_tools" / "npm" / "node_modules" / "@kaelio" / "ktx" / "dist" / "connectors" / "duckdb" / "connector.js"
    check("ktx 0.16.0 with the read-only DuckDB patch", conn.exists() and "enable_external_access: 'false'" in conn.read_text(), "make setup")

    print(f"\nAgent workspaces ({DEMO})")
    ws_ok = all((DEMO / w / ".mcp.json").exists() for w in ("installed", "written", "rot"))
    check("workspaces installed, written, rot", ws_ok, "make workspaces")
    parents = [p / "CLAUDE.md" for p in [DEMO.resolve(), *DEMO.resolve().parents] if (p / "CLAUDE.md").exists()]
    check("no CLAUDE.md above the demo folder", not parents, f"remove {parents[0]}" if parents else "")
    status = run(["uv", "run", "--frozen", "python", "scripts/ktx_serve.py", "status"], cwd=ROOT)
    check("ktx servers running (7801-7803)", status.count("serving") == 3, "make serve")

    blocking = [n for n, ok, _ in results if not ok and "tmux" not in n]
    print()
    if not blocking:
        print(f"{G}Ready.{X} Try: make check STATE=rot PR_BODY=kelder-dbt/.pr/rot.md, or scripts/demo_terminal.sh side-by-side")
    else:
        nxt = next(f for n, ok, f in results if not ok and "tmux" not in n)
        print(f"{Y}Next:{X} {nxt}")
    sys.exit(0)


if __name__ == "__main__":
    main()
