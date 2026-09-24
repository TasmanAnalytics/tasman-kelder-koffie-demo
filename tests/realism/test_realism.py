"""Distribution shape checks on the raw data (brief section 5.7)."""

import pandas as pd

AMS = "Europe/Amsterdam"


def _retail(raw):
    return """from shopify.orders where source_name = 'web'
              and coalesce(tags, '') not in ('Subscription First Order', 'Gift Subscription')"""


def test_retail_orders_follow_the_human_hour_profile(raw):
    df = raw.execute(f"select hour(timezone('{AMS}', created_at)) h, count(*) n {_retail(raw)} group by 1").df().set_index("h").n
    trough = df.reindex([2, 3, 4]).fillna(0).mean()
    for h in (7, 8, 19, 20, 21):
        assert df.get(h, 0) > 2 * trough, (h, df.get(h, 0), trough)


def test_subscription_orders_are_created_at_the_morning_run(raw):
    share = raw.execute(f"""select avg(case when strftime(timezone('{AMS}', created_at), '%H:%M') between '05:00' and '05:29' then 1 else 0 end)
                            from shopify.orders where source_name in ('subscription_contract', 'recharge')""").fetchone()[0]
    assert share > 0.90


def test_february_voluntary_cancellations_spread_over_the_day(raw):
    df = raw.execute(f"""select hour(occurred_at) h, count(*) n from shopify.subscription_contract_events
                         where event_type = 'cancelled' and json_extract_string(detail, '$.reason') <> 'max_retries_reached'
                         and timezone('{AMS}', occurred_at) >= timestamp '2026-02-01' and timezone('{AMS}', occurred_at) < timestamp '2026-03-01'
                         group by 1""").df()
    assert df.n.sum() > 300
    assert (df.n / df.n.sum()).max() <= 0.12


def test_march_cancellations_cluster_at_midnight_utc(raw):
    df = raw.execute(f"""
        with c as (
            select occurred_at as t from shopify.subscription_contract_events where event_type = 'cancelled'
            union all
            select cancelled_at from recharge.subscriptions where cancelled_at is not null
        )
        select hour(t) h, count(*) n from c
        where timezone('{AMS}', t) >= timestamp '2026-03-01' and timezone('{AMS}', t) < timestamp '2026-04-01' group by 1""").df()
    share = df.set_index("h").n.get(0, 0) / df.n.sum()
    assert share > 0.60, share


def test_retail_orders_by_weekday(raw):
    df = raw.execute(f"select isodow(timezone('{AMS}', created_at)) d, count(*) n {_retail(raw)} group by 1").df()
    assert df.n.max() >= 1.15 * df.n.min()


def test_cohort_survival_and_tenure_hazard(truth):
    df = truth.execute("""
        with s as (
            select world_subscription_id id, min(valid_from) as started,
                   min(case when true_status in ('cancelled', 'expired') then valid_from end) term
            from subscription_episodes group by 1
        ), g as (select world_subscription_id id from id_map where not is_gift)
        select date_diff('day', started, coalesce(term, timestamptz '2026-07-01')) as days, term is not null as ended
        from s join g using (id)
        where started >= timestamptz '2025-01-01' and started < timestamptz '2025-10-01'
    """).df()
    ended = df[df.ended]
    months = (ended.days // 30.44).astype(int) + 1
    alive = [(df.days >= (k - 1) * 30.44).sum() for k in range(1, 10)]
    events = [(months == k).sum() for k in range(1, 10)]
    hazard = [e / a for e, a in zip(events, alive)]
    survival = pd.Series(alive) / alive[0]
    assert (survival.diff().dropna() <= 0).all()
    assert hazard[0] > 1.8 * hazard[5], hazard


def test_december_retail_peak(raw):
    df = raw.execute(f"select strftime(timezone('{AMS}', created_at), '%Y-%m') m, count(*) n {_retail(raw)} group by 1").df().set_index("m").n
    assert df["2025-12"] >= 1.8 * df.median()


def test_klaviyo_outage_window_is_empty_and_neighbours_are_normal(raw):
    n = raw.execute("""select count(*) from klaviyo.events
                       where timestamp >= timestamptz '2026-04-09 06:00:00+00' and timestamp < timestamptz '2026-04-10 13:00:00+00'""").fetchone()[0]
    assert n == 0
    daily = raw.execute(f"select cast(timezone('{AMS}', timestamp) as date) d, count(*) n from klaviyo.events group by 1").df()
    daily["d"] = pd.to_datetime(daily.d)
    s = daily.set_index("d").n
    for day in ("2026-04-08", "2026-04-11"):
        t = pd.Timestamp(day)
        ref = s.reindex([t - pd.Timedelta(days=7 * k) for k in (1, 2, 3)]).mean()
        assert abs(s[t] / ref - 1) <= 0.30, (day, s[t], ref)


def test_every_email_is_example_dot_com(raw):
    for q in ("select email from shopify.customers", "select email from recharge.customers", "select email from klaviyo.profiles"):
        bad = raw.execute(f"select count(*) from ({q}) where email not like '%@example.com'").fetchone()[0]
        assert bad == 0, q
