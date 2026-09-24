"""World simulation, part two: orders, fulfilment, refunds, email engagement and ad spend.

Subscription orders come from the charges in world.py. Retail orders, email engagement and
ads are simulated here. Everything stays in local wall seconds and world identifiers; the
source systems in systems/*.py assign their own ids and formats.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
import yaml

from .catalogue import FLAVOUR, Catalogue
from .common import (
    DAY,
    HOUR,
    NEVER,
    ProfileSampler,
    add_months,
    at_time_of_day,
    iso_dow,
    month_key,
    rng_for,
    ts,
)
from .world import CHANNELS, COUNTRIES, K_FIRST, K_GIFT, K_RECOVERY, K_RECURRING, WorldResult

O_SUB_FIRST, O_SUB_RECURRING, O_GIFT_PURCHASE, O_GIFT_SHIPMENT, O_RETAIL, O_BUNDLE, O_EMAIL = range(7)
ORDER_KINDS = ["sub_first", "sub_recurring", "gift_purchase", "gift_shipment", "retail", "bundle", "retail_email"]


@dataclass
class CommerceResult:
    customers: pd.DataFrame      # all customers (subscription and retail)
    orders: pd.DataFrame         # one row per order (local times, world ids)
    lines: pd.DataFrame          # order lines
    fulfillments: pd.DataFrame
    refunds: pd.DataFrame
    campaigns: pd.DataFrame
    email_events: pd.DataFrame   # world email engagement (before any outage)
    ads: pd.DataFrame            # daily spend per platform campaign
    channel_daily: pd.DataFrame


class Commerce:
    def __init__(self, cfg: dict, cat: Catalogue, world: WorldResult):
        self.cfg = cfg
        self.cat = cat
        self.world = world
        self.d = cfg["dates"]
        seed = cfg["seed"]
        self.r_ret = rng_for(seed, "commerce.retail")
        self.r_ful = rng_for(seed, "commerce.fulfilment")
        self.r_ref = rng_for(seed, "commerce.refunds")
        self.r_mail = rng_for(seed, "commerce.email")
        self.r_ads = rng_for(seed, "commerce.ads")
        self.r_ch = rng_for(seed, "commerce.channels")
        prof = cfg["profiles"]
        self.human = ProfileSampler(prof["human_hour"], prof["human_dow"])
        self.office = ProfileSampler([0] * 9 + [1] * 8 + [0] * 7, [1, 1, 1, 1, 1, 0, 0])
        self.w0 = ts(self.d["window_start"])
        self.cutoff = ts(self.d["cutoff_local"])
        self.v = cat.variants.set_index("sku")
        self.coffee_vids = cat._coffee_variant_ids

    # ------------------------------------------------------------------ ads and channels

    def ad_multiplier(self, days: np.ndarray) -> np.ndarray:
        m = self.cfg["ads"]["multipliers"]
        days = np.asarray(days, dtype=np.int64)
        mk = month_key(days)
        mult = np.ones(len(days))
        bf = ts(self.d["black_friday"])
        mult = np.where((days >= bf - 4 * DAY) & (days <= bf + 3 * DAY), m["black_friday_week"], mult)
        mult = np.where(np.char.endswith(mk.astype(str), "-01"), mult * m["january"], mult)
        bs, be = ts(self.d["bundle_start"]), ts(self.d["bundle_end"])
        mult = np.where((days >= bs) & (days <= be), mult * m["bundle_week"], mult)
        summer = np.char.endswith(mk.astype(str), "-07") | np.char.endswith(mk.astype(str), "-08")
        return np.where(summer, mult * m["summer"], mult)

    def simulate_ads(self) -> pd.DataFrame:
        a = self.cfg["ads"]
        days = np.arange(self.w0, self.cutoff, DAY)
        mult = self.ad_multiplier(days)
        dow = iso_dow(days)
        week = np.where(dow >= 5, 0.92, 1.03)
        rows = []
        specs = [
            ("meta", "act_1180442907", "23851120", "KEL | Prospecting | NL-BE", 0.55),
            ("meta", "act_1180442907", "23851121", "KEL | Retargeting | Site visitors", 0.25),
            ("meta", "act_1180442907", "23851122", "KEL | Abonnement promo", 0.20),
            ("google", "482-117-9031", "19002231", "KEL Brand", 0.25),
            ("google", "482-117-9031", "19002232", "KEL Generic koffieabonnement", 0.45),
            ("google", "482-117-9031", "19002233", "KEL Shopping", 0.30),
        ]
        for platform, acct, cid, name, share in specs:
            base = a["meta_daily_eur"] if platform == "meta" else a["google_daily_eur"]
            noise = np.exp(self.r_ads.normal(0, 0.08, len(days)))
            spend = np.round(base * share * mult * week * noise, 2)
            if platform == "meta":
                impr = np.round(spend / a["meta_cpm_eur"] * 1000 * np.exp(self.r_ads.normal(0, 0.05, len(days)))).astype(int)
                clicks = self.r_ads.binomial(impr, a["meta_ctr"])
            else:
                clicks = np.round(spend / a["google_cpc_eur"] * np.exp(self.r_ads.normal(0, 0.06, len(days)))).astype(int)
                impr = np.round(clicks / a["google_ctr"] * np.exp(self.r_ads.normal(0, 0.05, len(days)))).astype(int)
            rows.append(pd.DataFrame(dict(day=days, platform=platform, account_id=acct, campaign_id=cid,
                                          campaign_name=name, spend=spend, impressions=impr, clicks=clicks)))
        return pd.concat(rows, ignore_index=True)

    def channel_probs(self, t: np.ndarray) -> np.ndarray:
        """Row-wise first-order channel probabilities for timestamps t."""
        base = np.array([self.cfg["channels"]["base_share"][c] for c in CHANNELS])
        mult = self.ad_multiplier(at_time_of_day(t, 0))
        p = np.tile(base, (len(t), 1))
        p[:, 0] *= mult
        p[:, 1] *= mult
        return p / p.sum(axis=1, keepdims=True)

    def draw_channels(self, t: np.ndarray) -> np.ndarray:
        p = self.channel_probs(t)
        u = self.r_ch.random(len(t))[:, None]
        return (u > np.cumsum(p, axis=1)).sum(axis=1)

    # ------------------------------------------------------------------ orders

    def subscription_orders(self) -> tuple[pd.DataFrame, pd.DataFrame]:
        w = self.world
        ch = w.charges
        ch = ch[(ch.t >= self.w0) & (ch.t < self.cutoff)].reset_index(drop=True)
        subs = w.subs.set_index("sub_id")
        s = subs.loc[ch["sub"].to_numpy()]
        kind = np.where(ch.kind == K_FIRST, O_SUB_FIRST, O_SUB_RECURRING)
        first_gift = ch.kind.eq(K_GIFT) & (ch.t.to_numpy() == s.start.to_numpy())
        kind = np.where(ch.kind == K_GIFT, np.where(first_gift, O_GIFT_PURCHASE, O_GIFT_SHIPMENT), kind)
        orders = pd.DataFrame(dict(t=ch.t.to_numpy(), customer_id=s.customer_id.to_numpy(), sub_id=ch["sub"].to_numpy(),
                                   kind=kind, charge_kind=ch.kind.to_numpy()))
        unit = self.cat.coffee_price(s.product_idx.to_numpy().astype(int), s.size_g.to_numpy())
        vid = self.cat.coffee_variant(s.product_idx.to_numpy().astype(int), s.size_g.to_numpy(), s.grind.to_numpy().astype(int))
        qty = s.bags.to_numpy().astype(int)
        gross = unit * qty
        disc = np.round(gross * self.cfg["catalogue"]["subscriber_discount"], 2)
        ship = np.where((qty == 1) & (s.size_g.to_numpy() == 250), self.cfg["catalogue"]["shipping_fee_single_bag"], 0.0)
        # first-box promo codes for promo cohorts
        promo_code = np.full(len(orders), "", dtype=object)
        mk = month_key(orders.t.to_numpy())
        is_first = kind == O_SUB_FIRST
        promo_first = is_first & s.promo.to_numpy()
        rate = np.where(np.isin(mk, ["2024-11", "2025-11"]), 0.40, np.where(np.isin(mk, ["2026-01", "2025-01"]), 0.25, 0.20))
        extra = np.where(promo_first, np.round((gross - disc) * rate, 2), 0.0)
        promo_code[promo_first & np.isin(mk, ["2024-11", "2025-11"])] = "BLACKFRIDAY40"
        promo_code[promo_first & np.isin(mk, ["2026-01", "2025-01"])] = "NIEUWJAAR25"
        promo_code[promo_first & ~np.isin(mk, ["2024-11", "2025-11", "2026-01", "2025-01"])] = "EERSTEBOX20"
        # gift purchase and shipments
        gp = kind == O_GIFT_PURCHASE
        gs = kind == O_GIFT_SHIPMENT
        gift_sku = self.v.loc["GIFT-SUB-3"]
        house = self.v.loc[[k for k in self.v.index if k.startswith("BL-KELD-HUIS-250-WB")][0]]
        vid = np.where(gp, gift_sku.id, np.where(gs, house.id, vid))
        unit = np.where(gp, gift_sku.price, np.where(gs, house.price, unit))
        qty = np.where(gp | gs, 1, qty)
        gross = unit * qty
        disc = np.where(gp, 0.0, np.where(gs, gross, disc + extra))
        ship = np.where(gp | gs, 0.0, ship)
        orders["subtotal"] = np.round(gross - disc, 2)
        orders["discount"] = np.round(disc, 2)
        orders["shipping"] = ship
        orders["total"] = np.round(gross - disc + ship, 2)
        orders["tax"] = np.round((gross - disc) * 0.09 / 1.09, 2)
        orders["discount_code"] = np.where(gs, "", promo_code)
        lines = pd.DataFrame(dict(okey=np.arange(len(orders)), variant_id=vid, quantity=qty, price=unit, discount=np.round(disc, 2)))
        return orders, lines

    def _pick_items(self, n: int, month: np.ndarray, bundle: np.ndarray):
        """Retail baskets: list of (variant_id, qty, price) per order, returned as flat arrays + order index."""
        r = self.r_ret
        cat = self.cat
        v = cat.variants
        coffee = v[v.kind == "coffee"]
        eq = v[v.kind == "equipment"]
        box = v[v.sku == "GIFT-XMAS-BOX"].iloc[0]
        bnd = v[v.sku == "BUNDLE-VADERDAG-2026"].iloc[0]
        # coffee availability by month
        prod_months = cat.products.set_index("id").months
        c_months = coffee.product_id.map(prod_months)
        oi, vids, qtys, prices = [], [], [], []
        mm = np.array([int(m[5:7]) for m in month])
        coffee_ids = coffee.id.to_numpy()
        coffee_price = coffee.price.to_numpy()
        coffee_is_1kg = (coffee.size_g == 1000).to_numpy()
        avail = np.array([[m is None or (mo in m) for m in c_months] for mo in range(1, 13)])  # 12 x n_coffee
        w_coffee = np.where(coffee_is_1kg, 0.08, 1.0)
        eq_w = eq.sku.map({"EQ-FILTERS-100": 0.35, "EQ-MUG": 0.25, "EQ-DRIPPER-V60": 0.20, "EQ-SCALE": 0.10,
                           "EQ-GRINDER-HAND": 0.07, "EQ-GRINDER-ELEC": 0.03}).to_numpy()
        eq_w = eq_w / eq_w.sum()
        for i in range(n):
            if bundle[i]:
                oi.append(i); vids.append(bnd.id); qtys.append(1); prices.append(bnd.price)
                if r.random() < 0.25:
                    k = r.integers(0, len(coffee_ids))
                    oi.append(i); vids.append(coffee_ids[k]); qtys.append(1); prices.append(coffee_price[k])
                continue
            u = r.random()
            if mm[i] in (11, 12) and u < 0.22:
                oi.append(i); vids.append(box.id); qtys.append(1); prices.append(box.price)
                continue
            n_items = 1 + (r.random() < 0.22) + (r.random() < 0.04)
            for _ in range(n_items):
                if r.random() < 0.12:
                    k = r.choice(len(eq), p=eq_w)
                    e = eq.iloc[k]
                    oi.append(i); vids.append(e.id); qtys.append(1); prices.append(e.price)
                else:
                    ww = w_coffee * avail[mm[i] - 1]
                    k = r.choice(len(coffee_ids), p=ww / ww.sum())
                    q = 1 + (r.random() < 0.26)
                    oi.append(i); vids.append(coffee_ids[k]); qtys.append(q); prices.append(coffee_price[k])
        return np.array(oi), np.array(vids), np.array(qtys), np.array(prices, dtype=float)

    def _month_bounds(self):
        m = self.w0
        while m < self.cutoff:
            m1 = int(add_months(np.array([m]), 1)[0])
            yield m, m1, str(month_key([m])[0])
            m = m1

    def _retail_boost(self, m, key):
        rc = self.cfg["retail"]
        bf = ts(self.d["black_friday"])
        bfw = (bf - 4 * DAY, bf + 3 * DAY)

        def boost(day, _):
            b = np.where((day >= bfw[0]) & (day <= bfw[1]), rc["black_friday_week_multiplier"], 1.0)
            if key[5:] == "12":
                dom = (day - m) // DAY + 1
                b = b * np.where(dom <= 20, 1.25, np.where(dom <= 23, 0.9, 0.35))
            return b / 2.0

        return boost

    def _month_total(self, m, m1, key, noise):
        rc = self.cfg["retail"]
        mult = rc["december_multiplier"] if key[5:] == "12" else 1.0
        n = rc["orders_per_month"] * mult * noise
        bf = ts(self.d["black_friday"])
        if m <= bf - 4 * DAY < m1:
            n = n * (1 + (rc["black_friday_week_multiplier"] - 1) * 7 / 30)
        return int(round(n))

    def _bundle_times(self, n):
        bs, be = ts(self.d["bundle_start"]), ts(self.d["bundle_end"]) + DAY

        def bboost(day, _):
            # demand builds towards Father's Day (Sunday 21 June)
            return np.clip(0.35 + 0.65 * (day - bs) / (be - bs), 0.3, 1.0)

        return np.sort(self.human.sample(self.r_ret, np.full(n, bs), np.full(n, be), day_boost=bboost))

    def retail_customers(self, next_cid: int) -> pd.DataFrame:
        """Retail-only customers: a warm-up pool before the window, then arrivals whose first order creates them."""
        rc = self.cfg["retail"]
        r = self.r_ret
        n_w = rc["warmup_retail_customers"]
        wu = np.sort(self.human.sample(r, np.full(n_w, ts(self.d["launch"])), np.full(n_w, self.w0)))
        parts = [pd.DataFrame(dict(created=wu, first_kind=-1))]
        self.month_noise = {}
        for m, m1, key in self._month_bounds():
            noise = float(np.exp(r.normal(0, 0.03)))
            self.month_noise[key] = noise
            n_new = int(round(self._month_total(m, m1, key, noise) * rc["share_new_customer"]))
            t = np.sort(self.human.sample(r, np.full(n_new, m), np.full(n_new, m1), day_boost=self._retail_boost(m, key)))
            parts.append(pd.DataFrame(dict(created=t, first_kind=O_RETAIL)))
            if key == "2026-06":
                nb = int(round(rc["bundle_orders"] * 0.6))
                parts.append(pd.DataFrame(dict(created=self._bundle_times(nb), first_kind=O_BUNDLE)))
        c = pd.concat(parts, ignore_index=True).sort_values("created", kind="stable").reset_index(drop=True)
        c["customer_id"] = np.arange(next_cid, next_cid + len(c))
        c["country"] = np.array(COUNTRIES)[r.choice(len(COUNTRIES), len(c), p=[self.cfg["world"]["country_mix"][x] for x in COUNTRIES])]
        c["consent"] = r.random(len(c)) < self.cfg["world"]["consent_share"]
        c["kind"] = "retail"
        return c

    def retail_orders(self, retail_c: pd.DataFrame, email_orders: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
        rc = self.cfg["retail"]
        r = self.r_ret
        subs = self.world.subs
        rows = []
        pool_ids = retail_c.customer_id.to_numpy()
        pool_created = retail_c.created.to_numpy()
        firsts = retail_c[retail_c.first_kind >= 0]
        rows.append(pd.DataFrame(dict(t=firsts.created.to_numpy(), customer_id=firsts.customer_id.to_numpy(), sub_id=-1,
                                      kind=firsts.first_kind.to_numpy(), charge_kind=-1)))
        email_mk = month_key(email_orders.t.to_numpy()) if len(email_orders) else np.array([])
        first_mk = month_key(firsts.created.to_numpy())
        share_sub = rc["share_subscriber"] / (rc["share_subscriber"] + rc["share_existing_retail"])
        for m, m1, key in self._month_bounds():
            n_total = self._month_total(m, m1, key, self.month_noise[key])
            n_first = int((first_mk == key).sum())
            n_email = int((email_mk == key).sum())
            n = max(0, n_total - n_first - n_email + (int(round(rc["bundle_orders"] * 0.6)) if key == "2026-06" else 0))
            t = self.human.sample(r, np.full(n, m), np.full(n, m1), day_boost=self._retail_boost(m, key))
            kind = np.full(n, O_RETAIL)
            if key == "2026-06":
                nb = rc["bundle_orders"] - int(round(rc["bundle_orders"] * 0.6))
                t = np.concatenate([t, self._bundle_times(nb)])
                kind = np.concatenate([kind, np.full(nb, O_BUNDLE)])
            o = np.argsort(t, kind="stable")
            t, kind = t[o], kind[o]
            n = len(t)
            is_sub = r.random(n) < share_sub
            cust = np.full(n, -1, dtype=np.int64)
            act = subs[(subs.start < m) & (subs.term > m1) & ~subs.is_gift]
            cust[is_sub] = act.customer_id.to_numpy()[r.integers(0, len(act), int(is_sub.sum()))]
            rep = np.flatnonzero(~is_sub)
            upto = np.searchsorted(pool_created, t[rep])
            cust[rep] = pool_ids[np.floor(r.random(len(rep)) * np.maximum(upto, 1)).astype(np.int64)]
            rows.append(pd.DataFrame(dict(t=t, customer_id=cust, sub_id=-1, kind=kind, charge_kind=-1)))
        if len(email_orders):
            rows.append(pd.DataFrame(dict(t=email_orders.t.to_numpy(), customer_id=email_orders.customer_id.to_numpy(),
                                          sub_id=-1, kind=O_EMAIL, charge_kind=-1)))
        orders = pd.concat(rows, ignore_index=True)
        orders = orders.sort_values(["t", "customer_id"], kind="stable").reset_index(drop=True)
        mk = month_key(orders.t.to_numpy())
        oi, vids, qtys, prices = self._pick_items(len(orders), mk, (orders.kind == O_BUNDLE).to_numpy())
        lines = pd.DataFrame(dict(okey=oi, variant_id=vids, quantity=qtys, price=prices, discount=0.0))
        g = lines.assign(gross=lines.price * lines.quantity).groupby("okey").gross.sum()
        vat = self.cat.variants.set_index("id").vat_rate
        rate = lines.variant_id.map(vat)
        lines_tax = (lines.price * lines.quantity * rate / (1 + rate)).groupby(lines.okey).sum()
        orders["subtotal"] = g.reindex(orders.index).to_numpy().round(2)
        orders["discount"] = 0.0
        orders["shipping"] = np.where(orders.subtotal < 40, 4.95, 0.0)
        orders["total"] = (orders.subtotal + orders.shipping).round(2)
        orders["tax"] = lines_tax.reindex(orders.index).to_numpy().round(2)
        orders["discount_code"] = ""
        return orders, lines

    # ------------------------------------------------------------------ email

    def email(self, customers: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """Campaigns and flows. Returns campaigns, engagement events, email-driven orders."""
        k = self.cfg["klaviyo"]
        r = self.r_mail
        spec = yaml.safe_load(open(FLAVOUR / "campaigns.yaml"))
        prof = customers[customers.consent].sort_values(["created", "customer_id"], kind="stable").reset_index(drop=True)
        pid = prof.customer_id.to_numpy()
        pcreated = prof.created.to_numpy()
        propensity = r.gamma(3.0, 1 / 3.0, len(prof))
        unsub_at = np.full(len(prof), NEVER, dtype=np.int64)
        # Thursdays 10:00 local
        first_thu = self.w0 + ((3 - iso_dow([self.w0])[0]) % 7) * DAY
        sends = np.arange(first_thu, self.cutoff, 7 * DAY) + k["campaign_hour_local"] * HOUR
        camps, ev = [], []
        rot = spec["rotation"]
        ri = 0
        for ci, send in enumerate(sends):
            day = str(np.datetime64(int(send // DAY), "D"))
            if day in spec["fixed"]:
                name, subj = spec["fixed"][day]["name"], spec["fixed"][day]["subject"]
            else:
                name, subj = rot[ri % len(rot)]["name"], rot[ri % len(rot)]["subject"]
                ri += 1
            aud = np.flatnonzero((pcreated < send) & (unsub_at > send))
            camps.append(dict(campaign_idx=ci, name=f"{day} {name}", subject=subj, send=send, audience=len(aud)))
            n = len(aud)
            recv = send + r.integers(0, 15 * 60, n)
            p_open = np.minimum(0.95, k["open_rate"] * propensity[aud])
            opened = r.random(n) < p_open
            o_t = recv + np.minimum(7 * DAY, np.round(np.exp(r.normal(np.log(2 * HOUR), 1.4, n)))).astype(np.int64)
            clicked = opened & (r.random(n) < k["click_rate"] / k["open_rate"])
            c_t = o_t + np.round(r.exponential(8 * 60, n)).astype(np.int64)
            ordered = clicked & (r.random(n) < k["order_rate"] / k["click_rate"])
            ord_t = c_t + np.minimum(k["attribution_days"] * DAY - 60, np.round(np.exp(r.normal(np.log(1.5 * HOUR), 1.5, n)))).astype(np.int64)
            uns = opened & (r.random(n) < k["unsubscribe_rate_per_campaign"] / k["open_rate"])
            unsub_at[aud[uns]] = o_t[uns] + 30
            src = dict(campaign_idx=ci, flow="")
            ev.append(pd.DataFrame(dict(metric="Received Email", customer_id=pid[aud], t=recv, **src)))
            ev.append(pd.DataFrame(dict(metric="Opened Email", customer_id=pid[aud[opened]], t=o_t[opened], **src)))
            ev.append(pd.DataFrame(dict(metric="Clicked Email", customer_id=pid[aud[clicked]], t=c_t[clicked], **src)))
            ev.append(pd.DataFrame(dict(metric="Unsubscribed", customer_id=pid[aud[uns]], t=o_t[uns] + 30, **src)))
            ev.append(pd.DataFrame(dict(metric="_order", customer_id=pid[aud[ordered]], t=ord_t[ordered], **src)))
        campaigns = pd.DataFrame(camps)
        # flows
        fr = k["flow_rates"]
        in_win = (pcreated >= self.w0) & (pcreated < self.cutoff)
        flows = []
        flows.append(("welcome", pid[in_win], pcreated[in_win] + 5 * 60))
        subs = self.world.subs
        first = subs[(subs.start >= self.w0) & (subs.start < self.cutoff) & ~subs.is_gift]
        consent = set(pid.tolist())
        fm = first.customer_id.isin(consent).to_numpy()
        flows.append(("post_purchase", first.customer_id.to_numpy()[fm], at_time_of_day(first.start.to_numpy()[fm] + 3 * DAY, 10)))
        c = self.world.cancels
        vc = c[(c.reason == 1) & (c.t >= self.w0 - 21 * DAY)]
        vcust = subs.set_index("sub_id").loc[vc["sub"].to_numpy(), "customer_id"].to_numpy()
        vm = np.isin(vcust, pid)
        flows.append(("win_back", vcust[vm], at_time_of_day(vc.t.to_numpy()[vm] + 21 * DAY, 10)))
        n_ab = int(k["abandoned_checkouts_per_month"] * ((self.cutoff - self.w0) / (30.44 * DAY)))
        ab_t = np.sort(self.human.sample(r, np.full(n_ab, self.w0), np.full(n_ab, self.cutoff)))
        upto = np.searchsorted(pcreated, ab_t)
        ab_c = pid[np.floor(r.random(n_ab) * np.maximum(upto, 1)).astype(np.int64)]
        flows.append(("abandoned_checkout", ab_c, ab_t + HOUR))
        for fname, cust, t in flows:
            keep = (t >= self.w0) & (t < self.cutoff + 30 * DAY)
            cust, t = cust[keep], t[keep]
            n = len(t)
            rates = fr[fname]
            opened = r.random(n) < rates["open"]
            o_t = t + np.round(np.exp(r.normal(np.log(1.5 * HOUR), 1.3, n))).astype(np.int64)
            clicked = opened & (r.random(n) < rates["click"] / rates["open"])
            c_t = o_t + np.round(r.exponential(6 * 60, n)).astype(np.int64)
            ordered = clicked & (r.random(n) < k["flow_order_rate_given_click"])
            ord_t = c_t + np.minimum(k["attribution_days"] * DAY - 60, np.round(np.exp(r.normal(np.log(HOUR), 1.4, n)))).astype(np.int64)
            src = dict(campaign_idx=-1, flow=fname)
            ev.append(pd.DataFrame(dict(metric="Received Email", customer_id=cust, t=t, **src)))
            ev.append(pd.DataFrame(dict(metric="Opened Email", customer_id=cust[opened], t=o_t[opened], **src)))
            ev.append(pd.DataFrame(dict(metric="Clicked Email", customer_id=cust[clicked], t=c_t[clicked], **src)))
            ev.append(pd.DataFrame(dict(metric="_order", customer_id=cust[ordered], t=ord_t[ordered], **src)))
        events = pd.concat(ev, ignore_index=True)
        events = events[(events.t >= self.w0) & (events.t < self.cutoff)]
        orders = events[events.metric == "_order"][["customer_id", "t", "campaign_idx", "flow"]].reset_index(drop=True)
        events = events[events.metric != "_order"].sort_values(["t", "customer_id", "metric"], kind="stable").reset_index(drop=True)
        return campaigns, events, orders

    # ------------------------------------------------------------------ fulfilment and refunds

    def fulfil(self, orders: pd.DataFrame, customers: pd.DataFrame) -> pd.DataFrame:
        r = self.r_ful
        dl = self.cfg["delivery"]
        n = len(orders)
        t = orders.t.to_numpy()
        country = orders.customer_id.map(customers.set_index("customer_id").country).to_numpy()
        is_sub_run = orders.kind.isin([O_SUB_RECURRING, O_GIFT_SHIPMENT]).to_numpy()
        day = at_time_of_day(t, 0)
        dow = iso_dow(day)
        # recurring subscription orders ship the same working day; web orders before noon ship same day, else next working day
        same_day = is_sub_run | (t - day < 12 * HOUR)
        ship_day = np.where(same_day, day, day + DAY)
        d2 = iso_dow(ship_day)
        ship_day = ship_day + np.where(d2 == 5, 2 * DAY, np.where(d2 == 6, DAY, 0))
        ship_t = ship_day + np.where(is_sub_run, 11 * HOUR, 14 * HOUR) + r.integers(0, 4 * HOUR, n)
        ship_t = np.maximum(ship_t, t + HOUR)
        postnl = country == "NL"
        pk = np.array(list(dl["postnl_days"].keys()))
        dk = np.array(list(dl["dhl_days"].keys()))
        days = np.where(postnl, pk[r.choice(len(pk), n, p=list(dl["postnl_days"].values()))],
                        dk[r.choice(len(dk), n, p=list(dl["dhl_days"].values()))])
        ss, se = ts(self.d["strike_ship_start"]), ts(self.d["strike_ship_end"])
        strike = postnl & (at_time_of_day(ship_t, 0) >= ss) & (at_time_of_day(ship_t, 0) <= se)
        lo, hi = dl["strike_delay_days"]
        nominal_day = at_time_of_day(ship_t, 0) + days * DAY
        nominal_day = nominal_day + np.where(iso_dow(nominal_day) == 6, DAY, 0)
        days = np.where(strike, r.integers(lo, hi + 1, n), days)
        deliv_day = at_time_of_day(ship_t, 0) + days * DAY
        deliv_day = deliv_day + np.where(iso_dow(deliv_day) == 6, DAY, 0)  # no Sunday delivery
        tod = 10 * HOUR + r.integers(0, 10 * HOUR, n)
        deliv_t = deliv_day + tod
        nominal_t = nominal_day + tod
        never = strike & (r.random(n) < dl["strike_never_delivered"])
        deliv_t = np.where(never, NEVER, deliv_t)
        return pd.DataFrame(dict(okey=np.arange(n), ship_t=ship_t, carrier=np.where(postnl, "PostNL", "DHL"),
                                 deliv_t=deliv_t, nominal_t=nominal_t, never=never, strike=strike))

    def refunds(self, orders: pd.DataFrame, ful: pd.DataFrame) -> pd.DataFrame:
        r = self.r_ref
        rc = self.cfg["retail"]
        n = len(orders)
        notes = yaml.safe_load(open(FLAVOUR / "refund_notes.yaml"))["notes"]
        paid = orders.total.to_numpy() > 0
        base = paid & ~ful.strike.to_numpy() & (r.random(n) < rc["refund_rate"])
        strike = paid & ful.strike.to_numpy() & (r.random(n) < rc["strike_refund_rate"])
        strike |= paid & ful.never.to_numpy()
        note_i = r.choice(len(notes), n, p=[x["share"] for x in notes])
        note = np.array([x["note"] for x in notes])[note_i]
        note = np.where(strike, "late_delivery", note)
        deliv = ful.deliv_t.to_numpy()
        ref_t = np.where(deliv < NEVER, deliv, ful.ship_t.to_numpy() + 8 * DAY) + r.integers(2 * HOUR, 3 * DAY, n)
        ref_t = self.office.sample(r, ref_t, ref_t + 3 * DAY)
        full = strike | (r.random(n) < 0.6)
        amount = np.where(full, orders.total.to_numpy(), np.round(orders.total.to_numpy() * r.uniform(0.3, 0.7, n), 2))
        m = (base | strike) & (ref_t < self.cutoff)
        return pd.DataFrame(dict(okey=np.flatnonzero(m), t=ref_t[m], amount=amount[m], note=note[m], strike=strike[m]))

    # ------------------------------------------------------------------ run

    def run(self) -> CommerceResult:
        w = self.world
        cust = w.customers[["customer_id", "created", "country", "consent"]].copy()
        cust["kind"] = "subscriber"
        cust["first_kind"] = -1
        retail_c = self.retail_customers(int(cust.customer_id.max()) + 1)
        customers = pd.concat([cust, retail_c], ignore_index=True)
        ads = self.simulate_ads()
        sub_orders, sub_lines = self.subscription_orders()
        campaigns, events, email_orders = self.email(customers)
        ret_orders, ret_lines = self.retail_orders(retail_c, email_orders)
        orders = pd.concat([sub_orders, ret_orders], ignore_index=True)
        lines = pd.concat([sub_lines, ret_lines.assign(okey=ret_lines.okey + len(sub_orders))], ignore_index=True)
        order = np.lexsort((orders.customer_id.to_numpy(), orders.t.to_numpy()))
        remap = np.empty(len(orders), dtype=np.int64)
        remap[order] = np.arange(len(orders))
        orders = orders.iloc[order].reset_index(drop=True)
        orders["okey"] = np.arange(len(orders))
        lines["okey"] = remap[lines.okey.to_numpy()]
        lines = lines.sort_values(["okey"], kind="stable").reset_index(drop=True)
        # first-order channel for a customer's first web order; repeat web orders get a repeat channel
        web = orders.kind.isin([O_SUB_FIRST, O_GIFT_PURCHASE, O_RETAIL, O_BUNDLE, O_EMAIL]).to_numpy()
        ch = self.draw_channels(orders.t.to_numpy())
        created = orders.customer_id.map(customers.set_index("customer_id").created).to_numpy()
        first_web = web & (np.abs(orders.t.to_numpy() - created) < 60)
        repeat_ch = np.array(["direct", "email", "organic"])[self.r_ch.choice(3, len(orders), p=[0.5, 0.2, 0.3])]
        channel = np.where(first_web, np.array(CHANNELS)[ch], np.where(web, repeat_ch, ""))
        channel = np.where(orders.kind.to_numpy() == O_EMAIL, "email", channel)
        orders["channel"] = channel
        ful = self.fulfil(orders, customers)
        ref = self.refunds(orders, ful)
        return CommerceResult(customers=customers, orders=orders, lines=lines, fulfillments=ful, refunds=ref,
                              campaigns=campaigns, email_events=events, ads=ads, channel_daily=pd.DataFrame())
