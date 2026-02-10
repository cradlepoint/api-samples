#!/usr/bin/env python3
"""
Apply or regrade device subscriptions in NCM API v3 by MAC address from a CSV file.

This script reads a CSV file containing MAC addresses and subscription IDs, then applies
or regrades subscriptions to the corresponding devices in NCM. It processes devices in
chunks of 100 for optimal API performance and groups devices by subscription ID for
efficient batch processing. Supports MAC addresses in any format (with or without separators).

CSV Format:
    Required columns (case-insensitive, automatically detected):
        - MAC address: one of "mac", "mac address", "mac_address", or "macaddress"
        - Subscription ID: one of "subscription_id", "subscription", or "subscription id"
    
    Example CSV:
        mac,subscription_id
        003044A2CA75,BA-NCADV
        00:30:44:A2:CA:76,BA-NCADV
        mac_address,subscription
        003044A2CA77,BA-NCADV

Usage:
    python "Regrade Subscriptions by MAC.py" <csv_filename>

Requirements:
    - NCM API v3 token set as TOKEN or NCM_API_TOKEN environment variable
      (can be set in the API Keys tab of the CSV Script Manager)
    - CSV file with MAC addresses and subscription IDs
    - MAC addresses can be in any format (colons, dashes, spaces, or no separators)
"""

import csv
import os
import sys
from ncm import ncm

if len(sys.argv) < 2:
    print("Error: CSV filename required as command-line argument")
    print(f"Usage: {sys.argv[0]} <csv_filename>")
    sys.exit(1)

csv_filename = sys.argv[1]

# Get token from environment variable
token = os.environ.get("TOKEN") or os.environ.get("NCM_API_TOKEN")

# Possible MAC address column names (case-insensitive)
mac_address_column_names = ["mac", "mac address", "mac_address", "macaddress"]

# Possible subscription_id column names (case-insensitive)
subscription_id_column_names = ["subscription_id", "subscription", "subscription id"]

if not token:
    print("Error: Please set your NCM API v3 token as TOKEN or NCM_API_TOKEN environment variable")
    print("You can set it in the API Keys tab of the CSV Script Manager")
    sys.exit(1)

def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

# Initialize the NCM client
ncm_client = ncm.NcmClientv3(api_key=token, log_events=True)

# Read MAC addresses and subscription IDs from CSV file
try:
    with open(csv_filename, 'r') as file:
        csv_reader = csv.DictReader(file)
        # Get the actual column names from the CSV
        csv_columns = [col.lower() for col in csv_reader.fieldnames]
        
        # Find the MAC address column (case-insensitive match)
        mac_address_column = None
        for col_name in mac_address_column_names:
            if col_name.lower() in csv_columns:
                # Find the actual column name (preserving original case)
                for original_col in csv_reader.fieldnames:
                    if original_col.lower() == col_name.lower():
                        mac_address_column = original_col
                        break
                if mac_address_column:
                    break
        
        if not mac_address_column:
            print(f"Error: Could not find MAC address column. Looking for: {', '.join(mac_address_column_names)}")
            print(f"Available columns: {', '.join(csv_reader.fieldnames)}")
            exit(1)
        
        print(f"Using MAC address column: '{mac_address_column}'")
        
        # Find the subscription_id column (case-insensitive match)
        subscription_id_column = None
        for col_name in subscription_id_column_names:
            if col_name.lower() in csv_columns:
                # Find the actual column name (preserving original case)
                for original_col in csv_reader.fieldnames:
                    if original_col.lower() == col_name.lower():
                        subscription_id_column = original_col
                        break
                if subscription_id_column:
                    break
        
        if not subscription_id_column:
            print(f"Error: Could not find subscription_id column. Looking for: {', '.join(subscription_id_column_names)}")
            print(f"Available columns: {', '.join(csv_reader.fieldnames)}")
            exit(1)
        
        print(f"Using subscription_id column: '{subscription_id_column}'")
        
        devices = []
        for row in csv_reader:
            mac = row[mac_address_column].lower().strip().replace(':', '')
            sub_id = row[subscription_id_column].strip()
            devices.append({'mac': mac, 'subscription_id': sub_id})
except FileNotFoundError:
    print(f"Error: CSV file '{csv_filename}' not found")
    exit(1)
except KeyError as e:
    print(f"Error: Column '{e}' not found in CSV file")
    exit(1)
except Exception as e:
    print(f"Error reading CSV file: {e}")
    exit(1)

print(f"Found {len(devices)} devices to regrade. Processing in chunks of 100...")

# Group devices by subscription_id for efficient processing
subscription_groups = {}
for device in devices:
    sub_id = device['subscription_id']
    if sub_id not in subscription_groups:
        subscription_groups[sub_id] = []
    subscription_groups[sub_id].append(device['mac'])

# Regrade devices in chunks of 100, grouped by subscription_id
if devices:
    for subscription_id, mac_addresses in subscription_groups.items():
        print(f"Processing {len(mac_addresses)} devices with subscription_id: {subscription_id}")
        for chunk in chunks(mac_addresses, 100):
            try:
                result = ncm_client.regrade(subscription_id, chunk)
                print(f"Chunk regrade result for {subscription_id}: {result}")
            except Exception as e:
                print(f"Error processing chunk for {subscription_id}: {e}")
else:
    print("No devices found in CSV file")
