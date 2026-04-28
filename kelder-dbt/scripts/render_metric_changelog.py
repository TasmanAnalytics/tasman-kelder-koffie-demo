"""Render seeds/context/metric_changelog.csv to context/metric_changelog.md.

Run from the repository root: python scripts/render_metric_changelog.py
CI fails if the markdown and the seed disagree (run with --check).
"""

import csv
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SEED = ROOT / "seeds" / "context" / "metric_changelog.csv"
OUT = ROOT / "context" / "metric_changelog.md"


def render() -> str:
    rows = list(csv.DictReader(open(SEED, newline="")))
    lines = [
        "# Metric changelog",
        "",
        "Generated from `seeds/context/metric_changelog.csv` by `scripts/render_metric_changelog.py`.",
        "Do not edit by hand. The same rows are in the warehouse as `context.metric_changelog`.",
        "",
    ]
    for metric in sorted({r["metric"] for r in rows}):
        lines += [f"## {metric}", "", "| Version | Valid from | Definition | Reason for change |", "|---|---|---|---|"]
        for r in sorted((r for r in rows if r["metric"] == metric), key=lambda r: r["valid_from"]):
            lines.append(f"| {r['version']} | {r['valid_from']} | {r['definition']} | {r['reason_for_change']} |")
        lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    text = render()
    if "--check" in sys.argv:
        if not OUT.exists() or OUT.read_text() != text:
            sys.exit("context/metric_changelog.md is out of date: run scripts/render_metric_changelog.py")
        print("metric_changelog.md matches the seed")
    else:
        OUT.write_text(text)
        print(f"wrote {OUT.relative_to(ROOT)}")
