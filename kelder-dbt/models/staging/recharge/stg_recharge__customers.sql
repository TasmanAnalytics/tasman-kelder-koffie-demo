select
    id as recharge_customer_id,
    shopify_customer_id,
    lower(email) as email,
    created_at
from {{ source('recharge', 'customers') }}
where not _fivetran_deleted
