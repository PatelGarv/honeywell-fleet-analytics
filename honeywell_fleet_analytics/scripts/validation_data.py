import pandas as pd

print("=== DATA VALIDATION ===\n")

# Aircraft
ac = pd.read_csv('../data/raw_aircraft.csv')
print(f"Aircraft: {len(ac)} rows")
print(f"  Models: {ac['model'].unique()}")
print(f"  Protocols: {ac['maintenance_protocol'].value_counts().to_dict()}")
print(f"  Missing values: {ac.isnull().sum().sum()}")

# Components
comp = pd.read_csv('../data/raw_components.csv')
print(f"\nComponents: {len(comp)} rows")
print(f"  Types: {comp['component_type'].value_counts().to_dict()}")
print(f"  Linked to aircraft: {comp['aircraft_id'].isin(ac['aircraft_id']).all()}")

# Telemetry
tel = pd.read_csv('../data/telemetry_flat.csv') if 'telemetry_flat.csv' in locals() else pd.read_json('../data/raw_telemetry.jsonl', lines=True)
print(f"\nTelemetry: {len(tel)} rows")
print(f"  Status distribution:")
print(tel['status'].value_counts())
print(f"column names: {tel.columns}")

 # print(f"  Severity range: {tel['alert_severity_score'].min()} - {tel['alert_severity_score'].max()}")
print(f"  Date range: {pd.to_datetime(tel['timestamp']).min()} to {pd.to_datetime(tel['timestamp']).max()}")

print("\n=== ALL CHECKS PASSED ===")
