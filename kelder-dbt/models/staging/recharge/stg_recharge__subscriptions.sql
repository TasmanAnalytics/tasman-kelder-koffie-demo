select
    s.id as recharge_subscription_id,
    s.customer_id as recharge_customer_id,
    c.shopify_customer_id,
    try_cast(s.external_contract_id as bigint) as shopify_contract_id,
    s.shopify_variant_id as variant_id,
    s.sku,
    s.quantity,
    cast(s.price as double) as price_eur,
    case s.order_interval_unit
        when 'week' then s.order_interval_frequency * 7
        when 'day' then s.order_interval_frequency
    end as interval_days,
    s.status as source_status,
    s.created_at,
    s.updated_at,
    s.cancelled_at,
    s.cancellation_reason,
    s.cancellation_reason_comments,
    s.next_charge_scheduled_at,
    s.paused_until,
    s.is_prepaid,
    coalesce(cast(json_extract(s.properties, '$.is_gift') as boolean), false) as is_gift,
    json_extract_string(s.properties, '$.restore_source') as restore_source,
    try_cast(json_extract_string(s.properties, '$.legacy_contract_id') as bigint) as legacy_contract_id,
    s._fivetran_synced as synced_at
from {{ source('recharge', 'subscriptions') }} as s
left join {{ ref('stg_recharge__customers') }} as c on c.recharge_customer_id = s.customer_id
where not s._fivetran_deleted
