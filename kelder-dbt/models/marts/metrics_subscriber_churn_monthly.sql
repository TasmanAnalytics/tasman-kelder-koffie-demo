with months as (
    select * from {{ ref('int_reporting_months') }}
),

events as (
    select * from {{ ref('int_subscription_events') }}
    where not is_gift
),

spans as (
    select
        subscription_key,
        min(case when event_type = 'started' then occurred_at end) as started_at,
        min(case when event_type in ('cancelled', 'expired') then occurred_at end) as ended_at
    from events
    group by 1
),

base as (
    select m.month, count(s.subscription_key) as base_subscribers
    from months as m
    left join spans as s
        on s.started_at < m.month_start
        and (s.ended_at is null or s.ended_at >= m.month_start)
    group by 1
),

cancellations as (
    select event_month as month, count(distinct subscription_key) as voluntary_cancellations
    from events
    where event_type = 'cancelled' and is_voluntary_cancellation
    group by 1
),

failed_payments as (
    select event_month as month, count(distinct subscription_key) as failed_payments
    from events
    where event_type = 'payment_failed'
    group by 1
),

monthly as (
    select
        m.month,
        b.base_subscribers,
        coalesce(c.voluntary_cancellations, 0) as voluntary_cancellations,
        coalesce(f.failed_payments, 0) as involuntary_churn
    from months as m
    left join base as b using (month)
    left join cancellations as c using (month)
    left join failed_payments as f using (month)
)

select
    month,
    base_subscribers,
    voluntary_cancellations + involuntary_churn as churned_subscribers,
    round((voluntary_cancellations + involuntary_churn) / base_subscribers, 6) as churn_rate
from monthly
order by month
