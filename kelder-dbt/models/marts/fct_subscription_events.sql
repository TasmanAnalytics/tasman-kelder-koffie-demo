select
    md5(subscription_key || '|' || event_type || '|' || cast(occurred_at as varchar)) as subscription_event_id,
    subscription_key,
    event_type,
    occurred_at,
    event_month,
    source,
    cancellation_reason,
    is_voluntary_cancellation,
    billing_cycle_date,
    recovered_at,
    is_recovered_within_30_days,
    is_gift
from {{ ref('int_subscription_events') }}
