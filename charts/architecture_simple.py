"""Simple setup diagram for a slide: one question, one agent, the data and the notes.

    uv run python charts/architecture_simple.py

Writes charts/out/architecture_simple.svg. The three result cards are read from demo/trial_summary.md
(board-number question), never typed in.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import domain_model as dm  # noqa: E402
from architecture import DARK_HONING, board_results  # noqa: E402
from domain_model import BAKSTEEN, CREMA, ESPRESSO, GRACHT, HAND, HONING, LINE, MONO, MUTED, OUT, PAPER, SANS, SERIF, t, wrap  # noqa: E402


def card(x, y, w, h, title, lines, color, ink=CREMA, sub=None):
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="20" fill="{PAPER}" stroke="{color}" stroke-width="3"/>'
    s += f'<path d="M{x} {y + 20}a20 20 0 0 1 20 -20h{w - 40}a20 20 0 0 1 20 20v44h-{w}z" fill="{color}"/>'
    s += t(x + 26, y + 44, title, 30, SERIF, ink, 600)
    ty = y + 100
    if sub:
        s += t(x + 26, ty, sub, 14, MONO, DARK_HONING if color == HONING else color, 700, spacing=0.8)
        ty += 32
    s += wrap(x + 26, ty, lines, 20, SANS, ESPRESSO, 29)
    return s


def arrow(x1, y1, x2, y2, color, text=None, tx=None, ty=None, anchor="middle"):
    dx, dy = x2 - x1, y2 - y1
    n = (dx * dx + dy * dy) ** 0.5
    ux, uy = dx / n, dy / n
    s = f'<line x1="{x1}" y1="{y1}" x2="{x2 - ux * 20}" y2="{y2 - uy * 20}" stroke="{color}" stroke-width="4" stroke-linecap="round"/>'
    s += f'<path d="M{x2} {y2}L{x2 - ux * 24 - uy * 12} {y2 - uy * 24 + ux * 12}L{x2 - ux * 24 + uy * 12} {y2 - uy * 24 - ux * 12}Z" fill="{color}"/>'
    if text:
        s += t(tx, ty, text, 17, MONO, color, 700, anchor)
    return s


def result(x, y, w, head, sub, right, runs, good):
    col = GRACHT if good else BAKSTEEN
    s = f'<rect x="{x}" y="{y}" width="{w}" height="118" rx="16" fill="{PAPER}" stroke="{LINE}" stroke-width="2"/>'
    s += f'<rect x="{x}" y="{y}" width="10" height="118" rx="5" fill="{col}"/>'
    s += t(x + 32, y + 42, head, 22, SERIF, ESPRESSO, 600)
    s += t(x + 32, y + 72, sub, 14.5, MONO, MUTED)
    s += t(x + 32, y + 100, "board number right", 13, MONO, MUTED)
    s += t(x + w - 26, y + 94, f"{right}/{runs}" if runs else "–", 52, SERIF, col, 600, "end")
    return s


def build() -> str:
    b = ""
    # the question
    b += f'<path d="M60 250h300a24 24 0 0 1 24 24v112a24 24 0 0 1 -24 24h-230l-40 34v-34h-30a24 24 0 0 1 -24 -24v-112a24 24 0 0 1 24 -24z" fill="{ESPRESSO}"/>'
    b += wrap(84, 300, ["“What was churn in", "March? One number", "for the board.”"], 27, HAND, CREMA, 34)
    b += t(60, 478, "SAME QUESTION, EVERY RUN", 13, MONO, MUTED, 600, spacing=1)

    # the agent
    b += card(470, 210, 300, 240, "Claude", ["Plans, looks things up,", "runs queries, answers."], BAKSTEEN, sub="THE AGENT")
    b += arrow(384, 330, 470, 330, ESPRESSO)

    # the data door
    b += card(890, 150, 290, 190, "ktx", ["Runs its SQL,", "read-only."], GRACHT, sub="THE DOOR TO THE DATA")
    b += card(1260, 150, 290, 190, "Warehouse", ["Kelder's numbers,", "built by dbt."], ESPRESSO, sub="DUCKDB")
    b += arrow(770, 290, 890, 245, GRACHT)
    b += arrow(1180, 245, 1260, 245, ESPRESSO)

    # the notes
    b += card(890, 400, 660, 200, "The written notes", [], HONING, ink=ESPRESSO, sub="WHY THE NUMBERS ARE WHAT THEY ARE")
    b += wrap(916, 548, ["Decision 0007: the 12 March import", "wrote paused subscriptions as cancelled."], 19, SANS, ESPRESSO, 27)
    b += f'<line x1="1300" y1="478" x2="1300" y2="584" stroke="{LINE}" stroke-width="1.5"/>'
    b += t(1320, 500, "Two ways in:", 15, MONO, DARK_HONING, 700)
    b += t(1320, 530, "1  AGENTS.md in the repo", 15, MONO, ESPRESSO)
    b += t(1320, 560, "2  the ktx wiki", 15, MONO, ESPRESSO)
    b += arrow(770, 390, 890, 470, DARK_HONING)

    # results
    res = board_results()
    b += t(60, 668, "WHAT THE AGENT TOLD THE BOARD", 13, MONO, MUTED, 600, spacing=1)
    for i, (ws, head, sub, good) in enumerate([("installed", "No notes", "finds the odd batch, not why", False),
                                                ("written", "Notes in the repo", "AGENTS.md, read at start", True),
                                                ("wiki", "Notes in the ktx wiki", "found with wiki_search", True)]):
        r, n = res.get(ws, (0, 0))
        b += result(60 + i * 500, 684, 470, head, sub, r, n, good and r > 0)
    return dm.frame(b, "How the demo works", "ONE AGENT · THE DATA · THE NOTES",
                    "The right answer is 3.3%. Same model, same warehouse, same question; only the notes change.",
                    badge="KELDER KOFFIE DEMO")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "architecture_simple.svg").write_text(build())
    print("wrote charts/out/architecture_simple.svg")


if __name__ == "__main__":
    main()
