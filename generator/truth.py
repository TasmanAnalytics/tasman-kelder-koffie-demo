"""The hidden ground truth: what really happened, written to data/truth/kelder_truth.duckdb.

Used only by the builder's tests. Never loaded into a warehouse, never copied to a workspace.
All metrics here are computed from the world, independently of the source-system rendering.
"""

from __future__ import annotations

import json
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

from .common import DAY, NEVER, add_months, month_key, month_start, ts
from .systems.common import utc
from .world import R_EXPIRED, R_MAX_RETRIES, R_VOLUNTARY, WorldResult
from .world_commerce import O_BUNDLE, O_EMAIL, O_GIFT_PURCHASE, O_RETAIL, CommerceResult


def months_between(a: str, b: str) -> list[str]:
    out, m = [], month_start(int(a[:4]), int(a[5:]))
    end = month_start(int(b[:4]), int(b[5:]))
    while m <= end:
        out.append(str(month_key([m])[0]))
        m = int(add_months(np.array([m]), 1)[0])
    return out


def attributed_revenue(events: pd.DataFrame, days: int) -> pd.DataFrame:
    """Placed Order value with a click by the same profile in the previous `days` days (the governed rule)."""
    po = events[events.metric_name == "Placed Order"][["profile_id", "timestamp", "value_eur"]].sort_values("timestamp", kind="stable")
    cl = events[events.metric_name == "Clicked Email"][["profile_id", "timestamp"]].rename(columns={"timestamp": "click_ts"}).sort_values("click_ts", kind="stable")
    m = pd.merge_asof(po, cl, left_on="timestamp", right_on="click_ts", by="profile_id", direction="backward",
                      tolerance=pd.Timedelta(days=days))
    m = m[m.click_ts.notna()]
    local_day = m.timestamp.dt.tz_convert("Europe/Amsterdam").dt.date
    return m.assign(day=local_day).groupby("day").agg(orders=("value_eur", "size"), revenue=("value_eur", "sum")).reset_index()


