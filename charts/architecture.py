"""Architecture diagram: how dbt, DuckDB, ktx and Claude fit together in the Kelder demo, and where a domain
layer and a BI tool such as Omni would sit.

    uv run python charts/architecture.py

Writes charts/out/architecture.svg. Solid boxes exist in this repository. Dashed boxes are design or
illustration: the domain layer is not built on Kelder, and Omni is not part of the demo.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import domain_model as dm  # noqa: E402
from domain_model import (BAKSTEEN, CREMA, ESPRESSO, GRACHT, HONING, LINE, MONO, MUTED, PAPER, SANS, SERIF,  # noqa: E402
                          H, OUT, W, t, wrap)


def box(x, y, w, h, title, lines=(), color=ESPRESSO, dashed=False, fill=PAPER, title_fill=None, size=15, head=None):
    dash = ' stroke-dasharray="7 6"' if dashed else ""
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="12" fill="{fill}" stroke="{color}" stroke-width="2.2"{dash}/>'
    ty = y + 30
    if head:
        s += f'<path d="M{x} {y + 12}a12 12 0 0 1 12 -12h{w - 24}a12 12 0 0 1 12 12v{head - 12}h-{w}z" fill="{color}"/>'
        s += t(x + 16, y + head - 13, title, 20, SERIF, CREMA, 600)
        ty = y + head + 26
    else:
        s += t(x + 16, ty, title, 20, SERIF, title_fill or color, 600)
        ty += 26
    s += wrap(x + 16, ty, list(lines), size, SANS, ESPRESSO, size * 1.42)
    return s


def chip(x, y, w, h, title, sub=None, color=ESPRESSO, dashed=False, fill=CREMA):
    dash = ' stroke-dasharray="6 5"' if dashed else ""
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="9" fill="{fill}" stroke="{color}" stroke-width="2"{dash}/>'
    s += t(x + w / 2, y + (28 if sub else h / 2 + 5), title, 15, MONO, color, 600, "middle")
    if sub:
        s += t(x + w / 2, y + 52, sub, 12, MONO, MUTED, 400, "middle")
    return s


def link(x1, y1, x2, y2, color=ESPRESSO, dashed=False, width=2.4, head=True, path=None):
    dash = ' stroke-dasharray="8 6"' if dashed else ""
    d = path or f"M{x1} {y1}L{x2} {y2}"
    s = f'<path d="{d}" fill="none" stroke="{color}" stroke-width="{width}"{dash}/>'
    if head:
        # arrowhead at (x2, y2), direction from the last segment
        px, py = (x1, y1) if not path else (path_last(path)[0], path_last(path)[1])
        dx, dy = x2 - px, y2 - py
        n = (dx * dx + dy * dy) ** 0.5 or 1
        ux, uy = dx / n, dy / n
        s += f'<path d="M{x2} {y2}L{x2 - ux * 15 - uy * 7} {y2 - uy * 15 + ux * 7}L{x2 - ux * 15 + uy * 7} {y2 - uy * 15 - ux * 7}Z" fill="{color}"/>'
    return s


def path_last(path):
    """Second-to-last point of an M/H/V path, so the arrowhead can point along the final segment."""
    toks = path.replace("M", " M ").replace("H", " H ").replace("V", " V ").replace("L", " L ").split()
    pts, x, y, i = [], 0.0, 0.0, 0
    while i < len(toks):
        c = toks[i]
        if c in ("M", "L"):
            x, y = float(toks[i + 1]), float(toks[i + 2]); i += 3
        elif c == "H":
            x = float(toks[i + 1]); i += 2
        else:
            y = float(toks[i + 1]); i += 2
        pts.append((x, y))
    return pts[-2]


def tag(x, y, text, color=MUTED):
    wd = len(text) * 7.6 + 18
    return (f'<rect x="{x - wd / 2}" y="{y - 13}" width="{wd}" height="24" rx="12" fill="{CREMA}" stroke="{LINE}"/>'
            + t(x, y + 4, text, 12, MONO, color, 500, "middle"))


def build() -> str:
    b = ""
    # ---- sources
    b += t(50, 158, "SOURCES (SIMULATED)", 12.5, MONO, MUTED, 600, spacing=1)
    for i, (n, sub) in enumerate([("Shopify", "orders, customers"), ("Recharge", "subscriptions"), ("Klaviyo", "email events"), ("Ad platforms", "spend")]):
        y = 176 + i * 74
        b += f'<rect x="50" y="{y}" width="200" height="60" rx="10" fill="{PAPER}" stroke="{ESPRESSO}" stroke-width="2"/>'
        b += t(66, y + 26, n, 17, SERIF, ESPRESSO, 600) + t(66, y + 46, sub, 12, MONO, MUTED)
    b += f'<path d="M250 206H285M250 280H285M250 354H285M250 428H285M285 206V428" fill="none" stroke="{ESPRESSO}" stroke-width="2.4"/>'
    b += link(285, 300, 335, 300)
    b += t(50, 480, "load_raw.py loads Parquet into raw_*", 12, MONO, MUTED)

    # ---- warehouse (DuckDB) with dbt inside
    b += f'<rect x="320" y="150" width="680" height="342" rx="16" fill="none" stroke="{GRACHT}" stroke-width="3"/>'
    b += f'<path d="M320 166a16 16 0 0 1 16 -16h648a16 16 0 0 1 16 16v26h-680z" fill="{GRACHT}"/>'
    b += t(340, 178, "DuckDB warehouse", 21, SERIF, CREMA, 600) + t(985, 178, "one file per state", 12.5, MONO, HONING, 500, "end")
    cy, cw = 210, 120
    for i, (n, sub, dashed) in enumerate([("raw_*", "as loaded", False), ("staging", "cleaned", False), ("intermediate", "joined", False),
                                          ("domain", "DESIGN", True), ("marts", "fct + metrics", False)]):
        x = 336 + i * 130
        b += chip(x, cy, cw, 70, n, sub, BAKSTEEN if dashed else ESPRESSO, dashed)
        if i:
            b += link(x - 10, cy + 35, x, cy + 35, BAKSTEEN if i in (3, 4) else ESPRESSO, dashed=i in (3, 4), width=2, path=f"M{x - 10} {cy + 35}H{x}")
    b += f'<rect x="336" y="302" width="640" height="56" rx="9" fill="{CREMA}" stroke="{ESPRESSO}" stroke-width="2"/>'
    b += t(352, 326, "context schema", 15, MONO, ESPRESSO, 600) + t(352, 346, "business_events · metric_changelog · column caveats", 13, MONO, MUTED)
    b += f'<rect x="336" y="376" width="640" height="46" rx="9" fill="{ESPRESSO}"/>'
    b += t(352, 405, "dbt (dbt-duckdb)  builds, tests and documents every layer", 16, MONO, CREMA, 500)
    b += t(985, 470, "kelder_before.duckdb · kelder_with_context.duckdb · kelder_rot.duckdb", 12, MONO, MUTED, 400, "end")

    # ---- repo
    b += box(320, 560, 680, 170, "kelder-dbt/  (git)", [
        "models, tests, profiles.yml", "AGENTS.md: where each note lives",
        "context/: decision records, glossary, quirks, verified_queries.yml", "pull request template: the metric-impact question"],
        ESPRESSO, head=42, size=15)
    b += link(660, 560, 660, 494, ESPRESSO, path="M660 560V494")
    b += tag(660, 528, "models + tests + context")

    # ---- ktx
    b += box(1060, 150, 250, 200, "ktx", [
        "Reads the warehouse", "(read-only), kelder-dbt/", "and the dbt manifest.", "An LLM ingest builds a", "semantic layer and a wiki."],
        ESPRESSO, head=42, size=14)
    b += t(1076, 340, "serves MCP, 127.0.0.1:7801-7803", 11, MONO, MUTED)
    b += link(1000, 250, 1060, 250, path="M1000 250H1060")
    b += tag(1030, 224, "SQL")

    # ---- Claude
    b += box(1360, 150, 200, 200, "Claude Code", [
        "The agent. Pinned model.", "Tools: Read, Grep, Glob", "and the ktx tools.", "Reads AGENTS.md and", "the repo copy directly."],
        GRACHT, head=42, size=14)
    b += link(1310, 250, 1360, 250, path="M1310 250H1360")
    b += tag(1335, 224, "MCP")

    # ---- Omni (illustrative)
    b += box(1360, 400, 200, 130, "Omni", [
        "A standard BI tool.", "Models the marts;", "dashboards, board pack."],
        BAKSTEEN, dashed=True, size=14)
    b += t(1376, 520, "ILLUSTRATIVE", 11, MONO, BAKSTEEN, 600, spacing=1)
    b += link(1000, 450, 1360, 450, BAKSTEEN, dashed=True, path="M1000 450H1360")
    b += tag(1180, 424, "SQL", BAKSTEEN)

    # ---- checks
    b += box(1060, 560, 500, 170, "Checks (make check, CI)", [
        "Verified queries against pinned answers.", "Capture check on the pull request body.",
        "Design: a lineage check, so presentation models", "read only from the domain layer."],
        BAKSTEEN, size=15, head=42)
    b += link(1000, 645, 1060, 645, path="M1000 645H1060")

    # ---- domain note
    b += f'<rect x="50" y="526" width="252" height="204" rx="12" fill="{CREMA}" stroke="{HONING}" stroke-width="2.4" stroke-dasharray="7 6"/>'
    b += t(66, 554, "Where the domain layer fits", 14, SERIF, ESPRESSO, 600)
    b += wrap(66, 580, ["Between staging and", "the marts. Sources map", "into it once. Everything", "downstream, including", "ktx, Omni and the", "agent, reads from it."], 13.5, SANS, ESPRESSO, 19.5)

    # ---- legend
    b += f'<rect x="60" y="832" width="34" height="16" rx="4" fill="none" stroke="{ESPRESSO}" stroke-width="2"/>' + t(102, 845, "built in this repository", 12.5, MONO, MUTED)
    b += f'<rect x="320" y="832" width="34" height="16" rx="4" fill="none" stroke="{BAKSTEEN}" stroke-width="2" stroke-dasharray="5 4"/>' + t(362, 845, "design or illustration, not in the demo", 12.5, MONO, MUTED)
    return dm.frame(b, "How the pieces fit together", "SOURCES · DBT · DUCKDB · KTX · CLAUDE, WITH A DOMAIN LAYER AND A BI TOOL",
                    "In a real company DuckDB would be Snowflake, BigQuery or similar; the shape stays the same.",
                    badge="SOLID: BUILT · DASHED: DESIGN")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "architecture.svg").write_text(build())
    print("wrote charts/out/architecture.svg")


if __name__ == "__main__":
    main()
