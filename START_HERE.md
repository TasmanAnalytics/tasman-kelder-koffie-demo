# Start here

The Kelder Coffee context layer demo, for Thomas in't Veld's talk at Compass AI & Tech Summit
(Budapest, 1 October 2026). This page gets a fresh machine, or a fresh Claude Code session, from a
copied folder to a working demo.

## What you need

- macOS with [uv](https://docs.astral.sh/uv/), git, and Node.js 18 or newer with npm (`brew install node`).
- Optional: tmux (`brew install tmux`), only for the side-by-side clip.
- An `ANTHROPIC_API_KEY` in `.env`, only for agent runs (trials, recordings, isolation checks).
  Everything else works without it.

Copy the whole folder, including the hidden `.git` directory. The three states of Kelder's repo are git
tags. `data/`, `build/` and `.venv/` can be left behind; they are rebuilt.

## Five commands

```bash
make setup
```

This installs the Python environment (pinned in `uv.lock`) and the pinned agent tooling in
`~/kelder-demo/_tools`: Claude Code 2.1.281, ktx 0.16.0 with its read-only patch, and Node 22. It also
creates `.env` from `.env.example` if there is none. Nothing is installed globally.

```bash
make all
```

This generates the data, builds the three warehouse states, runs the tests, and renders the charts and
`index.html`. It takes about three minutes.

```bash
make demo
```

This creates the agent workspaces in `~/kelder-demo/`, starts one ktx server per workspace, and runs the
leak check. The first start downloads ktx's small Python runtime (about 170 MB).

```bash
make doctor
```

This checks everything above and prints the next command to run. Run it whenever something looks off.

```bash
open index.html
```

This is the evidence page for the talk: the three tenets, each with the chart or trial that backs it.

## Then

| To do this | Run |
|---|---|
| Show the checks CI runs on the rot commit (red on purpose) | `make check STATE=rot PR_BODY=kelder-dbt/.pr/rot.md` |
| Record clip 1: same question, two agents | `scripts/demo_terminal.sh side-by-side` |
| Record clip 2: the context goes stale | `scripts/demo_terminal.sh rot` |
| Prove the agents are isolated (a few cents) | `uv run python scripts/verify_isolation.py` |
| Run trials (about $0.10 to $0.30 a run) | `make trials WORKSPACE=written N=3`, then `make summary` |
| Stop, start or check the ktx servers | `make serve-stop`, `make serve`, `make serve-status` |

## Where things stand (28 September 2026)

- **Built and verified.** The generator and all reconciliation targets pass. The three warehouse states are built, and with-context equals the hidden truth exactly. The verified answers are frozen and the check tooling works. ktx is serving all three workspaces, the leak check passes 25 of 25, and the isolation dry runs pass.
- **Trials.** 45 runs at N=3 on `claude-opus-5-5` cost $7.80. The results are in `demo/trial_summary.md` and `demo/labels/labels.csv`; Thomas has not labelled them yet.
  - The agent without context found most things by detective work, but gave 2.8% as March's board number (the true figure is 3.3%).
  - The agent in the rot workspace caught the rot bug itself.
- **Open.**
  - Thomas's labels.
  - N=10 trials (about EUR 34).
  - The two recorded clips.
  - How to frame claims 1 and 3 given the trials.
  - A private GitHub repository and pull request (later).

## Read next

- [`TALK_FLOW.md`](TALK_FLOW.md): the talk's flow, numbers and trial findings.
- [`README.md`](README.md): how the pieces fit together.
- [`BUILD_LOG.md`](BUILD_LOG.md): every decision, deviation and checkpoint.
- [`BUILD_BRIEF.md`](BUILD_BRIEF.md): the original specification.
