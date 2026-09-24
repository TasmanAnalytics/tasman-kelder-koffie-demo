"""A readable profile of the generated data, so a human can sniff-test it in ten minutes."""

from __future__ import annotations

from pathlib import Path

import pandas as pd


def _md(df: pd.DataFrame) -> str:
    cols = list(df.columns)
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    for _, r in df.iterrows():
        out.append("| " + " | ".join("" if pd.isna(v) else (f"{v:.4f}" if isinstance(v, float) and abs(v) < 1 else (f"{v:,.2f}" if isinstance(v, float) else str(v))) for v in r) + " |")
    return "\n".join(out)


def write(path: Path, cfg, truth_tables, shop, rc, kl, ad, manifest):
    m = truth_tables["metrics_monthly"].copy()
    m = m[m.month <= cfg["dates"]["window_end"][:7]]
    lines = ["# Kelder Coffee: profile of the generated data", "",
             f"Seed {cfg['seed']}. Window {cfg['dates']['window_start']} to {cfg['dates']['window_end']}. "
             "All figures below come from the world (the truth), not from the warehouse.", "",
             "## Targets", "", _md(truth_tables["targets"]), "",
             "## Monthly subscription metrics (truth, adjusted)", "",
             _md(m[["month", "base", "voluntary_cancellations", "first_failures", "unrecovered_failures_final", "unrecovered_failures_asof",
                    "churn_v1", "churn_v2_final", "churn_v2_asof", "paused_count", "pause_rate", "new_subscribers", "gift_subscriptions_sold"]]), "",
             "## Orders and email (truth)", "",
             _md(m[["month", "retail_orders", "email_attributed_revenue_world", "email_attributed_revenue_observed"]]), "",
             "## Raw table sizes", ""]
    sizes = []
    for system, tables in (("raw_shopify", shop), ("raw_recharge", rc), ("raw_klaviyo", kl), ("raw_ads", ad)):
        for name, df in sorted(tables.items()):
            sizes.append(dict(table=f"{system}.{name}", rows=len(df), columns=len(df.columns)))
    lines += [_md(pd.DataFrame(sizes)), ""]
    o = shop["orders"]
    lh = o[o.source_name == "web"].created_at.dt.tz_convert("Europe/Amsterdam").dt.hour.value_counts().sort_index()
    sh = o[o.source_name != "web"].created_at.dt.tz_convert("Europe/Amsterdam").dt.hour.value_counts().sort_index()
    lines += ["## Orders by local hour", "", _md(pd.DataFrame(dict(hour=range(24), web=[int(lh.get(h, 0)) for h in range(24)],
                                                                   subscription=[int(sh.get(h, 0)) for h in range(24)]))), ""]
    sub = rc["subscriptions"]
    c = sub[sub.cancelled_at.notna()]
    mar = c[(c.cancelled_at >= "2026-03-01") & (c.cancelled_at < "2026-04-01")]
    hh = mar.cancelled_at.dt.hour.value_counts().sort_index()
    lines += ["## Recharge cancellations stamped in March 2026, by UTC hour", "",
              _md(pd.DataFrame(dict(hour_utc=range(24), cancellations=[int(hh.get(h, 0)) for h in range(24)]))), ""]
    lines += ["## Incident manifest", "", _md(manifest.groupby(["incident", "table_name", "change_type"]).size().rename("rows").reset_index()), ""]
    path.write_text("\n".join(lines))
