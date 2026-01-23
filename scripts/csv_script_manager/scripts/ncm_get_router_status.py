#!/usr/bin/env python3
"""
Get router status and information from NCM using identifiers from a CSV file.

This script reads a CSV file containing router identifiers (ID, MAC address, or serial
number) and retrieves the corresponding router information from NCM. It displays a
formatted table showing router ID, name, and state. Automatically detects which
identifier type is available in the CSV and uses the most appropriate lookup method.

CSV Format:
    Required columns (at least one, case-insensitive):
        - id: Router ID (preferred)
        - mac: MAC address (used if id not found)
        - serial_number: Serial number (used if id and mac not found)
    
    Alternative column names accepted:
        - For ID: "id", "router id", "router_id"
        - For MAC: "mac", "mac address", "mac_address"
        - For Serial: "serial_number", "serial number", "serial"
    
    Example CSV:
        id,name,mac,serial_number
        1234567,My Router,003044A2CA75,WC2338TA003678

Usage:
    python3 ncm_get_router_status.py <csv_file_path>

Requirements:
    - NCM API access (configured via ncm module)
    - CSV file with at least one router identifier column
"""
import sys
import csv
import ncm

if len(sys.argv) < 2:
    print("Usage: python3 ncm_get_router_status.py <csv_file_path>")
    sys.exit(1)

# Read CSV and find router identifiers
with open(sys.argv[1], 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    headers = {h.lower(): h for h in reader.fieldnames}
    
    # Try to find ID column first (case-insensitive)
    lookup_col = next((headers[k] for k in ['id', 'router id', 'router_id'] if k in headers), None)
    lookup_type = 'id'
    
    # If no ID column, try MAC
    if not lookup_col:
        lookup_col = next((headers[k] for k in ['mac', 'mac address', 'mac_address'] if k in headers), None)
        lookup_type = 'mac'
    
    # If no MAC column, try serial number
    if not lookup_col:
        lookup_col = next((headers[k] for k in ['serial_number', 'serial number', 'serial'] if k in headers), None)
        lookup_type = 'serial_number'
    
    if not lookup_col:
        print(f"Error: No router identifier column found. Available: {reader.fieldnames}")
        print("Expected one of: id, router id, router_id, mac, mac address, mac_address, serial_number, serial number, serial")
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

# Print results
print(f"{'ID':<20} {'Name':<30} {'State':<20}")
print("-" * 70)
for r in all_routers:
    print(f"{r.get('id', 'N/A'):<20} {r.get('name', 'N/A'):<30} {r.get('state', 'N/A'):<20}")