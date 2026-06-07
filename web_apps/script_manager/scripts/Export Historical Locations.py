#!/usr/bin/env python3
"""
Export historical location records for each router to individual CSV files.

This script reads a CSV file containing router identifiers, retrieves historical
location records from the NCM API v2 historical_locations/ endpoint for each router,
and writes the results to individual CSV files in the csv_files folder. Each router
gets its own CSV file named with the router ID and name.

Optionally filter results to a specific date/time range by setting START_DATE and
END_DATE below. If both are left empty, all historical locations are exported.

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

Date/Time Filtering:
    Edit START_DATE and END_DATE at the top of this script to filter results.
    Accepted formats:
        Date only:      "YYYY-MM-DD"            (time defaults to 00:00:00)
        Date and time:  "YYYY-MM-DDTHH:MM:SS"   (ISO 8601)
        Date and time:  "YYYY-MM-DD HH:MM:SS"

    You can set one or both. Leave as "" to skip that boundary.

    Examples:
        START_DATE = "2025-01-01"                   # Everything from Jan 1 2025 onward
        END_DATE   = "2025-06-30"                   # Everything up to Jun 30 2025
        START_DATE = "2025-03-01T08:00:00"          # From Mar 1 at 8 AM
        END_DATE   = "2025-03-01T17:00:00"          # To Mar 1 at 5 PM
        START_DATE = "2025-03-01 08:00:00"          # Space-separated also works

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
ncm.set_api_keys(log_events=True)

# ============================================================================
# DATE/TIME RANGE FILTER
#
# Set these to filter historical locations to a specific time window.
# Leave as "" to export all records (no filtering on that boundary).
#
# Accepted formats:
#   "YYYY-MM-DD"             - date only (time defaults to 00:00:00)
#   "YYYY-MM-DDTHH:MM:SS"   - ISO 8601 date and time
#   "YYYY-MM-DD HH:MM:SS"   - date and time with space separator
# ============================================================================
START_DATE = ""   # e.g. "2025-01-01" or "2025-03-01T08:00:00"
END_DATE   = ""   # e.g. "2025-06-30" or "2025-03-01T17:00:00"

if len(sys.argv) < 2:
    print('Usage: python "Export Historical Locations.py" <csv_file_path>')
    sys.exit(1)

DATETIME_FORMATS = [
    '%Y-%m-%dT%H:%M:%S',
    '%Y-%m-%d %H:%M:%S',
    '%Y-%m-%d',
]


def parse_datetime(value):
    """Parse a date or datetime string into ISO 8601 format for the API."""
    for fmt in DATETIME_FORMATS:
        try:
            return datetime.strptime(value, fmt).strftime('%Y-%m-%dT%H:%M:%S')
        except ValueError:
            continue
    print(f"Error: Invalid date/time format: '{value}'")
    print("Accepted formats: YYYY-MM-DD, YYYY-MM-DDTHH:MM:SS, YYYY-MM-DD HH:MM:SS")
    sys.exit(1)

LOCATION_FIELDS = [
    'accuracy', 'altitude_meters', 'carrier_id', 'cinr', 'created_at',
    'created_at_timeuuid', 'dbm', 'ecio', 'latitude', 'longitude', 'mph',
    'net_device_name', 'rfband', 'rfband_5g', 'rsrp', 'rsrp_5g', 'rsrq',
    'rsrq_5g', 'rssi', 'signal_percent', 'sinr', 'sinr_5g', 'summary'
]

# Build date range filter kwargs for the API
date_filter = {}
if START_DATE.strip():
    date_filter['created_at__gt'] = parse_datetime(START_DATE.strip())
    print(f"Filtering: after {date_filter['created_at__gt']}")
if END_DATE.strip():
    date_filter['created_at__lte'] = parse_datetime(END_DATE.strip())
    print(f"Filtering: before {date_filter['created_at__lte']}")

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
    locations = ncm.get_historical_locations(router_id, limit='all', **date_filter)
    
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
