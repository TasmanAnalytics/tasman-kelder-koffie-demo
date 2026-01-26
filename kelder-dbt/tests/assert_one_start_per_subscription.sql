-- Every subscription key starts exactly once and ends at most once.
select subscription_key
from {{ ref('int_subscription_events') }}
group by 1
having count(case when event_type = 'started' then 1 end) <> 1
    or count(case when event_type in ('cancelled', 'expired') then 1 end) > 1
