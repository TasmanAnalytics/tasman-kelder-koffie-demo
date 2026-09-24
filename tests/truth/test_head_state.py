"""CI: the pull request's head state must still equal the ground truth (adjusted metrics)."""

import pandas as pd
import pytest

from conftest import WAREHOUSE, warehouse


@pytest.mark.skipif(not (WAREHOUSE / "kelder_head.duckdb").exists(), reason="head state not built (CI only)")
def test_head_state_churn_equals_truth(truth):
    t = truth.execute("select month, base, churned_v1, churned_v2_asof from metrics_monthly where month <= '2026-06'").df()
    t["month"] = pd.to_datetime(t.month + "-01")
    con = warehouse("head")
    h = con.execute("select * from main.metrics_subscriber_churn_monthly").df()
    h["month"] = pd.to_datetime(h.month)
    m = h.merge(t, on="month")
    assert (m.base_subscribers_v2_restated == m.base).all()
    assert (m.churned_subscribers_v2_restated == m.churned_v2_asof).all()
    assert (m.churned_subscribers_v1 == m.churned_v1).all()
