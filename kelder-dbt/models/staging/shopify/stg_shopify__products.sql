select
    id as product_id,
    title as product_title,
    product_type
from {{ source('shopify', 'products') }}
where not _fivetran_deleted
