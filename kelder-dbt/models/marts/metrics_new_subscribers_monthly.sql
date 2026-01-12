with months as (
    select * from {{ ref('int_reporting_months') }}
),

subs as (
    select * from {{ ref('fct_subscriptions') }}
    where not is_gift
)

select
    m.month,
    count(s.subscription_key) as new_subscribers,
    count(case when s.first_order_channel in ('paid_social', 'paid_search') then 1 end) as new_subscribers_paid,
    count(case when s.first_order_channel not in ('paid_social', 'paid_search') then 1 end) as new_subscribers_unpaid,
    count(case when s.first_order_channel is null then 1 end) as new_subscribers_without_web_order
from months as m
left join subs as s
    on s.started_at >= m.month_start and s.started_at < m.month_end
group by 1
order by 1
