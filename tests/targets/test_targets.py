"""The generated data hits every number in 'Numbers that must reconcile' (brief section 3.5)."""

import pytest

STAMP = "2026-03-12 00:00:00+00"


def test_every_target_in_truth_passes(truth):
    rows = truth.execute("select target, expected, achieved, passed from targets").fetchall()
    assert len(rows) >= 28
    failed = [r for r in rows if not r[3]]
    assert not failed, failed


def _migration_counts(raw, contract_status):
    return raw.execute(f"""
        select count(*) from recharge.subscriptions s
        join shopify.subscription_contracts c on s.external_contract_id = cast(c.id as varchar)
        where s.cancelled_at = timestamptz '{STAMP}' and s.cancellation_reason is null and c.status = '{contract_status}'
    """).fetchone()[0]


def test_migration_artefacts_in_raw_data(raw, truth):
    n = _migration_counts(raw, "PAUSED")
    assert 1880 <= n <= 1920
    assert n == truth.execute("select count(*) from id_map where is_migration_artifact").fetchone()[0]


def test_queued_genuine_cancellations_in_raw_data(raw):
    assert 120 <= _migration_counts(raw, "ACTIVE") <= 180


def test_nothing_else_carries_the_midnight_stamp(raw):
    total = raw.execute(f"select count(*) from recharge.subscriptions where cancelled_at = timestamptz '{STAMP}'").fetchone()[0]
    assert total == _migration_counts(raw, "PAUSED") + _migration_counts(raw, "ACTIVE")


def test_base_on_1_march_2026(truth):
    base = truth.execute("select base from metrics_monthly where month = '2026-03'").fetchone()[0]
    assert abs(base - 31200) <= 150


def test_base_on_1_january_2025(truth):
    base = truth.execute("select base from metrics_monthly where month = '2025-01'").fetchone()[0]
    assert abs(base - 20000) <= 300


def test_march_raw_and_adjusted(truth):
    base, churned = truth.execute("select base, churned_v1 from metrics_monthly where month = '2026-03'").fetchone()
    a = truth.execute("select count(*) from id_map where is_migration_artifact").fetchone()[0]
    raw_rate, adj_rate = (churned + a) / base, churned / base
    assert 0.0937 <= raw_rate <= 0.0943 and round(raw_rate * 100, 1) == 9.4
    assert 0.0327 <= adj_rate <= 0.0333 and round(adj_rate * 100, 1) == 3.3


@pytest.mark.parametrize("month,target", [
    ("2025-01", 3.7), ("2025-02", 3.5), ("2025-03", 3.4), ("2025-04", 3.3), ("2025-05", 3.3), ("2025-06", 3.2),
    ("2025-07", 3.4), ("2025-08", 3.4), ("2025-09", 3.1), ("2025-10", 3.0), ("2025-11", 3.0), ("2025-12", 3.1),
    ("2026-01", 3.4), ("2026-02", 3.0), ("2026-03", 3.3), ("2026-04", 2.8), ("2026-05", 2.9), ("2026-06", 2.8),
])
def test_monthly_v1_adjusted(truth, month, target):
    v = truth.execute("select churn_v1 from metrics_monthly where month = ?", [month]).fetchone()[0]
    assert abs(v * 100 - target) <= 0.02


def test_trailing_mean_sep_to_feb(truth):
    v = truth.execute("select avg(churn_v1) from metrics_monthly where month between '2025-09' and '2026-02'").fetchone()[0]
    assert round(v * 100, 1) == 3.1


def test_v1_minus_restated_v2_q1_2026(truth):
    v = truth.execute("select avg(churn_v1 - churn_v2_asof) * 100 from metrics_monthly where month between '2026-01' and '2026-03'").fetchone()[0]
    assert 0.4 <= v <= 0.7


def test_as_reported_may_below_april(truth):
    apr = truth.execute("select churn_v1 from metrics_monthly where month = '2026-04'").fetchone()[0]
    may = truth.execute("select churn_v2_asof from metrics_monthly where month = '2026-05'").fetchone()[0]
    assert may < apr


def test_restated_v2_first_half_improvement(truth):
    h25 = truth.execute("select avg(churn_v2_asof) from metrics_monthly where month between '2025-01' and '2025-06'").fetchone()[0]
    h26 = truth.execute("select avg(churn_v2_asof) from metrics_monthly where month between '2026-01' and '2026-06'").fetchone()[0]
    assert 0.3 <= (h25 - h26) * 100 <= 0.8


def test_june_is_provisional_in_the_truth(truth):
    final, asof = truth.execute("select churn_v2_final, churn_v2_asof from metrics_monthly where month = '2026-06'").fetchone()
    assert asof < final
