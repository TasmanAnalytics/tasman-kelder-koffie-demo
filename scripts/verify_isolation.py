"""Pre-trial dry runs (a few cents each). Run once per workspace before any trial:

    uv run python scripts/verify_isolation.py

Checks, with the exact trial settings:
1. the agent sees only Read, Grep, Glob and the warehouse tools;
2. it cannot read the build repository (BUILD_BRIEF.md) or a sibling workspace;
3. in written and rot, AGENTS.md is loaded (the agent quotes a marker line that is added to a
   temporary copy of the workspace's AGENTS.md and removed afterwards); in installed, it is not.
Results go to demo/isolation/<workspace>.json. Nothing here counts as a trial.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import agent_cmd  # noqa: E402

ROOT = agent_cmd.ROOT
OUT = ROOT / "demo" / "isolation"
MARKER = "ISOLATION-MARKER: teal walrus 7431"
QUESTIONS = {
    "tools": "List every tool you can call right now, by exact name, one per line. Do not call any tool.",
    "read_brief": f"Use the Read tool on {ROOT / 'BUILD_BRIEF.md'} and quote its first line. If you cannot, say DENIED.",
    "read_sibling": "Use the Read tool on {sibling} and quote its first line. If you cannot, say DENIED.",
    "marker": "Do your instructions contain a line starting with ISOLATION-MARKER? If yes, quote it exactly; if not, say NONE. Do not call any tool.",
}


def ask(ws: Path, q: str) -> str:
    cmd = agent_cmd.headless(ws, q, max_turns=4, budget_usd=0.5)
    p = subprocess.run(cmd, cwd=ws, env=agent_cmd.agent_env(), stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=300)
    for line in reversed(p.stdout.splitlines()):
        try:
            m = json.loads(line)
        except json.JSONDecodeError:
            continue
        if m.get("type") == "result":
            return m.get("result", "") or ""
    return "NO RESULT: " + p.stderr[-500:]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    ok_all = True
    for name in ("installed", "written", "rot"):
        ws = agent_cmd.DEMO / name
        if not ws.exists():
            continue
        agents = ws / "kelder-dbt" / "AGENTS.md"
        backup = None
        if agents.exists():
            backup = agents.read_text()
            agents.write_text(backup + f"\n{MARKER}\n")
        try:
            sibling = agent_cmd.DEMO / ("written" if name != "written" else "installed") / "kelder-dbt" / "README.md"
            ans = {k: ask(ws, q.format(sibling=sibling)) for k, q in QUESTIONS.items()}
        finally:
            if backup is not None:
                agents.write_text(backup)
        checks = {
            "no_bash_or_web": not any(t.strip() in ("Bash", "WebSearch", "WebFetch")
                                      for t in ans["tools"].split("\n\n")[0].splitlines()),
            "brief_denied": "DENIED" in ans["read_brief"].upper() and "Kelder Coffee: build brief" not in ans["read_brief"],
            "sibling_denied": "DENIED" in ans["read_sibling"].upper(),
            "agents_md_loaded": (MARKER in ans["marker"]) == (backup is not None),
        }
        ok_all &= all(checks.values())
        (OUT / f"{name}.json").write_text(json.dumps({"answers": ans, "checks": checks}, indent=2))
        print(name, checks)
    sys.exit(0 if ok_all else 1)


if __name__ == "__main__":
    main()
