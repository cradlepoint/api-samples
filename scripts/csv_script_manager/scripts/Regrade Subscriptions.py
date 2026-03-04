#!/usr/bin/env python3
"""
Apply or regrade device subscriptions in NCM API v3 from a CSV file.

This script reads a CSV file containing device identifiers and subscription IDs, then applies
or regrades subscriptions to the corresponding devices in NCM. It processes devices in
chunks of 100 for optimal API performance and groups devices by subscription ID for
efficient batch processing.

CSV Format:
    Required columns (case-insensitive):
        - id: Router ID (or use mac/serial_number as alternative)
        - subscription_id: Subscription ID (or "subscription")
    
    Alternative identifier columns:
        - For ID: "id", "router", "routerid", "router id", "router_id"
        - For MAC: "mac", "mac address", "mac_address", "macaddress"
        - For Serial: "serial_number", "serial number", "serial"
    
    Example CSV:
        id,subscription_id
        1234567,BA-NCADV
        1234568,BA-NCADV

Usage:
    python "Regrade Subscriptions.py" <csv_filename>

Requirements:
    - NCM API v3 token set as TOKEN or NCM_API_TOKEN environment variable
    - CSV file with device identifiers and subscription IDs
"""

import csv
import os
import sys
from ncm import ncm
import ncm as ncm_v2

if len(sys.argv) < 2:
    print("Error: CSV filename required")
    sys.exit(1)

csv_filename = sys.argv[1]
token = os.environ.get("TOKEN") or os.environ.get("NCM_API_TOKEN")

if not token:
    print("Error: TOKEN environment variable not set")
    sys.exit(1)

def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

ncm_client = ncm.NcmClientv3(api_key=token, log_events=True)

with open(csv_filename, 'r') as f:
    reader = csv.DictReader(f)
    headers = {h.lower(): h for h in reader.fieldnames}
    
    # Find identifier column
    id_keys = ['id', 'router', 'routerid', 'router id', 'router_id']
    id_col = next((headers[k] for k in id_keys if k in headers), None)
    
    if not id_col:
        mac_col = next((headers[k] for k in ['mac', 'mac address', 'mac_address', 'macaddress'] if k in headers), None)
        serial_col = next((headers[k] for k in ['serial_number', 'serial number', 'serial'] if k in headers), None)
        if not mac_col and not serial_col:
            print("Error: No device identifier column found")
            sys.exit(1)
    
    # Find subscription column
    sub_col = next((headers[k] for k in ['subscription_id', 'subscription', 'subscription id'] if k in headers), None)
    if not sub_col:
        print("Error: No subscription_id column found")
        sys.exit(1)
    
    devices = []
    for row in reader:
        # Get device MAC
        if id_col:
            router_id = row[id_col].strip()
            routers = ncm_v2.get_routers(id=router_id)
        elif mac_col:
            routers = ncm_v2.get_routers(mac=row[mac_col].strip())
        else:
            routers = ncm_v2.get_routers(serial_number=row[serial_col].strip())
        
        if routers:
            mac = routers[0]['mac'].lower().replace(':', '')
            sub_id = row[sub_col].strip()
            devices.append({'mac': mac, 'subscription_id': sub_id})

print(f"Found {len(devices)} devices to regrade")

# Group by subscription_id
subscription_groups = {}
for device in devices:
    sub_id = device['subscription_id']
    if sub_id not in subscription_groups:
        subscription_groups[sub_id] = []
    subscription_groups[sub_id].append(device['mac'])

for subscription_id, mac_addresses in subscription_groups.items():
    print(f"Processing {len(mac_addresses)} devices with subscription: {subscription_id}")
    for chunk in chunks(mac_addresses, 100):
        try:
            result = ncm_client.regrade(subscription_id, chunk)
            print(f"Chunk result: {result}")
        except Exception as e:
            print(f"Error: {e}")
