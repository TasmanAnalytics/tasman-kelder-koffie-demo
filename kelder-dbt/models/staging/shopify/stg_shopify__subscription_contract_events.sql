select
    id as contract_event_id,
    contract_id,
    event_type,
    occurred_at,
    json_extract_string(detail, '$.reason') as reason,
    try_cast(json_extract_string(detail, '$.pause_until') as date) as pause_until,
    json_extract_string(detail, '$.error_code') as error_code,
    try_cast(json_extract_string(detail, '$.order_id') as bigint) as order_id
from {{ source('shopify', 'subscription_contract_events') }}
where not _fivetran_deleted
