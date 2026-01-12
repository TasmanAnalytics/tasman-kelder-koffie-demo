with customers as (
    select * from {{ ref('stg_shopify__customers') }}
),

orders as (
    select customer_id, order_id, created_at, channel
    from {{ ref('stg_shopify__orders') }}
    where source_name = 'web'
),

first_orders as (
    select customer_id, created_at as first_order_at, channel as first_order_channel
    from orders
    qualify row_number() over (partition by customer_id order by created_at, order_id) = 1
),

order_counts as (
    select customer_id, count(*) as web_orders from orders group by 1
),

subs as (
    select customer_id, count(*) as subscriptions, bool_or(status in ('active', 'paused') and not is_gift) as is_active_subscriber
    from {{ ref('int_subscriptions_unified') }}
    group by 1
)

select
    c.customer_id,
    c.email,
    c.first_name,
    c.last_name,
    c.country_code,
    k.country_name,
    k.region,
    c.created_at,
    c.accepts_marketing,
    f.first_order_at,
    f.first_order_channel,
    coalesce(n.web_orders, 0) as web_orders,
    coalesce(s.subscriptions, 0) as subscriptions,
    coalesce(s.is_active_subscriber, false) as is_active_subscriber
from customers as c
left join {{ ref('countries') }} as k using (country_code)
left join first_orders as f using (customer_id)
left join order_counts as n using (customer_id)
left join subs as s using (customer_id)
