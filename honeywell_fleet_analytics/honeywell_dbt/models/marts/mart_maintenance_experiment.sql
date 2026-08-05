select
    t.maintenance_protocol,
    t.component_type,
    count(distinct t.component_id) as total_components,
    count(distinct case when t.status = 'CRITICAL' then t.component_id end) as critical_failures,
    count(distinct case when t.status = 'WARNING' then t.component_id end) as warnings,
    avg(t.alert_severity_score) as avg_severity,
    avg(datediff('day', c.install_date, date(t.reading_timestamp))) as avg_component_age_days
from {{ ref('int_sensor_trends') }} t
join {{ ref('stg_components') }} c on t.component_id = c.component_id
group by 1, 2
