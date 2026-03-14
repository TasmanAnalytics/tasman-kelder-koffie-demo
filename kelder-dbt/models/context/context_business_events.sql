{{ config(alias='business_events', schema='context', materialized='table') }}

-- Dated events that moved a metric. Check this table before explaining any anomaly.
select
    event_date,
    event_type,
    title,
    description,
    string_split(affected_metrics, ';') as affected_metrics,
    expected_effect,
    owner,
    source_link
from {{ ref('business_events') }}
order by event_date
