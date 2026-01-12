with source as (
    select * from {{ source('shopify', 'orders') }}
    where not _fivetran_deleted
),

parsed as (
    select
        *,
        nullif(regexp_extract(landing_site, 'utm_source=([^&]+)', 1), '') as utm_source,
        nullif(regexp_extract(landing_site, 'utm_medium=([^&]+)', 1), '') as utm_medium,
        nullif(regexp_extract(landing_site, 'utm_campaign=([^&]+)', 1), '') as utm_campaign
    from source
)

select
    id as order_id,
    name as order_name,
    customer_id,
    created_at,
    processed_at,
    financial_status,
    fulfillment_status,
    currency,
    cast(subtotal_price as double) as subtotal_price_eur,
    cast(total_tax as double) as total_tax_eur,
    cast(total_discounts as double) as total_discounts_eur,
    cast(total_price as double) as total_price_eur,
    source_name,
    source_name in ('subscription_contract', 'recharge') as is_subscription_renewal,
    coalesce(tags, '') like '%Subscription First Order%' as is_subscription_first_order,
    coalesce(tags, '') like '%Gift Subscription%' as is_gift_subscription_order,
    nullif(tags, '') as tags,
    landing_site,
    referring_site,
    utm_source,
    utm_medium,
    utm_campaign,
    -- channel grouping for web orders, from UTM parameters first and the referrer second
    case
        when source_name <> 'web' then null
        when utm_medium = 'paid_social' then 'paid_social'
        when utm_medium = 'cpc' then 'paid_search'
        when utm_medium = 'email' or utm_source = 'klaviyo' then 'email'
        when regexp_matches(coalesce(referring_site, ''), 'google\.|bing\.|duckduckgo\.') then 'organic'
        when referring_site is not null then 'referral'
        else 'direct'
    end as channel,
    discount_codes,
    cancelled_at
from parsed
