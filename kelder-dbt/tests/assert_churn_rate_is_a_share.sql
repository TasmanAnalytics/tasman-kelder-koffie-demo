-- Churn and pause rates are shares of the base, so they must sit between 0 and 1.
select month from {{ ref('metrics_subscriber_churn_monthly') }}
where churn_rate_as_reported not between 0 and 1
    or churn_rate_v1 not between 0 and 1
    or churn_rate_v2_restated not between 0 and 1
union all
select month from {{ ref('metrics_pause_rate_monthly') }} where pause_rate not between 0 and 1
