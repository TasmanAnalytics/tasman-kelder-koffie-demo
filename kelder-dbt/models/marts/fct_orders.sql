with orders as (
    select * from {{ ref('stg_shopify__orders') }}
),

lines as (
    select
        l.order_id,
        bool_or(v.product_type = 'gift_box') as contains_gift_box,
        bool_or(v.product_type = 'bundle') as contains_bundle,
        sum(l.quantity) as items
    from {{ ref('stg_shopify__order_lines') }} as l
    left join {{ ref('stg_shopify__product_variants') }} as v using (variant_id)
    group by 1
),

refunds as (
    select order_id, sum(refund_amount_eur) as refunded_eur, min(refunded_at) as first_refunded_at
    from {{ ref('stg_shopify__refunds') }}
    group by 1
),

shipments as (
    select order_id, min(shipped_at) as shipped_at, min(delivered_at) as delivered_at, any_value(carrier) as carrier,
           bool_or(fulfillment_status = 'failure') as has_failed_delivery
    from {{ ref('stg_shopify__fulfillments') }}
    group by 1
)

select
    o.order_id,
    o.order_name,
    o.customer_id,
    o.created_at,
    {{ local_date('o.created_at') }} as order_date,
    o.source_name,
    o.channel,
    o.is_subscription_first_order or o.is_subscription_renewal as is_subscription_order,
    o.is_subscription_first_order,
    o.is_subscription_renewal,
    o.is_gift_subscription_order or coalesce(l.contains_gift_box, false) as is_gift,
    coalesce(l.contains_bundle, false) as contains_bundle,
    l.items,
    o.subtotal_price_eur,
    o.total_discounts_eur,
    o.total_tax_eur,
    o.total_price_eur,
    coalesce(r.refunded_eur, 0) > 0 as is_refunded,
    coalesce(r.refunded_eur, 0) as refunded_eur,
    r.first_refunded_at,
    s.carrier,
    s.shipped_at,
    s.delivered_at,
    coalesce(s.has_failed_delivery, false) as has_failed_delivery,
    date_diff('day', {{ local_date('s.shipped_at') }}, {{ local_date('s.delivered_at') }}) as delivery_days
from orders as o
left join lines as l using (order_id)
left join refunds as r using (order_id)
left join shipments as s using (order_id)
