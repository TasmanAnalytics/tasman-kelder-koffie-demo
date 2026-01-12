select
    id as customer_id,
    lower(email) as email,
    first_name,
    last_name,
    country_code,
    created_at,
    accepts_marketing,
    nullif(tags, '') as tags
from {{ source('shopify', 'customers') }}
where not _fivetran_deleted
