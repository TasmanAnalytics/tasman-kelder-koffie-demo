"""Four kinds of knowledge, four homes: where each kind of written context lives in the Kelder repo.

    uv run python charts/knowledge_homes.py

Writes charts/out/knowledge_homes.svg. The examples are Kelder's own: the churned_at caveat, the business
events table, decision records and verified queries. In the trials the agent reached them through ktx
(SQL and the wiki) or by reading the repository directly.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import domain_model as dm  # noqa: E402
from architecture import DARK_HONING  # noqa: E402
from domain_model import BAKSTEEN, CREMA, ESPRESSO, GRACHT, HONING, LINE, MONO, MUTED, OUT, PAPER, SANS, SERIF, t, wrap  # noqa: E402

KINDS = [
    # kind, example, home, where exactly, fill, border, ink
    ("STRUCTURAL", "“churned_at is wrong for the 12 March backfill”", "dbt YAML", "column descriptions and caveats",
     "#F2E1B8", DARK_HONING, ESPRESSO),
    ("TEMPORAL", "“billing moved to Recharge on 12 March”", "Warehouse tables", "context.business_events, metric_changelog",
     "#D6E3DF", GRACHT, ESPRESSO),
    ("NARRATIVE", "“why churn is defined this way”", "Markdown in the repo", "decision records, glossary, AGENTS.md",
     "#F0D9CF", BAKSTEEN, ESPRESSO),
    ("BEHAVIOURAL", "“what a correct answer looks like”", "Verified queries", "pinned answers; doubles as the check in CI",
     ESPRESSO, ESPRESSO, CREMA),
]


def build() -> str:
    b = ""
    top, step, h = 170, 162, 128
    for i, (kind, example, home, where, fill, border, ink) in enumerate(KINDS):
        y = top + i * step
        mid = y + h / 2
        # the kind, on the left
        b += f'<rect x="60" y="{y + 18}" width="26" height="26" rx="5" fill="{fill}" stroke="{border}" stroke-width="2"/>'
        b += t(102, y + 38, kind, 16, MONO, ESPRESSO, 700, spacing=1.2)
        b += t(102, y + 80, example, 21, SERIF, MUTED, 400, style="italic")
        b += f'<line x1="60" x2="600" y1="{y + h - 4}" y2="{y + h - 4}" stroke="{LINE}" stroke-width="1.5"/>'
        # arrow to its home
        b += f'<line x1="630" y1="{mid}" x2="712" y2="{mid}" stroke="{ESPRESSO}" stroke-width="2.6"/>'
        b += f'<path d="M726 {mid}l-16 -8v16z" fill="{ESPRESSO}"/>'
        # the home
        b += f'<rect x="740" y="{y}" width="500" height="{h}" rx="16" fill="{fill}" stroke="{border}" stroke-width="2.4"/>'
        b += t(772, y + 52, home, 25, MONO, ink, 600)
        b += t(772, y + 92, where, 15.5, MONO, ink if ink == CREMA else MUTED)

    # bracket into the agent
    y0, y1 = top + 14, top + 3 * step + h - 14
    ym = (y0 + y1) / 2
    b += f'<path d="M1256 {y0}h24v{y1 - y0}h-24" fill="none" stroke="{ESPRESSO}" stroke-width="2.6"/>'
    b += f'<line x1="1280" y1="{ym}" x2="1402" y2="{ym}" stroke="{ESPRESSO}" stroke-width="2.6"/>'
    b += f'<path d="M1416 {ym}l-16 -8v16z" fill="{ESPRESSO}"/>'
    b += t(1292, ym - 60, "through ktx,", 14, MONO, ESPRESSO, 600)
    b += t(1292, ym - 40, "or straight", 14, MONO, ESPRESSO, 600)
    b += t(1292, ym - 20, "from the repo", 14, MONO, ESPRESSO, 600)

    # the agent
    b += f'<rect x="1420" y="{ym - 150}" width="136" height="300" rx="18" fill="{BAKSTEEN}"/>'
    b += t(1488, ym - 18, "ONE", 20, MONO, CREMA, 700, "middle", spacing=1.5)
    b += t(1488, ym + 10, "AGENT", 20, MONO, CREMA, 700, "middle", spacing=1.5)
    b += t(1488, ym + 50, "Claude Code", 13, MONO, HONING, 500, "middle")
    b += t(1488, ym + 70, "in the demo", 13, MONO, HONING, 500, "middle")
    return dm.frame(b, "Four kinds of knowledge, four homes", "THE KIND OF KNOWLEDGE DECIDES WHERE IT LIVES",
                    "All four are in Kelder's with-context repo and warehouse. None of them needs a new tool.",
                    badge="KELDER KOFFIE · WITH CONTEXT")


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "knowledge_homes.svg").write_text(build())
    print("wrote charts/out/knowledge_homes.svg")


if __name__ == "__main__":
    main()
