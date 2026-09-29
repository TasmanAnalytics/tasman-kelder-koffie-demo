"""Brand-styled charts for the slides. Reads only warehouse state files, never the truth database,
so every chart is evidence about the warehouse.

    uv run python charts/render.py

Writes charts/out/<stem>.svg, <stem>.png (2400x1350) and <stem>.json (the plotted values).
"""

from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

import duckdb
import matplotlib

matplotlib.use("Agg")
import matplotlib.dates as mdates  # noqa: E402
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib import font_manager  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "charts" / "out"
FONTS = ROOT / "charts" / "fonts"
WAREHOUSE = ROOT / "data" / "warehouse"

# Kelder Koffie brand: Crema, Espresso, Gracht, Baksteen. The names below are roles, not colours.
CREAM, SLATE, SAGE, BRICK = "#F4EADB", "#2A1C15", "#2F5B55", "#A9462B"
SLATE_LIGHT = "#CDBFA9"
W_IN, H_IN, DPI = 12, 6.75, 200  # 2400 x 1350 px


def setup_fonts() -> dict:
    found = {}
    for f in sorted(FONTS.glob("*.ttf")):
        font_manager.fontManager.addfont(str(f))
        name = font_manager.FontProperties(fname=str(f)).get_name()
        found[name] = f.name
    display = "EB Garamond" if "EB Garamond" in found else "Georgia"
    mono = "Roboto Mono" if "Roboto Mono" in found else "Menlo"
    body = "Helvetica Neue"
    if display != "EB Garamond" or mono != "Roboto Mono":
        print("WARNING: EB Garamond or Roboto Mono not found in charts/fonts; using fallback fonts", file=sys.stderr)
    plt.rcParams.update({
        "font.family": body, "font.size": 19, "text.color": SLATE, "axes.labelcolor": SLATE,
        "axes.edgecolor": SLATE, "xtick.color": SLATE, "ytick.color": SLATE, "axes.facecolor": CREAM,
        "figure.facecolor": CREAM, "savefig.facecolor": CREAM, "axes.spines.top": False,
        "axes.spines.right": False, "axes.linewidth": 1.0, "svg.fonttype": "none",
    })
    return {"display": display, "mono": mono, "body": body}


F = {}


def mono(size=12, **kw):
    return dict(fontfamily=F["mono"], fontsize=round(size * 1.4, 1), **kw)


def figure():
    fig, ax = plt.subplots(figsize=(W_IN, H_IN), dpi=DPI)
    fig.subplots_adjust(left=0.1, right=0.97, top=0.86, bottom=0.18)
    return fig, ax


def style_axes(ax, pct=True):
    for lab in ax.get_xticklabels() + ax.get_yticklabels():
        lab.set_fontfamily(F["mono"])
        lab.set_fontsize(17)
    ax.tick_params(length=0, pad=8)
    ax.grid(axis="y", color=SLATE_LIGHT, linewidth=0.6, alpha=0.6)
    ax.set_axisbelow(True)
    if pct:
        ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{v:.0f}%" if v == int(v) else f"{v:.1f}%"))


def source_line(fig, text):
    fig.text(0.08, 0.03, text, **mono(7.6, color=SLATE, alpha=0.8))


def save(fig, stem, values):
    OUT.mkdir(parents=True, exist_ok=True)
    fig.savefig(OUT / f"{stem}.svg")
    fig.savefig(OUT / f"{stem}.png", dpi=DPI)
    plt.close(fig)
    (OUT / f"{stem}.json").write_text(json.dumps(values, indent=2, default=str) + "\n")
    print(f"wrote charts/out/{stem}.{{svg,png,json}}")


def con(state):
    p = WAREHOUSE / f"kelder_{state}.duckdb"
    if not p.exists():
        sys.exit(f"{p.name} missing: run make build-all")
    c = duckdb.connect(str(p), read_only=True)
    c.execute("set TimeZone = 'UTC'")
    return c


# --------------------------------------------------------------------------------------------- charts


