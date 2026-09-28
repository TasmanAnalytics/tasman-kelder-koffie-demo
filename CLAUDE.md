@START_HERE.md

# Working on this repository (for Claude Code)

This is the build repository behind a conference talk. The person you work with is Thomas in't Veld.
Before changing anything, read `BUILD_LOG.md` (decisions and checkpoints) and `thinking/progress.md`
(current state). `BUILD_BRIEF.md` is the specification; where it and `BUILD_LOG.md` disagree, the log
records what was decided since.

## Ask Thomas before

- installing anything outside the project environment or `~/kelder-demo/_tools`, or installing anything globally;
- creating or pushing a GitHub repository, or making anything public;
- any batch of agent runs projected above EUR 50 (the N=10 matrix is about EUR 34);
- deleting data, trial runs or ktx ingest output (`demo/runs/`, `demo/ktx/`);
- changing any number in "Numbers that must reconcile" (brief 3.5) or the calibration in `generator/config.yaml`;
- freezing verified results (`make freeze-verified`). Never re-freeze to make a failing check pass.

## Honesty rules for the demo

- Never put ground truth, the generator, the brief, the log, pinned answers or git history in a workspace. `make leak-check` must pass.
- Report every trial run. Never discard, re-run or change data, context, prompts or settings to push a result. If anything changes, re-run the affected trials and log it.
- Never state a number that a test or query has not produced.
- ktx ingest output is derived by a tool and stored once per state. Report what it inferred; never remove it.

## Git conventions

- Commits that touch `kelder-dbt/` are Kelder's own history. Author and committer are `Sanne de Vries <sanne@example.com>`, backdated to January to June 2026, with no Co-Authored-By trailer. They never mix with builder changes.
- The states are tags: `kelder/before-context` (a side branch), `kelder/with-context` and `kelder/rot` (one commit on top of with-context). `scripts/build_state.py` builds any of them. See `thinking/git_history_plan.md` before rewriting any history.
- Builder commits are small, after each passing step.

## Style for anything a person reads

British English, short plain sentences, no em dashes. Code identifiers keep the article's spelling
(for example `is_migration_artifact`).

## Useful to know

- Agent runs go through `scripts/agent_cmd.py`. It uses the pinned Claude Code in `~/kelder-demo/_tools/npm`, a dedicated config directory, only Read, Grep, Glob and the ktx tools, and a scrubbed environment. Do not run demo agents any other way.
- ktx needs a clean environment. A session-level `ANTHROPIC_BASE_URL` breaks its API calls.
- `make doctor` tells you what is missing on this machine.
