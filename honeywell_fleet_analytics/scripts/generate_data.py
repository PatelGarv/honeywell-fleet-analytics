import pandas as pd
import numpy as np
from faker import Faker
import json
import random
from datetime import datetime, timedelta

fake = Faker()
Faker.seed(42)
np.random.seed(42)

print("Generating Honeywell fleet data...")

# ============================================
# 1. AIRCRAFT REGISTRY (50 aircraft)
# ============================================
aircraft = []
for i in range(50):
    install_date = fake.date_between(datetime(2019, 1, 1), datetime(2023, 6, 1))
    aircraft.append({
        'aircraft_id': f'AC-{i:03d}',
        'model': random.choice(['B737-800', 'A320neo', 'B777-300', 'A350-900', 'B787-9']),
        'operator': random.choice(['Delta', 'United', 'American', 'Southwest', 'FedEx', 'UPS', 'Atlas Air']),
        'install_date': install_date.strftime('%Y-%m-%d'),
        'total_flight_hours': random.randint(5000, 45000),
        'maintenance_protocol': random.choice(['standard', 'predictive_v2']),
        'base_location': fake.city()
    })
aircraft_df = pd.DataFrame(aircraft)
print(f"Aircraft: {len(aircraft_df)} rows")

# ============================================
# 2. COMPONENT MASTER (200 components)
# ============================================
components = []
comp_types = ['hydraulic_pump', 'fuel_sensor', 'oil_pressure_valve', 
              'temperature_probe', 'vibration_sensor']
for i in range(200):
    ac = random.choice(aircraft)
    comp_type = random.choice(comp_types)
    install = fake.date_between(
        datetime.strptime(ac['install_date'], '%Y-%m-%d'), 
        datetime(2024, 1, 1)
    )
    components.append({
        'component_id': f'CMP-{i:04d}',
        'aircraft_id': ac['aircraft_id'],
        'component_type': comp_type,
        'install_date': install.strftime('%Y-%m-%d'),
        'expected_life_hours': random.randint(8000, 25000),
        'maintenance_protocol': ac['maintenance_protocol']
    })
components_df = pd.DataFrame(components)
print(f"Components: {len(components_df)} rows")

# ============================================
# 3. SENSOR TELEMETRY (50,000 readings)
# ============================================
telemetry = []
statuses = ['NORMAL', 'ADVISORY', 'WARNING', 'CRITICAL']

for i in range(50000):
    comp = random.choice(components)
    ts = fake.date_time_between(datetime(2024, 1, 1), datetime(2024, 12, 31))
    
    # Age-based degradation logic
    age_days = (ts - datetime.strptime(comp['install_date'], '%Y-%m-%d')).days
    age_years = age_days / 365.0
    
    if age_years > 3.5:
        base_prob = [0.35, 0.30, 0.22, 0.13]
    elif age_years > 2.0:
        base_prob = [0.50, 0.25, 0.17, 0.08]
    elif age_years > 1.0:
        base_prob = [0.62, 0.22, 0.12, 0.04]
    else:
        base_prob = [0.75, 0.15, 0.08, 0.02]
    
    status = random.choices(statuses, weights=base_prob)[0]
    
    # Sensor values correlated with status
    if comp['component_type'] == 'hydraulic_pump':
        pressure = np.random.normal(2800, 150) if status == 'NORMAL' else np.random.normal(2200, 350)
        temp = np.random.normal(85, 8) if status == 'NORMAL' else np.random.normal(115, 18)
        readings = {'pressure_psi': round(max(pressure, 1500), 1), 
                    'temp_c': round(max(temp, 50), 1)}
    elif comp['component_type'] == 'fuel_sensor':
        flow_rate = np.random.normal(450, 25) if status == 'NORMAL' else np.random.normal(380, 55)
        contamination = np.random.normal(2, 0.8) if status == 'NORMAL' else np.random.normal(9, 4)
        readings = {'flow_rate_gph': round(max(flow_rate, 200), 1), 
                    'contamination_ppm': round(max(contamination, 0), 2)}
    elif comp['component_type'] == 'temperature_probe':
        temp_reading = np.random.normal(220, 15) if status == 'NORMAL' else np.random.normal(280, 35)
        drift = np.random.normal(0.5, 0.3) if status == 'NORMAL' else np.random.normal(3.5, 2)
        readings = {'temp_reading_c': round(max(temp_reading, 150), 1), 
                    'sensor_drift_pct': round(max(drift, 0), 2)}
    elif comp['component_type'] == 'oil_pressure_valve':
        pressure = np.random.normal(45, 5) if status == 'NORMAL' else np.random.normal(32, 8)
        leakage = np.random.normal(0.1, 0.05) if status == 'NORMAL' else np.random.normal(1.2, 0.8)
        readings = {'oil_pressure_psi': round(max(pressure, 10), 1), 
                    'leakage_rate_ml_hr': round(max(leakage, 0), 2)}
    else:  # vibration_sensor
        vibration = np.random.normal(50, 12) if status == 'NORMAL' else np.random.normal(85, 25)
        freq_drift = np.random.normal(0.2, 0.1) if status == 'NORMAL' else np.random.normal(1.5, 0.8)
        readings = {'vibration_hz': round(max(vibration, 10), 2), 
                    'frequency_drift_hz': round(max(freq_drift, 0), 2)}
    
    # Alert severity score
    if status == 'NORMAL':
        severity = random.randint(0, 25)
    elif status == 'ADVISORY':
        severity = random.randint(26, 50)
    elif status == 'WARNING':
        severity = random.randint(51, 75)
    else:
        severity = random.randint(76, 100)
    
    telemetry.append({
        'reading_id': f'R{i:06d}',
        'component_id': comp['component_id'],
        'aircraft_id': comp['aircraft_id'],
        'timestamp': ts.isoformat(),
        'component_type': comp['component_type'],
        'status': status,
        'flight_hours_at_reading': max(0, comp['expected_life_hours'] - random.randint(100, 5000)),
        'properties': json.dumps({
            'sensor_readings': readings,
            'alert_severity_score': severity,
            'maintenance_protocol': comp['maintenance_protocol'],
            'model': next(a['model'] for a in aircraft if a['aircraft_id'] == comp['aircraft_id']),
            'operator': next(a['operator'] for a in aircraft if a['aircraft_id'] == comp['aircraft_id']),
            'base_location': next(a['base_location'] for a in aircraft if a['aircraft_id'] == comp['aircraft_id'])
        })
    })

telemetry_df = pd.DataFrame(telemetry)
print(f"Telemetry: {len(telemetry_df)} rows")

# ============================================
# 4. SAVE RAW FILES
# ============================================
aircraft_df.to_csv('../data/raw_aircraft.csv', index=False)
components_df.to_csv('../data/raw_components.csv', index=False)
telemetry_df.to_json('../data/raw_telemetry.jsonl', orient='records', lines=True)

print("Raw data saved to data/ folder")
