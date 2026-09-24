"""Run the same questions many times in one workspace and keep every transcript.

    uv run python scripts/run_trials.py --workspace installed --prompts all --n 3

Fresh session per run, 30-turn limit, 10-minute timeout, pinned model. Saves the full stream to
demo/runs/<workspace>/<prompt_id>/<n>.json and a readable rendering beside it (<n>.md).
Cost guard: prints tokens and cost, and projects the full matrix at N=10.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import agent_cmd  # noqa: E402

ROOT = agent_cmd.ROOT
RUNS = ROOT / "demo" / "runs"
EUR_PER_USD = 0.86  # rough, for the cost guard only
TIMEOUT = 600


def render(messages: list[dict]) -> tuple[str, dict]:
    calls, final, meta = [], "", {}
    for m in messages:
        if m.get("type") == "assistant":
            for c in m.get("message", {}).get("content", []):
                if c.get("type") == "tool_use":
                    arg = c.get("input", {})
                    calls.append(f"- `{c.get('name')}` {json.dumps(arg, ensure_ascii=False)[:400]}")
        if m.get("type") == "result":
            final = m.get("result", "") or ""
            meta = {k: m.get(k) for k in ("subtype", "is_error", "num_turns", "duration_ms", "total_cost_usd", "usage", "session_id")}
    text = "## Final answer\n\n" + final + "\n\n## Tool calls\n\n" + ("\n".join(calls) or "(none)") + "\n\n## Run metadata\n\n```json\n" + json.dumps(meta, indent=2) + "\n```\n"
    return text, meta


def next_index(d: Path) -> int:
    existing = [int(p.stem) for p in d.glob("*.json") if p.stem.isdigit()]
    return max(existing, default=0) + 1


def run_one(workspace: str, pid: str, prompt: str) -> dict:
    ws = agent_cmd.DEMO / workspace
    out_dir = RUNS / workspace / pid
    out_dir.mkdir(parents=True, exist_ok=True)
    i = next_index(out_dir)
    cmd = agent_cmd.headless(ws, prompt)
    t0 = time.time()
    try:
        p = subprocess.run(cmd, cwd=ws, env=agent_cmd.agent_env(), stdin=subprocess.DEVNULL, capture_output=True, text=True, timeout=TIMEOUT)
        lines, err = p.stdout.splitlines(), p.stderr
    except subprocess.TimeoutExpired as e:
        lines, err = (e.stdout or b"").decode(errors="ignore").splitlines() if isinstance(e.stdout, bytes) else (e.stdout or "").splitlines(), "TIMEOUT"
    msgs = []
    for l in lines:
        try:
            msgs.append(json.loads(l))
        except json.JSONDecodeError:
            msgs.append({"type": "unparsed", "text": l})
    # Claude Code spills large tool results under <config>/projects/<workspace>/<session>/; they are in the
    # transcript already, so clear them so no later run can ever see an earlier one's files
    spill = Path(agent_cmd.agent_env()["CLAUDE_CONFIG_DIR"]) / "projects" / str(ws).replace("/", "-")
    if spill.exists():
        import shutil
        shutil.rmtree(spill)
    record = {"workspace": workspace, "prompt_id": pid, "prompt": prompt, "run": i, "model": agent_cmd.model(),
              "command": cmd, "elapsed_s": round(time.time() - t0, 1), "stderr": err[-4000:], "messages": msgs}
    (out_dir / f"{i}.json").write_text(json.dumps(record, indent=2, ensure_ascii=False))
    text, meta = render(msgs)
    (out_dir / f"{i}.md").write_text(f"# {workspace} / {pid} / run {i}\n\n> {prompt}\n\n" + text)
    return {"run": i, **meta}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--workspace", required=True)
    ap.add_argument("--prompts", default="all", help="comma-separated ids, or all (the workspace's row in the matrix)")
    ap.add_argument("--n", type=int, default=3)
    ap.add_argument("--confirm-budget-eur", type=float, default=0.0, help="required when the projected cost exceeds EUR 50")
    a = ap.parse_args()
    spec = yaml.safe_load(open(ROOT / "demo" / "prompts.yaml"))
    ids = spec["matrix"][a.workspace] if a.prompts == "all" else a.prompts.split(",")
    if not (agent_cmd.DEMO / a.workspace / ".mcp.json").exists():
        sys.exit(f"workspace {a.workspace} missing: run make workspaces")
    if "ANTHROPIC_API_KEY" not in agent_cmd.agent_env() and not (Path(agent_cmd.agent_env()["CLAUDE_CONFIG_DIR"]) / ".credentials.json").exists():
        print("note: no ANTHROPIC_API_KEY in .env; relying on a login inside the dedicated config dir", file=sys.stderr)
    planned = len(ids) * a.n
    if planned > 20 and a.confirm_budget_eur <= 0:
        sys.exit(f"{planned} runs planned: run N=3 first, check the projection, then pass --confirm-budget-eur")
    costs = []
    for pid in ids:
        for _ in range(a.n):
            m = run_one(a.workspace, pid, spec["prompts"][pid])
            c = m.get("total_cost_usd") or 0.0
            costs.append(c)
            print(f"{a.workspace:9} {pid:26} run {m['run']:>2}  turns {m.get('num_turns')}  ${c:.3f}  {m.get('subtype')}")
            if a.confirm_budget_eur and sum(costs) * EUR_PER_USD > a.confirm_budget_eur:
                sys.exit(f"stopped: spent EUR {sum(costs) * EUR_PER_USD:.2f}, over the confirmed budget")
    if costs:
        mean = sum(costs) / len(costs)
        full = sum(len(v) for v in spec["matrix"].values()) * 10
        print(f"\nspent ${sum(costs):.2f} (about EUR {sum(costs) * EUR_PER_USD:.2f}) over {len(costs)} runs; mean ${mean:.3f}/run")
        print(f"projected full matrix at N=10: {full} runs, about ${mean * full:.0f} (EUR {mean * full * EUR_PER_USD:.0f})")


if __name__ == "__main__":
    main()
