#!/usr/bin/env python3
"""
Add location data columns to existing CSV file.

This script reads a CSV file with router IDs, retrieves location data from NCM API v2,
and adds location columns to the original CSV file.

CSV Format:
    Input columns:
        - router_id (required): Router ID or full router URL
    
    Example input:
        router_id
        1234567
        7654321
    
    Output: Original CSV with added location columns (latitude, longitude, altitude_meters, accuracy, etc.)

Usage:
    python "Export Locations.py" input.csv

Requirements:
    - NCM API keys (X-CP-API-ID, X-CP-API-KEY, X-ECM-API-ID, X-ECM-API-KEY)
      Set in script or as environment variables (X_CP_API_ID, X_CP_API_KEY, X_ECM_API_ID, X_ECM_API_KEY)
"""

import os
import csv
import sys
import ncm

# ============================================================================
# CONFIGURATION
#
# - api_keys: optional inline API keys; leave blank to use environment variables
#   (X_CP_API_ID, X_CP_API_KEY, X_ECM_API_ID, X_ECM_API_KEY) instead.
# ============================================================================

# Optional inline API keys (fallback is environment variables)
api_keys = {
    "X-CP-API-ID": "",
    "X-CP-API-KEY": "",
    "X-ECM-API-ID": "",
    "X-ECM-API-KEY": "",
}

# Load API keys from environment variables if not set in code (maintains backward compatibility)
if not api_keys.get("X-CP-API-ID"):
    api_keys["X-CP-API-ID"] = os.environ.get("X_CP_API_ID", "")
if not api_keys.get("X-CP-API-KEY"):
    api_keys["X-CP-API-KEY"] = os.environ.get("X_CP_API_KEY", "")
if not api_keys.get("X-ECM-API-ID"):
    api_keys["X-ECM-API-ID"] = os.environ.get("X_ECM_API_ID", "")
if not api_keys.get("X-ECM-API-KEY"):
    api_keys["X-ECM-API-KEY"] = os.environ.get("X_ECM_API_KEY", "")

# Filter out empty values
api_keys = {k: v for k, v in api_keys.items() if v}

# Check if we have API keys
if not api_keys:
    print("Error: No API keys found. Please set them either:")
    print("  1. In the script (api_keys dictionary), or")
    print("  2. As environment variables (X_CP_API_ID, X_CP_API_KEY, X_ECM_API_ID, X_ECM_API_KEY)")
    print("     You can set them in the API Keys tab of the Script Manager")
    sys.exit(1)

n2 = ncm.NcmClientv2(api_keys=api_keys, log_events=True)

def main():
    """Main function to add location data to CSV."""
    
    # Get CSV filename from command line or default
    csv_filename = sys.argv[1] if len(sys.argv) > 1 else 'input.csv'
    filepath = os.path.join('csv_files', csv_filename)
    
    if not os.path.exists(filepath):
        print(f"Error: File not found: {filepath}")
        sys.exit(1)
    
    # Read existing CSV
    with open(filepath, 'r', newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        rows = list(reader)
        original_fieldnames = reader.fieldnames
    
    if not rows:
        print("Error: CSV file is empty.")
        sys.exit(1)
    
    # Support common router ID column variants (case-insensitive)
    id_candidates = ['id', 'router', 'routerid', 'router id', 'router_id']
    normalized = {
        col.lower().strip().replace(' ', '').replace('_', ''): col
        for col in original_fieldnames
    }
    
    id_column = None
    for name in id_candidates:
        key = name.lower().strip().replace(' ', '').replace('_', '')
        if key in normalized:
            id_column = normalized[key]
            break
    
    if not id_column:
        print(f"Error: Could not find router ID column. Available columns: {', '.join(original_fieldnames)}")
        print("Expected one of: id, router, routerid, router id, router_id (case-insensitive).")
        sys.exit(1)
    
    print(f"Processing {len(rows)} routers...")
    
    # Get all locations once
    locations = n2.get_locations()
    location_map = {}
    for loc in locations:
        router_url = loc.get('router', '')
        router_id = router_url.split('/')[-2] if router_url else ''
        if router_id:
            location_map[router_id] = loc
    
    # Determine new columns - only specific location fields
    new_columns = ['latitude', 'longitude', 'altitude_meters', 'accuracy', 'method']
    
    # Add location data to rows
    for row in rows:
        router_id = str(row[id_column]).split('/')[-2] if '/' in str(row[id_column]) else str(row[id_column])
        loc = location_map.get(router_id, {})
        for col in new_columns:
            row[col] = loc.get(col, '')
    
    # Write back to same file
    all_fieldnames = list(original_fieldnames) + new_columns
    with open(filepath, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=all_fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    
    print(f"Successfully added location columns to: {filepath}")

if __name__ == '__main__':
    main()
