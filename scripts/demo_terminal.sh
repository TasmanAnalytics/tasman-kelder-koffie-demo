#!/usr/bin/env bash
# Terminal set-up and demo layouts for the two recorded clips.
#
#   scripts/demo_terminal.sh setup          prompt, colours and font hints; checks prerequisites
#   scripts/demo_terminal.sh side-by-side   clip 1: tmux split, installed left, written right
#   scripts/demo_terminal.sh rot            clip 2: rot diff, then the rot agent, then make check
#   scripts/demo_terminal.sh agent <ws>     one agent in this terminal (installed, written or rot), no tmux needed
#
# Every agent pane runs Claude Code with exactly the trial settings (scripts/agent_cmd.py).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
DEMO="${KELDER_DEMO_DIR:-$HOME/kelder-demo}"

agent() {  # agent <workspace>: print the command line that starts an interactive agent in a workspace
  (cd "$ROOT" && uv run python - "$1" <<'PY'
import shlex, sys
sys.path.insert(0, "scripts")
import agent_cmd
ws = agent_cmd.DEMO / sys.argv[1]
env = " ".join(f"{k}={shlex.quote(v)}" for k, v in agent_cmd.agent_env().items() if k != "ANTHROPIC_API_KEY")
key = "ANTHROPIC_API_KEY=$(grep ^ANTHROPIC_API_KEY= " + shlex.quote(str(agent_cmd.ROOT / ".env")) + " | cut -d= -f2-)"
print(f"cd {shlex.quote(str(ws))} && env -i {env} {key} " + " ".join(shlex.quote(a) for a in agent_cmd.interactive(ws)))
PY
  )
}

minimal_prompt='export PS1="\$ " PROMPT="%# " ; clear'

case "${1:-}" in
  setup)
    command -v tmux >/dev/null || echo "tmux is not installed (needed for side-by-side): brew install tmux"
    command -v claude >/dev/null || echo "claude is not on PATH"
    [ -f "$ROOT/.env" ] || echo "no .env: copy .env.example and add ANTHROPIC_API_KEY"
    cat <<'TXT'
Terminal settings for recording (set once in Terminal or iTerm2):
  - window 1920x1080, font size 20 pt or larger (a monospaced font; Roboto Mono if installed)
  - background #fff9eb, text #526476, cursor #526476, selection #90b39d
  - notifications off: Focus > Do Not Disturb
  - minimal prompt: this script sets PS1="$ " in every pane
The warehouse MCP server is started by Claude Code itself from each workspace's .mcp.json.
TXT
    ;;
  side-by-side)
    command -v tmux >/dev/null || { echo "tmux is required: brew install tmux"; exit 1; }
    left="$(agent installed)"; right="$(agent written)"
    tmux kill-session -t kelder 2>/dev/null || true
    tmux new-session -d -s kelder -x 240 -y 60 "bash --noprofile --norc -c '$minimal_prompt; $left; exec bash --noprofile --norc'"
    tmux split-window -h -t kelder "bash --noprofile --norc -c '$minimal_prompt; $right; exec bash --noprofile --norc'"
    tmux set -t kelder status off
    tmux set -t kelder pane-border-style fg='#90b39d'
    tmux set -t kelder pane-active-border-style fg='#526476'
    echo "Ask in both panes, in this order:"
    echo "  1. Why did subscriber churn spike in March 2026?"
    echo "  2. What was subscriber churn in March 2026? I need one number for the board deck."
    tmux attach -t kelder
    ;;
  rot)
    cd "$ROOT"
    eval "$minimal_prompt"
    echo "\$ git show kelder/rot -- kelder-dbt/models"
    git --no-pager show refs/tags/kelder/rot -- kelder-dbt/models
    read -r -p "(press enter to start the rot agent; ask the like-for-like question, then /exit)"
    bash -c "$(agent rot)"
    echo "\$ make check STATE=rot PR_BODY=kelder-dbt/.pr/rot.md"
    FORCE_COLOR=1 make -s check STATE=rot PR_BODY=kelder-dbt/.pr/rot.md || true
    ;;
  agent)
    case "${2:-}" in installed|written|rot) ;; *) echo "usage: scripts/demo_terminal.sh agent installed|written|rot"; exit 1 ;; esac
    eval "$minimal_prompt"
    bash -c "$(agent "$2")"
    ;;
  *)
    sed -n '2,9p' "$0"; exit 1 ;;
esac
