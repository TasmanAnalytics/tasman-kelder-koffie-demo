"""Start, stop or check the ktx MCP server for each agent workspace.

Each workspace's ktx project is in ~/kelder-demo/_tools/ktx-projects/<workspace>/ (see make_workspace.py).

    uv run python scripts/ktx_serve.py start|stop|status [--workspace installed|written|rot]

Each workspace's kelder-dbt/ is a ktx project (ktx.yaml, semantic-layer/, wiki/, .ktx/). The server
runs outside the agent, in a scrubbed environment, with the LLM off (so no memory-writing tools)
and telemetry off, and listens on 127.0.0.1 only. ktx git-inits its project directory; the .git it
creates is removed, because a workspace must not contain one.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import make_workspace  # noqa: E402

NPM_BIN = make_workspace.DEMO / "_tools" / "npm" / "node_modules" / ".bin"
PORTS = {"installed": 7801, "written": 7802, "rot": 7803}
RUNTIME = make_workspace.DEMO / "_tools" / "ktx-runtime"


def env() -> dict:
    return {"PATH": f"{NPM_BIN}:/usr/bin:/bin:/usr/sbin:/sbin", "HOME": os.environ["HOME"], "LANG": "en_GB.UTF-8",
            "KTX_TELEMETRY_DISABLED": "1", "DO_NOT_TRACK": "1", "KTX_NO_UPDATE_CHECK": "1", "KTX_RUNTIME_ROOT": str(RUNTIME)}


def ktx(args, project: Path) -> subprocess.CompletedProcess:
    return subprocess.run([str(NPM_BIN / "ktx"), *args, "--project-dir", str(project)], env=env(), cwd=project,
                          stdin=subprocess.DEVNULL, capture_output=True, text=True)


def url(name: str) -> str:
    return f"http://127.0.0.1:{PORTS[name]}/mcp"


def alive(name: str) -> bool:
    req = urllib.request.Request(url(name), method="POST", data=b'{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"probe","version":"1"}}}',
                                 headers={"content-type": "application/json", "accept": "application/json, text/event-stream"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status == 200
    except Exception:
        return False


def strip_git(project: Path):
    g = project / ".git"
    if g.exists():
        shutil.rmtree(g)


def start(name: str):
    project = make_workspace.KTX_PROJECTS / name
    if not (project / "ktx.yaml").exists():
        sys.exit(f"{name}: no ktx project; run make workspaces")
    if alive(name):
        print(f"{name}: already serving {url(name)}")
        return
    RUNTIME.mkdir(parents=True, exist_ok=True)
    r = ktx(["admin", "reindex"], project)
    if r.returncode:
        sys.exit(f"{name}: reindex failed\n{r.stdout}\n{r.stderr}")
    r = ktx(["mcp", "start", "--port", str(PORTS[name])], project)
    for _ in range(30):
        if alive(name):
            break
        time.sleep(1)
    strip_git(make_workspace.DEMO / name / "kelder-dbt")
    print(f"{name}: {'serving ' + url(name) if alive(name) else 'FAILED to start'}")
    if not alive(name):
        print(r.stdout, r.stderr)


def _listener_pids(name: str) -> list[int]:
    """ktx processes serving this workspace's project on its port (never anything else)."""
    out = subprocess.run(["lsof", "-ti", f"tcp:{PORTS[name]}", "-sTCP:LISTEN"], capture_output=True, text=True).stdout.split()
    pids = []
    for pid in out:
        cmd = subprocess.run(["ps", "-o", "command=", "-p", pid], capture_output=True, text=True).stdout
        if "ktx" in cmd and str(make_workspace.KTX_PROJECTS / name) in cmd:
            pids.append(int(pid))
    return pids


def stop(name: str):
    project = make_workspace.KTX_PROJECTS / name
    if project.exists():
        ktx(["mcp", "stop"], project)
    for _ in range(10):
        if not alive(name):
            break
        time.sleep(1)
    if alive(name):
        for pid in _listener_pids(name):
            os.kill(pid, 15)
        time.sleep(2)
    print(f"{name}: stopped" if not alive(name) else f"{name}: still running (port {PORTS[name]} held by another process)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("action", choices=["start", "stop", "status"])
    ap.add_argument("--workspace", choices=sorted(PORTS))
    a = ap.parse_args()
    for n in [a.workspace] if a.workspace else list(PORTS):
        if a.action == "start":
            start(n)
        elif a.action == "stop":
            stop(n)
        else:
            print(f"{n}: {'serving ' + url(n) if alive(n) else 'not running'}")


if __name__ == "__main__":
    main()
