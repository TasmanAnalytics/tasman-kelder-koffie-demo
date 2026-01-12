-- Unified event stream per subscription key: started, paused, resumed, cancelled, expired,
-- payment_failed and payment_recovered. Start and end come from the unified subscription rows;
-- pauses come from both systems' status histories; payment events from int_payment_episodes.

with subs as (
    select * from {{ ref('int_subscriptions_unified') }}
),

recharge_keys as (
    select
        recharge_subscription_id,
        coalesce('shp-' || shopify_contract_id, 'rch-' || recharge_subscription_id) as subscription_key
    from {{ ref('stg_recharge__subscriptions') }}
),

lifecycle as (
    select subscription_key, 'started' as event_type, started_at as occurred_at,
           cast(null as varchar) as cancellation_reason, 'subscription' as source
    from subs
    union all
    select subscription_key, case when status = 'expired' then 'expired' else 'cancelled' end, ended_at,
           cancellation_reason, 'subscription'
    from subs
    where ended_at is not null
),

shopify_pauses as (
    select 'shp-' || contract_id as subscription_key,
           case event_type when 'paused' then 'paused' else 'resumed' end as event_type,
           occurred_at, cast(null as varchar) as cancellation_reason, 'shopify' as source
    from {{ ref('stg_shopify__subscription_contract_events') }}
    where event_type in ('paused', 'resumed')
),

recharge_pauses as (
    select k.subscription_key,
           case e.verb when 'paused' then 'paused' else 'resumed' end,
           e.occurred_at, cast(null as varchar), 'recharge'
    from {{ ref('stg_recharge__subscription_events') }} as e
    join recharge_keys as k using (recharge_subscription_id)
    where e.verb in ('paused', 'unpaused')
),

payments as (
    select subscription_key, 'payment_failed', first_failed_at, cast(null as varchar), 'billing'
    from {{ ref('int_payment_episodes') }}
    union all
    select subscription_key, 'payment_recovered', recovered_at, cast(null as varchar), 'billing'
    from {{ ref('int_payment_episodes') }}
    where recovered_at is not null
),

events as (
    select * from lifecycle
    union all select * from shopify_pauses
    union all select * from recharge_pauses
    union all select * from payments
)

select
    e.subscription_key,
    e.event_type,
    e.occurred_at,
    {{ local_month('e.occurred_at') }} as event_month,
    e.source,
    e.cancellation_reason,
    e.event_type = 'cancelled' and coalesce(e.cancellation_reason, '') <> 'max_retries_reached' as is_voluntary_cancellation,
    p.billing_cycle_date,
    p.recovered_at,
    p.is_recovered_within_30_days,
    s.is_gift
from events as e
join subs as s using (subscription_key)
left join {{ ref('int_payment_episodes') }} as p
    on e.event_type = 'payment_failed' and p.subscription_key = e.subscription_key and p.first_failed_at = e.occurred_at