def compute(cfg: dict, world: WorldResult, com: CommerceResult, klaviyo_clean: pd.DataFrame, klaviyo_final: pd.DataFrame,
            reg, internal: dict, manifest: pd.DataFrame) -> dict[str, pd.DataFrame]:
    d = cfg["dates"]
    cutoff = ts(d["cutoff_local"])
    s = world.subs
    ng = s[~s.is_gift]
    months = months_between("2025-01", d["simulate_until"][:7])
    pauses = world.pauses
    cancels = world.cancels
    dn = world.dunning
    vol = cancels[cancels.reason == R_VOLUNTARY]
    rows = []
    for key in months:
        M0 = month_start(int(key[:4]), int(key[5:]))
        M1 = int(add_months(np.array([M0]), 1)[0])
        base_mask = (ng.start < M0) & (ng.term >= M0)
        base = int(base_mask.sum())
        v = int(((vol.t >= M0) & (vol.t < M1)).sum())
        dm = (dn.t0 >= M0) & (dn.t0 < M1)
        ff = int(dm.sum())
        unrec = int((dm & ~dn.recovered.astype(bool)).sum())
        unrec_asof = int((dm & ~dn.recovered.astype(bool) & (dn.t_end <= cutoff)).sum())
        in_pause = (pauses.start < M0) & (pauses.end > M0)
        paused = int(pauses[in_pause]["sub"].isin(ng.sub_id[base_mask]).sum())
        p_starts = int(((pauses.start >= M0) & (pauses.start < M1)).sum())
        new = int(((ng.start >= M0) & (ng.start < M1)).sum())
        gifts = int(((s.start >= M0) & (s.start < M1) & s.is_gift).sum())
        rows.append(dict(month=key, base=base, voluntary_cancellations=v, first_failures=ff,
                         unrecovered_failures_final=unrec, unrecovered_failures_asof=unrec_asof,
                         churned_v1=v + ff, churned_v2_final=v + unrec, churned_v2_asof=v + unrec_asof,
                         churn_v1=(v + ff) / base, churn_v2_final=(v + unrec) / base, churn_v2_asof=(v + unrec_asof) / base,
                         paused_count=paused, pause_starts=p_starts, pause_rate=p_starts / base,
                         new_subscribers=new, gift_subscriptions_sold=gifts))
    metrics = pd.DataFrame(rows)
    # orders and email revenue (window only)
    o = com.orders
    o = o[o.t < cutoff]
    mk = pd.Series(month_key(o.t.to_numpy()), index=o.index)
    retail = o[o.kind.isin([O_RETAIL, O_BUNDLE, O_EMAIL])]
    metrics["retail_orders"] = metrics.month.map(mk[retail.index].value_counts()).fillna(0).astype(int)
    days = cfg["klaviyo"]["attribution_days"]
    rev_world = attributed_revenue(klaviyo_clean, days)
    rev_obs = attributed_revenue(klaviyo_final, days)
    daily = pd.DataFrame(dict(day=sorted(set(rev_world.day) | set(rev_obs.day))))
    daily = daily.merge(rev_world.rename(columns={"orders": "orders_world", "revenue": "revenue_world"}), on="day", how="left")
    daily = daily.merge(rev_obs.rename(columns={"orders": "orders_observed", "revenue": "revenue_observed"}), on="day", how="left").fillna(0)
    daily["month"] = pd.to_datetime(daily.day).dt.strftime("%Y-%m")
    mon = daily.groupby("month")[["revenue_world", "revenue_observed"]].sum()
    metrics["email_attributed_revenue_world"] = metrics.month.map(mon.revenue_world).fillna(0).round(2)
    metrics["email_attributed_revenue_observed"] = metrics.month.map(mon.revenue_observed).fillna(0).round(2)
    metrics.loc[metrics.month > d["window_end"][:7], ["retail_orders", "email_attributed_revenue_world", "email_attributed_revenue_observed"]] = np.nan

    # type 2 status history
    ep = []
    ps = pauses.sort_values(["sub", "start"], kind="stable")
    by_sub = {k: g for k, g in ps.groupby("sub")}
    for sid, cust, start, term, reason in zip(s.sub_id, s.customer_id, s.start, s.term, s.term_reason):
        cur = start
        for pst, pend in zip(by_sub[sid].start, by_sub[sid].end) if sid in by_sub else []:
            if pst >= term:
                break
            ep.append((sid, cust, "active", cur, pst))
            ep.append((sid, cust, "paused", pst, min(pend, term)))
            cur = min(pend, term)
        if cur < term:
            ep.append((sid, cust, "active", cur, term))
        if term < NEVER:
            ep.append((sid, cust, "expired" if reason == R_EXPIRED else "cancelled", term, NEVER))
    ep = pd.DataFrame(ep, columns=["world_subscription_id", "customer_id", "true_status", "valid_from", "valid_to"])
    ep = ep[ep.valid_to > ep.valid_from]
    episodes = pd.DataFrame(dict(world_subscription_id=ep.world_subscription_id.to_numpy(), customer_id=ep.customer_id.to_numpy(),
                                 true_status=ep.true_status.to_numpy(), valid_from=utc(ep.valid_from.to_numpy()),
                                 valid_to=utc(ep.valid_to.to_numpy())))
    # id map
    restore_of = internal.get("restore_of", {})
    id_map = pd.DataFrame(dict(world_subscription_id=s.sub_id.to_numpy(), is_gift=s.is_gift.to_numpy()))
    id_map["shopify_contract_id"] = id_map.world_subscription_id.map(reg.contract).astype("Int64")
    id_map["recharge_subscription_id"] = id_map.world_subscription_id.map(internal["rc_of"]).astype("Int64")
    id_map["recharge_restore_subscription_id"] = id_map.world_subscription_id.map(pd.Series(restore_of, dtype="int64")).astype("Int64")
    id_map["is_migration_artifact"] = s.artefact.to_numpy()
    id_map["is_queued_cancellation"] = s.queued.to_numpy()
    # dunning episodes
    retry = np.array(cfg["world"]["retry_days"])
    dd = dn.copy()
    retries = []
    for t0, rec, rd in zip(dd.t0, dd.recovered, dd.rec_day):
        n = int(np.searchsorted(retry, rd)) + 1 if rec else len(retry)
        retries.append(json.dumps([str(utc([t0 + x * DAY])[0]) for x in retry[:n]]))
    dunning = pd.DataFrame(dict(world_subscription_id=dd["sub"].to_numpy(), first_failure_at=utc(dd.t0.to_numpy()),
                                first_failure_month=month_key(dd.t0.to_numpy()), retries=retries,
                                outcome=np.where(dd.recovered.astype(bool), "recovered", "unrecovered"),
                                outcome_at=utc(dd.t_end.to_numpy()), recovery_day=dd.rec_day.to_numpy()))
    return dict(subscription_episodes=episodes, id_map=id_map, dunning_episodes=dunning, metrics_monthly=metrics,
                email_attribution_daily=daily, incident_manifest=manifest)


