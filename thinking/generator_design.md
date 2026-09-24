# Generator design

## Layers

1. `world.py`: what really happened. Customers, subscriptions, status spans, charges,
   dunning episodes, pauses, cancellations, retail orders, email engagement, ad spend.
   Pure numpy/pandas, local Amsterdam time internally, converted to UTC on output.
2. `systems/*.py`: render the world through Shopify, Recharge, Klaviyo, ads. Source schemas,
   ids, quirks (Recharge paused = active + paused_until; created_at date-only for imported rows).
3. `incidents.py`: explicit transformations of rendered tables, each change logged to
   `incident_manifest` (incident, table, row id, change type, before, after).
   Incidents: migration artefacts + queued genuine cancellations (Recharge), Klaviyo outage
   deletion, PostNL strike delays/refunds (world-level, see below), freeze charge shift.

Honest note: some incidents must exist in the world, not only in rendering, because they change
behaviour (freeze shifts charges; strike delays deliveries and triggers refunds; restores change
when subscribers resume). The manifest still logs every rendered row they create or alter.
Rule used: an incident is world-level if the customer experienced it; rendering-level if only the
data is wrong. Migration artefact status and Klaviyo deletion are rendering-level. Freeze, strike,
restore timing are world-level, and their rows are still logged in the manifest.

## Time

- Internally: numpy datetime64[s] in local Amsterdam wall time for scheduling
  (charges at 05:00 local, human-time events), converted to UTC with pandas tz handling.
- Data cutoff: 2026-07-01 00:00 Europe/Amsterdam (= 2026-06-30 22:00 UTC). Everything after
  is simulated (to 2026-08-31, for v2 resolution) but only stored in the truth DB.
- Month = local calendar month. Base = in-base at 00:00 local on the 1st.

## Subscription state machine (world)

status in {active, paused, cancelled, expired}. Gifts: active then expired after 3 shipments.
Per subscription arrays: start, interval_days (14/28/42), next_charge, pause_end, in_dunning,
dunning_t0, terminal time.

Monthly loop (local months), from 2023-04 to 2026-08:

1. base = count(start < m0 and not terminated before m0 and not gift).
2. new subs this month (scale x curve); start times from human profile.
3. Pinned months (2025-01..2026-06): T = round(target x base); F = round(0.36 T); V = T - F.
   Unpinned (warm-up, Jul-Aug 2026): counts from hazards.
4. Failures: candidates = active, not in dunning, with >=1 scheduled charge in month.
   weight = method multiplier x frailty. Pick one scheduled charge in month as t0.
   Retries days 1,3,7,14,21,28 at 05:00. Recovered w.p. by method; recovery day weighted early.
   Unrecovered: cancel at t0 + 30 days, reason max_retries_reached.
5. Voluntary: candidates = active (not in dunning, not failing this month) incl. new subs and
   subs resuming from pause this month. weight = tenure hazard x promo mult x frailty x
   (active-day fraction, post-pause week counted x4).
6. Timing: 40% within 3 days after latest shipment; else across active days, DOW weighted;
   hour from human profile.
7. Pause diversion from 2026-03-28: extra pauses = round(V_period x 0.35/0.65), same pool/timing.
8. Self-serve pauses: hazard 2%/month (x1.8 Jul/Aug), durations 1/2/3/6 months (35/30/20/15).
   Shopify until 2026-03-11; none 2026-03-12..27; Recharge from 2026-03-28.
9. Paused stock at freeze pinned to artefact count A: solved inside the Feb/early-March steps.
10. Charges derived from the final timelines (after all events are fixed), not during sampling,
    except the scheduled-charge calendar needed for failure selection (same deterministic rule).

## Calibration

- Warm-up scale bisection: base at 2025-01-01 = 20,000 +/- 300.
- Main scale bisection: base at 2026-03-01 = 31,200 +/- 150.
- A = round(0.094 x base_mar) - T_mar, then check both March rates in range and A in 1880..1920.

## Migration (2026-03-12)

- Freeze: no charges 2026-03-11 20:00 to 2026-03-12 12:00 local; the 12 March 05:00 run moves to
  13 March 05:00. Retries due then move too.
- Queued genuine cancellations: voluntary cancellations requested while the Shopify app's cancel
  processing was frozen for the migration (window start set in config) are imported cancelled at
  2026-03-12 00:00:00 UTC, null reason. Shopify last sync shows them ACTIVE.
- PAUSED contracts: imported cancelled at 2026-03-12 00:00:00 UTC, null reason (artefacts).
- Restores: ops job weekdays 09:15 local from 2026-03-16, on original pause_until date
  (next weekday >= max(pause_until, 16 March)). In the world, the subscriber resumes at the restore
  time. Pause_until after 2026-06-30: not restored in data.
- Open dunning episodes carry over to Recharge: Recharge charge row with scheduled_at = original
  billing cycle date, retries continue.

## v1/v2

- v1 churned(m) = voluntary cancels in m + dunning episode starts in m.
- v2 churned(m) = voluntary cancels in m + episodes starting in m and unrecovered (final).
- v2 as-of 2026-07-01: an episode counts only if t0 + 30 days <= 2026-07-01 00:00 local.
- As-reported = v1 to 2026-04, v2 from 2026-05. Restated = v2 all months.
