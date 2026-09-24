# In-universe git history plan

All commits that touch `kelder-dbt/` are Kelder's own history: author and committer
`Sanne de Vries <sanne@example.com>`, backdated. They never contain builder files, and builder
commits never touch `kelder-dbt/`. No Co-Authored-By trailer on in-universe commits (they must read
as Kelder's history on stage); builder commits carry it.

## Topology

```
main:   C1 initial models (2026-01-12)
        C2 CAC + email attribution (2026-01-26)
        |\
        | B1 fail-payment 30-day rule from May, plain SQL (2026-04-28)   <- tag kelder/before-context
        |
        C3 flag artefacts, churned_at caveat, 0007, business_events seed + row 1 (2026-03-14) <- tag v2026.03.2
        C4 restores are continuations (2026-03-17)
        C5 pause campaign row (2026-03-28)
        C6 Klaviyo outage row + caveat (2026-04-10)
        C7 churn v2 logic, restated series, 0009, metric_changelog (2026-04-28)
        C8 PostNL strike row + delivery_days caveat (2026-05-20)
        C9 Father's Day bundle row (2026-06-15)
        C10 AGENTS.md draft, verified queries, glossary, quirks, PR template, older decision stubs (2026-06-19)
                                                                    <- tag kelder/with-context
        \
         R1 "Fix churn logic" (2026-06-26) on branch kelder/rot     <- tag kelder/rot
```

Why before-context is a side branch: the brief's before-context state must contain the plain
v1-before-May / v2-from-May switch, which in Kelder's history arrived on 28 April, after the
context work started. A counterfactual branch keeps that honest: same models, same switch, no
context.

Fixes to shared (non-context) models after the fact: an in-universe fix commit on both branches,
or history rewrite plus re-tag while nothing is pushed.
