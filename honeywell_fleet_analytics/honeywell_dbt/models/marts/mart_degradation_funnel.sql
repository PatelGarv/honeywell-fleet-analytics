with daily_status as (
    select 
        date(reading_timestamp) as reading_date,
        component_id,
        component_type,
        status
    from {{ ref('int_sensor_trends') }}
),

transitions as (
    select
        component_id,
        component_type,
        status,
        min(reading_date) as first_seen_date,
        count(*) as days_in_status
    from daily_status
    group by 1, 2, 3
)

select
    component_type,
    count(distinct case when status = 'NORMAL' then component_id end) as normal_count,
    count(distinct case when status = 'ADVISORY' then component_id end) as advisory_count,
    count(distinct case when status = 'WARNING' then component_id end) as warning_count,
    count(distinct case when status = 'CRITICAL' then component_id end) as critical_count,
    
    round(
        count(distinct case when status = 'ADVISORY' then component_id end) / 
        nullif(count(distinct case when status = 'NORMAL' then component_id end), 0), 
        4
    ) as normal_to_advisory_rate,
    
    round(
        count(distinct case when status = 'WARNING' then component_id end) / 
        nullif(count(distinct case when status = 'ADVISORY' then component_id end), 0), 
        4
    ) as advisory_to_warning_rate,

    round(
        count(distinct case when status = 'CRITICAL' then component_id end) / 
        nullif(count(distinct case when status = 'WARNING' then component_id end), 0), 
        4
    ) as warning_to_critical_rate

from transitions
group by 1
