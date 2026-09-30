"""ERD of Kelder's marts as built at the with-context state (crow's foot).

    uv run python charts/marts_erd.py

Writes charts/out/marts_erd.svg. Column types come from the with-context warehouse; columns that carry a
caveat in models/marts/_marts__models.yml are marked. Only the key columns of each table are drawn.
"""

from __future__ import annotations

import sys
from pathlib import Path

import duckdb
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
import domain_model as dm  # noqa: E402
from domain_model import (BAKSTEEN, CREMA, ESPRESSO, GRACHT, HEAD, HONING, MONO, MUTED, OUT, PAPER, ROOT, ROW,  # noqa: E402
                          bar_one, foot_many, t, table)

DB = ROOT / "data" / "warehouse" / "kelder_with_context.duckdb"
YML = ROOT / "build" / "with_context" / "kelder-dbt" / "models" / "marts" / "_marts__models.yml"

SHOW = {
    "dim_customers": [("PK", "customer_id"), ("", "email"), ("", "country_code"), ("", "created_at"),
                      ("", "first_order_channel"), ("", "is_active_subscriber")],
    "fct_subscriptions": [("PK", "subscription_key"), ("FK", "customer_id"), ("", "origin_system"), ("", "started_at"),
                          ("", "churned_at"), ("", "status"), ("", "is_gift"), ("", "mrr_eur"),
                          ("", "is_migration_artifact"), ("", "is_legacy_pause_restore"), ("FK", "continues_subscription_key")],
    "fct_subscription_events": [("PK", "subscription_event_id"), ("FK", "subscription_key"), ("", "event_type"),
                                ("", "occurred_at"), ("", "cancellation_reason"), ("", "is_voluntary_cancellation"),
                                ("", "is_recovered_within_30_days"), ("", "is_migration_artifact")],
    "fct_orders": [("PK", "order_id"), ("FK", "customer_id"), ("", "created_at"), ("", "channel"),
                   ("", "is_subscription_order"), ("", "total_price_eur"), ("", "carrier"), ("", "delivery_days")],
}
SHORT = {"TIMESTAMP WITH TIME ZONE": "timestamptz", "VARCHAR": "varchar", "BIGINT": "bigint", "BOOLEAN": "boolean",
         "DOUBLE": "double", "DATE": "date", "HUGEINT": "hugeint", "INTEGER": "int"}


def schema() -> tuple[dict, set]:
    con = duckdb.connect(str(DB), read_only=True)
    types = {}
    for tname in SHOW:
        types[tname] = {c: SHORT.get(ty, ty.lower()) for c, ty, *_ in con.execute(f"describe main.{tname}").fetchall()}
    con.close()
    caveats = set()
    for m in yaml.safe_load(YML.read_text())["models"]:
        for col in m.get("columns", []):
            if (col.get("meta") or {}).get("caveat"):
                caveats.add((m["name"], col["name"]))
    return types, caveats


def cols(name, types, caveats):
    out = [(k, c, types[name][c], (name, c) in caveats) for k, c in SHOW[name]]
    more = len(types[name]) - len(out)
    return out, more


def draw(x, y, w, name, types, caveats, color):
    cs, more = cols(name, types, caveats)
    s, h = table(x, y, w, name, cs, color)
    if more:
        s += t(x + w - 14, y + h + 18, f"+ {more} more columns", 11.5, MONO, MUTED, 400, "end")
    return s, h


def row_y(top, i):
    return top + HEAD + 22 + i * ROW - 5


def build() -> str:
    types, caveats = schema()
    b = ""
    cu, cuh = draw(60, 150, 340, "dim_customers", types, caveats, ESPRESSO)
    su, suh = draw(480, 150, 400, "fct_subscriptions", types, caveats, GRACHT)
    ev, evh = draw(960, 150, 400, "fct_subscription_events", types, caveats, BAKSTEEN)
    orr, orh = draw(60, 470, 340, "fct_orders", types, caveats, ESPRESSO)
    b += cu + su + ev + orr

    # dim_customers 1 -- 0..* fct_subscriptions
    y = row_y(150, 1)
    b += f'<line x1="400" y1="{y}" x2="480" y2="{y}" stroke="{ESPRESSO}" stroke-width="2.2"/>'
    b += bar_one(400, y, ("x", -1)) + foot_many(480, y, ("x", 1))
    # fct_subscriptions 1 -- 0..* fct_subscription_events
    y = row_y(150, 1)
    b += f'<line x1="880" y1="{y}" x2="960" y2="{y}" stroke="{ESPRESSO}" stroke-width="2.2"/>'
    b += bar_one(880, y, ("x", -1)) + foot_many(960, y, ("x", 1))
    # dim_customers 1 -- 0..* fct_orders
    b += f'<line x1="230" y1="{150 + cuh}" x2="230" y2="470" stroke="{ESPRESSO}" stroke-width="2.2"/>'
    b += bar_one(230, 150 + cuh, ("y", -1)) + foot_many(230, 470, ("y", 1))

    # context tables
    b += t(1392, 168, "CONTEXT SCHEMA", 12, MONO, MUTED, 600, spacing=1)
    for i, (n, l1, l2) in enumerate([("business_events", "what moved a", "number, and when"), ("metric_changelog", "each definition", "and its start date")]):
        yy = 182 + i * 90
        b += f'<rect x="1392" y="{yy}" width="168" height="76" rx="10" fill="{CREMA}" stroke="{HONING}" stroke-width="2"/>'
        b += t(1406, yy + 26, n, 13, MONO, ESPRESSO, 600) + t(1406, yy + 48, l1, 11.5, MONO, MUTED) + t(1406, yy + 64, l2, 11.5, MONO, MUTED)

    # metrics
    b += t(480, 640, "METRIC MODELS, THE NUMBERS PEOPLE REPORT", 12, MONO, MUTED, 600, spacing=1)
    metrics = [("subscriber_churn_monthly", "both event streams"), ("new_subscribers_monthly", "fct_subscriptions"),
               ("pause_rate_monthly", "adjusted events"), ("cac_monthly", "subscriptions, ad spend"),
               ("email_attribution_daily", "Klaviyo events")]
    for i, (n, src) in enumerate(metrics):
        x = 480 + i * 216
        b += f'<rect x="{x}" y="654" width="200" height="66" rx="10" fill="{PAPER}" stroke="{ESPRESSO}" stroke-width="2"/>'
        b += t(x + 12, 676, "metrics_", 11, MONO, MUTED) + t(x + 12, 696, n, 12.5, MONO, ESPRESSO, 600)
        b += t(x + 12, 712, "from " + src, 10.5, MONO, MUTED)

    # legend
    ly = 826
    b += t(60, ly, "PK", 12, MONO, HONING, 700) + t(86, ly, "primary key", 12.5, MONO, MUTED)
    b += t(210, ly, "FK", 12, MONO, GRACHT, 700) + t(236, ly, "foreign key", 12.5, MONO, MUTED)
    b += t(360, ly, "red column", 12.5, MONO, BAKSTEEN, 600) + t(460, ly, "= has a caveat in _marts__models.yml", 12.5, MONO, MUTED)
    return dm.frame(b, "Kelder marts, ERD", "AS BUILT BY DBT · CROW'S FOOT NOTATION · KEY COLUMNS ONLY",
                    "continues_subscription_key points to the subscription a legacy pause restore continues (decision 0008).",
                    badge="KELDER KOFFIE · MARTS")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "marts_erd.svg").write_text(build())
    print("wrote charts/out/marts_erd.svg")


if __name__ == "__main__":
    main()
