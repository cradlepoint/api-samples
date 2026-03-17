#!/usr/bin/env python3
"""
Export all historical location records for each router to individual CSV files.

This script reads a CSV file containing router identifiers, retrieves all historical
location records from the NCM API v2 historical_locations/ endpoint for each router,
and writes the results to individual CSV files in the csv_files folder. Each router
gets its own CSV file named with the router ID and name.

CSV Format:
    Required columns (at least one, case-insensitive):
        - id: Router ID (preferred)
        - mac: MAC address (used if id not found)
        - serial_number: Serial number (used if id and mac not found)
    
    Alternative column names accepted:
        - For ID: "id", "router", "routerid", "router id", "router_id"
        - For MAC: "mac", "mac address", "mac_address"
        - For Serial: "serial_number", "serial number", "serial"
    
    Example CSV:
        id,name
        1234567,My Router
        1234568,Another Router

Usage:
    python "Export Historical Locations.py" <csv_file_path>

Requirements:
    - NCM API v2 keys set as environment variables (X_CP_API_ID, X_CP_API_KEY, X_ECM_API_ID, X_ECM_API_KEY)
    - CSV file with at least one router identifier column
"""

import sys
import csv
import os
import re
from datetime import datetime
import ncm

if len(sys.argv) < 2:
    print('Usage: python "Export Historical Locations.py" <csv_file_path>')
    sys.exit(1)

LOCATION_FIELDS = [
    'accuracy', 'altitude_meters', 'carrier_id', 'cinr', 'created_at',
    'created_at_timeuuid', 'dbm', 'ecio', 'latitude', 'longitude', 'mph',
    'net_device_name', 'rfband', 'rfband_5g', 'rsrp', 'rsrp_5g', 'rsrq',
    'rsrq_5g', 'rssi', 'signal_percent', 'sinr', 'sinr_5g', 'summary'
]

# Read CSV and find router identifiers
with open(sys.argv[1], 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    headers = {h.lower(): h for h in reader.fieldnames}
    
    id_keys = ['id', 'router', 'routerid', 'router id', 'router_id']
    lookup_col = next((headers[k] for k in id_keys if k in headers), None)
    lookup_type = 'id'
    
    if not lookup_col:
        lookup_col = next((headers[k] for k in ['mac', 'mac address', 'mac_address'] if k in headers), None)
        lookup_type = 'mac'
    
    if not lookup_col:
        lookup_col = next((headers[k] for k in ['serial_number', 'serial number', 'serial'] if k in headers), None)
        lookup_type = 'serial_number'
    
    if not lookup_col:
        print(f"Error: No router identifier column found. Available: {reader.fieldnames}")
        sys.exit(1)
    
    print(f"Using '{lookup_col}' column to lookup routers by {lookup_type}")
    values = [row[lookup_col].strip() for row in reader if row[lookup_col].strip()]

# Fetch routers in chunks of 100
all_routers = []
for i in range(0, len(values), 100):
    chunk = values[i:i+100]
    if lookup_type == 'id':
        routers = ncm.get_routers(id__in=chunk)
    elif lookup_type == 'mac':
        routers = ncm.get_routers(mac__in=chunk)
    elif lookup_type == 'serial_number':
        routers = ncm.get_routers(serial_number__in=chunk)
    all_routers.extend(routers)

if not all_routers:
    print("No routers found.")
    sys.exit(0)

print(f"Found {len(all_routers)} routers. Exporting historical locations...\n")

os.makedirs('csv_files', exist_ok=True)
timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
csv_header = ['router_id', 'router_name'] + LOCATION_FIELDS

for router in all_routers:
    router_id = router['id']
    router_name = router.get('name', 'unknown')
    safe_name = re.sub(r'[^\w\-]', '_', router_name)
    
    print(f"Fetching locations for {router_name} (ID: {router_id})...")
    locations = ncm.get_historical_locations(router_id, limit='all')
    
    if not locations:
        print(f"  No historical locations found.")
        continue
    
    filename = f'historical_locations_{router_id}_{safe_name}_{timestamp}.csv'
    filepath = os.path.join('csv_files', filename)
    
    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=csv_header)
        writer.writeheader()
        for loc in locations:
            row = {'router_id': router_id, 'router_name': router_name}
            for field in LOCATION_FIELDS:
                row[field] = loc.get(field, '')
            writer.writerow(row)
    
    print(f"  Exported {len(locations)} records to: {filepath}")

print(f"\nDone!")
