-- One row per failed billing cycle (dunning episode): the first failed payment of a cycle and
-- whether a later retry of the same cycle succeeded. Billing runs at 05:00 Amsterdam time on the
-- cycle date; retries follow on days 1, 3, 7, 14, 21 and 28, and billing gives up on day 30.

with shopify_cycles as (
    select
        'shp-' || contract_id as subscription_key,
        billing_cycle_date,
        min(case when is_success then attempted_at end) as succeeded_at
    from {{ ref('stg_shopify__subscription_billing_attempts') }}
    group by 1, 2
    having bool_or(not is_success)
),

recharge_cycles as (
    select
        coalesce('shp-' || r.shopify_contract_id, 'rch-' || r.recharge_subscription_id) as subscription_key,
        c.billing_cycle_date,
        case when c.status = 'success' then c.processed_at end as succeeded_at
    from {{ ref('stg_recharge__charges') }} as c
    join {{ ref('stg_recharge__subscriptions') }} as r using (recharge_subscription_id)
    where c.number_times_tried > 1 or c.status = 'error'
),

cycles as (
    select subscription_key, billing_cycle_date, min(succeeded_at) as recovered_at
    from (
        select * from shopify_cycles
        union all
        select * from recharge_cycles
    )
    group by 1, 2
)

select
    subscription_key,
    billing_cycle_date,
    {{ local_time_on('billing_cycle_date', 5) }} as first_failed_at,
    recovered_at,
    recovered_at is not null
        and recovered_at < {{ local_time_on('billing_cycle_date', 5) }} + interval 30 day
        as is_recovered_within_30_days
from cycles
