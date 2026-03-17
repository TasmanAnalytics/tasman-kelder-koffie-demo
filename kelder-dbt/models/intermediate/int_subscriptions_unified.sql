-- One row per subscription key, across the Shopify subscription app and Recharge.
-- A subscription keeps one key for its whole life. Shopify contracts are keyed by contract id.
-- A Recharge subscription that carries a Shopify contract id continues that contract's key.
-- Any other Recharge subscription gets its own key.

with contracts as (
    select * from {{ ref('stg_shopify__subscription_contracts') }}
),

recharge as (
    select * from {{ ref('stg_recharge__subscriptions') }}
),

first_recharge_charge as (
    select recharge_subscription_id, order_id
    from {{ ref('stg_recharge__charges') }}
    qualify row_number() over (partition by recharge_subscription_id order by scheduled_at, charge_id) = 1
),

from_shopify as (
    select
        'shp-' || c.contract_id as subscription_key,
        'shopify' as origin_system,
        c.contract_id as shopify_contract_id,
        r.recharge_subscription_id,
        c.customer_id,
        c.created_at as started_at,
        c.origin_order_id,
        c.is_gift,
        coalesce(r.interval_days, c.interval_days) as interval_days,
        coalesce(r.quantity, c.quantity) as quantity,
        coalesce(r.variant_id, c.variant_id) as variant_id,
        r.price_eur,
        c.payment_method,
        c.source_status as shopify_status,
        r.source_status as recharge_status,
        r.paused_until,
        r.synced_at as recharge_synced_at,
        -- once a contract has a Recharge subscription, Recharge holds its current state
        case when r.recharge_subscription_id is null then c.cancelled_at else r.cancelled_at end as ended_at_source,
        case when r.recharge_subscription_id is null then c.cancellation_reason else r.cancellation_reason end as cancellation_reason,
        -- 2026-03-12 billing migration (decision 0007): the legacy import path had no paused state,
        -- so contracts that were PAUSED at the last Shopify sync arrived in Recharge as cancelled,
        -- stamped 2026-03-12 00:00:00 UTC with no reason. Genuine cancellations queued during the
        -- freeze carry the same stamp, but their contract was ACTIVE, so they are not flagged.
        coalesce(
            c.source_status = 'PAUSED'
            and r.cancelled_at = timestamptz '2026-03-12 00:00:00+00'
            and r.cancellation_reason is null,
            false
        ) as is_migration_artifact,
        false as is_legacy_pause_restore,
        cast(null as varchar) as continues_subscription_key
    from contracts as c
    left join recharge as r on r.shopify_contract_id = c.contract_id
),

from_recharge as (
    select
        'rch-' || r.recharge_subscription_id as subscription_key,
        'recharge' as origin_system,
        cast(null as bigint) as shopify_contract_id,
        r.recharge_subscription_id,
        r.shopify_customer_id as customer_id,
        r.created_at as started_at,
        f.order_id as origin_order_id,
        r.is_gift,
        r.interval_days,
        r.quantity,
        r.variant_id,
        r.price_eur,
        cast(null as varchar) as payment_method,
        cast(null as varchar) as shopify_status,
        r.source_status as recharge_status,
        r.paused_until,
        r.synced_at as recharge_synced_at,
        r.cancelled_at as ended_at_source,
        r.cancellation_reason,
        false as is_migration_artifact,
        -- operations re-created wiped pauses as new Recharge subscriptions from 2026-03-16;
        -- they continue the original subscription (context/quirks/legacy_pause_restores.md)
        coalesce(r.restore_source = 'legacy_pause', false) as is_legacy_pause_restore,
        case when r.restore_source = 'legacy_pause' then 'shp-' || r.legacy_contract_id end as continues_subscription_key
    from recharge as r
    left join first_recharge_charge as f using (recharge_subscription_id)
    where r.shopify_contract_id is null
),

unioned as (
    select * from from_shopify
    union all
    select * from from_recharge
),

-- status unification: Shopify statuses are upper case and include FAILED (billing gave up);
-- Recharge has no paused status, so an active subscription with paused_until in the future is paused
unified as (
    select
        *,
        case
            when recharge_status is null then
                case shopify_status
                    when 'ACTIVE' then 'active'
                    when 'PAUSED' then 'paused'
                    when 'CANCELLED' then 'cancelled'
                    when 'FAILED' then 'cancelled'
                    when 'EXPIRED' then 'expired'
                end
            when recharge_status = 'active' and paused_until > cast(recharge_synced_at as date) then 'paused'
            else recharge_status
        end as status
    from unioned
)

select
    subscription_key,
    origin_system,
    shopify_contract_id,
    recharge_subscription_id,
    customer_id,
    started_at,
    origin_order_id,
    is_gift,
    interval_days,
    quantity,
    variant_id,
    price_eur,
    payment_method,
    status,
    case when status = 'cancelled' then ended_at_source end as churned_at,
    case when status in ('cancelled', 'expired') then ended_at_source end as ended_at,
    case when status = 'cancelled' then cancellation_reason end as cancellation_reason,
    is_migration_artifact,
    is_legacy_pause_restore,
    continues_subscription_key
from unified
