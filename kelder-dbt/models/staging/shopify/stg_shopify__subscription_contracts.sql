select
    id as contract_id,
    customer_id,
    status as source_status,
    created_at,
    updated_at,
    next_billing_date,
    billing_interval,
    billing_interval_count,
    case billing_interval
        when 'WEEK' then billing_interval_count * 7
        when 'DAY' then billing_interval_count
    end as interval_days,
    line_variant_id as variant_id,
    line_quantity as quantity,
    paused_at,
    pause_until,
    cancelled_at,
    cancellation_reason,
    coalesce(cast(json_extract(custom_attributes, '$.is_gift') as boolean), false) as is_gift,
    json_extract_string(custom_attributes, '$.grind') as grind,
    json_extract_string(custom_attributes, '$.payment_method') as payment_method,
    origin_order_id,
    _fivetran_synced as synced_at
from {{ source('shopify', 'subscription_contracts') }}
where not _fivetran_deleted
