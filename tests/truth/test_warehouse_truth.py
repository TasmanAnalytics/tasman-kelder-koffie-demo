"""Warehouse metrics equal the hidden ground truth (brief sections 2 and 3.5).

with-context: adjusted metrics equal the truth exactly, numerator and denominator.
before-context: reproduces the raw record, so March shows 9.4%.
rot: the restated series breaks and the year-on-year conclusion flips.
"""

import pandas as pd
import pytest

from conftest import warehouse

MONTHS = ("2025-01-01", "2026-06-01")


@pytest.fixture(scope="module")
def truth_monthly(truth):
    df = truth.execute("select * from metrics_monthly where month <= '2026-06'").df()
    df["month"] = pd.to_datetime(df.month + "-01")
    return df.set_index("month")


def _churn(state):
    con = warehouse(state)
    df = con.execute("select * from main.metrics_subscriber_churn_monthly").df()
    con.close()
    df["month"] = pd.to_datetime(df.month)
    return df.set_index("month")


@pytest.fixture(scope="module")
def wc():
    return _churn("with_context")


def test_with_context_base_equals_truth(wc, truth_monthly):
    pd.testing.assert_series_equal(wc.base_subscribers, truth_monthly.base, check_names=False, check_dtype=False)
    pd.testing.assert_series_equal(wc.base_subscribers_v2_restated, truth_monthly.base, check_names=False, check_dtype=False)


def test_with_context_v1_numerator_equals_truth(wc, truth_monthly):
    pd.testing.assert_series_equal(wc.churned_subscribers_v1, truth_monthly.churned_v1, check_names=False, check_dtype=False)


def test_with_context_restated_v2_numerator_equals_truth_as_of(wc, truth_monthly):
    pd.testing.assert_series_equal(wc.churned_subscribers_v2_restated, truth_monthly.churned_v2_asof, check_names=False, check_dtype=False)


def test_with_context_as_reported_equals_truth(wc, truth_monthly):
    expected = truth_monthly.churned_v1.where(truth_monthly.index < "2026-05-01", truth_monthly.churned_v2_asof)
    pd.testing.assert_series_equal(wc.churned_subscribers, expected, check_names=False, check_dtype=False)
    assert (wc.definition_version_as_reported == ["v1"] * 16 + ["v2"] * 2).all()


def test_with_context_rates_are_numerator_over_base(wc):
    assert (wc.churn_rate_v2_restated - (wc.churned_subscribers_v2_restated / wc.base_subscribers_v2_restated)).abs().max() < 1e-6


def test_march_raw_and_adjusted_in_with_context(wc):
    m = wc.loc["2026-03-01"]
    assert round(m.churn_rate_as_reported * 100, 1) == 3.3
    assert round(m.churn_rate_as_reported_raw * 100, 1) == 9.4


def test_only_latest_month_is_provisional(wc):
    assert wc.is_provisional.sum() == 1 and wc.is_provisional.loc["2026-06-01"]


def test_with_context_new_subscribers_equal_truth(truth_monthly):
    con = warehouse("with_context")
    df = con.execute("select month, new_subscribers from main.metrics_new_subscribers_monthly").df()
    df["month"] = pd.to_datetime(df.month)
    pd.testing.assert_series_equal(df.set_index("month").new_subscribers, truth_monthly.new_subscribers, check_names=False, check_dtype=False)


def test_with_context_pause_metrics_equal_truth(truth_monthly):
    con = warehouse("with_context")
    df = con.execute("select * from main.metrics_pause_rate_monthly").df()
    df["month"] = pd.to_datetime(df.month)
    df = df.set_index("month")
    pd.testing.assert_series_equal(df.pauses_started, truth_monthly.pause_starts, check_names=False, check_dtype=False)
    pd.testing.assert_series_equal(df.paused_at_month_start, truth_monthly.paused_count, check_names=False, check_dtype=False)


def test_email_attribution_equals_truth(truth):
    con = warehouse("with_context")
    wh = con.execute("select day, attributed_orders, attributed_revenue_eur from main.metrics_email_attribution_daily").df()
    t = truth.execute("select day, orders_observed, revenue_observed, revenue_world from email_attribution_daily").df()
    m = wh.merge(t, on="day", how="left").fillna(0)
    assert (m.attributed_orders == m.orders_observed).all()
    assert (m.attributed_revenue_eur - m.revenue_observed).abs().max() < 0.01
    april = m[(pd.to_datetime(m.day) >= "2026-04-01") & (pd.to_datetime(m.day) < "2026-05-01")]
    assert april.revenue_world.sum() > 1.1 * april.attributed_revenue_eur.sum()


def test_flags_equal_truth(truth):
    con = warehouse("with_context")
    art = con.execute("select count(*) from main.fct_subscriptions where is_migration_artifact").fetchone()[0]
    rest = con.execute("select count(*) from main.fct_subscriptions where is_legacy_pause_restore").fetchone()[0]
    assert art == truth.execute("select count(*) from id_map where is_migration_artifact").fetchone()[0]
    assert rest == truth.execute("select count(recharge_restore_subscription_id) from id_map").fetchone()[0]
    keys = con.execute("select continues_subscription_key from main.fct_subscriptions where is_legacy_pause_restore").df()
    flagged = set(con.execute("select subscription_key from main.fct_subscriptions where is_migration_artifact").df().subscription_key)
    assert set(keys.continues_subscription_key) <= flagged


def test_before_context_shows_the_raw_record(truth_monthly):
    b = _churn("before")
    m = b.loc["2026-03-01"]
    assert round(m.churn_rate * 100, 1) == 9.4
    pd.testing.assert_series_equal(b.base_subscribers.loc[:"2026-03-01"], truth_monthly.base.loc[:"2026-03-01"], check_names=False, check_dtype=False)
    con = warehouse("before")
    new = con.execute("select sum(new_subscribers) from main.metrics_new_subscribers_monthly where month >= '2026-03-01'").fetchone()[0]
    assert new > truth_monthly.new_subscribers.loc["2026-03-01":].sum() + 1000  # restores counted as new


def test_before_context_has_no_context_layer():
    con = warehouse("before")
    schemas = {r[0] for r in con.execute("select schema_name from duckdb_schemas()").fetchall()}
    assert "context" not in schemas
    cols = {r[0] for r in con.execute("select column_name from duckdb_columns()").fetchall()}
    assert not {"is_migration_artifact", "is_legacy_pause_restore"} & cols


def test_rot_restated_march_jumps_about_six_points(wc):
    rot = _churn("rot")
    jump = (rot.churn_rate_v2_restated - wc.churn_rate_v2_restated).loc["2026-03-01"] * 100
    assert 5.5 <= jump <= 6.5, jump


def test_rot_flips_the_year_on_year_conclusion(wc):
    rot = _churn("rot")
    for df, better in ((wc, True), (rot, False)):
        h25 = df.churn_rate_v2_restated.loc["2025-01-01":"2025-06-01"].mean()
        h26 = df.churn_rate_v2_restated.loc["2026-01-01":"2026-06-01"].mean()
        assert (h26 < h25) == better
        if better:
            assert 0.3 <= (h25 - h26) * 100 <= 0.8


def test_rot_leaves_the_as_reported_series_alone(wc):
    rot = _churn("rot")
    cols = ["churned_subscribers", "churn_rate_as_reported", "churn_rate_as_reported_raw", "churn_rate_v1"]
    pd.testing.assert_frame_equal(rot[cols], wc[cols])
