select
    id as charge_id,
    customer_id as recharge_customer_id,
    subscription_id as recharge_subscription_id,
    status,
    scheduled_at,
    processed_at,
    cast(total_price as double) as total_price_eur,
    error_type,
    retry_date,
    number_times_tried,
    external_order_id as order_id,
    {{ local_date('scheduled_at') }} as billing_cycle_date
from {{ source('recharge', 'charges') }}
where not _fivetran_deleted
