"""Written context stays consistent with its sources in the with-context and rot states."""

import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent.parent


@pytest.mark.parametrize("state", ["with_context", "rot"])
def test_metric_changelog_markdown_matches_seed(state):
    project = ROOT / "build" / state / "kelder-dbt"
    if not project.exists():
        pytest.skip(f"{state} not built")
    r = subprocess.run([sys.executable, "scripts/render_metric_changelog.py", "--check"], cwd=project, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_core_fact_is_findable_everywhere():
    """12 March 2026 migration, ~1,900 paused subscriptions written as cancelled: in the caveat,
    business_events, decision 0007, the March verified query and AGENTS.md."""
    p = ROOT / "build" / "with_context" / "kelder-dbt"
    if not p.exists():
        pytest.skip("with_context not built")
    places = {
        "caveat": (p / "models" / "marts" / "_marts__models.yml").read_text(),
        "business_events": (p / "seeds" / "context" / "business_events.csv").read_text(),
        "decision_0007": (p / "context" / "decisions" / "0007-recharge-migration-churn-artifacts.md").read_text(),
        "verified_query": (p / "context" / "verified_queries.yml").read_text().split("id: churn_march_2026")[1].split("- id:")[0],
        "agents_md": (p / "AGENTS.md").read_text(),
    }
    for name, text in places.items():
        t = text.lower()
        assert "1,900" in t, name
        assert "paused" in t and "cancelled" in t, name
        assert ("12 march" in t or "2026-03-12" in t or "12 mar" in t), name
