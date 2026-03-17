#!/usr/bin/env python3
"""
Get all custom alerts for the last 90 days and export to CSV.

This script retrieves custom alerts from NCM API v2 and exports them to a timestamped
CSV file in the csv_files folder. No input CSV file is required.

CSV Format:
    Output columns:
        - alert_id: Unique alert identifier
        - created_at: Alert creation timestamp
        - router_id: Router ID
        - router_name: Router name
        - alert_type: Type of alert
        - message: Alert message
        - severity: Alert severity
        - detected_at: Detection timestamp
    
    Example output:
        alert_id,created_at,router_id,router_name,alert_type,message,severity,detected_at
        12345,2024-01-15T10:30:00Z,67890,Router1,custom,Alert message,high,2024-01-15T10:29:55Z

Usage:
    python "Export Custom Alerts.py"

Requirements:
    - NCM API v2 keys set as environment variables (X_CP_API_ID, X_CP_API_KEY, X_ECM_API_ID, X_ECM_API_KEY)
    - csv_files folder will be created if it doesn't exist
"""

import os
import csv
import sys
from datetime import datetime, timedelta
import ncm

# Get API keys from environment
api_keys = {
    "X-CP-API-ID": os.environ.get("X_CP_API_ID", ""),
    "X-CP-API-KEY": os.environ.get("X_CP_API_KEY", ""),
    "X-ECM-API-ID": os.environ.get("X_ECM_API_ID", ""),
    "X-ECM-API-KEY": os.environ.get("X_ECM_API_KEY", "")
}

api_keys = {k: v for k, v in api_keys.items() if v}

if not api_keys:
    print("Error: Please set NCM API v2 keys as environment variables")
    sys.exit(1)

ncm.api_keys = api_keys

# Calculate start time (90 days ago)
start_time = datetime.utcnow() - timedelta(days=90)

# Generate filename with timestamp
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
filename = f'custom_alerts_{timestamp}.csv'

print(f"Retrieving custom alerts from the last 90 days...")

# Get all alerts
alerts = ncm.get_alerts(created_at__gt=start_time.isoformat())

# Filter for custom alerts only
custom_alerts = [a for a in alerts if a.get('type') == 'custom']

if not custom_alerts:
    print("No custom alerts found in the last 90 days.")
    sys.exit(0)

# Create csv_files folder if it doesn't exist
os.makedirs('csv_files', exist_ok=True)
filepath = os.path.join('csv_files', filename)

# Write to CSV
with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
    fieldnames = ['alert_id', 'created_at', 'router_id', 'router_name', 
                  'alert_type', 'message', 'severity', 'detected_at']
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    
    writer.writeheader()
    for alert in custom_alerts:
        writer.writerow({
            'alert_id': alert.get('id', ''),
            'created_at': alert.get('created_at', ''),
            'router_id': alert.get('router', ''),
            'router_name': alert.get('router_name', ''),
            'alert_type': alert.get('type', ''),
            'message': alert.get('info', ''),
            'severity': alert.get('severity', ''),
            'detected_at': alert.get('detected_at', '')
        })

print(f"Successfully exported {len(custom_alerts)} custom alerts to: {filepath}")
