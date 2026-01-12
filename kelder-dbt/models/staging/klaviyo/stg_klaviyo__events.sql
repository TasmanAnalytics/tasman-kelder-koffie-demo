select
    id as event_id,
    metric_name,
    profile_id,
    timestamp as occurred_at,
    campaign_id,
    flow_id,
    cast(value_eur as double) as value_eur,
    attributed_message_id,
    shopify_order_id as order_id
from {{ source('klaviyo', 'events') }}
where not _fivetran_deleted
