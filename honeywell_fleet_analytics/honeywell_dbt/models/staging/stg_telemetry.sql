with source as (
    select * from {{ source('raw', 'telemetry') }}
),

parsed as (
    select
        reading_id,
        component_id,
        aircraft_id,
        component_type,
        status,
        timestamp::timestamp_ntz as reading_timestamp,
        flight_hours_at_reading,
        
        -- Snowflake JSON parsing (returns NULL if key doesn't exist for that component type)
        PARSE_JSON(sensor_readings):pressure_psi::float as pressure_psi,
        PARSE_JSON(sensor_readings):temp_c::float as temp_c,
        PARSE_JSON(sensor_readings):flow_rate_gph::float as flow_rate_gph,
        PARSE_JSON(sensor_readings):contamination_ppm::float as contamination_ppm,
        PARSE_JSON(sensor_readings):vibration_hz::float as vibration_hz,
        PARSE_JSON(sensor_readings):temp_reading_c::float as temp_reading_c,
        PARSE_JSON(sensor_readings):sensor_drift_pct::float as sensor_drift_pct,
        PARSE_JSON(sensor_readings):oil_pressure_psi::float as oil_pressure_psi,
        PARSE_JSON(sensor_readings):leakage_rate_ml_hr::float as leakage_rate_ml_hr,
        PARSE_JSON(sensor_readings):frequency_drift_hz::float as frequency_drift_hz,
        
        alert_severity_score,
        maintenance_protocol,
        model,
        operator,
        base_location
    from source
)

select * from parsed
