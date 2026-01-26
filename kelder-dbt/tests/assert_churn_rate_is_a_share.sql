-- Churn and pause rates are shares of the base, so they must sit between 0 and 1.
select month from {{ ref('metrics_subscriber_churn_monthly') }} where churn_rate < 0 or churn_rate > 1
union all
select month from {{ ref('metrics_pause_rate_monthly') }} where pause_rate < 0 or pause_rate > 1
