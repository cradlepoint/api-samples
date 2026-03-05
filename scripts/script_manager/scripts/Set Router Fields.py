#!/usr/bin/env python3
"""Set router fields from a CSV file using NCM API.

Reads router identifiers and field values from CSV and updates routers using
ncm.set_router_fields(). Updates only the fields provided in the CSV.
Empty cells will clear the field value (set to empty string).

CSV Format:
    Required columns (case-insensitive):
        - id: Router ID (or use mac/serial_number as alternative)
    
    Optional columns (any combination):
        - name: Router name
        - description: Router description
        - asset_id: Asset ID
        - custom1: Custom field 1
        - custom2: Custom field 2
    
    Alternative identifier columns:
        - For ID: "id", "router", "routerid", "router id", "router_id"
        - For MAC: "mac", "mac address", "mac_address"
        - For Serial: "serial_number", "serial number", "serial"
        - For Description: "description", "desc"
    
    Example CSV:
        id,name,desc,asset_id,custom1,custom2
        1234567,New Name,New Description,ASSET-001,Value1,Value2

Usage:
    python "Set Router Fields.py" <csv_file_path>

Requirements:
    - NCM API access (configured via ncm module)
    - CSV file with router identifier and at least one field to update
"""
import sys
import csv
import ncm

if len(sys.argv) < 2:
    print('Usage: python "Set Router Fields.py" <csv_file_path>')
    sys.exit(1)

with open(sys.argv[1], 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    headers = {h.lower(): h for h in reader.fieldnames}
    
    # Find identifier column
    id_keys = ['id', 'router', 'routerid', 'router id', 'router_id']
    id_col = next((headers[k] for k in id_keys if k in headers), None)
    
    if not id_col:
        mac_col = next((headers[k] for k in ['mac', 'mac address', 'mac_address'] if k in headers), None)
        serial_col = next((headers[k] for k in ['serial_number', 'serial number', 'serial'] if k in headers), None)
        if not mac_col and not serial_col:
            print("Error: No router identifier column found")
            sys.exit(1)
    
    # Map field columns
    field_map = {}
    for field in ['name', 'description', 'asset_id', 'custom1', 'custom2']:
        if field in headers:
            field_map[field] = headers[field]
        elif field == 'description' and 'desc' in headers:
            field_map[field] = headers['desc']
    
    if not field_map:
        print("Error: No fields to update found in CSV")
        sys.exit(1)
    
    print(f"Updating fields: {', '.join(field_map.keys())}")
    
    for row in reader:
        # Get router ID
        if id_col:
            router_id = row[id_col].strip()
        else:
            # Lookup by MAC or serial
            if mac_col and row[mac_col].strip():
                routers = ncm.get_routers(mac=row[mac_col].strip())
            elif serial_col and row[serial_col].strip():
                routers = ncm.get_routers(serial_number=row[serial_col].strip())
            else:
                continue
            router_id = routers[0]['id'] if routers else None
        
        if not router_id:
            continue
        
        # Build fields dict
        fields = {field: row[col].strip() for field, col in field_map.items()}
        
        if fields:
            ncm.set_router_fields(router_id, **fields)
            print(f"Updated router {router_id}: {fields}")
