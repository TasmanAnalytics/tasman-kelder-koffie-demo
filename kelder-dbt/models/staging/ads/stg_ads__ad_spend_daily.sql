-- One row per platform, campaign and day, in EUR.
select
    date as spend_date,
    'meta' as platform,
    'paid_social' as channel,
    campaign_id,
    campaign_name,
    cast(spend as double) as spend_eur,
    impressions,
    clicks
from {{ source('ads', 'meta_ads_daily') }}
where not _fivetran_deleted

union all

select
    date,
    'google',
    'paid_search',
    campaign_id,
    campaign_name,
    cost_micros / 1e6,
    impressions,
    clicks
from {{ source('ads', 'google_ads_daily') }}
where not _fivetran_deleted
