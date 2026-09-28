# Progress (28 September 2026)

## Done
- Generator, targets, realism, incidents, determinism: all pass. `make all` takes about 3 minutes.
- kelder-dbt in three states (tags); with-context equals the truth exactly; rot fails exactly the like-for-like verified query and the capture check.
- Verified answers frozen (approved by Thomas, 24 September).
- Charts in brand fonts; `index.html` generated from the build outputs (`make index`).
- Agent tooling pinned in `~/kelder-demo/_tools/npm` (`tools/demo/setup.sh`); ktx patched to read-only with file access off.
- ktx ingest stored per state in `demo/ktx/`; workspaces serve ktx from `~/kelder-demo/_tools/ktx-projects/<ws>` (a workspace must not contain .git).
- Leak check 25/25; isolation dry runs pass in all three workspaces.
- Trials at N=3: 45 runs, $7.80, transcripts in `demo/runs/` (git-ignored), reviewed readings in the notes column of `demo/labels/labels.csv`.
- Narrative doc (Claude Docs, "Kelder Coffee: the talk narrative"), `TALK_FLOW.md`, `START_HERE.md`, `CLAUDE.md`, `make setup` / `make doctor` / `make demo`.

## Findings to keep in mind
- Without context, the agent detects the 12 March batch and most other events by detective work, but gives 2.8% as March's board number (truth 3.3%).
- With written context: right on all six questions in about a third of the turns.
- In the rot workspace the agent catches the rot bug itself (3/3).
- The strong forms of claims 1 and 3 did not hold. The framing is Thomas's call; do not tune anything to change it.

## Open
- Thomas labels the runs; decide on N=10 (about EUR 34).
- Record clips 1 and 2 (`scripts/demo_terminal.sh`).
- GitHub repository and a pull request from `kelder/rot`, when Thomas says.
