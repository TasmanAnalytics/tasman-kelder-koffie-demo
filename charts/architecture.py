"""Architecture diagrams: how sources, dbt, the warehouse, ktx, an agent and a BI tool fit together, drawn twice.

    uv run python charts/architecture.py

Writes three files:
- charts/out/architecture_plain.svg: the plain stack. The agent and a BI tool query the marts directly, with no
  ktx and no context layer.
- charts/out/architecture_without_context.svg: the usual stack. The agent reaches the data through ktx (SQL and
  a semantic layer inferred from the schema); nothing records why a number moved.
- charts/out/architecture.svg: the same stack with a context layer: a domain layer, the context schema, the
  written notes in the repo, the two routes by which they reach the agent, and the checks that keep them honest.

These explain how the pieces work together; they make a general point rather than separate built from designed.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import domain_model as dm  # noqa: E402
from domain_model import (BAKSTEEN, CREMA, ESPRESSO, GRACHT, HAND, HONING, MONO, MUTED, OUT, PAPER,  # noqa: E402
                          SANS, SERIF, t, wrap)

DARK_HONING = "#8A5F12"  # honing is too faint for text on crema


def panel(x, y, w, h, title, color, head=44):
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{PAPER}" stroke="{color}" stroke-width="2.6"/>'
    s += f'<path d="M{x} {y + 14}a14 14 0 0 1 14 -14h{w - 28}a14 14 0 0 1 14 14v{head - 14}h-{w}z" fill="{color}"/>'
    s += t(x + 18, y + head - 14, title, 21, SERIF, CREMA, 600)
    return s


def chip(x, y, w, h, title, sub=None, color=ESPRESSO):
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" fill="{CREMA}" stroke="{color}" stroke-width="2"/>'
    s += t(x + w / 2, y + (h / 2 - 3 if sub else h / 2 + 5), title, 13.5, MONO, color, 600, "middle")
    if sub:
        s += t(x + w / 2, y + h / 2 + 17, sub, 12, MONO, MUTED, 400, "middle")
    return s


def route(points, color=ESPRESSO, width=2.6):
    """An orthogonal path through points [(x, y), ...] with an arrowhead at the last point."""
    d = "M" + " L".join(f"{x} {y}" for x, y in points)
    s = f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round"/>'
    (x1, y1), (x2, y2) = points[-2], points[-1]
    dx, dy = x2 - x1, y2 - y1
    n = (dx * dx + dy * dy) ** 0.5 or 1
    ux, uy = dx / n, dy / n
    s += (f'<path d="M{x2} {y2}L{x2 - ux * 15 - uy * 7} {y2 - uy * 15 + ux * 7}'
          f'L{x2 - ux * 15 + uy * 7} {y2 - uy * 15 - ux * 7}Z" fill="{color}"/>')
    return s


def label(x, y, text, color=ESPRESSO, anchor="middle"):
    wd = len(text) * 7.7 + 20
    x0 = x - wd / 2 if anchor == "middle" else x
    return (f'<rect x="{x0}" y="{y - 13}" width="{wd}" height="25" rx="12.5" fill="{CREMA}" stroke="{color}" stroke-width="1.3"/>'
            + t(x0 + wd / 2, y + 4, text, 12.5, MONO, color, 600, "middle"))


def build(mode: str) -> str:
    """mode: "plain" (no ktx, no context), "without" (ktx, no context) or "with" (ktx and a context layer)."""
    with_context = mode == "with"
    b = ""
    # ---- sources
    b += t(50, 168, "SOURCES", 12, MONO, MUTED, 600, spacing=1)
    for i, (n, sub) in enumerate([("Shopify", "orders"), ("Recharge", "subscriptions"), ("Klaviyo", "email"), ("Ad platforms", "spend")]):
        y = 182 + i * 66
        b += f'<rect x="50" y="{y}" width="180" height="54" rx="10" fill="{PAPER}" stroke="{ESPRESSO}" stroke-width="2"/>'
        b += t(64, y + 24, n, 16, SERIF, ESPRESSO, 600) + t(64, y + 43, sub, 11.5, MONO, MUTED)
    b += route([(230, 310), (280, 310)])

    # ---- warehouse
    b += panel(280, 150, 620, 320, "Warehouse", GRACHT)
    b += t(884, 180, "built and tested by dbt", 12.5, MONO, HONING, 500, "end")
    if with_context:
        names = [("raw", "as loaded"), ("staging", "cleaned"), ("intermediate", "joined"), ("domain", "what exists"), ("marts", "fct, metrics")]
        cw, gap = 108, 12
    else:
        names = [("raw", "as loaded"), ("staging", "cleaned"), ("intermediate", "joined"), ("marts", "fct, metrics")]
        cw, gap = 138, 12
    for i, (n, sub) in enumerate(names):
        x = 296 + i * (cw + gap)
        b += chip(x, 212, cw, 64, n, sub, BAKSTEEN if n == "domain" else ESPRESSO)
        if i:
            b += route([(x - gap, 244), (x, 244)], width=2)
    if with_context:
        b += f'<rect x="296" y="296" width="588" height="54" rx="9" fill="{CREMA}" stroke="{ESPRESSO}" stroke-width="2"/>'
        b += t(312, 319, "context schema", 15, MONO, ESPRESSO, 600)
        b += t(312, 339, "business_events · metric_changelog", 12, MONO, MUTED)
        b += wrap(296, 384, ["Domain layer: sources map into it once, and", "everything downstream reads only from it."], 13.5, SANS, BAKSTEEN, 19)
    else:
        b += wrap(296, 330, ["Correct as calculations. Nothing in these", "tables says why a number moved."], 16, SANS, ESPRESSO, 23)
    b += t(296, 448, "DuckDB in the demo; Snowflake or BigQuery in real life", 12, MONO, MUTED)

    if mode != "plain":
        # ---- ktx
        b += panel(960, 150, 270, 280, "ktx", ESPRESSO)
        b += chip(976, 208, 238, 70, "SQL gateway", "the agent's queries, read-only", GRACHT)
        b += f'<rect x="976" y="292" width="238" height="120" rx="9" fill="{CREMA}" stroke="{DARK_HONING}" stroke-width="2"/>'
        if with_context:
            b += t(1095, 318, "wiki + semantic layer", 15, MONO, DARK_HONING, 600, "middle")
            b += wrap(992, 342, ["semantic layer from the", "schema, plus a wiki that", "holds the written notes"], 12, MONO, MUTED, 18)
        else:
            b += t(1095, 318, "semantic layer", 15, MONO, DARK_HONING, 600, "middle")
            b += wrap(992, 342, ["inferred from the schema", "and the dbt code: tables,", "columns, a best guess"], 12, MONO, MUTED, 18)
        b += route([(900, 243), (976, 243)], GRACHT)
        b += label(938, 222, "SQL", GRACHT)

    # ---- agent and BI tool
    b += panel(1290, 150, 260, 190, "Agent", BAKSTEEN)
    if mode == "plain":
        b += wrap(1308, 222, ["Claude, or any agent.", "Writes SQL against the", "marts and answers."], 15, SANS, ESPRESSO, 22)
        b += route([(900, 243), (1290, 243)], BAKSTEEN)
        b += label(1095, 243, "SQL over MCP", BAKSTEEN)
    else:
        b += wrap(1308, 222, ["Claude in the demo.", "Asks ktx for data and", "meaning, then answers."], 15, SANS, ESPRESSO, 22)
        b += route([(1230, 243), (1290, 243)], BAKSTEEN)
        b += label(1260, 222, "MCP", BAKSTEEN)
    b += panel(1290, 372, 260, 150, "BI tool", BAKSTEEN)
    b += t(1308, 440, "e.g. Omni, Lightdash", 12.5, MONO, BAKSTEEN, 600)
    b += wrap(1308, 466, ["Dashboards, board pack.", "Brings its own model,", "AI notes and usage data."], 13.5, SANS, ESPRESSO, 19)
    b += route([(900, 452), (1290, 452)], BAKSTEEN)
    b += label(992 if mode != "plain" else 1095, 452, "reads the marts", BAKSTEEN)
    if mode != "plain":
        b += route([(1230, 400), (1290, 400)], BAKSTEEN)

    # ---- repo
    b += panel(280, 540, 620, 170, "The team's git repo", ESPRESSO)
    b += t(298, 614, "dbt models and tests", 15, MONO, ESPRESSO, 600)
    b += wrap(298, 638, ["staging, intermediate, marts,", "column descriptions, tests"], 13.5, SANS, ESPRESSO, 20)
    b += route([(440, 540), (440, 470)])
    b += label(440, 505, "dbt build")
    if with_context:
        b += f'<rect x="590" y="596" width="294" height="100" rx="9" fill="{CREMA}" stroke="{DARK_HONING}" stroke-width="2"/>'
        b += t(606, 620, "the written notes", 15, MONO, DARK_HONING, 600)
        b += wrap(606, 644, ["AGENTS.md, decision records,", "glossary, quirks, verified queries"], 13.5, SANS, ESPRESSO, 20)
        b += route([(884, 626), (1095, 626), (1095, 430)], DARK_HONING)
        b += label(1095, 560, "route 2: copied into the ktx wiki", DARK_HONING)
        b += route([(884, 676), (1260, 676), (1260, 310), (1290, 310)], DARK_HONING)
        b += label(1262, 676, "route 1: AGENTS.md read at start", DARK_HONING, anchor="start")
        b += panel(50, 540, 190, 170, "Checks", BAKSTEEN)
        b += wrap(66, 612, ["verified queries", "against pinned", "answers; one impact", "question per PR"], 13.5, SANS, ESPRESSO, 19)
        b += route([(280, 625), (240, 625)], BAKSTEEN)
        b += t(50, 790, "The reasons are written down once, reach every reader, and the checks keep them true.", 28, HAND, GRACHT, 600)
        title, sub, badge = ("With a context layer", "THE SAME STACK, WITH THE REASONS WRITTEN DOWN", "WITH CONTEXT")
        note = "The notes reach the agent straight from the repo, or through the ktx wiki. Either works."
    else:
        b += wrap(606, 614, ["The reasons behind the numbers", "live in people's heads, Slack", "threads and a wiki page."], 15, SANS, MUTED, 22)
        if mode == "plain":
            b += t(50, 790, "Every reader works out what the numbers mean on its own.", 28, HAND, BAKSTEEN, 600)
            title, sub, badge = ("The plain stack", "SOURCES · DBT · WAREHOUSE · AGENT AND BI TOOL ON THE MARTS", "NO KTX, NO CONTEXT")
            note = "Both query the marts directly: the agent has only table and column names to go on, the BI tool only its own model."
        else:
            b += t(50, 790, "The agent can find what looks odd. Nothing tells it why.", 28, HAND, BAKSTEEN, 600)
            title, sub, badge = ("Without a context layer", "SOURCES · DBT · WAREHOUSE · KTX · AGENT · BI TOOL", "WITHOUT CONTEXT")
            note = "ktx gives the agent SQL and a semantic layer it inferred from the schema; the meaning is a guess."
    return dm.frame(b, title, sub, note, badge=badge)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    for name, mode in (("architecture_plain", "plain"), ("architecture_without_context", "without"), ("architecture", "with")):
        (OUT / f"{name}.svg").write_text(build(mode))
        print(f"wrote charts/out/{name}.svg")


if __name__ == "__main__":
    main()
