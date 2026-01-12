-- Customer acquisition cost for paid channels: ad spend over new subscribers whose first
-- order came through that channel (UTM parameters on the first order).

with months as (
    select * from {{ ref('int_reporting_months') }}
),

channels as (
    select * from (values ('paid_social', 'meta'), ('paid_search', 'google')) as t(channel, platform)
),

spend as (
    select cast(date_trunc('month', spend_date) as date) as month, channel, sum(spend_eur) as ad_spend_eur
    from {{ ref('stg_ads__ad_spend_daily') }}
    group by 1, 2
),

new_subs as (
    select {{ local_month('started_at') }} as month, first_order_channel as channel, count(*) as new_subscribers
    from {{ ref('fct_subscriptions') }}
    where not is_gift
    group by 1, 2
)

select
    m.month,
    c.channel,
    c.platform,
    round(coalesce(s.ad_spend_eur, 0), 2) as ad_spend_eur,
    coalesce(n.new_subscribers, 0) as new_subscribers,
    round(s.ad_spend_eur / nullif(n.new_subscribers, 0), 2) as cac_eur
from months as m
cross join channels as c
left join spend as s on s.month = m.month and s.channel = c.channel
left join new_subs as n on n.month = m.month and n.channel = c.channel
order by 1, 2
