select id as flow_id, name as flow_name
from {{ source('klaviyo', 'flows') }}
where not _fivetran_deleted
