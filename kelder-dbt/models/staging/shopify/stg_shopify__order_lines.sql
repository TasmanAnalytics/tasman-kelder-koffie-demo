select
    id as order_line_id,
    order_id,
    variant_id,
    sku,
    quantity,
    cast(price as double) as unit_price_eur,
    cast(total_discount as double) as discount_eur,
    cast(price as double) * quantity - cast(total_discount as double) as line_total_eur
from {{ source('shopify', 'order_lines') }}
where not _fivetran_deleted
