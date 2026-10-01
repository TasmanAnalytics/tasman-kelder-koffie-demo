# Demo playbook

Three short beats, about ten minutes in all. Every number below comes from the recorded runs in
`demo/trial_summary.md` and `demo/labels/labels.csv`. Live answers vary from run to run, so have the
recorded answers in `demo/selected/` open as a backup.

## Before you start

Once, on the demo machine:

```bash
make setup && make all && make demo
make doctor
```

On the day:

```bash
make serve-status        # all four ktx servers should say "serving"; if not: make serve
```

## Beat 1: the churn number, without and with context (4 minutes)

**Left terminal, no notes:**

```bash
scripts/demo_terminal.sh agent installed
```

**Right terminal, notes in the repo:**

```bash
scripts/demo_terminal.sh agent written
```

**Ask both:**

> What was subscriber churn in March 2026? I need one number for the board deck.

**Provenance:**

- **Left.** The agent asks ktx what data exists (`wiki_search`, `discover_data`), then runs SQL. It
  finds 2,045 cancellations with no reason, all on 12 March. This is
  good detective work; say so.
- **Right.** It greps `context/verified_queries.yml`, runs one SQL query through ktx, then greps
  the column caveats. It goes straight to the right files, because `AGENTS.md` was loaded when the session started and says where everything is.

**What they answer:**

- **Left:** a wrong number. In the recorded runs it recommended 2.8% four times out of five, and once
  said to report 9.4% with a footnote. It never gave 3.3% (0 of 5).
- **Right:** 9.4% raw, 3.3% adjusted, and why: decision 0007. 3 of 3 runs.
- On the board-number question the agent with notes took 6 turns on average, against 16 without.

**The line:** "Same model, same data, same question. The difference is one file somebody wrote down."

**Optional third terminal:** `scripts/demo_terminal.sh agent wiki`. The same notes, but only in the
ktx wiki. It finds them with `wiki_search` and gives 3.3% (2 of 2). Where the notes live matters
less than whether they exist.

**Backup:** `demo/selected/installed__churn_board_number.md` and
`demo/selected/written__churn_board_number.md`.

## Beat 2: context drift (4 minutes)

One command runs the whole beat:

```bash
scripts/demo_terminal.sh rot
```

**Step 1, the commit.** It prints the diff of "Fix churn logic" (Sanne, 26 June). Point at the last
change: the restated series now joins `series_unadjusted`. The pull request body has one line and
no impact box ticked. Every note still says the migration rows are excluded. Every dbt test passes.

**Step 2, the agent.** Press enter to start the agent in the `rot` workspace, then ask:

> Has churn improved year on year? Compare the first half of 2026 with the first half of 2025, like for like.

In the recorded runs the agent read the churn model's SQL, saw that it contradicts the caveat, and
recomputed. It answered "improved, 2.45% against 2.85%" and flagged the bug at line 107 (3 of 3
runs, our reading of the transcripts). Type `/exit` when it is done.

**Step 3, the check.** The script then runs `make check` on the commit. Two things fail, on purpose:

- The verified query `churn_yoy_like_for_like` gets 3.50% where the pinned answer is 2.45%.
- The capture check: "exactly one metric-impact option must be ticked; found 0".

The other six verified queries pass. March's as-reported number still matches, because decision
0007 pins it. Nothing pins the restated series, which is where the damage hides.

**The line:** "The agent caught it because it reads SQL. The dashboard and the board pack don't. They
would both say churn got worse."

**Backup:** `demo/selected/rot__churn_yoy_like_for_like.md`.

## Beat 3: what the agent actually checks (2 minutes)

Kelder has no domain layer, so don't claim the agent reads one. It checks the model layer. Show two files:

1. `kelder-dbt/models/marts/_marts__models.yml`, lines 119 to 125: the caveat on `churned_at`. This
   is the written rule. In all three recorded board-number runs with notes, the agent greps the models for
   `caveat`.
2. `metrics_subscriber_churn_monthly.sql` at the rot state, line 107: the code that breaks the rule.
   The agent opened this file in all three recorded rot runs (a `Read` call in each transcript) and
   compared it with the caveat. To show
   the rot version:

   ```bash
   git show refs/tags/kelder/rot:kelder-dbt/models/marts/metrics_subscriber_churn_monthly.sql | sed -n 100,110p
   ```

Then open `kelder-dbt/docs/domain_model_logical.svg`, marked in that folder as a proposal. It shows
where the rule would live instead: a cancellation needs an initiator and a reason, and the import
rows have neither.

**The line:** "The agent did this check at question time, once per question, and only because it
happened to read the SQL. A domain model does it once, when the data is built, for every reader."

## If something goes wrong

| Symptom | Fix |
|---|---|
| The agent has no ktx tools, or they error | `make serve-status`, then `make serve` |
| "No API key" or an authentication error | Check `ANTHROPIC_API_KEY` in `.env` |
| Anything else | `make doctor` prints the next step |
| A live answer comes out odd | Say so, then switch to the matching file in `demo/selected/` |
