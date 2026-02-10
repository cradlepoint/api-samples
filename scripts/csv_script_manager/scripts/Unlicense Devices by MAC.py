#!/usr/bin/env python3
"""
Unlicense devices in NCM API v3 by MAC address from a CSV file.

This script reads a CSV file containing MAC addresses and removes licenses from the
corresponding devices in NCM. It processes devices in batches of 100 for optimal API
performance. Supports MAC addresses in any format (with colons, dashes, spaces, or
no separators) and automatically normalizes them.

CSV Format:
    Required columns (case-insensitive, automatically detected):
        - MAC address: One of "mac", "mac address", "mac_address", or "macaddress"
    
    Example CSV:
        mac
        003044A2CA75
        00:30:44:A2:CA:76
        mac_address
        003044A2CA77

Usage:
    python "Unlicense Devices by MAC.py" <csv_file_path>

Requirements:
    - NCM API v3 token set as TOKEN or NCM_API_TOKEN environment variable
      (Can be set in the API Keys tab of the CSV Script Manager)
    - CSV file with MAC addresses (can be in any format: with colons, dashes, spaces, or no separators)
"""

import csv
import os
import sys
from ncm import ncm

# Get CSV filename from command-line argument
if len(sys.argv) < 2:
    print("Error: CSV filename required as command-line argument")
    print(f"Usage: {sys.argv[0]} <csv_file_path>")
    sys.exit(1)

csv_filename = sys.argv[1]

# Get token from environment variable
token = os.environ.get('TOKEN') or os.environ.get('NCM_API_TOKEN')

if not token:
    print("Error: Please set your NCM API v3 token as TOKEN environment variable")
    print("You can set it in the API Keys tab of the CSV Script Manager")
    sys.exit(1)

# Possible MAC address column names (case-insensitive)
mac_address_column_names = ["mac", "mac address", "mac_address", "macaddress"]

def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

# Initialize the NCM client
ncm_client = ncm.NcmClientv3(api_key=token, log_events=True)

# Check if CSV file exists
if not os.path.exists(csv_filename):
    print(f"Error: CSV file not found: {csv_filename}")
    sys.exit(1)

# Read all MAC addresses from CSV file
try:
    with open(csv_filename, 'r', encoding='utf-8') as file:
        csv_reader = csv.DictReader(file)
        
        if not csv_reader.fieldnames:
            print("Error: CSV file appears to be empty or invalid")
            sys.exit(1)
        
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
            sys.exit(1)
        
        print(f"Using MAC address column: '{mac_address_column}'")
        
        mac_addresses = []
        for row in csv_reader:
            mac = row[mac_address_column].strip()
            if mac:
                # Normalize MAC address (remove colons, convert to lowercase)
                mac = mac.lower().replace(':', '').replace('-', '').replace(' ', '')
                if mac:
                    mac_addresses.append(mac)
        
        print(f"Found {len(mac_addresses)} devices to unlicense")
        
        # Unlicense devices in chunks of 100
        if mac_addresses:   
            for chunk in chunks(mac_addresses, 100):
                try:
                    result = ncm_client.unlicense_devices(chunk)
                    print(f"Chunk unlicense result: {result}")
                except Exception as e:
                    print(f"Error processing chunk: {e}")
        else:
            print("No MAC addresses found in CSV file")
            
except FileNotFoundError:
    print(f"Error: CSV file not found: {csv_filename}")
    sys.exit(1)
except KeyError as e:
    print(f"Error: Column '{e}' not found in CSV file")
    sys.exit(1)
except Exception as e:
    print(f"Error reading CSV file: {e}")
    sys.exit(1)