def cancellations_by_hour():
    c = con("before")
    rows = c.execute("""
        select strftime(timezone('Europe/Amsterdam', occurred_at), '%Y-%m') as month, hour(occurred_at) as hour_utc, count(*) as n
        from main.fct_subscription_events
        where event_type = 'cancelled'
          and timezone('Europe/Amsterdam', occurred_at) >= timestamp '2026-02-01'
          and timezone('Europe/Amsterdam', occurred_at) < timestamp '2026-04-01'
        group by all order by all
    """).fetchall()
    data = {m: [0] * 24 for m in ("2026-02", "2026-03")}
    for m, h, n in rows:
        data[m][h] = n
    fig, axes = plt.subplots(1, 2, figsize=(W_IN, H_IN), dpi=DPI, sharey=True)
    fig.subplots_adjust(left=0.1, right=0.97, top=0.86, bottom=0.22, wspace=0.08)
    for ax, (m, label) in zip(axes, [("2026-02", "FEBRUARY 2026"), ("2026-03", "MARCH 2026")]):
        colors = [SLATE] * 24
        if m == "2026-03":
            colors[0] = BRICK
        ax.bar(range(24), data[m], color=colors, width=0.78)
        ax.set_xticks([0, 6, 12, 18, 23])
        ax.set_xticklabels(["00", "06", "12", "18", "23"])
        style_axes(ax, pct=False)
        ax.set_title(label, loc="left", **mono(12, color=SLATE))
        ax.set_xlabel("hour of day (UTC)", **mono(11))
    axes[0].set_ylabel("subscription cancellations", **mono(11))
    top = data["2026-03"][0]
    axes[1].annotate(f"{top:,} at 00:00 UTC", xy=(0, top), xytext=(3, top * 0.93), **mono(12, color=BRICK),
                     arrowprops=dict(arrowstyle="-", color=BRICK, lw=1))
    source_line(fig, "Kelder Coffee warehouse, before-context state · fct_subscription_events, cancelled")
    save(fig, "cancellations_by_hour_feb_mar_2026", {"unit": "cancellations", "hour_utc": list(range(24)), **data})


def churn_monthly_2026_events():
    c = con("with_context")
    rows = c.execute("""
        select month, churn_rate_as_reported, churn_rate_as_reported_raw, definition_version_as_reported, is_provisional
        from main.metrics_subscriber_churn_monthly where month >= date '2026-01-01' order by month
    """).fetchall()
    events = c.execute("select event_date, event_type, title from context.business_events order by event_date").fetchall()
    months = [r[0] for r in rows]
    x = [dt.datetime(m.year, m.month, 15) for m in months]
    adj = [r[1] * 100 for r in rows]
    raw_mar = next(r[2] for r in rows if r[0].month == 3) * 100
    fig, ax = figure()
    ax.plot(x[:-1], adj[:-1], color=SLATE, lw=3.6, marker="o", ms=7, zorder=3)
    ax.plot(x[-2:], adj[-2:], color=SLATE, lw=3.6, ls=(0, (3, 2)), zorder=2)
    ax.plot(x[-1], adj[-1], marker="o", ms=8, mfc=CREAM, mec=SLATE, mew=2, zorder=4)
    i_mar = [m.month for m in months].index(3)
    ax.plot([x[i_mar], x[i_mar]], [adj[i_mar], raw_mar], color=SLATE_LIGHT, lw=1.2, zorder=1)
    ax.plot(x[i_mar], raw_mar, marker="o", ms=9, color=BRICK, zorder=5)
    ax.annotate(f"{raw_mar:.1f}% raw", xy=(x[i_mar], raw_mar), xytext=(10, -4), textcoords="offset points", **mono(13, color=BRICK))
    ax.annotate(f"{adj[i_mar]:.1f}% adjusted", xy=(x[i_mar], adj[i_mar]), xytext=(-14, -40), textcoords="offset points", ha="right", **mono(12, color=SAGE))
    ax.annotate("provisional", xy=(x[-1], adj[-1]), xytext=(-10, -22), textcoords="offset points", ha="right", **mono(11, color=SLATE))
    v2 = dt.datetime(2026, 5, 1)
    ax.axvline(v2, color=SLATE, lw=1, ls="--", alpha=0.8)
    ax.text(v2, 10.6, "v1 | v2", ha="center", **mono(10.5, color=SLATE))
    ax.set_ylim(0, 10.5)
    ax.set_xlim(dt.datetime(2026, 1, 1), dt.datetime(2026, 7, 1))
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonthday=15))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
    style_axes(ax)
    ax.set_ylabel("subscriber churn, as reported", **mono(11))
    plotted_events = [{"event_date": d, "event_type": etype, "title": title} for d, etype, title in events]
    mig = next((d for d, etype, _ in events if etype == "migration"), None)
    if mig:
        ax.text(dt.datetime(mig.year, mig.month, mig.day), 10.05, "12 MAR: billing migration", ha="right", va="top",
                **mono(11, color=SLATE))
    source_line(fig, "Kelder Coffee warehouse, with-context state · metrics_subscriber_churn_monthly")
    save(fig, "churn_monthly_2026_events", {
        "unit": "percent", "series": [{"month": m, "churn_rate_as_reported": a, "definition_version": r[3], "is_provisional": r[4]}
                                      for m, a, r in zip(months, adj, rows)],
        "march_raw": raw_mar, "events": plotted_events})


