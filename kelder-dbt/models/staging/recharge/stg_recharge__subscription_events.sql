select
    id as recharge_event_id,
    subscription_id as recharge_subscription_id,
    verb,
    created_at as occurred_at,
    json_extract_string(payload, '$.cancellation_reason') as cancellation_reason,
    try_cast(json_extract_string(payload, '$.paused_until') as date) as paused_until,
    json_extract_string(payload, '$.source') as pause_source
from {{ source('recharge', 'subscription_events') }}
where not _fivetran_deleted
