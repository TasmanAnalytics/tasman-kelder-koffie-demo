"""Simplified setup diagram for a slide: data, ktx, Claude, and the written notes.

    uv run python charts/architecture_simple.py

Writes charts/out/architecture_simple.svg. It shows the path the trial transcripts show: Claude queries the
warehouse through ktx, and reads the written notes straight from the repository.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import domain_model as dm  # noqa: E402
from domain_model import BAKSTEEN, CREMA, ESPRESSO, GRACHT, HONING, MONO, MUTED, OUT, PAPER, SANS, SERIF, t, wrap  # noqa: E402


def block(x, y, w, h, title, sub, lines, color):
    ink = ESPRESSO if color == HONING else CREMA  # crema on honing is too faint
    subc = "#8A5F12" if color == HONING else color
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="18" fill="{PAPER}" stroke="{color}" stroke-width="3"/>'
    s += f'<path d="M{x} {y + 18}a18 18 0 0 1 18 -18h{w - 36}a18 18 0 0 1 18 18v52h-{w}z" fill="{color}"/>'
    s += t(x + 26, y + 46, title, 32, SERIF, ink, 600)
    s += t(x + 26, y + 108, sub, 15, MONO, subc, 600, spacing=0.5)
    s += wrap(x + 26, y + 144, lines, 20, SANS, ESPRESSO, 29)
    return s


def arrow(x1, y1, x2, y2, label, color=ESPRESSO, lx=None, ly=None):
    dx, dy = x2 - x1, y2 - y1
    n = (dx * dx + dy * dy) ** 0.5
    ux, uy = dx / n, dy / n
    s = f'<line x1="{x1}" y1="{y1}" x2="{x2 - ux * 18}" y2="{y2 - uy * 18}" stroke="{color}" stroke-width="4"/>'
    s += f'<path d="M{x2} {y2}L{x2 - ux * 22 - uy * 11} {y2 - uy * 22 + ux * 11}L{x2 - ux * 22 + uy * 11} {y2 - uy * 22 - ux * 11}Z" fill="{color}"/>'
    lx = (x1 + x2) / 2 if lx is None else lx
    ly = (y1 + y2) / 2 - 22 if ly is None else ly
    wd = len(label) * 10.5 + 30
    s += f'<rect x="{lx - wd / 2}" y="{ly - 20}" width="{wd}" height="36" rx="18" fill="{CREMA}" stroke="{color}" stroke-width="1.6"/>'
    s += t(lx, ly + 6, label, 17, MONO, color, 600, "middle")
    return s


def build() -> str:
    b = ""
    b += block(60, 170, 400, 250, "The data", "DUCKDB, BUILT BY DBT",
               ["Kelder's warehouse:", "subscriptions, orders,", "cancellations, churn."], ESPRESSO)
    b += block(600, 170, 400, 250, "ktx", "THE AGENT'S DOOR TO THE DATA",
               ["Runs the agent's SQL,", "read-only. Also offers", "its own inferred wiki."], GRACHT)
    b += block(1140, 170, 400, 250, "Claude", "THE AGENT",
               ["Answers the question.", "Queries data through ktx,", "reads the notes directly."], BAKSTEEN)
    b += block(600, 540, 400, 220, "The written notes", "IN THE TEAM'S GIT REPO",
               ["AGENTS.md, decision records,", "caveats, verified queries."], HONING)
    b += arrow(600, 320, 460, 320, "SQL", ESPRESSO)
    b += arrow(1140, 320, 1000, 320, "tool calls", GRACHT)
    b += arrow(1000, 650, 1260, 420, "reads the files", "#8A5F12", lx=1225, ly=560)
    b += t(80, 640, "Without the notes, the agent", 26, dm.HAND, BAKSTEEN, 600)
    b += t(80, 676, "finds the odd batch but not why.", 26, dm.HAND, BAKSTEEN, 600)
    b += t(80, 730, "With them, it gets 3.3% and says why.", 26, dm.HAND, GRACHT, 600)
    return dm.frame(b, "How the demo is wired", "ONE QUESTION, ONE AGENT, TWO SOURCES",
                    "Simplified. In the trials the notes reached Claude through the repo files, not through ktx.",
                    badge="SIMPLIFIED VIEW")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "architecture_simple.svg").write_text(build())
    print("wrote charts/out/architecture_simple.svg")


if __name__ == "__main__":
    main()
