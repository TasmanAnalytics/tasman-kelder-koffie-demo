# Progress (2026-09-24, end of first session)

Done: generator + tests; loader; kelder-dbt three states with in-universe history; truth tests (exact);
verified queries + capture check + make check + freeze script (not frozen); CI workflow; workspaces +
leak check (fallback MCP, live probes); charts (fallback fonts); trial harness, summariser, isolation dry
run, demo_terminal.sh; README; make all = 3 min.

Blocked on Thomas: API key, AGENTS.md rewrite, freeze approval, font download, tmux, ktx decision, GitHub.

When AGENTS.md arrives:
1. Commit it in-universe as Sanne (date 2026-06-19 or 20) on top of C10 -> rewrite: easiest is to
   amend history: new commit after C10, move tag kelder/with-context to it, cherry-pick rot commit on top
   with its original dates (GIT_*_DATE env), move kelder/rot tag + branch.
2. make build-all, make workspaces, make leak-check, verify_isolation.py, then N=3 trials.
