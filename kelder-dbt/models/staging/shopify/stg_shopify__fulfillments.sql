select
    id as fulfillment_id,
    order_id,
    created_at as shipped_at,
    tracking_company as carrier,
    status as fulfillment_status,
    delivered_at
from {{ source('shopify', 'fulfillments') }}
where not _fivetran_deleted
