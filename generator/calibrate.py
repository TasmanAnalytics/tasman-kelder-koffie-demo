"""Solvers for acquisition scale and pinned counts.

1. Warm-up scale: base on 2025-01-01 hits 20,000 +/- 300.
2. Main scale: base on 2026-03-01 hits 31,200 +/- 150.
3. The artefact count A is then pinned inside the simulation so both March rates round
   correctly (see SubscriptionWorld._required_artefacts), and checked here.

Both solvers are plain bisection on a fixed seed, so the solution is deterministic.
"""

from __future__ import annotations

from .catalogue import Catalogue
from .world import SubscriptionWorld, WorldResult


def _base_at(cfg, cat, ws, ms, month: str, pin_freeze=False) -> int:
    w = SubscriptionWorld(cfg, cat, ws, ms, until=month, pin_freeze=pin_freeze)
    r = w.run()
    return int(r.monthly.set_index("month").loc[month, "base"])


def _bisect(f, lo, hi, target, tol_abs, max_iter=40):
    flo, fhi = f(lo) - target, f(hi) - target
    if flo > 0 or fhi < 0:
        raise RuntimeError(f"bracket does not contain target: f(lo)-t={flo}, f(hi)-t={fhi}")
    best = (abs(flo), lo)
    for _ in range(max_iter):
        mid = (lo + hi) / 2
        fm = f(mid) - target
        best = min(best, (abs(fm), mid))
        if abs(fm) <= tol_abs:
            return mid, fm
        if fm < 0:
            lo = mid
        else:
            hi = mid
    return best[1], None


def solve(cfg: dict, cat: Catalogue, verbose: bool = True) -> tuple[WorldResult, dict]:
    t = cfg["targets"]
    acq = cfg["acquisition"]
    ms_guess = acq["main_scale_guess"]
    ws, dw = _bisect(lambda s: _base_at(cfg, cat, s, ms_guess, "2025-01"), 0.4 * acq["warmup_scale_guess"],
                     2.5 * acq["warmup_scale_guess"], t["base_2025_01_01"], 25)
    if verbose:
        print(f"warm-up scale {ws:.3f}")
    ms, dm = _bisect(lambda s: _base_at(cfg, cat, ws, s, "2026-03"), 0.4 * ms_guess, 2.0 * ms_guess,
                     t["base_2026_03_01"], 15)
    if verbose:
        print(f"main scale {ms:.3f}")
    world = SubscriptionWorld(cfg, cat, ws, ms, pin_freeze=True)
    res = world.run()
    m = res.monthly.set_index("month")
    base_mar = int(m.loc["2026-03", "base"])
    A = int(res.subs.artefact.sum())
    T_mar = int(m.loc["2026-03", "T"])
    report = dict(
        warmup_scale=ws, main_scale=ms,
        base_2025_01_01=int(m.loc["2025-01", "base"]), base_2026_03_01=base_mar,
        artefacts=A, march_adj_events=T_mar,
        march_raw=(T_mar + A) / base_mar, march_adj=T_mar / base_mar,
    )
    ok = (
        abs(report["base_2025_01_01"] - t["base_2025_01_01"]) <= t["base_2025_01_01_tol"]
        and abs(base_mar - t["base_2026_03_01"]) <= t["base_2026_03_01_tol"]
        and t["artefacts_min"] <= A <= t["artefacts_max"]
        and t["march_raw_min"] <= report["march_raw"] <= t["march_raw_max"]
        and t["march_adj_min"] <= report["march_adj"] <= t["march_adj_max"]
    )
    report["ok"] = ok
    if verbose:
        print(report)
    if not ok:
        raise RuntimeError(f"calibration failed: {report}")
    return res, report
