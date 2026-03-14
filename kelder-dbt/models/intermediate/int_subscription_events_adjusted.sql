-- Adjusted event stream (decision 0007). The 2026-03-12 billing migration wrote a cancellation
-- for every subscription that was paused at the last Shopify sync. Those cancellations never
-- happened: the subscriptions were paused. This stream drops them, so a flagged subscription
-- stays paused from its Shopify pause onwards.

with events as (
    select * from {{ ref('int_subscription_events') }}
),

artifacts as (
    select subscription_key from {{ ref('int_subscriptions_unified') }}
    where is_migration_artifact
)

select e.*
from events as e
where not (
    e.event_type = 'cancelled'
    and e.subscription_key in (select subscription_key from artifacts)
)
