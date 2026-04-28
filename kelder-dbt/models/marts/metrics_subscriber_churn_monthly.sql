-- Governed monthly subscriber churn. Definitions: context/glossary.md and context/metric_changelog.md.
--
-- Two event streams feed it. Adjusted excludes the 2026-03-12 migration artefacts and treats
-- restores as continuations (decision 0007); report from it. Unadjusted counts the artefacts and
-- matches Recharge exports, for finance reconciliation only.
--
-- Two definitions (decision 0009). v1: a failed payment counts as churn on the day it fails.
-- v2: it counts only if not recovered within 30 days, in the month of the first failure. For the
-- latest month, failures younger than 30 days at the as-of date are not churn yet, so that month
-- is provisional and will be revised upward.

with months as (
    select * from {{ ref('int_reporting_months') }}
),

adjusted_events as (
    select * from {{ ref('int_subscription_events_adjusted') }}
    where not is_gift
),

unadjusted_events as (
    select * from {{ ref('int_subscription_events') }}
    where not is_gift
),
{% for stream in ['adjusted', 'unadjusted'] %}
spans_{{ stream }} as (
    select
        subscription_key,
        min(case when event_type = 'started' then occurred_at end) as started_at,
        min(case when event_type in ('cancelled', 'expired') then occurred_at end) as ended_at
    from {{ stream }}_events
    group by 1
),

base_{{ stream }} as (
    select m.month, count(s.subscription_key) as base_subscribers
    from months as m
    left join spans_{{ stream }} as s
        on s.started_at < m.month_start
        and (s.ended_at is null or s.ended_at >= m.month_start)
    group by 1
),

churn_{{ stream }} as (
    select
        event_month as month,
        count(distinct case when event_type = 'cancelled' and is_voluntary_cancellation then subscription_key end)
            as voluntary_cancellations,
        count(distinct case when event_type = 'payment_failed' then subscription_key end) as failed_payments,
        count(distinct case
            when event_type = 'payment_failed'
                and not is_recovered_within_30_days
                and occurred_at + interval 30 day <= {{ local_midnight("date '" ~ var('as_of_date') ~ "'") }}
            then subscription_key
        end) as failed_payments_unrecovered_30d
    from {{ stream }}_events
    group by 1
),

series_{{ stream }} as (
    select
        m.month,
        b.base_subscribers,
        coalesce(c.voluntary_cancellations, 0) + coalesce(c.failed_payments, 0) as churned_v1,
        coalesce(c.voluntary_cancellations, 0) + coalesce(c.failed_payments_unrecovered_30d, 0) as churned_v2
    from months as m
    left join base_{{ stream }} as b using (month)
    left join churn_{{ stream }} as c using (month)
),
{% endfor %}
-- As reported: v1 before 1 May 2026, v2 from then. Board decks quoted v1 before May.
as_reported as (
    select
        month,
        case when month < date '2026-05-01' then 'v1' else 'v2' end as definition_version,
        base_subscribers,
        case when month < date '2026-05-01' then churned_v1 else churned_v2 end as churned_subscribers
    from series_adjusted
),

-- Restated: v2 for every month, for like-for-like comparisons across 1 May 2026.
restated_v2 as (
    select month, base_subscribers, churned_v2
    from series_adjusted
),

-- As reported, artefacts included: for reconciliation against Recharge exports only.
as_reported_raw as (
    select
        month,
        base_subscribers,
        case when month < date '2026-05-01' then churned_v1 else churned_v2 end as churned_subscribers
    from series_unadjusted
)

select
    m.month,
    r.definition_version as definition_version_as_reported,
    r.base_subscribers,
    r.churned_subscribers,
    round(r.churned_subscribers / r.base_subscribers, 6) as churn_rate_as_reported,
    raw.base_subscribers as base_subscribers_raw,
    raw.churned_subscribers as churned_subscribers_raw,
    round(raw.churned_subscribers / raw.base_subscribers, 6) as churn_rate_as_reported_raw,
    a.churned_v1 as churned_subscribers_v1,
    round(a.churned_v1 / a.base_subscribers, 6) as churn_rate_v1,
    v2.base_subscribers as base_subscribers_v2_restated,
    v2.churned_v2 as churned_subscribers_v2_restated,
    round(v2.churned_v2 / v2.base_subscribers, 6) as churn_rate_v2_restated,
    m.is_latest_month as is_provisional
from months as m
join as_reported as r using (month)
join restated_v2 as v2 using (month)
join as_reported_raw as raw using (month)
join series_adjusted as a using (month)
order by m.month
