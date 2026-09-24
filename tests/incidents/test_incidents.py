"""Each incident leaves exactly its fingerprint, and changes exactly the rows in the manifest."""

import json
import os
import pickle

import numpy as np
import pandas as pd
import pytest

from generator.generate import build

AMS = "Europe/Amsterdam"
STAMP = pd.Timestamp("2026-03-12 00:00:00", tz="UTC")


@pytest.fixture(scope="module")
def b():
    # KELDER_BUILD_CACHE=<file.pkl> reuses one in-memory build across runs while developing
    cache = os.environ.get("KELDER_BUILD_CACHE")
    if cache and os.path.exists(cache):
        return pickle.load(open(cache, "rb"))
    out = build()
    out.log = None
    if cache:
        pickle.dump(out, open(cache, "wb"))
    return out


def _ids(man, incident, table, change):
    m = man[(man.incident == incident) & (man.table_name == table) & (man.change_type == change)]
    return set(m.row_id)


def _changed(clean: pd.DataFrame, final: pd.DataFrame, cols):
    """Ids present in both frames whose values differ in any column (two missing values count as equal)."""
    cols = [c for c in cols if c != "id"]
    c = clean.set_index("id")
    f = final.set_index("id")
    common = c.index.intersection(f.index)
    diff = np.zeros(len(common), dtype=bool)
    for col in cols:
        x, y = c.loc[common, col], f.loc[common, col]
        both_na = x.isna().to_numpy() & y.isna().to_numpy()
        one_na = x.isna().to_numpy() ^ y.isna().to_numpy()
        ne = np.array([a != b for a, b in zip(x.astype(object), y.astype(object))], dtype=bool)
        diff |= (ne & ~both_na) | one_na
    return {str(i) for i in common[diff]}


def test_recharge_subscriptions_change_only_in_manifest(b):
    clean, final = b.recharge_clean["subscriptions"], b.systems["recharge"]["subscriptions"]
    man = b.manifest
    inserted = {str(i) for i in set(final.id) - set(clean.id)}
    assert inserted == _ids(man, "recharge_migration", "raw_recharge.subscriptions", "insert")
    assert set(clean.id) <= set(final.id)
    cols = [c for c in clean.columns if not c.startswith("_")]
    assert _changed(clean, final, cols) == _ids(man, "recharge_migration", "raw_recharge.subscriptions", "update")


def test_recharge_events_change_only_in_manifest(b):
    clean, final = b.recharge_clean["subscription_events"], b.systems["recharge"]["subscription_events"]
    man = b.manifest
    assert {str(i) for i in set(clean.id) - set(final.id)} == _ids(man, "recharge_migration", "raw_recharge.subscription_events", "delete")
    assert {str(i) for i in set(final.id) - set(clean.id)} == _ids(man, "recharge_migration", "raw_recharge.subscription_events", "insert")
    assert _changed(clean, final, ["subscription_id", "verb", "created_at", "payload"]) == \
        _ids(man, "recharge_migration", "raw_recharge.subscription_events", "update")


def test_recharge_charges_change_only_in_manifest(b):
    clean, final = b.recharge_clean["charges"], b.systems["recharge"]["charges"]
    assert set(clean.id) == set(final.id)
    cols = [c for c in clean.columns if not c.startswith("_")]
    assert _changed(clean, final, cols) == _ids(b.manifest, "recharge_migration", "raw_recharge.charges", "update")


def test_artefacts_and_queued_share_the_stamp_and_nothing_distinguishes_them_in_recharge(b):
    s = b.systems["recharge"]["subscriptions"]
    stamped = s[s.cancelled_at == STAMP]
    assert stamped.cancellation_reason.isna().all()
    assert stamped.external_contract_id.notna().all()
    art = int(b.world.subs.artefact.sum())
    q = int((b.world.subs.queued & (b.world.subs.term <= b.internal["stamp"])).sum())
    assert len(stamped) == art + int(b.world.subs.queued.sum())


def test_restores_point_at_paused_contracts_and_run_at_0915_on_weekdays(b):
    s = b.systems["recharge"]["subscriptions"]
    props = s.properties.map(json.loads)
    restores = s[props.map(lambda p: p.get("restore_source") == "legacy_pause")]
    assert len(restores) > 1000
    contracts = b.systems["shopify"]["subscription_contracts"].set_index("id")
    legacy = restores.properties.map(lambda p: int(json.loads(p)["legacy_contract_id"]))
    assert (contracts.loc[legacy.to_numpy(), "status"] == "PAUSED").all()
    local = restores.created_at.dt.tz_convert(AMS)
    assert (local.dt.strftime("%H:%M") == "09:15").all()
    assert (local.dt.dayofweek < 5).all()
    assert (local.dt.date >= pd.Timestamp("2026-03-16").date()).all()
    assert restores.external_contract_id.isna().all()


def test_klaviyo_outage_deletes_exactly_the_manifest_rows(b):
    clean, final = b.klaviyo_clean_events, b.systems["klaviyo"]["events"]
    gone = {str(i) for i in set(clean.id) - set(final.id)}
    assert gone == _ids(b.manifest, "klaviyo_outage", "raw_klaviyo.events", "delete")
    assert set(final.id) <= set(clean.id)
    lo, hi = pd.Timestamp("2026-04-09 06:00", tz="UTC"), pd.Timestamp("2026-04-10 13:00", tz="UTC")
    removed = clean[clean.id.isin([g for g in clean.id if str(g) in gone])]
    assert ((removed.timestamp >= lo) & (removed.timestamp < hi)).all()
    assert not ((final.timestamp >= lo) & (final.timestamp < hi)).any()


