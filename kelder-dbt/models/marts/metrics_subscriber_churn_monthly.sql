-- Governed monthly subscriber churn. Definitions: context/glossary.md.
-- Two event streams feed it. Adjusted excludes the 2026-03-12 migration artefacts (decision 0007)
-- and is the number to report. Unadjusted counts them, and matches Recharge exports for finance.

with months as (
    select * from {{ ref('int_reporting_months') }}
),

adjusted_events as (
    select * from {{ ref('int_subscription_events_adjusted') }}
    where not is_gift
),

unadjusted_events as (
    select * from {{ ref('int_subscription_events') }}
    where not is_gift
),
{% for stream in ['adjusted', 'unadjusted'] %}
spans_{{ stream }} as (
    select
        subscription_key,
        min(case when event_type = 'started' then occurred_at end) as started_at,
        min(case when event_type in ('cancelled', 'expired') then occurred_at end) as ended_at
    from {{ stream }}_events
    group by 1
),

base_{{ stream }} as (
    select m.month, count(s.subscription_key) as base_subscribers
    from months as m
    left join spans_{{ stream }} as s
        on s.started_at < m.month_start
        and (s.ended_at is null or s.ended_at >= m.month_start)
    group by 1
),

churn_{{ stream }} as (
    select
        event_month as month,
        count(distinct case when event_type = 'cancelled' and is_voluntary_cancellation then subscription_key end)
            as voluntary_cancellations,
        count(distinct case when event_type = 'payment_failed' then subscription_key end) as failed_payments
    from {{ stream }}_events
    group by 1
),

series_{{ stream }} as (
    select
        m.month,
        b.base_subscribers,
        coalesce(c.voluntary_cancellations, 0) + coalesce(c.failed_payments, 0) as churned_v1
    from months as m
    left join base_{{ stream }} as b using (month)
    left join churn_{{ stream }} as c using (month)
),
{% endfor %}
final as (
    select
        m.month,
        a.base_subscribers,
        a.churned_v1 as churned_subscribers,
        round(a.churned_v1 / a.base_subscribers, 6) as churn_rate,
        u.base_subscribers as base_subscribers_raw,
        u.churned_v1 as churned_subscribers_raw,
        round(u.churned_v1 / u.base_subscribers, 6) as churn_rate_raw
    from months as m
    join series_adjusted as a using (month)
    join series_unadjusted as u using (month)
)

select * from final
order by month
