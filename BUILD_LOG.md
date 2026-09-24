# Build log

Decisions, deviations from `BUILD_BRIEF.md`, judgement calls and open questions.
Newest checkpoint at the bottom of each section.

## Deviations and judgement calls

| Date | Area | Decision | Reason |
|---|---|---|---|
| 2026-09-24 | Repo | The build repository is this folder (`tasman-kelder-koffie`), standing in for `kelder-coffee/`. `initial-brief.md` renamed to `BUILD_BRIEF.md`. | The brief names the brief file `BUILD_BRIEF.md`; the leak check looks for that name. |
| 2026-09-24 | Calibration | The article chart (labelled illustrative) reads Jan 3.0, Feb 3.1, Mar 9.4/3.3, Apr 3.4, May 2.6, Jun 2.7 by pixel measurement. Jan and Apr differ from the calibration table by more than 0.2 points. Thomas chose to keep the brief's table. | Brief section 3.5 requires stopping to ask. |
| 2026-09-24 | Working notes | A `thinking/` folder holds design notes and decisions. It is builder-only and never reaches a workspace. | Requested by Thomas. |

## Open questions

- tmux is not installed; `scripts/demo_terminal.sh side-by-side` needs it. Installing it (`brew install tmux`) is a global install and needs Thomas's approval.
- No `ANTHROPIC_API_KEY` in the environment. Trials need either a key in `.env` or a Claude Code login inside the dedicated configuration directory.

## Checkpoints
