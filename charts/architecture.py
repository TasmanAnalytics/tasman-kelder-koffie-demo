"""Architecture diagram: how dbt, DuckDB, ktx and Claude fit together in the Kelder demo, the two routes by
which the written notes reach the agent, and where a domain layer and a modern BI tool (Omni, Lightdash) would sit.

    uv run python charts/architecture.py

Writes charts/out/architecture.svg. Solid boxes exist in this repository. Dashed boxes are design or
illustration: the domain layer is not built on Kelder, and no BI tool is part of the demo. The trial results
on the workspace chips are read from demo/trial_summary.md, never typed in.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import domain_model as dm  # noqa: E402
from domain_model import (BAKSTEEN, CREMA, ESPRESSO, GRACHT, HONING, LINE, MONO, MUTED, OUT, PAPER, ROOT,  # noqa: E402
                          SANS, SERIF, t, wrap)

DARK_HONING = "#8A5F12"  # honing is too faint for text on crema


def board_results() -> dict:
    """{workspace: (right, runs)} for the board-number question, from the trial summary."""
    out = {}
    p = ROOT / "demo" / "trial_summary.md"
    if p.exists():
        for line in p.read_text().splitlines():
            cells = [c.strip() for c in line.strip("|").split("|")]
            if line.startswith("| ") and len(cells) == 9 and cells[1] == "churn_board_number":
                out[cells[0]] = (int(cells[3]), int(cells[2]))
    return out


def panel(x, y, w, h, title, color, dashed=False, head=44, title_ink=CREMA):
    dash = ' stroke-dasharray="8 6"' if dashed else ""
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{PAPER}" stroke="{color}" stroke-width="2.6"{dash}/>'
    if dashed:
        s += t(x + 18, y + 32, title, 21, SERIF, color, 600)
    else:
        s += f'<path d="M{x} {y + 14}a14 14 0 0 1 14 -14h{w - 28}a14 14 0 0 1 14 14v{head - 14}h-{w}z" fill="{color}"/>'
        s += t(x + 18, y + head - 14, title, 21, SERIF, title_ink, 600)
    return s


def chip(x, y, w, h, title, sub=None, color=ESPRESSO, dashed=False):
    dash = ' stroke-dasharray="6 5"' if dashed else ""
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" fill="{CREMA}" stroke="{color}" stroke-width="2"{dash}/>'
    s += t(x + w / 2, y + (h / 2 - 3 if sub else h / 2 + 5), title, 13.5, MONO, color, 600, "middle")
    if sub:
        s += t(x + w / 2, y + h / 2 + 17, sub, 12, MONO, MUTED, 400, "middle")
    return s


def route(points, color=ESPRESSO, dashed=False, width=2.6, head=True):
    """An orthogonal path through points [(x, y), ...] with an arrowhead at the last point."""
    dash = ' stroke-dasharray="8 6"' if dashed else ""
    d = "M" + " L".join(f"{x} {y}" for x, y in points)
    s = f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}"{dash} stroke-linejoin="round"/>'
    if head:
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


def build() -> str:
    b = ""
    # ---- sources
    b += t(50, 168, "SOURCES (SIMULATED)", 12, MONO, MUTED, 600, spacing=1)
    for i, (n, sub) in enumerate([("Shopify", "orders"), ("Recharge", "subscriptions"), ("Klaviyo", "email"), ("Ad platforms", "spend")]):
        y = 182 + i * 66
        b += f'<rect x="50" y="{y}" width="180" height="54" rx="10" fill="{PAPER}" stroke="{ESPRESSO}" stroke-width="2"/>'
        b += t(64, y + 24, n, 16, SERIF, ESPRESSO, 600) + t(64, y + 43, sub, 11.5, MONO, MUTED)
    b += route([(230, 310), (280, 310)])

    # ---- warehouse
    b += panel(280, 150, 620, 320, "DuckDB warehouse", GRACHT)
    b += t(884, 180, "built and tested by dbt", 12.5, MONO, HONING, 500, "end")
    names = [("raw_*", "as loaded", False), ("staging", "cleaned", False), ("intermediate", "joined", False),
             ("domain", "design", True), ("marts", "fct, metrics", False)]
    for i, (n, sub, dashed) in enumerate(names):
        x = 296 + i * 120
        b += chip(x, 212, 108, 64, n, sub, BAKSTEEN if dashed else ESPRESSO, dashed)
        if i:
            b += route([(x - 12, 244), (x, 244)], BAKSTEEN if i in (3, 4) else ESPRESSO, dashed=i in (3, 4), width=2)
    b += f'<rect x="296" y="296" width="588" height="54" rx="9" fill="{CREMA}" stroke="{ESPRESSO}" stroke-width="2"/>'
    b += t(312, 319, "context schema", 15, MONO, ESPRESSO, 600)
    b += t(312, 339, "business_events · metric_changelog (with-context state only)", 12, MONO, MUTED)
    b += wrap(296, 384, ["Domain layer (design): sources map into it once,", "and everything downstream reads only from it."], 13.5, SANS, BAKSTEEN, 19)
    b += t(296, 448, "one file per state: before · with-context · rot", 12, MONO, MUTED)

    # ---- ktx
    b += panel(960, 150, 270, 280, "ktx", ESPRESSO)
    b += chip(976, 208, 238, 70, "SQL gateway", "the agent's queries, read-only", GRACHT)
    b += f'<rect x="976" y="292" width="238" height="120" rx="9" fill="{CREMA}" stroke="{DARK_HONING}" stroke-width="2"/>'
    b += t(1095, 318, "wiki + semantic layer", 15, MONO, DARK_HONING, 600, "middle")
    b += wrap(992, 342, ["built once by an LLM ingest:", "wiki pages, table and column", "descriptions, a few measures"], 12, MONO, MUTED, 18)
    b += route([(900, 243), (976, 243)], GRACHT)
    b += label(938, 222, "SQL", GRACHT)

    # ---- Claude and a BI tool
    b += panel(1290, 150, 260, 190, "Claude Code", BAKSTEEN)
    b += wrap(1308, 222, ["The agent, pinned model.", "Tools: Read, Grep, Glob", "and the ktx tools only."], 15, SANS, ESPRESSO, 22)
    b += route([(1230, 243), (1290, 243)], BAKSTEEN)
    b += label(1260, 222, "MCP", BAKSTEEN)
    b += panel(1290, 372, 260, 150, "Modern BI tool", BAKSTEEN, dashed=True)
    b += t(1308, 426, "e.g. Omni, Lightdash", 12.5, MONO, BAKSTEEN, 600)
    b += wrap(1308, 452, ["Dashboards, board pack.", "Brings its own context:", "its model, AI notes and", "usage data. Illustrative."], 13.5, SANS, ESPRESSO, 19)
    b += route([(900, 452), (1290, 452)], BAKSTEEN, dashed=True)
    b += label(992, 452, "reads the marts", BAKSTEEN)
    b += route([(1230, 398), (1290, 398)], BAKSTEEN, dashed=True)
    # ---- repo
    b += panel(280, 540, 620, 170, "kelder-dbt/  (the team's git repo)", ESPRESSO)
    b += t(298, 614, "dbt models and tests", 15, MONO, ESPRESSO, 600)
    b += wrap(298, 638, ["staging, intermediate, marts,", "column descriptions, tests"], 13.5, SANS, ESPRESSO, 20)
    b += f'<rect x="590" y="596" width="294" height="100" rx="9" fill="{CREMA}" stroke="{DARK_HONING}" stroke-width="2"/>'
    b += t(606, 620, "the written notes", 15, MONO, DARK_HONING, 600)
    b += wrap(606, 644, ["AGENTS.md, decision records,", "glossary, quirks, verified queries"], 13.5, SANS, ESPRESSO, 20)
    b += route([(440, 540), (440, 470)])
    b += label(440, 505, "dbt build")

    # two routes for the notes
    b += route([(884, 626), (1095, 626), (1095, 430)], DARK_HONING)
    b += label(1095, 560, "route 2: ingest copies notes into the wiki", DARK_HONING)
    b += route([(884, 676), (1260, 676), (1260, 310), (1290, 310)], DARK_HONING)
    b += label(1262, 676, "route 1: AGENTS.md loads at start", DARK_HONING, anchor="start")

    # ---- checks
    b += panel(50, 540, 190, 170, "Checks", BAKSTEEN)
    b += wrap(66, 612, ["make check, CI:", "verified queries", "against pinned", "answers; PR capture."], 13.5, SANS, ESPRESSO, 19)
    b += route([(280, 625), (240, 625)], BAKSTEEN)

    # ---- the four workspaces
    res = board_results()
    ws = [("installed", "before state, no notes", BAKSTEEN), ("written", "notes by route 1", GRACHT),
          ("wiki", "notes by route 2 only", GRACHT), ("rot", "route 1, one bad commit", GRACHT)]
    b += t(50, 752, "FOUR AGENT WORKSPACES · BOARD NUMBER RIGHT (3.3%)", 12, MONO, MUTED, 600, spacing=1)
    for i, (name, sub, col) in enumerate(ws):
        x = 50 + i * 378
        right, runs = res.get(name, (0, 0))
        b += f'<rect x="{x}" y="764" width="360" height="62" rx="10" fill="{PAPER}" stroke="{LINE}" stroke-width="1.6"/>'
        b += t(x + 16, 791, name, 17, MONO, ESPRESSO, 700) + t(x + 16, 813, sub, 12.5, MONO, MUTED)
        b += t(x + 344, 806, f"{right} of {runs}" if runs else "–", 26, SERIF, col if right else BAKSTEEN, 600, "end")
    return dm.frame(b, "How the pieces fit together", "SOURCES · DBT · DUCKDB · KTX · CLAUDE, AND TWO ROUTES FOR THE NOTES",
                    "Dashed: design or illustration, not in the demo. In a real company DuckDB would be Snowflake or BigQuery; the shape is the same.",
                    badge="SOLID: BUILT · DASHED: DESIGN")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "architecture.svg").write_text(build())
    print("wrote charts/out/architecture.svg")


if __name__ == "__main__":
    main()