def targets_table(cfg: dict, metrics: pd.DataFrame, artefacts: int, queued: int) -> pd.DataFrame:
    t = cfg["targets"]
    m = metrics.set_index("month")
    rows = []

    def add(name, target, achieved, ok):
        rows.append(dict(target=name, expected=str(target), achieved=float(achieved), passed=bool(ok)))

    add("base_2025_01_01", f"{t['base_2025_01_01']} +/- {t['base_2025_01_01_tol']}", m.loc["2025-01", "base"],
        abs(m.loc["2025-01", "base"] - t["base_2025_01_01"]) <= t["base_2025_01_01_tol"])
    b = m.loc["2026-03", "base"]
    add("base_2026_03_01", f"{t['base_2026_03_01']} +/- {t['base_2026_03_01_tol']}", b, abs(b - t["base_2026_03_01"]) <= t["base_2026_03_01_tol"])
    add("migration_artefacts", f"{t['artefacts_min']}..{t['artefacts_max']}", artefacts, t["artefacts_min"] <= artefacts <= t["artefacts_max"])
    raw = (m.loc["2026-03", "churned_v1"] + artefacts) / b
    adj = m.loc["2026-03", "churn_v1"]
    add("march_2026_v1_raw", f"{t['march_raw_min']}..{t['march_raw_max']}", raw, t["march_raw_min"] <= raw <= t["march_raw_max"])
    add("march_2026_v1_adjusted", f"{t['march_adj_min']}..{t['march_adj_max']}", adj, t["march_adj_min"] <= adj <= t["march_adj_max"])
    sf = m.loc["2025-09":"2026-02", "churn_v1"].mean()
    add("mean_v1_adjusted_2025_09_to_2026_02", "rounds to 3.1%", sf, round(sf * 100, 1) == 3.1)
    add("queued_genuine_cancellations", f"{t['queued_cancellations_min']}..{t['queued_cancellations_max']}", queued,
        t["queued_cancellations_min"] <= queued <= t["queued_cancellations_max"])
    q1 = m.loc["2026-01":"2026-03"]
    gap = ((q1.churn_v1 - q1.churn_v2_asof) * 100).mean()
    add("v1_minus_v2_restated_q1_2026_pp", f"{t['v1_minus_v2_q1_2026_min_pp']}..{t['v1_minus_v2_q1_2026_max_pp']}", gap,
        t["v1_minus_v2_q1_2026_min_pp"] <= gap <= t["v1_minus_v2_q1_2026_max_pp"])
    may_rep, apr_rep = m.loc["2026-05", "churn_v2_asof"], m.loc["2026-04", "churn_v1"]
    add("as_reported_may_below_april", "May v2 < April v1", may_rep - apr_rep, may_rep < apr_rep)
    imp = (m.loc["2025-01":"2025-06", "churn_v2_asof"].mean() - m.loc["2026-01":"2026-06", "churn_v2_asof"].mean()) * 100
    add("restated_v2_h1_improvement_pp", f"{t['yoy_improvement_min_pp']}..{t['yoy_improvement_max_pp']}", imp,
        t["yoy_improvement_min_pp"] <= imp <= t["yoy_improvement_max_pp"])
    for k, v in t["v1_adjusted"].items():
        a = m.loc[k, "churn_v1"]
        add(f"v1_adjusted_{k}", f"{v} +/- {t['monthly_tolerance_pp']}pp", a, abs(a - v) * 100 <= t["monthly_tolerance_pp"])
    return pd.DataFrame(rows)


def write(path: Path, tables: dict[str, pd.DataFrame]):
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        path.unlink()
    con = duckdb.connect(str(path))
    for name, df in tables.items():
        con.register("_df", df)
        con.execute(f"create table {name} as select * from _df")
        con.unregister("_df")
    con.close()
