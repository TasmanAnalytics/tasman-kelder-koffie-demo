select id as campaign_id, name as campaign_name, subject, send_time as sent_at, status, audience_size
from {{ source('klaviyo', 'campaigns') }}
where not _fivetran_deleted
