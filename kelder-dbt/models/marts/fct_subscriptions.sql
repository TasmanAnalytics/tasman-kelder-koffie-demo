with subs as (
    select * from {{ ref('int_subscriptions_unified') }}
),

orders as (
    select order_id, channel from {{ ref('stg_shopify__orders') }}
),

variants as (
    select variant_id, sku, product_title from {{ ref('stg_shopify__product_variants') }}
)

select
    s.subscription_key,
    s.customer_id,
    s.origin_system,
    s.shopify_contract_id,
    s.recharge_subscription_id,
    s.started_at,
    s.churned_at,
    s.ended_at,
    s.status,
    s.cancellation_reason,
    s.is_gift,
    s.interval_days,
    s.quantity,
    s.variant_id,
    v.sku,
    v.product_title,
    s.price_eur,
    case
        when s.is_gift then 0.0
        when s.status = 'active' then round(s.price_eur * 365.25 / 12 / s.interval_days, 2)
        else 0.0
    end as mrr_eur,
    s.payment_method,
    s.origin_order_id,
    o.channel as first_order_channel,
    s.is_migration_artifact
from subs as s
left join orders as o on o.order_id = s.origin_order_id
left join variants as v on v.variant_id = s.variant_id
