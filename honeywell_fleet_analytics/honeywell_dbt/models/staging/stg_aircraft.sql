select
    aircraft_id,
    model,
    operator,
    install_date::date as install_date,
    total_flight_hours,
    maintenance_protocol,
    base_location
from {{ source('raw', 'aircraft') }}
