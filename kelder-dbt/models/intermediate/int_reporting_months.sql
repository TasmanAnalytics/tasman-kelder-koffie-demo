-- Calendar months in the reporting window, with their start and end as instants
-- (00:00 Amsterdam time on the first of the month).

select
    cast(m as date) as month,
    {{ local_midnight('m') }} as month_start,
    {{ local_midnight("m + interval 1 month") }} as month_end,
    cast(m as date) = cast(date_trunc('month', date '{{ var("as_of_date") }}' - interval 1 day) as date) as is_latest_month
from range(date '{{ var("first_reporting_month") }}', date '{{ var("as_of_date") }}', interval 1 month) as t(m)
