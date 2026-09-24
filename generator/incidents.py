"""Incidents: explicit, logged transformations.

Two kinds, both written to the incident manifest:

- Rendering incidents change what the source systems recorded, not what happened:
  the Recharge import (paused contracts written as cancelled, queued cancellations stamped at
  midnight, operations restores) and the Fivetran Klaviyo outage (events never synced).
  They are applied here to the clean rendered tables, and every created, altered or removed row
  is logged with before and after values.
- World incidents changed what customers experienced: the billing freeze moved charges, the
  PostNL strike delayed parcels and caused refunds. They happen inside the world simulation;
  the rows they changed are logged here so the manifest is complete.
"""

from __future__ import annotations

import json

import numpy as np
import pandas as pd

from .common import DAY, NEVER, rng_for, ts, utc_to_local
from .systems.common import ids, to_json, utc


def _val(v):
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return None
    if isinstance(v, pd.Timestamp):
        return None if pd.isna(v) else v.isoformat()
    if v is pd.NaT:
        return None
    if isinstance(v, (np.integer,)):
        return int(v)
    if isinstance(v, (np.floating,)):
        return float(v)
    if isinstance(v, (np.bool_,)):
        return bool(v)
    try:
        if pd.isna(v):
            return None
    except (TypeError, ValueError):
        pass
    return str(v) if not isinstance(v, (int, float, bool, str)) else v


class Manifest:
    def __init__(self):
        self.rows = []

    def log(self, incident, table, row_id, change, before=None, after=None):
        enc = lambda d: None if d is None else json.dumps({k: _val(v) for k, v in d.items()}, sort_keys=True, ensure_ascii=False)
        self.rows.append(dict(incident=incident, table_name=table, row_id=str(row_id), change_type=change,
                              before_value=enc(before), after_value=enc(after)))

    def frame(self) -> pd.DataFrame:
        return pd.DataFrame(self.rows, columns=["incident", "table_name", "row_id", "change_type", "before_value", "after_value"])


# ---------------------------------------------------------------------------- Recharge migration


