"""Render the world through Recharge, from the 12 March 2026 import onwards.

This renderer produces the *clean* Recharge data: what the tables would hold if the import had
kept paused subscriptions paused. incidents.py then applies the migration damage (paused
contracts imported as cancelled, queued cancellations stamped at midnight, restores) as explicit,
logged transformations.

Recharge quirk (not an incident): there is no paused status. A paused subscription is 'active'
with paused_until set.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..catalogue import Catalogue
from ..common import DAY, NEVER, rng_for, ts, utc_to_local
from ..world import K_FIRST, K_GIFT, K_RECURRING, P_CANCEL_FLOW, R_EXPIRED, R_MAX_RETRIES, R_VOLUNTARY, WorldResult
from ..world_commerce import CommerceResult
from .common import fivetran, ids, synced_after, to_json, utc
from .shopify import ERRORS, Registry, local_date, order_lookup, snapshot_state

RECHARGE_ERRORS = {"card": ["card_declined", "insufficient_funds", "expired_card"],
                   "mandate": ["debit_rejected", "insufficient_funds"], "paypal": ["paypal_error"]}


def render(cfg: dict, cat: Catalogue, world: WorldResult, com: CommerceResult, reg: Registry) -> tuple[dict, dict]:
    d = cfg["dates"]
    r = rng_for(cfg["seed"], "recharge.render")
    cutoff = ts(d["cutoff_local"])
    cutoff_utc = utc([cutoff])[0]
    stamp_utc = pd.Timestamp(d["import_stamp_utc"], tz="UTC")
    stamp = int(utc_to_local(np.array([ts(d["import_stamp_utc"])]))[0])
    freeze_end = ts(d["freeze_end_local"])
    blackout_end = ts(d["pause_blackout_end_local"])

    snap = snapshot_state(cfg, world)
    migrated = snap[snap.snap_status.isin(["ACTIVE", "PAUSED"])].copy()
    subs = world.subs.set_index("sub_id")
    native = world.subs[world.subs.start >= freeze_end].copy()
    rs = pd.concat([migrated.assign(migrated=True), native.assign(migrated=False, snap_status=None)], ignore_index=True)
    rs = rs.sort_values(["migrated", "start", "sub_id"], ascending=[False, True, True], kind="stable").reset_index(drop=True)
    rs["rc_id"] = ids(r, len(rs), 480_000_000, 300)
    rc_of = pd.Series(rs.rc_id.to_numpy(), index=rs.sub_id.to_numpy())

    # customers
    first = rs.groupby("customer_id").agg(first_start=("start", "min"), any_migrated=("migrated", "max")).reset_index()
    first = first.sort_values(["any_migrated", "first_start", "customer_id"], ascending=[False, True, True], kind="stable").reset_index(drop=True)
    first["rcust"] = ids(r, len(first), 210_000_000, 120)
    rcust_of = pd.Series(first.rcust.to_numpy(), index=first.customer_id.to_numpy())
    c_created = np.where(first.any_migrated, stamp, first.first_start)
    customers = fivetran(pd.DataFrame(dict(
        id=first.rcust.to_numpy(), shopify_customer_id=first.customer_id.map(reg.shopify_customer).to_numpy(),
        email=first.customer_id.map(reg.names.email).to_numpy(), created_at=utc(c_created),
    )), synced_after(utc(c_created), r, cutoff_utc))

    # subscription state at the cutoff (clean)
    pauses = world.pauses
    lp = pauses[pauses.start < cutoff].sort_values(["sub", "start"]).groupby("sub").tail(1).set_index("sub")
    sid = rs.sub_id.to_numpy()
    p_start = pd.Series(sid).map(lp.start).to_numpy(dtype=float)
    p_end = pd.Series(sid).map(lp.end).to_numpy(dtype=float)
    p_src = pd.Series(sid).map(lp.source).to_numpy(dtype=float)
    term = rs.term.to_numpy()
    ended = term < cutoff
    status = np.where(ended, np.where(rs.term_reason == R_EXPIRED, "expired", "cancelled"), "active")
    paused_now = ~ended & ~np.isnan(p_start) & (np.nan_to_num(p_end, nan=0) >= cutoff)
    ch = world.charges
    nxt = ch[ch.t >= cutoff].groupby("sub").t.min()
    next_charge = pd.Series(sid).map(nxt).to_numpy(dtype=float)
    next_charge = np.where(~ended & ~paused_now & ~np.isnan(next_charge), next_charge, NEVER).astype(np.int64)
    # migrated rows carry the original contract date, date only, at 00:00:00 UTC
    contract_date_utc = pd.to_datetime(utc(rs.start.to_numpy()).dt.date).dt.tz_localize("UTC").astype("datetime64[us, UTC]")
    created_at = contract_date_utc.where(rs.migrated.to_numpy(), utc(rs.start.to_numpy()))
    reason = np.where(ended & (rs.term_reason == R_VOLUNTARY), pd.Series(sid).map(reg.reason_code).to_numpy(),
                      np.where(ended & (rs.term_reason == R_MAX_RETRIES), "max_retries_reached", None))
    comments = np.where(ended & (rs.term_reason == R_VOLUNTARY), pd.Series(sid).map(reg.reason_comment).to_numpy(), None)
    last_change = np.maximum.reduce([
        np.where(rs.migrated, stamp, rs.start.to_numpy()),
        np.where(~np.isnan(p_start) & (np.nan_to_num(p_start) >= stamp), np.nan_to_num(p_start), 0).astype(np.int64),
        np.where(~np.isnan(p_end) & (np.nan_to_num(p_end) < cutoff) & (np.nan_to_num(p_end) >= stamp), np.nan_to_num(p_end), 0).astype(np.int64),
        np.where(ended, term, 0),
    ])
    vids = cat.coffee_variant(rs.product_idx.to_numpy().astype(int), rs.size_g.to_numpy(), rs.grind.to_numpy().astype(int))
    house = cat.variants.set_index("sku").loc[[k for k in cat.variants.sku if k.startswith("BL-KELD-HUIS-250-WB")][0]]
    vids = np.where(rs.is_gift.to_numpy(), house.id, vids)
    vsku = cat.variants.set_index("id").sku
    props = to_json([{"is_gift": bool(g)} for g in rs.is_gift])
    subscriptions = pd.DataFrame(dict(
        id=rs.rc_id.to_numpy(), customer_id=rs.customer_id.map(rcust_of).to_numpy(),
        external_contract_id=np.where(rs.migrated, rs.sub_id.map(reg.contract).astype("Int64").astype(str), None),
        shopify_variant_id=vids, sku=pd.Series(vids).map(vsku).to_numpy(),
        quantity=np.where(rs.is_gift, 1, rs.bags).astype(int), price=np.where(rs.is_gift, 0.0, rs.price).round(2),
        order_interval_unit="week", order_interval_frequency=(rs.interval_days // 7).astype(int).to_numpy(),
        status=status, created_at=created_at.to_numpy(), updated_at=utc(last_change),
        cancelled_at=utc(np.where(ended, term, NEVER)), cancellation_reason=reason, cancellation_reason_comments=comments,
        next_charge_scheduled_at=utc(np.where(next_charge < NEVER, next_charge // DAY * DAY, NEVER)),
        paused_until=local_date(np.where(paused_now, np.nan_to_num(p_end, nan=0).astype(np.int64), NEVER)),
        is_prepaid=rs.is_gift.to_numpy().astype(bool), properties=props,
    ))
    subscriptions["created_at"] = subscriptions["created_at"].astype("datetime64[us, UTC]")

    # events (clean)
    ev = []
    mig = rs[rs.migrated]
    ev.append(pd.DataFrame(dict(sub=mig.sub_id, t=stamp, verb="created",
                                payload=to_json([{"external_contract_id": str(reg.contract[s])} for s in mig.sub_id]))))
    art = mig[mig.snap_status == "PAUSED"]
    art_until = art.sub_id.map(lp.end)
    ev.append(pd.DataFrame(dict(sub=art.sub_id, t=stamp, verb="paused",
                                payload=to_json([{"paused_until": str(np.datetime64(int(e // DAY), "D"))} for e in art_until]))))
    art_res = art[art_until.to_numpy() < cutoff]
    ev.append(pd.DataFrame(dict(sub=art_res.sub_id, t=art_res.sub_id.map(lp.end), verb="unpaused", payload=to_json([{}] * len(art_res)))))
    nat = rs[~rs.migrated]
    for verb in ("created", "activated"):
        ev.append(pd.DataFrame(dict(sub=nat.sub_id, t=nat.start, verb=verb, payload=to_json([{"is_gift": bool(g)} for g in nat.is_gift]))))
    pz = pauses[(pauses.start >= blackout_end) & (pauses.start < cutoff) & pauses["sub"].isin(rs.sub_id)]
    src = np.where(pz.source == P_CANCEL_FLOW, "cancel_flow", "customer_portal")
    ev.append(pd.DataFrame(dict(sub=pz["sub"], t=pz.start, verb="paused",
                                payload=to_json([{"paused_until": str(np.datetime64(int(e // DAY), "D")), "source": s}
                                                 for e, s in zip(pz.end, src)]))))
    uz = pz[pz.end < cutoff]
    ev.append(pd.DataFrame(dict(sub=uz["sub"], t=uz.end, verb="unpaused", payload=to_json([{}] * len(uz)))))
    endr = rs[(rs.term < cutoff) & ((rs.term >= stamp) | rs.queued)]
    verb = np.where(endr.term_reason == R_EXPIRED, "expired", "cancelled")
    pl = [{} if tr == R_EXPIRED else {"cancellation_reason": ("max_retries_reached" if tr == R_MAX_RETRIES else reg.reason_code.get(s))}
          for s, tr in zip(endr.sub_id, endr.term_reason)]
    ev.append(pd.DataFrame(dict(sub=endr.sub_id, t=endr.term, verb=verb, payload=to_json(pl))))
    ev = pd.concat(ev, ignore_index=True)
    ev["t"] = ev.t.astype(np.int64)
    ev = ev.sort_values(["t", "sub", "verb"], kind="stable").reset_index(drop=True)
    events = pd.DataFrame(dict(
        id=ids(r, len(ev), 1_200_000_000, 40), subscription_id=ev["sub"].map(rc_of).to_numpy(), verb=ev.verb.to_numpy(),
        created_at=utc(ev.t.to_numpy()), payload=ev.payload.to_numpy(), _sub=ev["sub"].to_numpy(), _t=ev.t.to_numpy(),
    ))

    # charges (clean)
    lookup = order_lookup(com)
    in_rc = ch["sub"].isin(rs.sub_id)
    succ = ch[in_rc & (ch.t >= freeze_end) & (ch.t < cutoff) & ch.kind.isin([K_RECURRING, K_GIFT, K_FIRST])].copy()
    dn = world.dunning
    dn = dn[dn["sub"].isin(rs.sub_id) & (dn.t_end >= stamp) & (dn.t0 < cutoff)].copy()
    retry = np.array(cfg["world"]["retry_days"])
    methods = subs.loc[dn["sub"].to_numpy(), "method"].to_numpy()
    rows = []
    for sub, t0, rec, rd, t_end, meth in zip(dn["sub"], dn.t0, dn.recovered, dn.rec_day, dn.t_end, methods):
        n_fail = int(np.searchsorted(retry, rd)) if rec else len(retry)
        tries_times = [int(t0)] + [int(t0 + dd * DAY) for dd in retry[:n_fail]]
        if rec and t_end < cutoff:
            st, proc, tried, rdate, err = "success", int(t_end), n_fail + 2, NEVER, None
        elif (not rec) and t_end < cutoff:
            st, proc, tried, rdate, err = "error", NEVER, len(retry) + 1, NEVER, RECHARGE_ERRORS[meth][0]
        else:
            done = [x for x in tries_times if x < cutoff]
            nxt_try = [int(t0 + dd * DAY) for dd in retry if t0 + dd * DAY >= cutoff]
            st, proc, tried, rdate, err = "error", NEVER, len(done), (nxt_try[0] if nxt_try else NEVER), RECHARGE_ERRORS[meth][0]
        rows.append((sub, int(t0), st, proc, tried, rdate, err, int(t_end) if st == "success" else -1))
    dunc = pd.DataFrame(rows, columns=["sub", "sched", "status", "proc", "tried", "retry", "err", "rec_t"])
    succ = pd.DataFrame(dict(sub=succ["sub"].to_numpy(), sched=succ.t.to_numpy(), status="success", proc=succ.t.to_numpy(), tried=1,
                             retry=NEVER, err=None, rec_t=succ.t.to_numpy()))
    allc = pd.concat([succ, dunc], ignore_index=True).sort_values(["sched", "sub"], kind="stable").reset_index(drop=True)
    okey = lookup.reindex(pd.MultiIndex.from_arrays([allc["sub"].to_numpy(), allc.rec_t.to_numpy()])).to_numpy()
    total = allc["sub"].map(subs.price).to_numpy()
    charges = pd.DataFrame(dict(
        id=ids(r, len(allc), 700_000_000, 60), customer_id=allc["sub"].map(subs.customer_id).map(rcust_of).to_numpy(),
        subscription_id=allc["sub"].map(rc_of).to_numpy(), status=allc.status.to_numpy(),
        scheduled_at=utc(allc.sched.to_numpy()), processed_at=utc(allc.proc.to_numpy().astype(np.int64)),
        total_price=np.round(total, 2), error_type=allc.err.to_numpy(),
        retry_date=utc(allc.retry.to_numpy().astype(np.int64)), number_times_tried=allc.tried.astype(int).to_numpy(),
        external_order_id=pd.Series(okey).map(reg.shopify_order).astype("Int64").to_numpy(),
        _sub=allc["sub"].to_numpy(), _t=allc.sched.to_numpy(),
    ))

    internal = dict(rc_of=rc_of, rcust_of=rcust_of, rs=rs, stamp=stamp, stamp_utc=stamp_utc, cutoff_utc=cutoff_utc, lp=lp)
    tables = dict(customers=customers, subscriptions=subscriptions, subscription_events=events, charges=charges)
    return tables, internal


def finalise(tables: dict, cutoff_utc, rng) -> dict:
    """Add Fivetran columns and drop helper columns after incidents have been applied."""
    out = {}
    for name, df in tables.items():
        df = df.drop(columns=[c for c in df.columns if c.startswith("_") and not c.startswith("_fivetran")])
        if "_fivetran_synced" not in df.columns:
            col = "updated_at" if "updated_at" in df.columns else ("processed_at" if "processed_at" in df.columns else "created_at")
            base = df[col].fillna(df["created_at"] if "created_at" in df.columns else df[col]) if col != "created_at" else df[col]
            if name == "charges":
                base = df["processed_at"].fillna(df["scheduled_at"])
            df = fivetran(df, synced_after(base, rng, cutoff_utc))
        out[name] = df
    return out
