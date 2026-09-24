"""Render ad spend through the Meta and Google Ads connectors."""

from __future__ import annotations

import numpy as np
import pandas as pd

from ..common import DAY, rng_for, ts
from ..world_commerce import CommerceResult
from .common import fivetran, synced_after, utc


def render(cfg: dict, com: CommerceResult) -> dict[str, pd.DataFrame]:
    r = rng_for(cfg["seed"], "ads.render")
    cutoff_utc = utc([ts(cfg["dates"]["cutoff_local"])])[0]
    a = com.ads.sort_values(["day", "platform", "campaign_id"], kind="stable")
    day = pd.to_datetime(a.day.to_numpy() // DAY, unit="D").date
    sync = synced_after(utc(a.day.to_numpy() + DAY + 3 * 3600), r, cutoff_utc, 10, 240)
    meta = a.platform.to_numpy() == "meta"
    m = pd.DataFrame(dict(date=day[meta], account_id=a.account_id.to_numpy()[meta], campaign_id=a.campaign_id.to_numpy()[meta],
                          campaign_name=a.campaign_name.to_numpy()[meta], spend=a.spend.to_numpy()[meta],
                          impressions=a.impressions.to_numpy()[meta], clicks=a.clicks.to_numpy()[meta]))
    g = pd.DataFrame(dict(date=day[~meta], customer_id=a.account_id.to_numpy()[~meta], campaign_id=a.campaign_id.to_numpy()[~meta],
                          campaign_name=a.campaign_name.to_numpy()[~meta], cost_micros=np.round(a.spend.to_numpy()[~meta] * 1e6).astype(np.int64),
                          impressions=a.impressions.to_numpy()[~meta], clicks=a.clicks.to_numpy()[~meta]))
    return dict(meta_ads_daily=fivetran(m, sync[meta].reset_index(drop=True)),
                google_ads_daily=fivetran(g, sync[~meta].reset_index(drop=True)))