def recharge_migration(cfg, tables: dict, internal: dict, world, reg, man: Manifest) -> dict:
    """Paused contracts imported as cancelled; queued cancellations stamped at the import; restores."""
    subs = tables["subscriptions"].copy()
    ev = tables["subscription_events"].copy()
    chg = tables["charges"].copy()
    rs = internal["rs"]
    rc_of = internal["rc_of"]
    stamp_utc = internal["stamp_utc"]
    cutoff = ts(cfg["dates"]["cutoff_local"])
    r = rng_for(cfg["seed"], "incidents.recharge")
    inc = "recharge_migration"
    subs_i = subs.set_index("id")
    wsubs = world.subs.set_index("sub_id")

    cols = ["status", "cancelled_at", "cancellation_reason", "cancellation_reason_comments", "paused_until",
            "updated_at", "next_charge_scheduled_at"]
    new_rows, new_events = [], []
    next_sub_id = int(subs.id.max())
    next_ev_id = int(ev.id.max())
    art = rs[rs.snap_status == "PAUSED"].sort_values("sub_id")
    for sub in art.sub_id:
        rid = int(rc_of[sub])
        before = subs_i.loc[rid, cols].to_dict()
        restore_t = int(wsubs.loc[sub, "restore_time"])
        restored = restore_t < cutoff
        if restored:
            # the restore subscription inherits the continuing state; the original is cancelled at the import
            next_sub_id += int(r.integers(1, 300))
            row = subs_i.loc[rid].to_dict()
            row["id"] = next_sub_id
            row["external_contract_id"] = None
            row["created_at"] = utc([restore_t])[0]
            row["properties"] = json.dumps({"is_gift": False, "legacy_contract_id": str(reg.contract[sub]),
                                            "restore_source": "legacy_pause"}, sort_keys=True)
            new_rows.append(row)
            internal.setdefault("restore_of", {})[int(sub)] = int(next_sub_id)
            man.log(inc, "raw_recharge.subscriptions", next_sub_id, "insert", None,
                    {"customer_id": row["customer_id"], "created_at": row["created_at"], "properties": row["properties"],
                     "status": row["status"]})
        after = dict(status="cancelled", cancelled_at=stamp_utc, cancellation_reason=None, cancellation_reason_comments=None,
                     paused_until=None, updated_at=stamp_utc, next_charge_scheduled_at=pd.NaT)
        for k, v in after.items():
            subs_i.at[rid, k] = v
        man.log(inc, "raw_recharge.subscriptions", rid, "update", before, after)
        # events: the 'paused' at the import becomes 'cancelled'; later events move to the restore
        m = ev["_sub"].to_numpy() == sub
        for i in np.flatnonzero(m):
            e = ev.iloc[i]
            if e.verb == "paused" and e["_t"] == internal["stamp"]:
                man.log(inc, "raw_recharge.subscription_events", e.id, "delete", {"verb": "paused", "created_at": e.created_at}, None)
                ev.iat[i, ev.columns.get_loc("verb")] = "__drop__"
            elif e["_t"] > internal["stamp"]:
                if e.verb == "unpaused" and restored and e["_t"] == restore_t:
                    man.log(inc, "raw_recharge.subscription_events", e.id, "delete", {"verb": "unpaused", "created_at": e.created_at}, None)
                    ev.iat[i, ev.columns.get_loc("verb")] = "__drop__"
                elif restored and e["_t"] >= restore_t:
                    man.log(inc, "raw_recharge.subscription_events", e.id, "update", {"subscription_id": rid}, {"subscription_id": next_sub_id})
                    ev.iat[i, ev.columns.get_loc("subscription_id")] = next_sub_id
        next_ev_id += int(r.integers(1, 40))
        new_events.append(dict(id=next_ev_id, subscription_id=rid, verb="cancelled", created_at=stamp_utc,
                               payload=json.dumps({"cancellation_reason": None}), _sub=sub, _t=internal["stamp"]))
        man.log(inc, "raw_recharge.subscription_events", next_ev_id, "insert", None, {"subscription_id": rid, "verb": "cancelled", "created_at": stamp_utc})
        if restored:
            for verb in ("created", "activated"):
                next_ev_id += int(r.integers(1, 40))
                new_events.append(dict(id=next_ev_id, subscription_id=next_sub_id, verb=verb, created_at=utc([restore_t])[0],
                                       payload=json.dumps({"is_gift": False}), _sub=sub, _t=restore_t))
                man.log(inc, "raw_recharge.subscription_events", next_ev_id, "insert", None,
                        {"subscription_id": next_sub_id, "verb": verb, "created_at": utc([restore_t])[0]})
            cm = (chg["_sub"].to_numpy() == sub) & (chg["_t"].to_numpy() >= restore_t)
            for i in np.flatnonzero(cm):
                man.log(inc, "raw_recharge.charges", chg.id.iat[i], "update", {"subscription_id": rid}, {"subscription_id": next_sub_id})
            chg.loc[cm, "subscription_id"] = next_sub_id

    # genuine cancellations queued during the freeze, imported with the same midnight stamp and no reason
    q = rs[rs.queued & rs.migrated].sort_values("sub_id")
    for sub in q.sub_id:
        rid = int(rc_of[sub])
        before = subs_i.loc[rid, ["cancelled_at", "cancellation_reason", "cancellation_reason_comments", "updated_at"]].to_dict()
        after = dict(cancelled_at=stamp_utc, cancellation_reason=None, cancellation_reason_comments=None, updated_at=stamp_utc)
        for k, v in after.items():
            subs_i.at[rid, k] = v
        man.log(inc, "raw_recharge.subscriptions", rid, "update", before, after)
        m = np.flatnonzero((ev["_sub"].to_numpy() == sub) & (ev.verb.to_numpy() == "cancelled"))
        for i in m:
            man.log(inc, "raw_recharge.subscription_events", ev.id.iat[i], "update",
                    {"created_at": ev.created_at.iat[i], "payload": ev.payload.iat[i]},
                    {"created_at": stamp_utc, "payload": json.dumps({"cancellation_reason": None})})
            ev.iat[i, ev.columns.get_loc("created_at")] = stamp_utc
            ev.iat[i, ev.columns.get_loc("payload")] = json.dumps({"cancellation_reason": None})
            ev.iat[i, ev.columns.get_loc("_t")] = internal["stamp"]

    subs = subs_i.reset_index()
    if new_rows:
        subs = pd.concat([subs, pd.DataFrame(new_rows)], ignore_index=True)
    for c in ("created_at", "updated_at", "cancelled_at", "next_charge_scheduled_at"):
        subs[c] = pd.to_datetime(subs[c], utc=True).astype("datetime64[us, UTC]")
    ev = ev[ev.verb != "__drop__"]
    ev = pd.concat([ev, pd.DataFrame(new_events)], ignore_index=True)
    ev["created_at"] = pd.to_datetime(ev.created_at, utc=True).astype("datetime64[us, UTC]")
    ev = ev.sort_values(["created_at", "id"], kind="stable").reset_index(drop=True)
    subs = subs.sort_values(["created_at", "id"], kind="stable").reset_index(drop=True)
    out = dict(tables)
    out.update(subscriptions=subs, subscription_events=ev, charges=chg)
    return out


