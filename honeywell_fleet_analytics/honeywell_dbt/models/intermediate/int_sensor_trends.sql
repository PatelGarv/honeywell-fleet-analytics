with parsed as (
    select * from {{ ref('stg_telemetry') }}
)

select
    reading_id,
    component_id,
    aircraft_id,
    component_type,
    reading_timestamp,
    status,
    pressure_psi,
    temp_c,
    flow_rate_gph,
    contamination_ppm,
    vibration_hz,
    temp_reading_c,
    sensor_drift_pct,
    oil_pressure_psi,
    leakage_rate_ml_hr,
    frequency_drift_hz,
    alert_severity_score,
    maintenance_protocol,
    model,
    operator,
    base_location,
    
    -- LAG for delta calculations (your Honeywell rolling-window skill)
    lag(pressure_psi) over (partition by component_id order by reading_timestamp) as prev_pressure,
    lag(temp_c) over (partition by component_id order by reading_timestamp) as prev_temp,
    lag(alert_severity_score) over (partition by component_id order by reading_timestamp) as prev_severity,
    
    -- Rolling averages (degradation tracking)
    avg(pressure_psi) over (
        partition by component_id 
        order by reading_timestamp 
        rows between 6 preceding and current row
    ) as pressure_7d_avg,
    
    avg(temp_c) over (
        partition by component_id 
        order by reading_timestamp 
        rows between 6 preceding and current row
    ) as temp_7d_avg,
    
    stddev(alert_severity_score) over (
        partition by component_id 
        order by reading_timestamp 
        rows between 13 preceding and current row
    ) as severity_14d_std,
    
    -- Time since last WARNING/CRITICAL alert
    datediff('minute', 
        lag(case when status in ('WARNING','CRITICAL') then reading_timestamp end) 
            over (partition by component_id order by reading_timestamp),
        reading_timestamp
    ) as minutes_since_last_alert,
    
    -- Row number for ranking most recent readings per component
    row_number() over (partition by component_id order by reading_timestamp desc) as recency_rank

from parsed