def churn_v1_vs_v2_restated():
    c = con("with_context")
    rows = c.execute("select month, churn_rate_v1, churn_rate_v2_restated, is_provisional from main.metrics_subscriber_churn_monthly order by month").fetchall()
    x = [dt.datetime(r[0].year, r[0].month, 15) for r in rows]
    v1 = [r[1] * 100 for r in rows]
    v2 = [r[2] * 100 for r in rows]
    fig, ax = figure()
    ax.plot(x, v1, color=SLATE, lw=3.6, marker="o", ms=5, label="v1: failed payment is churn on day one")
    ax.plot(x[:-1], v2[:-1], color=SAGE, lw=3.6, marker="o", ms=5, label="v2 restated: only if not recovered in 30 days")
    ax.plot(x[-2:], v2[-2:], color=SAGE, lw=3.6, ls=(0, (3, 2)))
    ax.plot(x[-1], v2[-1], marker="o", ms=7, mfc=CREAM, mec=SAGE, mew=2)
    brk = dt.datetime(2026, 5, 1)
    ax.axvline(brk, color=SLATE, lw=1, ls="--")
    ax.text(brk, ax.get_ylim()[1] if False else 4.05, "1 May 2026: reported series switches v1 to v2", ha="right", va="bottom",
            **mono(10.5, color=SLATE))
    ax.set_ylim(0, 4.2)
    ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%b %y"))
    style_axes(ax)
    leg = ax.legend(loc="lower left", frameon=False, prop={"family": F["mono"], "size": 15})
    for t in leg.get_texts():
        t.set_color(SLATE)
    ax.set_ylabel("subscriber churn, adjusted", **mono(11))
    source_line(fig, "Kelder Coffee warehouse, with-context state · metrics_subscriber_churn_monthly")
    save(fig, "churn_v1_vs_v2_restated", {"unit": "percent", "series": [
        {"month": r[0], "churn_rate_v1": a, "churn_rate_v2_restated": b, "is_provisional": r[3]} for r, a, b in zip(rows, v1, v2)]})


