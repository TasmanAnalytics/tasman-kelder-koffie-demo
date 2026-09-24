"""World simulation: what actually happened to every Kelder customer and subscription.

The simulator steps through local calendar months from launch (2023-04) to 2026-08.
From 2025-01 to 2026-06 the number of churn events per month is pinned to the calibration
targets; *who* experiences them is decided by weighted sampling on individual hazards.

All times are local Amsterdam wall seconds (see common.py). Nothing here knows about
source systems; rendering happens in systems/*.py and incidents in incidents.py.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from .catalogue import Catalogue, subscription_product_weights
from .common import (
    DAY,
    HOUR,
    NEVER,
    ProfileSampler,
    add_months,
    at_time_of_day,
    iso_dow,
    month_key,
    month_start,
    next_time_of_day,
    rng_for,
    ts,
    utc_to_local,
    weighted_choice_without_replacement,
)

ACTIVE, PAUSED, CANCELLED, EXPIRED, UNBORN = 0, 1, 2, 3, -1
R_NONE, R_VOLUNTARY, R_MAX_RETRIES, R_EXPIRED = 0, 1, 2, 3
K_FIRST, K_RECURRING, K_RECOVERY, K_GIFT = 0, 1, 2, 3
P_SHOPIFY, P_RECHARGE, P_CANCEL_FLOW = 0, 1, 2
METHODS = ["mandate", "card", "paypal"]
COUNTRIES = ["NL", "BE", "DE", "LU", "FR"]
CHANNELS = ["paid_social", "paid_search", "email", "organic", "referral", "direct"]


class Log:
    """Append-only columnar log."""

    def __init__(self, *cols):
        self.cols = cols
        self.parts = {c: [] for c in cols}

    def add(self, **kw):
        n = None
        for c in self.cols:
            v = np.atleast_1d(np.asarray(kw[c]))
            n = len(v) if n is None else n
            self.parts[c].append(v)

    def frame(self) -> pd.DataFrame:
        return pd.DataFrame({c: (np.concatenate(v) if v else np.array([])) for c, v in self.parts.items()})


@dataclass
class WorldResult:
    subs: pd.DataFrame
    customers: pd.DataFrame
    charges: pd.DataFrame
    pauses: pd.DataFrame
    cancels: pd.DataFrame
    dunning: pd.DataFrame
    monthly: pd.DataFrame
    artefacts: pd.DataFrame
    params: dict = field(default_factory=dict)


class SubscriptionWorld:
    def __init__(self, cfg: dict, cat: Catalogue, warmup_scale: float, main_scale: float,
                 until: str | None = None, pin_freeze: bool = True, verbose: bool = False):
        self.cfg = cfg
        self.cat = cat
        self.w = cfg["world"]
        self.d = cfg["dates"]
        self.warmup_scale = warmup_scale
        self.main_scale = main_scale
        self.until = until or self.d["simulate_until"][:7]
        self.pin_freeze = pin_freeze
        self.verbose = verbose
        seed = cfg["seed"]
        self.r_acq = rng_for(seed, "world.acquisition")
        self.r_attr = rng_for(seed, "world.attributes")
        self.r_fail = rng_for(seed, "world.failures")
        self.r_vol = rng_for(seed, "world.voluntary")
        self.r_pause = rng_for(seed, "world.pauses")
        self.r_time = rng_for(seed, "world.timing")
        self.r_gift = rng_for(seed, "world.gifts")
        prof = cfg["profiles"]
        self.human = ProfileSampler(prof["human_hour"], prof["human_dow"])

        cap = 160_000
        self.n = 0
        z = lambda dt_, fill=0: np.full(cap, fill, dtype=dt_)
        self.start = z(np.int64, NEVER)
        self.cust = z(np.int64, -1)
        self.interval = z(np.int64, 28)
        self.method = z(np.int8)
        self.frailty = z(np.float64, 1.0)
        self.promo = z(bool, False)
        self.gift = z(bool, False)
        self.bags = z(np.int8, 1)
        self.size = z(np.int16, 250)
        self.grind = z(np.int8)
        self.prod = z(np.int16)
        self.price = z(np.float64)
        self.status = z(np.int8, UNBORN)
        self.pause_start = z(np.int64, NEVER)
        self.pause_end = z(np.int64, NEVER)
        self.pause_row = z(np.int64, -1)
        self.next_charge = z(np.int64, NEVER)
        self.last_charge = z(np.int64, -NEVER)
        self.dun_until = z(np.int64, -NEVER)
        self.term = z(np.int64, NEVER)
        self.term_reason = z(np.int8, R_NONE)
        self.queued = z(bool, False)
        self.artefact = z(bool, False)
        self.orig_until = z(np.int64, NEVER)
        self.restore_time = z(np.int64, NEVER)
        self.channel = z(np.int8)

        self.cust_created = []
        self.cust_country = []
        self.cust_consent = []
        self.cust_is_gift_buyer = []

        self.charges = Log("sub", "t", "kind")
        self.pauses = Log("row", "sub", "start", "end", "orig_end", "source")
        self._pause_rows = 0
        self.pause_end_updates = {}
        self.cancels = Log("sub", "t", "reason", "queued")
        self.dunning = Log("sub", "t0", "recovered", "rec_day", "t_end")
        self.monthly = []

        # dates
        self.freeze_start = ts(self.d["freeze_start_local"])
        self.freeze_end = ts(self.d["freeze_end_local"])
        self.snapshot = int(utc_to_local(np.array([ts(self.d["shopify_last_sync_utc"])]))[0])
        self.import_local = int(utc_to_local(np.array([ts(self.d["import_stamp_utc"])]))[0])
        self.queue_start = ts(self.d["cancel_queue_start_local"])
        self.blackout_start = ts(self.d["pause_blackout_start_local"])
        self.blackout_end = ts(self.d["pause_blackout_end_local"])
        self.shopify_pause_last = ts(self.d["shopify_pause_last_local"])
        self.diversion_start = ts(self.d["pause_diversion_start_local"])
        self.restore_first = ts(self.d["restore_job_first_day"])
        hh, mm = self.d["restore_job_time"].split(":")
        self.restore_hh, self.restore_mm = int(hh), int(mm)
        self.window_end_day = ts(self.d["window_end"])
        self.freeze_month = "2026-03"
        self.feb_month = "2026-02"
        self.required_artefacts = None
        self.targets = cfg["targets"]["v1_adjusted"]

        # tenure hazard table (monthly probabilities)
        h = dict(self.w["voluntary_hazard_by_tenure"])
        for t in range(7, 19):
            h[t] = self.w["voluntary_hazard_7"] + (self.w["voluntary_hazard_18"] - self.w["voluntary_hazard_7"]) * (t - 7) / 11
        self.hazard = np.array([0.0] + [h[t] for t in range(1, 19)])
        self.pm = np.array([self.w["payment_failure_multiplier"][m] for m in METHODS])
        self.prec = np.array([self.w["recovery_probability"][m] for m in METHODS])
        self.product_p = subscription_product_weights(cat)

    # ------------------------------------------------------------------ helpers

    def shift(self, t):
        """Charges and retries due during the billing freeze run at the first 05:00 after it."""
        t = np.asarray(t, dtype=np.int64)
        in_freeze = (t >= self.freeze_start) & (t < self.freeze_end)
        return np.where(in_freeze, next_time_of_day(np.full_like(t, self.freeze_end), 5), t)

    def charge_time(self, t):
        return self.shift(next_time_of_day(t, 5))

    def tenure_hazard(self, idx, M0):
        age_days = np.maximum(0, M0 - self.start[idx]) / DAY
        tm = np.floor(age_days / 30.44).astype(int) + 1
        h = self.hazard[np.minimum(tm, 18)]
        promo = self.promo[idx] & (tm <= self.w["promo_months_of_effect"])
        return h * np.where(promo, self.w["promo_multiplier"], 1.0)

    def new_customers(self, t, country, consent):
        start_id = len(self.cust_created)
        self.cust_created.extend(t.tolist())
        self.cust_country.extend(country.tolist())
        self.cust_consent.extend(consent.tolist())
        self.cust_is_gift_buyer.extend([False] * len(t))
        return np.arange(start_id, start_id + len(t))

    def acquisition_count(self, key: str, i_warm: int, n_warm: int, i_main: int) -> int:
        acq = self.cfg["acquisition"]
        mult = acq["multipliers"]
        season = mult.get(key[5:], 1.0) * mult.get(key, 1.0)
        if key < "2025-01":
            lvl = acq["warmup_start_level"] + (acq["warmup_end_level"] - acq["warmup_start_level"]) * i_warm / max(1, n_warm - 1)
            return int(round(self.warmup_scale * lvl * season))
        lvl = (1 + acq["monthly_growth"]) ** i_main
        return int(round(self.main_scale * lvl * season))

    # ------------------------------------------------------------------ creation

    def add_subscriptions(self, starts: np.ndarray, key: str, gift: bool = False):
        n = len(starts)
        if n == 0:
            return np.empty(0, dtype=np.int64)
        r = self.r_attr
        idx = np.arange(self.n, self.n + n)
        self.n += n
        w = self.w
        self.start[idx] = starts
        # customer: mostly new; a few second subscriptions for an existing active subscriber
        second = (r.random(n) < w["second_subscription_share"]) & (not gift)
        existing_pool = np.flatnonzero((self.status[: idx[0]] == ACTIVE) & ~self.gift[: idx[0]])
        if len(existing_pool) == 0:
            second[:] = False
        ctry = r.choice(len(COUNTRIES), size=n, p=np.array([w["country_mix"][c] for c in COUNTRIES]))
        consent = r.random(n) < w["consent_share"]
        new_mask = ~second
        cust = np.full(n, -1, dtype=np.int64)
        cust[new_mask] = self.new_customers(starts[new_mask], ctry[new_mask], consent[new_mask])
        if second.any():
            pick = existing_pool[r.integers(0, len(existing_pool), second.sum())]
            cust[second] = self.cust[pick]
        self.cust[idx] = cust
        iv = list(w["plan_interval_days"].keys())
        self.interval[idx] = np.array(iv)[r.choice(len(iv), size=n, p=np.array(list(w["plan_interval_days"].values())))]
        bg = list(w["bags_per_shipment"].keys())
        self.bags[idx] = np.array(bg)[r.choice(len(bg), size=n, p=np.array(list(w["bags_per_shipment"].values())))]
        sz = list(w["bag_size_g"].keys())
        self.size[idx] = np.array(sz)[r.choice(len(sz), size=n, p=np.array(list(w["bag_size_g"].values())))]
        self.grind[idx] = r.choice(4, size=n, p=np.array(list(w["grind"].values())))
        self.method[idx] = r.choice(3, size=n, p=np.array([w["payment_method"][m] for m in METHODS]))
        k = w["frailty_gamma_shape"]
        self.frailty[idx] = r.gamma(k, 1.0 / k, size=n)
        self.prod[idx] = r.choice(len(self.product_p), size=n, p=self.product_p)
        unit = self.cat.coffee_price(self.prod[idx].astype(int), self.size[idx])
        disc = 1 - self.cfg["catalogue"]["subscriber_discount"]
        ship = np.where((self.bags[idx] == 1) & (self.size[idx] == 250), self.cfg["catalogue"]["shipping_fee_single_bag"], 0.0)
        self.price[idx] = np.round(self.bags[idx] * unit * disc + ship, 2)
        self.promo[idx] = key in self.cfg["acquisition"]["promo_cohort_months"]
        self.gift[idx] = gift
        self.status[idx] = ACTIVE
        self.next_charge[idx] = self.charge_time(at_time_of_day(starts, 0) + self.interval[idx] * DAY)
        self.last_charge[idx] = starts
        self.charges.add(sub=idx, t=starts, kind=np.full(n, K_FIRST if not gift else K_GIFT))
        return idx

    def add_gifts(self, n: int, a: int, b: int, key: str, boost=None):
        r = self.r_gift
        starts = self.human.sample(r, np.full(n, a), np.full(n, b), day_boost=boost)
        starts = np.sort(starts)
        idx = self.add_subscriptions(starts, key, gift=True)
        gi = self.cfg["gifts"]["interval_days"]
        self.interval[idx] = gi
        self.price[idx] = 0.0
        # prepaid: shipment 1 with the purchase, then two more at 05:00 every four weeks, then expired
        s2 = self.charge_time(at_time_of_day(starts, 0) + gi * DAY)
        s3 = self.charge_time(at_time_of_day(s2, 0) + gi * DAY)
        self.charges.add(sub=np.concatenate([idx, idx]), t=np.concatenate([s2, s3]), kind=np.full(2 * n, K_GIFT))
        self.term[idx] = s3 + 60
        self.term_reason[idx] = R_EXPIRED
        self.next_charge[idx] = NEVER
        for c in self.cust[idx]:
            self.cust_is_gift_buyer[c] = True
        return idx

    # ------------------------------------------------------------------ pauses

    def start_pauses(self, idx, t, source):
        n = len(idx)
        if n == 0:
            return
        durs = list(self.w["pause_duration_months"].keys())
        p = np.array(list(self.w["pause_duration_months"].values()))
        dur = np.array(durs)[self.r_pause.choice(len(durs), size=n, p=p)]
        end = add_months(at_time_of_day(t, 0), dur)
        rows = np.arange(self._pause_rows, self._pause_rows + n)
        self._pause_rows += n
        self.pause_start[idx] = t
        self.pause_end[idx] = end
        self.orig_until[idx] = end
        self.pause_row[idx] = rows
        self.pauses.add(row=rows, sub=idx, start=t, end=end, orig_end=end, source=np.full(n, source))

    def set_pause_end(self, idx, new_end):
        self.pause_end[idx] = new_end
        for r_, e in zip(self.pause_row[idx], new_end):
            self.pause_end_updates[int(r_)] = int(e)

    def restore_times(self, orig_until):
        """Ops job re-creates wiped pauses on the original pause_until date, weekdays 09:15, from 16 March."""
        day = np.maximum(at_time_of_day(orig_until, 0), self.restore_first)
        dow = iso_dow(day)
        day = day + np.where(dow == 5, 2 * DAY, np.where(dow == 6, DAY, 0))
        return day + self.restore_hh * HOUR + self.restore_mm * 60

    def mark_artefacts(self, idx):
        idx = idx[~self.artefact[idx]]
        if len(idx) == 0:
            return
        self.artefact[idx] = True
        rt = self.restore_times(self.orig_until[idx])
        self.restore_time[idx] = rt
        self.set_pause_end(idx, rt)

    # ------------------------------------------------------------------ month step

    def run(self) -> WorldResult:
        launch = ts(self.d["launch"])
        months = []
        m = launch
        until_start = month_start(int(self.until[:4]), int(self.until[5:7]))
        while m <= until_start:
            months.append(m)
            m = int(add_months(np.array([m]), 1)[0])
        keys = [str(month_key([m])[0]) for m in months]
        n_warm = sum(1 for k in keys if k < "2025-01")
        i_main = 0
        for i, (M0, key) in enumerate(zip(months, keys)):
            M1 = int(add_months(np.array([M0]), 1)[0])
            self.step(M0, M1, key, i, n_warm, i_main)
            if key >= "2025-01":
                i_main += 1
        return self.result()

    def step(self, M0, M1, key, i, n_warm, i_main):
        n0 = self.n
        st = self.status[:n0]
        status_m0 = st.copy()
        base_mask = (self.start[:n0] < M0) & (self.term[:n0] >= M0) & ~self.gift[:n0]
        base = int(base_mask.sum())
        paused_count = int((base_mask & (st == PAUSED)).sum())
        pinned = key >= "2025-01"
        target = self.targets.get(key, self.targets["2026-06"] if key > "2026-06" else None)

        # March 2026: every pause still open at the Shopify snapshot is wiped by the import
        if key == self.freeze_month and self.pin_freeze:
            prior = np.flatnonzero((st == PAUSED) & (self.pause_end[:n0] > self.snapshot))
            self.mark_artefacts(prior)

        # 1. resumes during the month
        resume = np.flatnonzero((st == PAUSED) & (self.pause_end[:n0] < M1))
        rt = self.pause_end[resume]
        self.status[resume] = ACTIVE
        self.next_charge[resume] = self.charge_time(rt)
        resume_t = np.full(n0, -NEVER, dtype=np.int64)
        resume_t[resume] = rt

        # 2. new subscriptions
        n_new = self.acquisition_count(key, i, n_warm, i_main)
        boost = None
        if key[5:] == "11":
            bf_day = ts(f"{key[:4]}-11-{str(self._black_friday_dom(int(key[:4]))).zfill(2)}")
            boost = lambda day, _: np.where((day >= bf_day - 4 * DAY) & (day < bf_day + 4 * DAY), 3.0, 1.0) / 3.0
        starts = np.sort(self.human.sample(self.r_acq, np.full(n_new, M0), np.full(n_new, M1), day_boost=boost))
        new_idx = self.add_subscriptions(starts, key)
        if key == "2025-12":
            self.add_gifts(self.cfg["gifts"]["dec_2025_count"], M0, ts("2025-12-24"), key)
        if key == "2026-06":
            self.add_gifts(self.cfg["gifts"]["fathers_day_count"], ts(self.d["bundle_start"]),
                           ts(self.d["bundle_end"]) + DAY, key)
        n1 = self.n
        resume_t = np.concatenate([resume_t, np.full(n1 - n0, -NEVER, dtype=np.int64)])

        # activity window in the month
        st0 = np.concatenate([status_m0, np.full(n1 - n0, UNBORN, dtype=np.int8)])
        a = np.full(n1, NEVER, dtype=np.int64)
        active_m0 = (self.start[:n1] < M0) & (st0 == ACTIVE) & (self.term[:n1] >= M0)
        a[active_m0] = M0
        a[resume] = resume_t[resume]
        a[new_idx] = self.start[new_idx]
        not_gift = ~self.gift[:n1]
        no_dunning = self.dun_until[:n1] < M0
        elig = (a < M1) & not_gift & no_dunning & (self.term[:n1] >= M1)
        # term >= M1 above excludes subs whose already-scheduled cancellation (failed dunning) lands this month
        elig &= ~((self.term[:n1] < M1) & (self.term[:n1] >= M0))

        # scheduled charges in the month, up to 4
        sched = np.full((n1, 4), NEVER, dtype=np.int64)
        nc = self.next_charge[:n1].copy()
        for k in range(4):
            ok = (nc < M1) & (a < M1)
            sched[ok, k] = nc[ok]
            nc[ok] = self.shift(at_time_of_day(nc[ok], 5) + self.interval[:n1][ok] * DAY)
        n_sched = (sched < NEVER).sum(axis=1)
        nc0 = self.next_charge[:n1].copy()
        failed = np.zeros(n1, dtype=bool)

        event_t = np.full(n1, NEVER, dtype=np.int64)
        taken = np.zeros(n1, dtype=bool)
        days_in_month = (M1 - M0) / DAY

        # 3. counts
        if pinned:
            T = int(round(target * base))
            F = int(round(self.w["involuntary_share"] * T))
            V = T - F
        else:
            T = F = V = None

        # 4. first payment failures
        fail_cand = np.flatnonzero(elig & (n_sched > 0))
        wf = self.pm[self.method[fail_cand]] * self.frailty[fail_cand]
        if pinned:
            chosen = fail_cand[weighted_choice_without_replacement(self.r_fail, wf, F)]
        else:
            p = 1 - (1 - np.minimum(0.9, self.w["warmup_failure_prob_per_charge"] * wf)) ** n_sched[fail_cand]
            chosen = fail_cand[self.r_fail.random(len(fail_cand)) < p]
        if len(chosen):
            k = np.floor(self.r_fail.random(len(chosen)) * n_sched[chosen]).astype(int)
            t0 = sched[chosen, k]
            self._start_dunning(chosen, t0)
            event_t[chosen] = t0
            taken[chosen] = True
            failed[chosen] = True
        F_real = len(chosen)

        # 5. voluntary cancellations
        vol_cand = np.flatnonzero(elig & ~taken)
        act_days = (M1 - a[vol_cand]) / DAY
        pp_days = np.zeros(len(vol_cand))
        is_res = resume_t[vol_cand] > -NEVER
        pp_end = resume_t[vol_cand] + self.w["post_pause_days"] * DAY
        pp_days[is_res] = (np.minimum(pp_end[is_res], M1) - resume_t[vol_cand][is_res]) / DAY
        window_factor = (act_days + (self.w["post_pause_multiplier"] - 1) * pp_days) / days_in_month
        wv = self.tenure_hazard(vol_cand, M0) * self.frailty[vol_cand] * window_factor
        if pinned:
            sel = weighted_choice_without_replacement(self.r_vol, wv, V)
        else:
            sel = np.flatnonzero(self.r_vol.random(len(vol_cand)) < np.minimum(0.9, wv))
        vc = vol_cand[sel]
        vt = self._cancel_times(vc, a, resume_t, sched, M1, act_days[sel], pp_days[sel])
        event_t[vc] = vt
        taken[vc] = True
        self.term[vc] = vt
        self.term_reason[vc] = R_VOLUNTARY
        queued = (vt >= self.queue_start) & (vt < self.import_local)
        self.queued[vc] = queued
        self.cancels.add(sub=vc, t=vt, reason=np.full(len(vc), R_VOLUNTARY), queued=queued)
        V_real = len(vc)

        # 6. pause diversion in the cancel flow
        n_div = 0
        if M1 > self.diversion_start:
            v_after = int((vt >= self.diversion_start).sum())
            n_div = int(round(v_after * self.w["pause_diversion_share"] / (1 - self.w["pause_diversion_share"])))
            div_a = np.maximum(a, self.diversion_start)
            dcand = np.flatnonzero(elig & ~taken & (div_a < M1))
            dw = self.tenure_hazard(dcand, M0) * self.frailty[dcand] * (M1 - div_a[dcand]) / DAY
            dsel = dcand[weighted_choice_without_replacement(self.r_pause, dw, min(n_div, len(dcand)))]
            dt_ = self.human.sample(self.r_time, div_a[dsel], np.full(len(dsel), M1))
            self.start_pauses(dsel, dt_, P_CANCEL_FLOW)
            event_t[dsel] = dt_
            taken[dsel] = True
            n_div = len(dsel)

        # 7. self-serve pauses
        n_self = self._self_serve_pauses(key, M0, M1, active_m0, elig, taken, event_t, base)

        # March 2026: pauses started 1-11 March are also wiped at the import
        if key == self.freeze_month and self.pin_freeze:
            at_snap = np.flatnonzero((self.pause_start[:n1] < self.snapshot) & (self.pause_end[:n1] > self.snapshot)
                                     & ~self.gift[:n1] & (self.term[:n1] > self.snapshot))
            self.mark_artefacts(at_snap)
            assert self.artefact.sum() == self.required_artefacts, (self.artefact.sum(), self.required_artefacts)

        # 8. charges for the month
        self._run_charges(M0, M1, a, event_t, n1, nc0, failed)

        # 9. status at month end
        term_now = np.flatnonzero((self.term[:n1] < M1) & (self.status[:n1] != CANCELLED) & (self.status[:n1] != EXPIRED))
        self.status[term_now] = np.where(self.term_reason[term_now] == R_EXPIRED, EXPIRED, CANCELLED)
        paused_now = np.flatnonzero((self.pause_start[:n1] < M1) & (self.pause_end[:n1] >= M1) & (self.status[:n1] == ACTIVE))
        self.status[paused_now] = PAUSED

        self.monthly.append(dict(month=key, base=base, paused_m0=paused_count, target=target, T=T, F=F_real, V=V_real,
                                 new=n_new, pauses_self=n_self, pauses_diverted=n_div))
        if self.verbose:
            print(self.monthly[-1])

    def _black_friday_dom(self, year: int) -> int:
        d = pd.Timestamp(year=year, month=11, day=30)
        while d.dayofweek != 4:
            d -= pd.Timedelta(days=1)
        return d.day

    def _start_dunning(self, idx, t0):
        w = self.w
        n = len(idx)
        rec = self.r_fail.random(n) < self.prec[self.method[idx]]
        rd = np.array(w["retry_days"])[self.r_fail.choice(len(w["retry_days"]), size=n, p=np.array(w["recovery_day_weights"]))]
        t_rec = self.shift(t0 + rd * DAY)
        t_can = self.shift(t0 + w["unrecovered_cancel_day"] * DAY)
        t_end = np.where(rec, t_rec, t_can)
        self.dun_until[idx] = t_end
        self.dunning.add(sub=idx, t0=t0, recovered=rec, rec_day=np.where(rec, rd, -1), t_end=t_end)
        r_idx = idx[rec]
        self.charges.add(sub=r_idx, t=t_rec[rec], kind=np.full(len(r_idx), K_RECOVERY))
        self.last_charge[r_idx] = t_rec[rec]
        self.next_charge[r_idx] = self.shift(at_time_of_day(t_rec[rec], 5) + self.interval[r_idx] * DAY)
        u_idx = idx[~rec]
        self.term[u_idx] = t_can[~rec]
        self.term_reason[u_idx] = R_MAX_RETRIES
        self.next_charge[u_idx] = NEVER
        self.cancels.add(sub=u_idx, t=t_can[~rec], reason=np.full(len(u_idx), R_MAX_RETRIES), queued=np.zeros(len(u_idx), bool))

    def _cancel_times(self, idx, a, resume_t, sched, M1, act_days, pp_days):
        n = len(idx)
        if n == 0:
            return np.empty(0, dtype=np.int64)
        r = self.r_time
        lo = a[idx].copy()
        hi = np.full(n, M1, dtype=np.int64)
        # post-pause week carries a higher hazard
        mult = self.w["post_pause_multiplier"]
        p_post = np.where(pp_days > 0, mult * pp_days / (act_days + (mult - 1) * pp_days), 0.0)
        u = r.random(n)
        post = u < p_post
        hi[post] = np.minimum(resume_t[idx][post] + self.w["post_pause_days"] * DAY, M1)
        # otherwise 40% within three days after the most recent shipment
        near = ~post & (r.random(n) < self.w["cancel_near_shipment_share"])
        s = sched[idx]
        ns = (s < NEVER).sum(axis=1)
        has = near & (ns > 0)
        k = np.floor(r.random(n) * np.maximum(ns, 1)).astype(int)
        ship = s[np.arange(n), np.minimum(k, 3)]
        lo_near = np.maximum(ship, lo)
        hi_near = np.minimum(ship + self.w["cancel_near_shipment_days"] * DAY, M1)
        good = has & (hi_near > lo_near + HOUR)
        lo[good] = lo_near[good]
        hi[good] = hi_near[good]
        return self.human.sample(r, lo, hi)

    def _self_serve_pauses(self, key, M0, M1, active_m0, elig, taken, event_t, base):
        n1 = self.n
        h = self.w["base_pause_hazard"] * (self.w["summer_pause_multiplier"] if key[5:] in ("07", "08") else 1.0)
        cand = np.flatnonzero(active_m0 & elig & ~taken)
        segs = []  # (lo, hi, source)
        if M1 <= self.blackout_start:
            hi = min(M1, self.shopify_pause_last) if M0 < self.shopify_pause_last <= M1 else M1
            segs.append((M0, hi, P_SHOPIFY))
        elif M0 >= self.blackout_end:
            segs.append((M0, M1, P_RECHARGE))
        else:
            if M0 < self.shopify_pause_last:
                segs.append((M0, self.shopify_pause_last, P_SHOPIFY))
            if M1 > self.blackout_end:
                segs.append((self.blackout_end, M1, P_RECHARGE))
        total = 0
        pool = cand.copy()
        for lo, hi, src in segs:
            frac = (hi - lo) / (M1 - M0)
            if self.pin_freeze and key == self.feb_month:
                n = self._feb_pause_count(len(pool), h, M0, base)
            elif self.pin_freeze and key == self.freeze_month and src == P_SHOPIFY:
                n = self._march_pause_count(M0, base)
            else:
                n = int(self.r_pause.binomial(len(pool), min(0.9, h * frac)))
            n = min(n, len(pool))
            sel = np.sort(self.r_pause.choice(len(pool), size=n, replace=False))
            idx = pool[sel]
            t = self.human.sample(self.r_time, np.full(n, lo), np.full(n, hi))
            self.start_pauses(idx, t, src)
            event_t[idx] = t
            taken[idx] = True
            pool = np.delete(pool, sel)
            total += n
        return total

    def _required_artefacts(self, base_mar: int) -> int:
        t_adj = int(round(self.targets["2026-03"] * base_mar))
        return int(round(self.cfg["targets"]["march_raw_round"] * base_mar)) - t_adj

    def _feb_pause_count(self, n_elig, h, M0, base_feb):
        n0 = self.n
        stock_before = int(((self.status[:n0] == PAUSED) & (self.pause_end[:n0] > self.snapshot)).sum())
        base_est = base_feb * 1.012
        a_est = self._required_artefacts(int(base_est))
        f_feb = 1 - self.w["pause_duration_months"][1] * (11 / 28)
        n_mar = n_elig * h * (10.8 / 31)
        k = (a_est - stock_before) / (n_elig * h * f_feb + n_mar)
        self.feb_k = k
        return int(self.r_pause.binomial(n_elig, min(0.9, max(0.0, h * k * 0.97))))

    def _march_pause_count(self, M0, base_mar):
        self.required_artefacts = self._required_artefacts(base_mar)
        n0 = self.n
        stock = int(self.artefact[:n0].sum())
        need = self.required_artefacts - stock
        if need < 0:
            raise RuntimeError(f"paused stock {stock} already above required artefacts {self.required_artefacts}")
        return need

    def _charge_loop(self, nc, stop, mask):
        nc = nc.copy()
        for _ in range(8):
            ok = mask & (nc < stop)
            if not ok.any():
                break
            i = np.flatnonzero(ok)
            self.charges.add(sub=i, t=nc[i], kind=np.full(len(i), K_RECURRING))
            self.last_charge[i] = nc[i]
            nc[i] = self.shift(at_time_of_day(nc[i], 5) + self.interval[i] * DAY)
        return nc

    def _run_charges(self, M0, M1, a, event_t, n1, nc0, failed):
        active = (a < M1) & ~self.gift[:n1]
        # phase 1: scheduled charges until the subscription's first event of the month
        stop = np.minimum(np.minimum(event_t, M1), self.term[:n1])
        nc = self._charge_loop(nc0, stop, active)
        # phase 2: failures recovered within the month continue billing after the recovery
        rec_in_month = failed & (self.dun_until[:n1] < M1) & (self.term[:n1] == NEVER)
        nc2 = self._charge_loop(self.next_charge[:n1], np.full(n1, M1, dtype=np.int64), rec_in_month)
        upd = active & ~failed & (event_t == NEVER)
        self.next_charge[:n1][upd] = nc[upd]
        self.next_charge[:n1][rec_in_month] = nc2[rec_in_month]
        other_event = (event_t < NEVER) & ~failed
        self.next_charge[:n1][other_event] = NEVER

    # ------------------------------------------------------------------ output

    def result(self) -> WorldResult:
        n = self.n
        subs = pd.DataFrame(dict(
            sub_id=np.arange(n), customer_id=self.cust[:n], start=self.start[:n], interval_days=self.interval[:n],
            method=np.array(METHODS)[self.method[:n]], frailty=self.frailty[:n], promo=self.promo[:n], is_gift=self.gift[:n],
            bags=self.bags[:n], size_g=self.size[:n], grind=self.grind[:n], product_idx=self.prod[:n], price=self.price[:n],
            term=self.term[:n], term_reason=self.term_reason[:n], queued=self.queued[:n], artefact=self.artefact[:n],
            orig_until=self.orig_until[:n], restore_time=self.restore_time[:n],
        ))
        customers = pd.DataFrame(dict(
            customer_id=np.arange(len(self.cust_created)), created=np.array(self.cust_created, dtype=np.int64),
            country=np.array(COUNTRIES)[np.array(self.cust_country, dtype=int)], consent=np.array(self.cust_consent, dtype=bool),
            gift_buyer=np.array(self.cust_is_gift_buyer, dtype=bool),
        ))
        pauses = self.pauses.frame()
        if len(pauses):
            upd = pd.Series(self.pause_end_updates, dtype="int64")
            m = pauses.row.isin(upd.index)
            pauses.loc[m, "end"] = upd.loc[pauses.row[m]].to_numpy()
        return WorldResult(
            subs=subs, customers=customers, charges=self.charges.frame().sort_values(["t", "sub"], kind="stable").reset_index(drop=True),
            pauses=pauses, cancels=self.cancels.frame(), dunning=self.dunning.frame(), monthly=pd.DataFrame(self.monthly),
            artefacts=subs[subs.artefact][["sub_id", "orig_until", "restore_time"]].reset_index(drop=True),
            params=dict(warmup_scale=self.warmup_scale, main_scale=self.main_scale, required_artefacts=self.required_artefacts),
        )