# ---------------------------------------------------------------------------- Klaviyo outage


def klaviyo_outage(cfg, events: pd.DataFrame, man: Manifest) -> pd.DataFrame:
    d = cfg["dates"]
    lo = pd.Timestamp(d["klaviyo_outage_start_utc"], tz="UTC")
    hi = pd.Timestamp(d["klaviyo_outage_end_utc"], tz="UTC")
    m = (events.timestamp >= lo) & (events.timestamp < hi)
    gone = events[m]
    for eid, metric, t in zip(gone.id, gone.metric_name, gone.timestamp):
        man.log("klaviyo_outage", "raw_klaviyo.events", eid, "delete", {"metric_name": metric, "timestamp": t}, None)
    return events[~m].reset_index(drop=True)


# ---------------------------------------------------------------------------- world incidents (logged only)


def log_billing_freeze(cfg, world, man: Manifest):
    fl = world.freeze_log
    if len(fl) == 0:
        return
    fl = fl[fl["sub"] >= 0].drop_duplicates()
    ch = world.charges
    real = set(zip(ch["sub"].tolist(), ch.t.tolist()))
    cn = world.cancels
    real |= set(zip(cn["sub"].tolist(), cn.t.tolist()))
    fl = fl[[(s, a) in real for s, a in zip(fl["sub"], fl.actual)]].sort_values(["sub", "nominal"])
    for s, n_, a, what in zip(fl["sub"], fl.nominal, fl.actual, fl.what):
        man.log("billing_freeze", "world.charges", f"{s}@{n_}", "shift", {"time_utc": utc([n_])[0], "what": what}, {"time_utc": utc([a])[0]})


def log_strike(cfg, com, reg, man: Manifest):
    f = com.fulfillments
    o = com.orders
    cutoff = ts(cfg["dates"]["cutoff_local"])
    aff = f[f.strike]
    for okey, nom, act, never in zip(aff.okey, aff.nominal_t, aff.deliv_t, aff.never):
        oid = reg.shopify_order.get(okey)
        if oid is None:
            continue
        man.log("postnl_strike", "raw_shopify.fulfillments", f"order:{oid}", "update",
                {"delivered_at": utc([nom])[0] if nom < cutoff else None},
                {"delivered_at": None if (never or act >= cutoff) else utc([act])[0], "status": "failure" if never else "success"})
    rf = com.refunds[com.refunds.strike]
    for okey, t, amt in zip(rf.okey, rf.t, rf.amount):
        oid = reg.shopify_order.get(okey)
        if oid is None:
            continue
        man.log("postnl_strike", "raw_shopify.refunds", f"order:{oid}", "insert", None, {"created_at": utc([t])[0], "amount": float(amt), "note": "late_delivery"})
