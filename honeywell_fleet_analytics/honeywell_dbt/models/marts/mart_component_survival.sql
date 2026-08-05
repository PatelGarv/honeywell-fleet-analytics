with first_alert as (
    select 
        component_id,
        component_type,
        aircraft_id,
        min(reading_timestamp) as first_alert_time,
        min(date(reading_timestamp)) as first_alert_date
    from {{ ref('int_sensor_trends') }}
    where status in ('WARNING', 'CRITICAL')
    group by 1, 2, 3
),

install_dates as (
    select 
        component_id,
        component_type,
        aircraft_id,
        install_date
    from {{ ref('stg_components') }}
)

select
    i.component_id,
    i.component_type,
    i.aircraft_id,
    i.install_date,
    f.first_alert_date,
    datediff('day', i.install_date, f.first_alert_date) as days_to_failure,
    datediff('month', i.install_date, f.first_alert_date) as months_to_failure,
    case when f.first_alert_date is null then 1 else 0 end as censored
    
from install_dates i
left join first_alert f on i.component_id = f.component_id
