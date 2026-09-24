# Decisions (running)

- 2026-09-24 Time is kept internally as local Amsterdam wall seconds; own DST converter verified against zoneinfo on 20k random times.
- 2026-09-24 Months beyond June 2026 (Jul, Aug) are simulated with pinned counts at June's target (2.8%), which is how "June 2026 hazard levels" is implemented.
- 2026-09-24 Warm-up applies the recurring seasonal multipliers (Nov x1.7, Dec x1.2, Jul/Aug x0.85) every year; 2026-specific ones (Jan 2026 x1.4, Jun 2026 x1.15) only once.
- 2026-09-24 Queued genuine cancellations: the Shopify app stopped processing cancellations from 2026-03-05 00:00 local. Every voluntary cancellation requested between then and the import (01:00 local 12 March) is queued. First run gives 142 (target 120 to 180).
- 2026-09-24 Freeze snapshot = Shopify connector last sync, 2026-03-11 21:30 UTC. Paused at that moment = artefact. Shopify pauses can start until 2026-03-11 20:00 local.
- 2026-09-24 Artefact subscribers resume in the world at their restore time (ops job, weekdays 09:15 from 16 March), so adjusted warehouse logic can equal the truth.
- 2026-09-24 Paused count at the freeze is pinned by boosting February pause starts with a solved multiplier and setting the exact number of 1-11 March Shopify pauses.
- 2026-09-24 A subscription in an open dunning episode at month start is not eligible for new events that month (simplification).
- 2026-09-24 Subscription price per shipment = bags x unit price x 0.9, plus EUR 4.95 shipping for a single 250 g bag. Most shipments land in EUR 15 to 30; 1 kg and 3-bag plans sit above.
- 2026-09-24 First calibration: warm-up scale 1787.4, main scale 1255.0; base 19,987 (2025-01-01) and 31,194 (2026-03-01); A = 1,903; March raw 9.399%, adjusted 3.299%; v1 - v2 Q1 2026 0.52 pp; restated v2 (as of 1 July) H1 2025 2.85% vs H1 2026 2.45%, improvement 0.40 pp.
