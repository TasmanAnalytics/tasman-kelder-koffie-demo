select
    id as billing_attempt_id,
    contract_id,
    created_at as attempted_at,
    completed_at,
    error_code,
    error_message,
    error_code is null as is_success,
    order_id,
    idempotency_key,
    -- key format: kelder-<contract id>-<billing cycle yyyymmdd>-<attempt number>
    strptime(split_part(idempotency_key, '-', 3), '%Y%m%d')::date as billing_cycle_date,
    cast(split_part(idempotency_key, '-', 4) as integer) as attempt_number
from {{ source('shopify', 'subscription_billing_attempts') }}
where not _fivetran_deleted
