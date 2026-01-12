select
    v.id as variant_id,
    v.product_id,
    v.sku,
    v.title as variant_title,
    cast(v.price as double) as list_price_eur,
    v.grams,
    p.product_title,
    p.product_type
from {{ source('shopify', 'product_variants') }} as v
left join {{ ref('stg_shopify__products') }} as p using (product_id)
where not v._fivetran_deleted
