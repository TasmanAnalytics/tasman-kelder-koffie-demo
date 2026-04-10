-- Email-attributed revenue: Klaviyo Placed Order value where the same profile clicked an email
-- in the five days before the order.
-- The Fivetran Klaviyo connector was down from 2026-04-09 06:00 UTC to 2026-04-10 13:00 UTC and
-- never backfilled (context.business_events). Days touched by the gap are flagged incomplete.

with days as (
    select cast(d as date) as day
    from range(date '{{ var("first_reporting_month") }}', date '{{ var("as_of_date") }}', interval 1 day) as t(d)
),

events as (
    select * from {{ ref('stg_klaviyo__events') }}
),

placed as (
    select event_id, profile_id, occurred_at, value_eur from events where metric_name = 'Placed Order'
),

clicks as (
    select profile_id, occurred_at as clicked_at from events where metric_name = 'Clicked Email'
),

attributed as (
    select
        p.*,
        c.clicked_at is not null and p.occurred_at - c.clicked_at <= interval 5 day as is_attributed
    from placed as p
    asof left join clicks as c
        on p.profile_id = c.profile_id and p.occurred_at >= c.clicked_at
),

daily as (
    select
        {{ local_date('occurred_at') }} as day,
        count(*) as placed_orders,
        sum(value_eur) as placed_order_revenue_eur,
        count(case when is_attributed then 1 end) as attributed_orders,
        sum(case when is_attributed then value_eur else 0 end) as attributed_revenue_eur
    from attributed
    group by 1
),

email_activity as (
    select
        {{ local_date('occurred_at') }} as day,
        count(case when metric_name = 'Received Email' then 1 end) as emails_received,
        count(case when metric_name = 'Opened Email' then 1 end) as emails_opened,
        count(case when metric_name = 'Clicked Email' then 1 end) as emails_clicked
    from events
    group by 1
)

select
    d.day,
    d.day between date '2026-04-09' and date '2026-04-15' as is_incomplete,
    coalesce(a.emails_received, 0) as emails_received,
    coalesce(a.emails_opened, 0) as emails_opened,
    coalesce(a.emails_clicked, 0) as emails_clicked,
    coalesce(x.placed_orders, 0) as placed_orders,
    round(coalesce(x.placed_order_revenue_eur, 0), 2) as placed_order_revenue_eur,
    coalesce(x.attributed_orders, 0) as attributed_orders,
    round(coalesce(x.attributed_revenue_eur, 0), 2) as attributed_revenue_eur
from days as d
left join daily as x using (day)
left join email_activity as a using (day)
order by 1
