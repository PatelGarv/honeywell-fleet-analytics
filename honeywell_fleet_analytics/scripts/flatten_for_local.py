# Save as scripts/flatten_for_local.py
import pandas as pd
import json

# Flatten telemetry for local analysis
telemetry_raw = []
with open('../data/raw_telemetry.jsonl', 'r') as f:
    for line in f:
        record = json.loads(line)
        props = json.loads(record['properties'])
        record['sensor_readings'] = json.dumps(props['sensor_readings'])
        record['alert_severity_score'] = props['alert_severity_score']
        record['maintenance_protocol'] = props['maintenance_protocol']
        record['model'] = props['model']
        record['operator'] = props['operator']
        record['base_location'] = props['base_location']
        del record['properties']
        telemetry_raw.append(record)

pd.DataFrame(telemetry_raw).to_csv('../data/telemetry_flat.csv', index=False)
print("Local CSV ready. Use this for pandas analysis until BigQuery is set up.")
