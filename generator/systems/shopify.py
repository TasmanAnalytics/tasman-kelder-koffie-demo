"""Render the world through Shopify (orders, customers, catalogue) and the Shopify subscription app.

Fivetran's Shopify connector syncs from 2025-01-01. The subscription tables were last synced at
2026-03-11 21:30 UTC, when the connector was paused for the move to Recharge, so they hold the
state at that moment.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import yaml
from faker import Faker

from ..catalogue import FLAVOUR, GRINDS, Catalogue
from ..common import DAY, HOUR, NEVER, month_key, rng_for, ts, utc_to_local
from ..world import K_FIRST, K_GIFT, K_RECOVERY, K_RECURRING, R_EXPIRED, R_MAX_RETRIES, R_VOLUNTARY, WorldResult
from ..world_commerce import O_BUNDLE, O_EMAIL, O_GIFT_PURCHASE, O_GIFT_SHIPMENT, O_RETAIL, O_SUB_FIRST, O_SUB_RECURRING, CommerceResult
from .common import fivetran, ids, slug, synced_after, to_json, utc

LOCALES = {"NL": "nl_NL", "BE": "nl_BE", "DE": "de_DE", "LU": "de_DE", "FR": "nl_BE"}
ERRORS = {
    "card": [("CARD_DECLINED", "Your card was declined."), ("INSUFFICIENT_FUNDS", "Insufficient funds."),
             ("EXPIRED_PAYMENT_METHOD", "The card has expired.")],
    "mandate": [("PAYMENT_METHOD_DECLINED", "SEPA direct debit was rejected by the bank."),
                ("INSUFFICIENT_FUNDS", "Insufficient funds.")],
    "paypal": [("PAYMENT_PROVIDER_ERROR", "PayPal billing agreement could not be charged.")],
}


class Registry:
    """World id -> source id maps shared between renderers."""

    def __init__(self):
        self.shopify_customer: pd.Series | None = None
        self.shopify_order: pd.Series | None = None
        self.contract: pd.Series | None = None
        self.names: pd.DataFrame | None = None
        self.reason_code: dict = {}
        self.reason_comment: dict = {}


def fake_people(cfg, customers: pd.DataFrame) -> pd.DataFrame:
    """Names and @example.com emails, deterministic per customer."""
    seed = cfg["seed"]
    out_first = np.empty(len(customers), dtype=object)
    out_last = np.empty(len(customers), dtype=object)
    for ctry, loc in sorted(LOCALES.items()):
        m = (customers.country == ctry).to_numpy()
        if not m.any():
            continue
        f = Faker(loc)
        f.seed_instance(seed + sum(map(ord, ctry)))
        n = int(m.sum())
        out_first[m] = [f.first_name() for _ in range(n)]
        out_last[m] = [f.last_name() for _ in range(n)]
    r = rng_for(seed, "shopify.emails")
    style = r.integers(0, 4, len(customers))
    num = r.integers(1, 99, len(customers))
    emails, seen = [], set()
    for fn, ln, st, nu in zip(out_first, out_last, style, num):
        a, b = slug(fn), slug(ln)
        local = [f"{a}.{b}", f"{a}{b}{nu}", f"{a[:1]}{b}", f"{a}.{b}{nu}"][st]
        e = f"{local}@example.com"
        k = 2
        while e in seen:
            e = f"{local}{k}@example.com"
            k += 1
        seen.add(e)
        emails.append(e)
    return pd.DataFrame(dict(customer_id=customers.customer_id.to_numpy(), first_name=out_first, last_name=out_last, email=emails))


def snapshot_state(cfg, world: WorldResult) -> pd.DataFrame:
    """Status of every Shopify subscription contract at the last sync."""
    d = cfg["dates"]
    snap = int(utc_to_local(np.array([ts(d["shopify_last_sync_utc"])]))[0])
    freeze_start = ts(d["freeze_start_local"])
    s = world.subs
    s = s[s.start < freeze_start].copy()
    st = np.full(len(s), "ACTIVE", dtype=object)
    ended = (s.term <= snap).to_numpy()
    st[ended & (s.term_reason == R_VOLUNTARY).to_numpy()] = "CANCELLED"
    st[ended & (s.term_reason == R_MAX_RETRIES).to_numpy()] = "FAILED"
    st[ended & (s.term_reason == R_EXPIRED).to_numpy()] = "EXPIRED"
    st[s.queued.to_numpy()] = "ACTIVE"
    st[s.artefact.to_numpy()] = "PAUSED"
    s["snap_status"] = st
    return s


def render(cfg: dict, cat: Catalogue, world: WorldResult, com: CommerceResult, reg: Registry) -> dict[str, pd.DataFrame]:
    d = cfg["dates"]
    seed = cfg["seed"]
    r = rng_for(seed, "shopify.render")
    cutoff = ts(d["cutoff_local"])
    cutoff_utc = utc([cutoff])[0]
    w0 = ts(d["window_start"])
    snap_utc = pd.Timestamp(d["shopify_last_sync_utc"], tz="UTC")
    snap = int(utc_to_local(np.array([ts(d["shopify_last_sync_utc"])]))[0])
    freeze_start = ts(d["freeze_start_local"])
    freeze_end = ts(d["freeze_end_local"])
    out: dict[str, pd.DataFrame] = {}

    # ------------------------------------------------------------------ customers
    cust = com.customers[com.customers.created < cutoff].sort_values(["created", "customer_id"], kind="stable").reset_index(drop=True)
    cid = ids(r, len(cust), 7_104_000_000_000, 5000)
    reg.shopify_customer = pd.Series(cid, index=cust.customer_id.to_numpy())
    people = fake_people(cfg, cust)
    reg.names = people.set_index("customer_id")
    subs = world.subs
    gift_buyers = set(world.customers.customer_id[world.customers.gift_buyer].tolist())
    tags = np.where(cust.kind == "subscriber", "subscriber", "")
    tags = np.where(cust.customer_id.isin(gift_buyers), "gift-buyer", tags)
    created = utc(cust.created.to_numpy())
    out["customers"] = fivetran(pd.DataFrame(dict(
        id=cid, email=people.email.to_numpy(), first_name=people.first_name.to_numpy(), last_name=people.last_name.to_numpy(),
        country_code=cust.country.to_numpy(), created_at=created, accepts_marketing=cust.consent.to_numpy().astype(bool),
        tags=tags,
    )), synced_after(pd.Series([cutoff_utc - pd.Timedelta(hours=2)] * len(cust)), r, cutoff_utc, 1, 90))

    # ------------------------------------------------------------------ catalogue
    p = cat.products
    out["products"] = fivetran(pd.DataFrame(dict(
        id=p.id.to_numpy(), title=p.title.to_numpy(), product_type=p.product_type.to_numpy(),
        created_at=pd.Timestamp("2023-03-20 10:00", tz="UTC"), status="active",
    )), cutoff_utc - pd.Timedelta(minutes=40))
    v = cat.variants
    out["product_variants"] = fivetran(pd.DataFrame(dict(
        id=v.id.to_numpy(), product_id=v.product_id.to_numpy(), sku=v.sku.to_numpy(), title=v.title.to_numpy(),
        price=v.price.to_numpy(), grams=v.grams.to_numpy(), taxable=v.taxable.to_numpy(),
    )), cutoff_utc - pd.Timedelta(minutes=40))

    # ------------------------------------------------------------------ orders
    o = com.orders
    o = o[(o.t >= w0) & (o.t < cutoff)].reset_index(drop=True)
    oid = ids(r, len(o), 5_921_000_000_000, 3000)
    reg.shopify_order = pd.Series(oid, index=o.okey.to_numpy())
    first_number = 10_001 + 38_000  # orders before the connector started are not synced
    name = np.char.add("#K", (first_number + np.arange(len(o))).astype(str))
    created = utc(o.t.to_numpy())
    kind = o.kind.to_numpy()
    recurring = np.isin(kind, [O_SUB_RECURRING, O_GIFT_SHIPMENT])
    source = np.where(recurring, np.where(o.t.to_numpy() < freeze_end, "subscription_contract", "recharge"), "web")
    tag = np.select(
        [kind == O_SUB_FIRST, kind == O_SUB_RECURRING, kind == O_GIFT_PURCHASE, kind == O_GIFT_SHIPMENT, kind == O_BUNDLE],
        ["Subscription First Order", "Subscription Recurring Order", "Gift Subscription", "Gift Subscription, Subscription Recurring Order", "Vaderdag"],
        "",
    )
    landing, referrer = _landing(o, r)
    ref = com.refunds
    ref_amt = ref.groupby("okey").amount.sum()
    refunded = o.okey.map(ref_amt).fillna(0).to_numpy()
    fin = np.where(refunded <= 0, "paid", np.where(refunded >= o.total.to_numpy() - 0.005, "refunded", "partially_refunded"))
    ful = com.fulfillments.set_index("okey")
    shipped = o.okey.map(ful.ship_t).to_numpy() < cutoff
    codes = to_json([[{"code": c, "amount": f"{a:.2f}", "type": "percentage"}] if c else [] for c, a in zip(o.discount_code, o.discount)])
    subs_by_id = subs.set_index("sub_id")
    out["orders"] = fivetran(pd.DataFrame(dict(
        id=oid, name=name, customer_id=o.customer_id.map(reg.shopify_customer).to_numpy(), created_at=created,
        processed_at=created + pd.to_timedelta(r.integers(1, 40, len(o)), unit="s"),
        financial_status=fin, fulfillment_status=np.where(shipped, "fulfilled", None), currency="EUR",
        subtotal_price=o.subtotal.to_numpy(), total_tax=o.tax.to_numpy(), total_discounts=o.discount.to_numpy(),
        total_price=o.total.to_numpy(), source_name=source, tags=tag, landing_site=landing, referring_site=referrer,
        discount_codes=codes, cancelled_at=pd.Series([pd.NaT] * len(o), dtype="datetime64[us, UTC]"),
    )), synced_after(created, r, cutoff_utc))

    lines = com.lines[com.lines.okey.isin(o.okey)].reset_index(drop=True)
    vsku = cat.variants.set_index("id").sku
    out["order_lines"] = fivetran(pd.DataFrame(dict(
        id=ids(r, len(lines), 13_880_000_000_000, 40), order_id=lines.okey.map(reg.shopify_order).to_numpy(),
        variant_id=lines.variant_id.to_numpy(), sku=lines.variant_id.map(vsku).to_numpy(), quantity=lines.quantity.to_numpy(),
        price=lines.price.to_numpy().round(2), total_discount=lines.discount.to_numpy().round(2),
    )), synced_after(lines.okey.map(pd.Series(created.to_numpy(), index=o.okey.to_numpy())), r, cutoff_utc))

    ref = ref[ref.okey.isin(o.okey)].sort_values(["t", "okey"], kind="stable").reset_index(drop=True)
    rc = utc(ref.t.to_numpy())
    out["refunds"] = fivetran(pd.DataFrame(dict(
        id=ids(r, len(ref), 901_000_000_000, 900), order_id=ref.okey.map(reg.shopify_order).to_numpy(), created_at=rc,
        amount=ref.amount.to_numpy().round(2), note=ref.note.to_numpy(),
    )), synced_after(rc, r, cutoff_utc))

    f = com.fulfillments
    f = f[f.okey.isin(o.okey) & (f.ship_t < cutoff)].sort_values(["ship_t", "okey"], kind="stable").reset_index(drop=True)
    fc = utc(f.ship_t.to_numpy())
    delivered = np.where(f.deliv_t.to_numpy() < cutoff, f.deliv_t.to_numpy(), NEVER)
    status = np.where(f.never.to_numpy(), "failure", "success")
    out["fulfillments"] = fivetran(pd.DataFrame(dict(
        id=ids(r, len(f), 4_710_000_000_000, 3000), order_id=f.okey.map(reg.shopify_order).to_numpy(), created_at=fc,
        tracking_company=f.carrier.to_numpy(), status=status, delivered_at=utc(delivered),
    )), synced_after(utc(np.where(delivered < NEVER, delivered, f.ship_t.to_numpy())), r, cutoff_utc))

    # ------------------------------------------------------------------ subscription contracts (state at last sync)
    s = snapshot_state(cfg, world).sort_values(["start", "sub_id"], kind="stable").reset_index(drop=True)
    kid = ids(r, len(s), 21_400_000, 400)
    reg.contract = pd.Series(kid, index=s.sub_id.to_numpy())
    pauses = world.pauses
    last_pause = pauses[pauses.start < snap].sort_values(["sub", "start"]).groupby("sub").tail(1).set_index("sub")
    ch = world.charges
    nxt = ch[ch.t > snap].groupby("sub").t.min()
    reasons = yaml.safe_load(open(FLAVOUR / "cancellation_reasons.yaml"))
    reg.reason_code, reg.reason_comment = _reasons(cfg, world, reasons)
    st = s.snap_status.to_numpy()
    sid = s.sub_id.to_numpy()
    lp_start = pd.Series(sid).map(last_pause.start).to_numpy(dtype=float)
    lp_orig = pd.Series(sid).map(last_pause.orig_end).to_numpy(dtype=float)
    lp_end = pd.Series(sid).map(last_pause.end).to_numpy(dtype=float)
    term = s.term.to_numpy()
    upd = s.start.to_numpy().astype(float)
    upd = np.where(~np.isnan(lp_start), np.maximum(upd, lp_start), upd)
    upd = np.where(~np.isnan(lp_end) & (lp_end <= snap), np.maximum(upd, lp_end), upd)
    upd = np.where(np.isin(st, ["CANCELLED", "FAILED", "EXPIRED"]), term, upd)
    next_bill = pd.Series(sid).map(nxt).to_numpy(dtype=float)
    next_bill = np.where(st == "ACTIVE", next_bill, np.where(st == "PAUSED", lp_orig, np.nan))
    next_bill = np.where(np.isnan(next_bill), NEVER, next_bill).astype(np.int64)
    vids = cat.coffee_variant(s.product_idx.to_numpy().astype(int), s.size_g.to_numpy(), s.grind.to_numpy().astype(int))
    house = cat.variants.set_index("sku").loc[[k for k in cat.variants.sku if k.startswith("BL-KELD-HUIS-250-WB")][0]].id
    vids = np.where(s.is_gift.to_numpy(), house, vids)
    attrs = to_json([{"is_gift": bool(g), "grind": GRINDS[int(gr)], "payment_method": pm}
                     for g, gr, pm in zip(s.is_gift, s.grind, s.method)])
    cancelled = np.where(np.isin(st, ["CANCELLED", "FAILED", "EXPIRED"]), term, NEVER)
    reason = np.where(st == "CANCELLED", pd.Series(sid).map(reg.reason_code).to_numpy(),
                      np.where(st == "FAILED", "max_retries_reached", None))
    paused = st == "PAUSED"
    out["subscription_contracts"] = fivetran(pd.DataFrame(dict(
        id=kid, customer_id=s.customer_id.map(reg.shopify_customer).to_numpy(), status=st,
        created_at=utc(s.start.to_numpy()), updated_at=utc(upd.astype(np.int64)),
        next_billing_date=local_date(next_bill),
        billing_interval="WEEK", billing_interval_count=(s.interval_days.to_numpy() // 7).astype(int),
        line_variant_id=vids, line_quantity=np.where(s.is_gift, 1, s.bags).astype(int),
        paused_at=utc(np.where(paused, np.nan_to_num(lp_start, nan=0).astype(np.int64), NEVER)),
        pause_until=local_date(np.where(paused, np.nan_to_num(lp_orig, nan=0).astype(np.int64), NEVER)),
        cancelled_at=utc(cancelled), cancellation_reason=reason, custom_attributes=attrs,
    )), snap_utc)

    # ------------------------------------------------------------------ contract events (webhook log, 2025-01-01 to the freeze)
    ev = []
    in_k = s.set_index("sub_id")
    new = in_k[(in_k.start >= w0)]
    ev.append(pd.DataFrame(dict(sub=new.index, t=new.start, event_type="created", detail=to_json([{"source": "checkout"}] * len(new)))))
    pz = pauses[(pauses.start >= w0) & (pauses.start < snap) & pauses["sub"].isin(in_k.index)]
    ev.append(pd.DataFrame(dict(sub=pz["sub"], t=pz.start, event_type="paused",
                                detail=to_json([{"pause_until": str(np.datetime64(int(e // DAY), "D")), "source": "customer_portal"}
                                                for e in pz.orig_end]))))
    rz = pauses[(pauses.end >= w0) & (pauses.end <= snap) & pauses["sub"].isin(in_k.index)]
    ev.append(pd.DataFrame(dict(sub=rz["sub"], t=rz.end, event_type="resumed", detail=to_json([{}] * len(rz)))))
    endk = in_k[(in_k.term >= w0) & (in_k.term <= snap) & ~in_k.queued]
    et = np.where(endk.term_reason == R_EXPIRED, "expired", "cancelled")
    det = [{"reason": "max_retries_reached"} if tr == R_MAX_RETRIES else ({} if tr == R_EXPIRED else {"reason": reg.reason_code.get(i)})
           for i, tr in zip(endk.index, endk.term_reason)]
    ev.append(pd.DataFrame(dict(sub=endk.index, t=endk.term, event_type=et, detail=to_json(det))))

    # billing attempts in the Shopify era
    att = _billing_attempts(cfg, world, in_k, w0, freeze_start, r, order_lookup(com))
    att["order_id"] = att.okey.map(reg.shopify_order)
    ok = att.error_code.isna()
    ev.append(pd.DataFrame(dict(sub=att["sub"][ok], t=att.t[ok] + 3, event_type="billing_succeeded",
                                detail=to_json([{"order_id": int(x)} if pd.notna(x) else {} for x in att.order_id[ok]]))))
    ev.append(pd.DataFrame(dict(sub=att["sub"][~ok], t=att.t[~ok] + 3, event_type="billing_failed",
                                detail=to_json([{"error_code": e, "attempt": int(n)} for e, n in zip(att.error_code[~ok], att.attempt[~ok])]))))
    ev = pd.concat(ev, ignore_index=True)
    ev = ev[(ev.t >= w0) & (ev.t <= snap)].sort_values(["t", "sub", "event_type"], kind="stable").reset_index(drop=True)
    et_utc = utc(ev.t.to_numpy())
    out["subscription_contract_events"] = fivetran(pd.DataFrame(dict(
        id=ids(r, len(ev), 880_000_000, 30), contract_id=ev["sub"].map(reg.contract).to_numpy(), event_type=ev.event_type.to_numpy(),
        occurred_at=et_utc, detail=ev.detail.to_numpy(),
    )), synced_after(et_utc, r, snap_utc, 1, 30))

    att = att.sort_values(["t", "sub"], kind="stable").reset_index(drop=True)
    at_utc = utc(att.t.to_numpy())
    out["subscription_billing_attempts"] = fivetran(pd.DataFrame(dict(
        id=ids(r, len(att), 60_500_000, 20), contract_id=att["sub"].map(reg.contract).to_numpy(), created_at=at_utc,
        completed_at=at_utc + pd.to_timedelta(r.integers(2, 25, len(att)), unit="s"), error_code=att.error_code.to_numpy(),
        error_message=att.error_message.to_numpy(), order_id=att.order_id.astype("Int64").to_numpy(),
        idempotency_key=[f"kelder-{k}-{c}-{n}" for k, c, n in zip(att["sub"].map(reg.contract), att.cycle, att.attempt)],
    )), synced_after(at_utc, r, snap_utc, 1, 30))
    return out


def _billing_attempts(cfg, world, in_k, w0, freeze_start, r, lookup) -> pd.DataFrame:
    """Every Shopify billing attempt from 2025-01-01 until the freeze, with its billing cycle and attempt number."""
    ch = world.charges
    ch = ch[(ch.t >= w0) & (ch.t < freeze_start) & ch["sub"].isin(in_k.index) & ch.kind.isin([K_RECURRING, K_GIFT])]
    subs = world.subs.set_index("sub_id")
    # gift purchases are checkout orders, not billing attempts
    first_gift = (ch.kind == K_GIFT).to_numpy() & (ch.t.to_numpy() == subs.loc[ch["sub"].to_numpy(), "start"].to_numpy())
    ch = ch[~first_gift]
    rows = dict(sub=[ch["sub"].to_numpy()], t=[ch.t.to_numpy()], cycle=[ymd(ch.t.to_numpy())], attempt=[np.ones(len(ch), int)],
                error_code=[np.full(len(ch), None, dtype=object)], error_message=[np.full(len(ch), None, dtype=object)])
    dn = world.dunning
    dn = dn[dn["sub"].isin(in_k.index)]
    retry = np.array(cfg["world"]["retry_days"])
    methods = subs.loc[dn["sub"].to_numpy(), "method"].to_numpy()
    subl, tl, cyl, atl, ecl, eml = [], [], [], [], [], []
    for sub, t0, rec, rd, t_end, meth in zip(dn["sub"], dn.t0, dn.recovered, dn.rec_day, dn.t_end, methods):
        n_fail = int(np.searchsorted(retry, rd)) if rec else len(retry)
        times = [int(t0)] + [int(t0 + dday * DAY) for dday in retry[:n_fail]]
        code, msg = ERRORS[meth][int(r.integers(0, len(ERRORS[meth])))]
        cyc = ymd(np.array([t0]))[0]
        for k, tt in enumerate(times):
            if w0 <= tt < freeze_start:
                subl.append(sub); tl.append(tt); cyl.append(cyc); atl.append(k + 1); ecl.append(code); eml.append(msg)
        if rec and w0 <= t_end < freeze_start:
            subl.append(sub); tl.append(int(t_end)); cyl.append(cyc); atl.append(n_fail + 2); ecl.append(None); eml.append(None)
    rows["sub"].append(np.array(subl, dtype=np.int64)); rows["t"].append(np.array(tl, dtype=np.int64))
    rows["cycle"].append(np.array(cyl, dtype=object)); rows["attempt"].append(np.array(atl, dtype=int))
    rows["error_code"].append(np.array(ecl, dtype=object)); rows["error_message"].append(np.array(eml, dtype=object))
    att = pd.DataFrame({k: np.concatenate(v) for k, v in rows.items()})
    idx = pd.MultiIndex.from_arrays([att["sub"].to_numpy(), att.t.to_numpy()])
    att["okey"] = lookup.reindex(idx).to_numpy()
    att.loc[att.error_code.notna(), "okey"] = np.nan
    return att


def ymd(sec: np.ndarray) -> np.ndarray:
    days = (np.asarray(sec, dtype=np.int64) // DAY).astype("datetime64[D]")
    return np.char.replace(np.datetime_as_string(days, unit="D").astype(str), "-", "")


def local_date(sec) -> pd.Series:
    """Local calendar date of local seconds; NEVER becomes None."""
    a = np.asarray(sec, dtype=np.int64)
    never = a >= NEVER // 2
    dd = pd.Series(pd.to_datetime(np.where(never, 0, a // DAY), unit="D")).dt.date
    dd[never] = None
    return dd


def order_lookup(com: CommerceResult) -> pd.Series:
    o = com.orders[com.orders.sub_id >= 0]
    return pd.Series(o.okey.to_numpy(), index=pd.MultiIndex.from_arrays([o.sub_id.to_numpy(), o.t.to_numpy()]))


def _reasons(cfg, world, reasons):
    r = rng_for(cfg["seed"], "shopify.reasons")
    s = world.subs[world.subs.term_reason == R_VOLUNTARY].sort_values("sub_id")
    codes = [x["code"] for x in reasons["reasons"]]
    p = np.array([x["share"] for x in reasons["reasons"]])
    c = np.array(codes)[r.choice(len(codes), len(s), p=p / p.sum())]
    comments = np.array(reasons["comments"], dtype=object)[r.integers(0, len(reasons["comments"]), len(s))]
    comments = np.where(comments == "", None, comments)
    return dict(zip(s.sub_id.tolist(), c.tolist())), dict(zip(s.sub_id.tolist(), comments.tolist()))


def _landing(o: pd.DataFrame, r) -> tuple[np.ndarray, np.ndarray]:
    ch = o.channel.to_numpy()
    n = len(o)
    land = np.full(n, None, dtype=object)
    refr = np.full(n, None, dtype=object)
    meta = np.array(["kel_prospecting_nl_be", "kel_retargeting", "kel_abonnement_promo"])
    goog = np.array(["kel_brand", "kel_generic_koffieabonnement", "kel_shopping"])
    pages = np.array(["/", "/collections/abonnement", "/products/kelder-huismelange", "/collections/single-origins"])
    mk = month_key(o.t.to_numpy())
    for i in np.flatnonzero(ch != ""):
        c = ch[i]
        page = pages[r.integers(0, len(pages))]
        if c == "paid_social":
            src = "facebook" if r.random() < 0.6 else "instagram"
            land[i] = f"{page}?utm_source={src}&utm_medium=paid_social&utm_campaign={meta[r.integers(0, 3)]}&fbclid=IwAR{r.integers(10**8, 10**9)}"
            refr[i] = "https://l.facebook.com/" if src == "facebook" else "https://l.instagram.com/"
        elif c == "paid_search":
            land[i] = f"{page}?utm_source=google&utm_medium=cpc&utm_campaign={goog[r.integers(0, 3)]}&gclid=Cj0KCQ{r.integers(10**8, 10**9)}"
            refr[i] = "https://www.google.com/"
        elif c == "email":
            land[i] = f"{page}?utm_source=klaviyo&utm_medium=email&utm_campaign=nieuwsbrief_{mk[i].replace('-', '_')}"
        elif c == "organic":
            land[i] = page
            refr[i] = ["https://www.google.com/", "https://www.bing.com/", "https://duckduckgo.com/"][int(r.choice(3, p=[0.85, 0.08, 0.07]))]
        elif c == "referral":
            land[i] = page
            refr[i] = ["https://www.koffiebloggers.nl/", "https://www.reddit.com/r/coffee/", "https://www.instagram.com/",
                       "https://www.linkedin.com/"][int(r.integers(0, 4))]
        else:
            land[i] = page
    return land, refr
