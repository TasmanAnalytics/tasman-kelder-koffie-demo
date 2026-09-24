"""Products, variants, prices and VAT. Prices include VAT."""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
import yaml

FLAVOUR = Path(__file__).resolve().parent / "flavour"
GRINDS = ["whole_bean", "filter", "espresso", "french_press"]
GRIND_CODE = {"whole_bean": "WB", "filter": "FI", "espresso": "ES", "french_press": "FP"}
SIZES = [250, 1000]


def _slug(s: str, n: int = 3) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    words = [w for w in re.split(r"[^A-Za-z]+", s) if w]
    return "-".join(w[:4].upper() for w in words[:n])


@dataclass
class Catalogue:
    products: pd.DataFrame  # id, title, product_type, vat_rate, months (list or None)
    variants: pd.DataFrame  # id, product_id, sku, title, price, grams, taxable, kind, size_g, grind, vat_rate

    def coffee_variant(self, product_idx: np.ndarray, size_g: np.ndarray, grind_idx: np.ndarray) -> np.ndarray:
        """Variant ids for coffee product positions (index into coffee_products), size and grind."""
        key = product_idx * 8 + (size_g == 1000).astype(int) * 4 + grind_idx
        return self._coffee_variant_ids[key]

    def coffee_price(self, product_idx: np.ndarray, size_g: np.ndarray) -> np.ndarray:
        p250 = self._coffee_price_250[product_idx]
        return np.where(size_g == 1000, np.round(p250 * 3.4 * 2) / 2, p250)

    @property
    def coffee_products(self) -> pd.DataFrame:
        return self.products[self.products.product_type.isin(["single_origin", "blend", "decaf"])].reset_index(drop=True)

    def sku_variant(self, sku: str) -> pd.Series:
        return self.variants.set_index("sku").loc[sku]


def build_catalogue(cfg: dict) -> Catalogue:
    spec = yaml.safe_load(open(FLAVOUR / "products.yaml"))
    vat_coffee = cfg["catalogue"]["vat_coffee"]
    vat_eq = cfg["catalogue"]["vat_equipment"]
    prods, vars_ = [], []
    pid = 8_100_000_000
    vid = 44_000_000_000
    coffee_variant_ids, coffee_price_250 = [], []

    def add_product(title, ptype, vat, months=None):
        nonlocal pid
        pid += 7919
        prods.append(dict(id=pid, title=title, product_type=ptype, vat_rate=vat, months=months))
        return pid

    def add_variant(product_id, sku, title, price, grams, kind, size_g=None, grind=None, vat=vat_coffee):
        nonlocal vid
        vid += 104729
        vars_.append(dict(id=vid, product_id=product_id, sku=sku, title=title, price=round(float(price), 2),
                          grams=int(grams), taxable=True, kind=kind, size_g=size_g, grind=grind, vat_rate=vat))
        return vid

    coffee_items = (
        [(c, "single_origin", "SO") for c in spec["single_origins"]]
        + [(c, "blend", "BL") for c in spec["blends"]]
        + [(c, "decaf", "DC") for c in spec["decaf"]]
    )
    for item, ptype, prefix in coffee_items:
        p = add_product(item["name"], ptype, vat_coffee, item.get("months"))
        coffee_price_250.append(item["price_250"])
        for size in SIZES:
            price = item["price_250"] if size == 250 else round(item["price_250"] * 3.4 * 2) / 2
            for g in GRINDS:
                sku = f"{prefix}-{_slug(item['name'])}-{size}-{GRIND_CODE[g]}"
                label = f"{'250 g' if size == 250 else '1 kg'} / {g.replace('_', ' ')}"
                v = add_variant(p, sku, label, price, size + 20, "coffee", size, g)
                coffee_variant_ids.append(v)
    for item in spec["equipment"]:
        p = add_product(item["name"], "equipment", vat_eq)
        add_variant(p, item["sku"], "Default", item["price"], item["grams"], "equipment", vat=vat_eq)
    for item in spec["gifts"]:
        kind = {"GIFT-XMAS-BOX": "gift_box", "GIFT-SUB-3": "gift_subscription", "BUNDLE-VADERDAG-2026": "bundle"}[item["sku"]]
        vat = vat_coffee
        p = add_product(item["name"], kind, vat, item.get("months"))
        add_variant(p, item["sku"], "Default", item["price"], item["grams"], kind, vat=vat)

    cat = Catalogue(pd.DataFrame(prods), pd.DataFrame(vars_))
    cat._coffee_variant_ids = np.array(coffee_variant_ids, dtype=np.int64)
    cat._coffee_price_250 = np.array(coffee_price_250, dtype=float)
    return cat


def subscription_product_weights(cat: Catalogue) -> np.ndarray:
    """Relative popularity of coffee products for subscriptions (blends and all-year origins dominate)."""
    cp = cat.coffee_products
    w = np.where(cp.product_type == "blend", 6.0, np.where(cp.product_type == "decaf", 1.2, 0.0))
    all_year = cp.months.apply(lambda m: m is not None and len(m) == 12)
    w = np.where((cp.product_type == "single_origin") & all_year, 4.0, w)
    w = np.where((cp.product_type == "single_origin") & ~all_year, 0.9, w)
    return w / w.sum()


def vat_part(gross: np.ndarray, rate: np.ndarray) -> np.ndarray:
    gross = np.asarray(gross, dtype=float)
    return np.round(gross * rate / (1 + rate), 2)
