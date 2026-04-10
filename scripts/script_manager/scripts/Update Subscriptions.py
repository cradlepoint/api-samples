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
    python "Update Subscriptions.py" <csv_filename>

Requirements:
    - NCM API v3 token set as TOKEN or NCM_API_TOKEN environment variable
    - CSV file with device identifiers and subscription IDs
"""

import csv
import os
import re
import sys
from ncm import ncm

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
        sub_id = row[sub_col].strip()

        # If CSV has MAC directly, use it without an API call
        if not id_col and mac_col:
            mac = row[mac_col].strip().upper().replace(':', '').replace('-', '')
            if not mac:
                print(f"Warning: Empty MAC in CSV row, skipping")
                continue
            devices.append({'mac': mac, 'subscription_id': sub_id})
            continue

        # For serial or ID lookups, use the v3 client's get_asset_endpoints
        if not id_col and serial_col:
            assets = ncm_client.get_asset_endpoints(serial_number=row[serial_col].strip())
        else:
            assets = ncm_client.get_asset_endpoints(id=row[id_col].strip())

        if assets:
            # v3 asset_endpoints returns mac_address in bare uppercase hex (e.g. 0030441A2B3C)
            mac = assets[0].get('attributes', {}).get('mac_address', '').upper().replace(':', '').replace('-', '')
            if mac:
                devices.append({'mac': mac, 'subscription_id': sub_id})
            else:
                print(f"Warning: No MAC found for device {row.get(id_col or serial_col, 'unknown')}")
        else:
            print(f"Warning: Device not found: {row.get(id_col or serial_col, 'unknown')}")

print(f"Found {len(devices)} devices to regrade")

# Validate MAC format (must be exactly 12 hex digits)
valid_mac = re.compile(r'^[0-9A-F]{12}$')
invalid_count = 0

# Group by subscription_id, deduplicating MACs within each group
subscription_groups = {}
for device in devices:
    sub_id = device['subscription_id']
    mac = device['mac']
    if not valid_mac.match(mac):
        invalid_count += 1
        print(f"Warning: Skipping invalid MAC '{mac}' (must be 12 hex digits)")
        continue
    if sub_id not in subscription_groups:
        subscription_groups[sub_id] = set()
    subscription_groups[sub_id].add(mac)

if invalid_count:
    print(f"Skipped {invalid_count} devices with invalid MACs")

total_success = 0
total_failed = 0
total_chunks = 0

for subscription_id, mac_set in subscription_groups.items():
    mac_addresses = list(mac_set)
    print(f"Processing {len(mac_addresses)} unique devices with subscription: {subscription_id}")
    for chunk in chunks(mac_addresses, 100):
        total_chunks += 1
        try:
            result = ncm_client.regrade(subscription_id, chunk)
            print(f"Chunk result: {result}")
            total_success += len(chunk)
        except Exception as e:
            print(f"Error: {e}")
            total_failed += len(chunk)

dupes = len(devices) - invalid_count - sum(len(s) for s in subscription_groups.values())
print(f"\n--- Summary ---")
print(f"CSV rows:     {len(devices)}")
print(f"Invalid MACs: {invalid_count}")
print(f"Duplicates:   {dupes}")
print(f"Submitted:    {total_success + total_failed} in {total_chunks} chunks")
print(f"Succeeded:    {total_success}")
print(f"Failed:       {total_failed}")
