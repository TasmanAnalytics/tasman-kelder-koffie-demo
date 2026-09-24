# Context

Source of truth: `BUILD_BRIEF.md` (renamed from `initial-brief.md`). The repo root
`/Users/thomas/Github/tasman-kelder-koffie` plays the role of `kelder-coffee/` in the brief.

Talk: Thomas in't Veld, Compass AI & Tech Summit, Budapest, Thu 1 Oct 2026 14:15.
Four claims: agents on a good warehouse give wrong explanations; written context fixes it;
context decays; forcing functions (PR template, pinned verified queries) catch decay.

## Environment facts (2026-09-24)

- macOS, Apple M4, 10 cores. uv 0.7.9, Python 3.12 (homebrew), Node 20.11.1, Claude Code 2.1.25.
- dbt-core 1.12.5, dbt-duckdb, duckdb 1.5.5, numpy 2.5, pandas 3.0 (pinned in uv.lock).
- No ANTHROPIC_API_KEY in the shell environment. Trials will need one in `.env`
  (or Claude Code login inside the dedicated config dir).
- tmux is not installed. `demo_terminal.sh side-by-side` needs it: ask Thomas before `brew install tmux`.
- No CLAUDE.md in `~`, `/Users` or `/`. `~/.claude/` exists (Thomas's config); demo runs use a dedicated CLAUDE_CONFIG_DIR.

## Gates that need Thomas (from brief section 12)

- Installing anything outside the project environment (tmux, global npm).
- Creating or pushing a GitHub repo; making anything public.
- API batch projected above EUR 50.
- Deleting data, runs, ingest outputs.
- Changing any number in "Numbers that must reconcile".
- Freezing verified results (`make freeze-verified`).
- Rewriting `AGENTS.md` by hand before trials.

## Answers from Thomas

- 2026-09-24: article chart (illustrative) differs from the calibration table by >0.2 in Jan and Apr.
  Thomas chose: keep the brief's table.
