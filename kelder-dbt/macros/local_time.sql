{#- Kelder reports in Amsterdam time. Raw timestamps are UTC (timestamptz). -#}

{% macro to_local(ts) -%}
    timezone('{{ var("reporting_timezone") }}', {{ ts }})
{%- endmacro %}

{% macro local_date(ts) -%}
    cast(timezone('{{ var("reporting_timezone") }}', {{ ts }}) as date)
{%- endmacro %}

{% macro local_month(ts) -%}
    cast(date_trunc('month', timezone('{{ var("reporting_timezone") }}', {{ ts }})) as date)
{%- endmacro %}

{#- Start of a local calendar date as a UTC instant, e.g. month starts at 00:00 Amsterdam. -#}
{% macro local_midnight(d) -%}
    timezone('{{ var("reporting_timezone") }}', cast({{ d }} as timestamp))
{%- endmacro %}

{#- A local wall-clock time on a local date, as a UTC instant (safe across daylight saving changes). -#}
{% macro local_time_on(d, hh, mm=0) -%}
    timezone('{{ var("reporting_timezone") }}', cast({{ d }} as timestamp) + interval {{ hh }} hour + interval {{ mm }} minute)
{%- endmacro %}
