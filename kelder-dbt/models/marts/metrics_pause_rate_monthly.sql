with months as (
    select * from {{ ref('int_reporting_months') }}
),

-- adjusted stream: migration artefacts stay paused (decision 0007)
events as (
    select * from {{ ref('int_subscription_events_adjusted') }}
    where not is_gift
),

spans as (
    select
        subscription_key,
        min(case when event_type = 'started' then occurred_at end) as started_at,
        min(case when event_type in ('cancelled', 'expired') then occurred_at end) as ended_at
    from events
    group by 1
),

status_changes as (
    select
        subscription_key,
        event_type,
        occurred_at,
        lead(occurred_at) over w as next_change_at,
        lag(event_type) over w as previous_change
    from events
    where event_type in ('paused', 'resumed', 'cancelled', 'expired')
    window w as (partition by subscription_key order by occurred_at, event_type)
),

-- a pause runs until the next resume or end; a resume with no pause before it in the data
-- belongs to a pause that started before the data begins
pause_spans as (
    select subscription_key, occurred_at as paused_from, next_change_at as paused_until
    from status_changes
    where event_type = 'paused'
    union all
    select c.subscription_key, s.started_at, c.occurred_at
    from status_changes as c
    join spans as s using (subscription_key)
    where c.event_type = 'resumed' and coalesce(c.previous_change, '') <> 'paused'
),

base as (
    select m.month, count(s.subscription_key) as base_subscribers
    from months as m
    left join spans as s
        on s.started_at < m.month_start and (s.ended_at is null or s.ended_at >= m.month_start)
    group by 1
),

paused as (
    select m.month, count(distinct p.subscription_key) as paused_at_month_start
    from months as m
    join pause_spans as p
        on p.paused_from < m.month_start and (p.paused_until is null or p.paused_until > m.month_start)
    group by 1
),

starts as (
    select event_month as month, count(*) as pauses_started
    from events
    where event_type = 'paused'
    group by 1
)

select
    m.month,
    b.base_subscribers,
    coalesce(p.paused_at_month_start, 0) as paused_at_month_start,
    coalesce(s.pauses_started, 0) as pauses_started,
    round(coalesce(s.pauses_started, 0) / b.base_subscribers, 6) as pause_rate,
    round(coalesce(p.paused_at_month_start, 0) / b.base_subscribers, 6) as paused_share
from months as m
left join base as b using (month)
left join paused as p using (month)
left join starts as s using (month)
order by 1
