-- Adjusted event stream (decision 0007). The 2026-03-12 billing migration wrote a cancellation
-- for every subscription that was paused at the last Shopify sync. Those cancellations never
-- happened: the subscriptions were paused. From 2026-03-16 operations re-created each wiped pause
-- as a new Recharge subscription on its original pause end date (a restore).
--
-- In this stream a flagged subscription stays paused from its Shopify pause until its restore is
-- created, or to the end of the data if it has not been restored yet. The restore then continues
-- the original subscription key and tenure: its events move to the original key and its own
-- start becomes a resume.

with events as (
    select * from {{ ref('int_subscription_events') }}
),

subs as (
    select * from {{ ref('int_subscriptions_unified') }}
),

artifacts as (
    select subscription_key from subs where is_migration_artifact
),

restores as (
    select subscription_key as restore_key, continues_subscription_key, started_at as restored_at
    from subs
    where is_legacy_pause_restore
),

kept as (
    select e.*
    from events as e
    where not (e.event_type = 'cancelled' and e.subscription_key in (select subscription_key from artifacts))
        and not (e.event_type = 'started' and e.subscription_key in (select restore_key from restores))
),

remapped as (
    select
        coalesce(r.continues_subscription_key, k.subscription_key) as subscription_key,
        k.* exclude (subscription_key)
    from kept as k
    left join restores as r on r.restore_key = k.subscription_key
),

resumes as (
    select
        continues_subscription_key as subscription_key,
        'resumed' as event_type,
        restored_at as occurred_at,
        {{ local_month('restored_at') }} as event_month,
        'restore' as source,
        cast(null as varchar) as cancellation_reason,
        false as is_voluntary_cancellation,
        cast(null as date) as billing_cycle_date,
        cast(null as timestamptz) as recovered_at,
        cast(null as boolean) as is_recovered_within_30_days,
        false as is_gift
    from restores
)

select * from remapped
union all by name
select * from resumes
