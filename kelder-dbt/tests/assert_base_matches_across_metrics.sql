-- Churn and pause rate use the same base.
select c.month
from {{ ref('metrics_subscriber_churn_monthly') }} as c
join {{ ref('metrics_pause_rate_monthly') }} as p using (month)
where c.base_subscribers <> p.base_subscribers
