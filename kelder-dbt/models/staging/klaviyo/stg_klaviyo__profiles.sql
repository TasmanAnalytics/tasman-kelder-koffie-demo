select id as profile_id, lower(email) as email, shopify_customer_id, created_at
from {{ source('klaviyo', 'profiles') }}
where not _fivetran_deleted
