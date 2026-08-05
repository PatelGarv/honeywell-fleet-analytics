select
    component_id,
    aircraft_id,
    component_type,
    install_date::date as install_date,
    expected_life_hours,
    maintenance_protocol
from {{ source('raw', 'components') }}
