select
    id as refund_id,
    order_id,
    created_at as refunded_at,
    cast(amount as double) as refund_amount_eur,
    note as refund_note
from {{ source('shopify', 'refunds') }}
where not _fivetran_deleted
