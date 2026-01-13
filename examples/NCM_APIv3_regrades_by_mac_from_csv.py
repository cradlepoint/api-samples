# This script applies/regrades a subscription to devices by MAC address using the NCM library (pip install -U ncm)
# It reads a CSV file with device details and applies/regrades subscriptions to the devices in NCM in chunks of 100
# Usage: python NCM_APIv3_regrades_by_mac_from_csv.py <csv_filename> [token]
# Token can be set via command-line argument, token environment variable, or hardcoded in the script
# CSV file must contain columns for MAC addresses and subscription_id
# Column names are automatically detected (case-insensitive):
#   MAC address: "mac", "mac address", or "mac_address"
#   Subscription ID: "subscription_id", "subscription", or "subscription id"

import csv
import os
import sys
from ncm import ncm

# Get CSV filename from command-line argument
if len(sys.argv) < 2:
    print("Error: CSV filename required as command-line argument")
    print(f"Usage: {sys.argv[0]} <csv_filename> [token]")
    exit(1)

csv_filename = sys.argv[1]

# Get token from command-line argument, environment variable, or use hardcoded value
if len(sys.argv) >= 3:
    token = sys.argv[2]
else:
    token = os.environ.get("token", "Put Your NCM APIv3 Token Here")

# Possible MAC address column names (case-insensitive)
mac_address_column_names = ["mac", "mac address", "mac_address"]

# Possible subscription_id column names (case-insensitive)
subscription_id_column_names = ["subscription_id", "subscription", "subscription id"]

# Check if token is still placeholder
if token == "Put Your NCM APIv3 Token Here":
    print("Error: Please set your NCM APIv3 token either:")
    print("  1. Pass it as a command-line argument: <csv_filename> <token>")
    print("  2. Set token environment variable, or")
    print("  3. Hardcode it in the script")
    exit(1)

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