def email_revenue_daily_april_2026():
    c = con("with_context")
    rows = c.execute("""
        select day, attributed_revenue_eur, is_incomplete from main.metrics_email_attribution_daily
        where day between date '2026-03-26' and date '2026-04-30' order by day
    """).fetchall()
    ev = c.execute("select event_date, description from context.business_events where event_type = 'outage'").fetchone()
    days = [dt.datetime(d.year, d.month, d.day, 12) for d, _, _ in rows]
    rev = [r[1] for r in rows]
    fig, ax = figure()
    colors = [SLATE] * len(rows)
    i9 = [d.date() for d in days].index(dt.date(2026, 4, 9))
    colors[i9] = BRICK
    ax.bar(days, rev, width=0.75, color=colors)
    lo, hi = dt.datetime(2026, 4, 9, 8), dt.datetime(2026, 4, 10, 15)  # 06:00 to 13:00 UTC in CEST
    ax.axvspan(lo, hi, color=SLATE_LIGHT, alpha=0.55, lw=0)
    ax.text(hi + dt.timedelta(hours=10), max(rev) * 0.95, "no Klaviyo data\n9 Apr 06:00 to\n10 Apr 13:00 UTC", va="top", **mono(11, color=SLATE))
    ax.plot(days[i9], max(rev) * 0.012, marker="^", ms=14, color=BRICK, zorder=5, clip_on=False)
    ax.annotate(f"Thu 9 Apr, campaign day: €{rev[i9]:,.0f}", xy=(days[i9], max(rev) * 0.03), xytext=(days[i9] - dt.timedelta(days=5.6), max(rev) * 0.45),
                **mono(12, color=BRICK), arrowprops=dict(arrowstyle="-", color=BRICK, lw=1))
    ax.set_xlim(dt.datetime(2026, 3, 25, 12), dt.datetime(2026, 5, 1))
    ax.xaxis.set_major_locator(matplotlib.ticker.FixedLocator(
        [mdates.date2num(dt.datetime(2026, m, d, 12)) for m, d in ((3, 29), (4, 5), (4, 9), (4, 16), (4, 23), (4, 30))]))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%-d %b"))
    style_axes(ax, pct=False)
    ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"€{v:,.0f}"))
    ax.set_ylabel("email revenue per day", **mono(11))
    source_line(fig, "Kelder Coffee warehouse, with-context state · metrics_email_attribution_daily, context.business_events")
    save(fig, "email_revenue_daily_april_2026", {"unit": "EUR", "series": [{"day": d, "attributed_revenue_eur": v, "is_incomplete": inc}
                                                                          for d, v, inc in rows], "outage": {"event_date": ev[0], "description": ev[1]}})


def yoy_like_for_like():
    vals = {}
    for state in ("with_context", "rot"):
        c = con(state)
        vals[state] = c.execute("""
            select avg(case when month between date '2025-01-01' and date '2025-06-01' then churn_rate_v2_restated end) * 100,
                   avg(case when month between date '2026-01-01' and date '2026-06-01' then churn_rate_v2_restated end) * 100
            from main.metrics_subscriber_churn_monthly
        """).fetchone()
    fig, ax = figure()
    groups = [("written context", "with_context"), ("after the rot commit", "rot")]
    w = 0.34
    for i, (label, state) in enumerate(groups):
        h25, h26 = vals[state]
        ax.bar(i - w / 2 - 0.02, h25, width=w, color=SLATE_LIGHT)
        ax.bar(i + w / 2 + 0.02, h26, width=w, color=BRICK if state == "rot" else SAGE)
        for xx, v, col in ((i - w / 2 - 0.02, h25, SLATE), (i + w / 2 + 0.02, h26, BRICK if state == "rot" else SLATE)):
            ax.text(xx, v + 0.06, f"{v:.2f}%", ha="center", **mono(13, color=col))
        ax.text(i - w / 2 - 0.02, -0.28, "H1 2025", ha="center", **mono(11))
        ax.text(i + w / 2 + 0.02, -0.28, "H1 2026", ha="center", **mono(11))
    ax.set_xticks([])
    top = max(max(v) for v in vals.values()) * 1.22
    for i, (label, _) in enumerate(groups):
        ax.text(i, top * 0.97, label.upper(), ha="center", va="top", **mono(13, color=SLATE))
    ax.set_ylim(0, top)
    style_axes(ax)
    ax.set_ylabel("mean monthly churn, restated v2", **mono(11))
    source_line(fig, "Kelder Coffee warehouse, with-context and rot states · metrics_subscriber_churn_monthly.churn_rate_v2_restated")
    save(fig, "yoy_like_for_like_written_vs_rot", {"unit": "percent", "mean_monthly_churn_rate_v2_restated": {
        s: {"h1_2025": v[0], "h1_2026": v[1], "change_pp": v[1] - v[0]} for s, v in vals.items()}})


def main():
    F.update(setup_fonts())
    cancellations_by_hour()
    churn_monthly_2026_events()
    churn_v1_vs_v2_restated()
    email_revenue_daily_april_2026()
    yoy_like_for_like()


if __name__ == "__main__":
    main()
