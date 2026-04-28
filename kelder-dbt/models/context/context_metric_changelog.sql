{{ config(alias='metric_changelog', schema='context', materialized='table') }}

-- Versioned metric definitions. Compare across a valid_from date only with a restated series.
select
    metric,
    version,
    valid_from,
    lead(valid_from) over (partition by metric order by valid_from) - interval 1 day as valid_to,
    definition,
    reason_for_change,
    lead(valid_from) over (partition by metric order by valid_from) is null as is_current
from {{ ref('metric_changelog') }}
order by metric, valid_from
