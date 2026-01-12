-- One row per billing attempt (Shopify) or charge (Recharge), keyed to the subscription key.
-- Recharge retries a failed charge in place, so one Recharge row can stand for several attempts.

with recharge_keys as (
    -- Recharge subscriptions that continue a Shopify contract share its key
    select
        recharge_subscription_id,
        coalesce('shp-' || shopify_contract_id, 'rch-' || recharge_subscription_id) as subscription_key
    from {{ ref('stg_recharge__subscriptions') }}
)

select
    'shp-' || a.contract_id as subscription_key,
    'shopify' as source_system,
    a.billing_attempt_id as source_id,
    a.billing_cycle_date,
    a.attempted_at,
    a.is_success,
    a.attempt_number as attempts,
    a.order_id
from {{ ref('stg_shopify__subscription_billing_attempts') }} as a

union all

select
    k.subscription_key,
    'recharge',
    c.charge_id,
    c.billing_cycle_date,
    coalesce(c.processed_at, c.scheduled_at),
    c.status = 'success',
    c.number_times_tried,
    c.order_id
from {{ ref('stg_recharge__charges') }} as c
join recharge_keys as k using (recharge_subscription_id)
