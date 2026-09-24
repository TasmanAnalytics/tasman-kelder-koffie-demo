"""Render email engagement through Klaviyo (profiles, campaigns, flows, events)."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..common import DAY, rng_for, ts
from ..world_commerce import O_BUNDLE, O_EMAIL, O_GIFT_PURCHASE, O_RETAIL, O_SUB_FIRST, CommerceResult
from .common import fivetran, hex_ids, synced_after, utc
from .shopify import Registry

FLOWS = {"welcome": "Welkom bij Kelder", "post_purchase": "Na je eerste bestelling", "win_back": "Win-back na opzegging",
         "abandoned_checkout": "Verlaten winkelwagen"}


def render(cfg: dict, com: CommerceResult, reg: Registry) -> dict[str, pd.DataFrame]:
    r = rng_for(cfg["seed"], "klaviyo.render")
    cutoff = ts(cfg["dates"]["cutoff_local"])
    cutoff_utc = utc([cutoff])[0]
    c = com.customers
    prof = c[c.consent & (c.created < cutoff)].sort_values(["created", "customer_id"], kind="stable").reset_index(drop=True)
    pid = hex_ids(r, len(prof), "01J")
    pid_of = pd.Series(pid, index=prof.customer_id.to_numpy())
    pc = utc(prof.created.to_numpy() + 20)
    profiles = fivetran(pd.DataFrame(dict(id=pid, email=prof.customer_id.map(reg.names.email).to_numpy(),
                                          shopify_customer_id=prof.customer_id.map(reg.shopify_customer).to_numpy(), created_at=pc)),
                        synced_after(pc, r, cutoff_utc))
    camp = com.campaigns
    cid = hex_ids(r, len(camp), "", 6)
    campaigns = fivetran(pd.DataFrame(dict(id=cid, name=camp.name.to_numpy(), subject=camp.subject.to_numpy(),
                                           send_time=utc(camp.send.to_numpy()), status="Sent", audience_size=camp.audience.to_numpy())),
                         synced_after(utc(camp.send.to_numpy()), r, cutoff_utc, 60, 600))
    fid = hex_ids(r, len(FLOWS), "", 6)
    flow_of = dict(zip(FLOWS.keys(), fid))
    flows = fivetran(pd.DataFrame(dict(id=fid, name=list(FLOWS.values()))), cutoff_utc - pd.Timedelta(hours=3))
    msg_of_campaign = pd.Series(np.char.add("msg_", cid), index=camp.campaign_idx.to_numpy())
    msg_of_flow = {k: f"msg_{v}" for k, v in flow_of.items()}

    e = com.email_events
    e = e[e.customer_id.isin(pid_of.index)]
    is_c = e.campaign_idx.to_numpy() >= 0
    campaign_id = np.where(is_c, pd.Series(e.campaign_idx.to_numpy()).map(pd.Series(cid, index=camp.campaign_idx.to_numpy())).to_numpy(), None)
    flow_id = np.where(~is_c, pd.Series(e.flow.to_numpy()).map(flow_of).to_numpy(), None)
    msg = np.where(is_c, pd.Series(e.campaign_idx.to_numpy()).map(msg_of_campaign).to_numpy(), pd.Series(e.flow.to_numpy()).map(msg_of_flow).to_numpy())
    eng = pd.DataFrame(dict(metric_name=e.metric.to_numpy(), customer_id=e.customer_id.to_numpy(), t=e.t.to_numpy(),
                            campaign_id=campaign_id, flow_id=flow_id, value_eur=np.nan, attributed_message_id=msg,
                            okey=-1))
    # Placed Order for every web order by a profile; Klaviyo attributes it to the last click within 5 days
    o = com.orders
    o = o[o.kind.isin([O_SUB_FIRST, O_GIFT_PURCHASE, O_RETAIL, O_BUNDLE, O_EMAIL]) & o.customer_id.isin(pid_of.index) & (o.t < cutoff)]
    po = pd.DataFrame(dict(customer_id=o.customer_id.to_numpy(), t=o.t.to_numpy() + r.integers(2, 30, len(o)), value_eur=o.total.to_numpy(),
                           okey=o.okey.to_numpy())).sort_values("t", kind="stable")
    clicks = eng[eng.metric_name == "Clicked Email"][["customer_id", "t", "attributed_message_id"]].sort_values("t", kind="stable")
    att = pd.merge_asof(po, clicks.rename(columns={"t": "click_t"}), left_on="t", right_on="click_t", by="customer_id",
                        direction="backward", tolerance=cfg["klaviyo"]["attribution_days"] * DAY)
    placed = pd.DataFrame(dict(metric_name="Placed Order", customer_id=att.customer_id.to_numpy(), t=att.t.to_numpy(), campaign_id=None,
                               flow_id=None, value_eur=att.value_eur.to_numpy(), attributed_message_id=att.attributed_message_id.to_numpy(),
                               okey=att.okey.to_numpy()))
    allev = pd.concat([eng, placed], ignore_index=True).sort_values(["t", "customer_id", "metric_name"], kind="stable").reset_index(drop=True)
    ts_ = utc(allev.t.to_numpy())
    events = fivetran(pd.DataFrame(dict(
        id=hex_ids(r, len(allev), "", 20), metric_name=allev.metric_name.to_numpy(),
        profile_id=allev.customer_id.map(pid_of).to_numpy(), timestamp=ts_, campaign_id=allev.campaign_id.to_numpy(),
        flow_id=allev.flow_id.to_numpy(), value_eur=allev.value_eur.to_numpy(),
        attributed_message_id=np.where(pd.isna(allev.attributed_message_id), None, allev.attributed_message_id),
        shopify_order_id=pd.Series(allev.okey.to_numpy()).map(reg.shopify_order).astype("Int64").to_numpy(),
    )), synced_after(ts_, r, cutoff_utc, 20, 400))
    return dict(profiles=profiles, campaigns=campaigns, flows=flows, events=events)