def test_kenya_nyeri_campaign_mostly_missing_but_late_opens_survive(b):
    camp = b.systems["klaviyo"]["campaigns"]
    cid = camp[camp.name.str.contains("Nieuwe oogst: Kenya Nyeri")].id.iloc[0]
    ev = b.systems["klaviyo"]["events"]
    ce = ev[ev.campaign_id == cid]
    aud = camp[camp.id == cid].audience_size.iloc[0]
    assert (ce.metric_name == "Received Email").sum() == 0
    assert 0 < (ce.metric_name == "Opened Email").sum() < 0.1 * aud


def test_shopify_orders_unaffected_by_the_outage(b):
    o = b.systems["shopify"]["orders"]
    day = o.created_at.dt.tz_convert(AMS).dt.date.astype(str)
    web = o[o.source_name == "web"]
    n = web.groupby(day[web.index]).size()
    assert n["2026-04-09"] > 0.6 * n[["2026-04-02", "2026-03-26", "2026-04-16"]].mean()


def test_billing_freeze_moves_charges_to_13_march(b):
    att = b.systems["shopify"]["subscription_billing_attempts"]
    ch = b.systems["recharge"]["charges"]
    lo, hi = pd.Timestamp("2026-03-11 20:00", tz=AMS), pd.Timestamp("2026-03-12 12:00", tz=AMS)
    assert not ((att.created_at >= lo) & (att.created_at < hi)).any()
    for col in ("scheduled_at", "processed_at"):
        assert not ((ch[col] >= lo) & (ch[col] < hi)).any()
    o = b.systems["shopify"]["orders"]
    subo = o[o.source_name != "web"]
    day = subo.created_at.dt.tz_convert(AMS).dt.date.astype(str).value_counts()
    assert day.get("2026-03-12", 0) == 0
    typical = day[["2026-03-05", "2026-03-06", "2026-03-19", "2026-03-20"]].mean()
    assert day["2026-03-13"] > 1.6 * typical
    shifted = b.manifest[b.manifest.incident == "billing_freeze"]
    assert len(shifted) > 0.8 * typical


def test_pause_campaign_and_blackout(b):
    ev = b.systems["recharge"]["subscription_events"]
    p = ev[ev.verb == "paused"]
    src = p.payload.map(lambda x: json.loads(x).get("source"))
    assert (p[src == "cancel_flow"].created_at >= pd.Timestamp("2026-03-28", tz=AMS)).all()
    assert (src == "cancel_flow").sum() > 500
    se = b.systems["shopify"]["subscription_contract_events"]
    sp = se[se.event_type == "paused"]
    lo, hi = pd.Timestamp("2026-03-12", tz=AMS), pd.Timestamp("2026-03-28", tz=AMS)
    assert not ((sp.occurred_at >= lo) & (sp.occurred_at < hi)).any()
    assert not ((p.created_at > STAMP) & (p.created_at < hi)).any()


def test_postnl_strike_delays_only_dutch_postnl_parcels_shipped_18_to_24_may(b):
    f = b.systems["shopify"]["fulfillments"]
    days = (f.delivered_at - f.created_at).dt.total_seconds() / 86400
    ship = f.created_at.dt.tz_convert(AMS).dt.date.astype(str)
    in_window = (ship >= "2026-05-18") & (ship <= "2026-05-24")
    post = f.tracking_company == "PostNL"
    strike = in_window & post
    assert days[strike].min() >= 2.5 and days[strike].quantile(0.5) >= 3
    assert days[post & ~in_window].quantile(0.99) < 3.5
    assert (f.status[strike] == "failure").mean() == pytest.approx(0.01, abs=0.005)
    assert (f.status[~strike] == "success").all()
    r = b.systems["shopify"]["refunds"]
    late = r[r.note == "late_delivery"]
    aff = set(b.systems["shopify"]["fulfillments"][strike].order_id)
    rate = late.order_id.isin(aff).sum() / len(aff)
    assert 0.05 <= rate <= 0.09
    assert len(_ids(b.manifest, "postnl_strike", "raw_shopify.fulfillments", "update")) == strike.sum()


def test_fathers_day_bundle_and_gift_subscriptions(b):
    lines = b.systems["shopify"]["order_lines"]
    o = b.systems["shopify"]["orders"].set_index("id")
    bl = lines[lines.sku == "BUNDLE-VADERDAG-2026"]
    t = o.loc[bl.order_id, "created_at"].dt.tz_convert(AMS).dt.date.astype(str)
    assert (t >= "2026-06-14").all() and (t <= "2026-06-21").all()
    assert len(bl) > 800
    s = b.systems["recharge"]["subscriptions"]
    gift = s[s.properties.map(lambda p: json.loads(p).get("is_gift", False))]
    gd = gift.created_at.dt.tz_convert(AMS).dt.date.astype(str)
    assert ((gd >= "2026-06-14") & (gd <= "2026-06-21")).all()
    assert (gift.price == 0).all() and gift.is_prepaid.all()
    assert 400 <= len(gift) <= 500
