select
    md5(e.subscription_key || '|' || e.event_type || '|' || cast(e.occurred_at as varchar)) as subscription_event_id,
    e.subscription_key,
    e.event_type,
    e.occurred_at,
    e.event_month,
    e.source,
    e.cancellation_reason,
    e.is_voluntary_cancellation,
    e.billing_cycle_date,
    e.recovered_at,
    e.is_recovered_within_30_days,
    e.is_gift,
    e.event_type = 'cancelled' and s.is_migration_artifact as is_migration_artifact
from {{ ref('int_subscription_events') }} as e
left join {{ ref('int_subscriptions_unified') }} as s using (subscription_key)
