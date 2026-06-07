#!/usr/bin/env python3
"""
Bulk configure groups in NCM from CSV file.

Reads CSV with group IDs and configuration values, then applies configurations
using the NCM library's patch_group_configuration method.

CSV Format:
    Required columns (case-insensitive):
        - id: Group ID
    
    Optional columns (customize based on your config):
        - ssid_1: SSID for radio 0
        - ssid_2: SSID for radio 1
        - (add any other columns needed for your configuration)
    
    Example CSV:
        id,ssid_1,ssid_2
        12345,MyWiFi,GuestWiFi
        12346,OfficeWiFi,VisitorWiFi

Usage:
    python "Configure Groups.py"                    # Uses default groups.csv and API keys from code/env
    python "Configure Groups.py" <csv_file_path>    # Uses specified CSV file and API keys from code/env

Requirements:
    - NCM API keys (X-CP-API-ID, X-CP-API-KEY, X-ECM-API-ID, X-ECM-API-KEY)
      Set in script or as environment variables (X_CP_API_ID, X_CP_API_KEY, X_ECM_API_ID, X_ECM_API_KEY)
    - CSV file with group IDs and configuration values

To customize this script:
    1. Export groups.csv from the Group View in NCM - make sure "ID" Column is included
    2. Use NCM's group-level Edit Config screen to build your configuration
    3. Copy the pending config output and paste it into the build_config() return value
    4. Update groups.csv to contain the columns that need to be applied to the group level config
    5. Update build_config() to reference groups column headers with row_data.get('column_name')
    6. Update csv_file variable if using a different filename than 'groups.csv'
"""

import csv
import os
import sys
import ncm

# ============================================================================
# CONFIGURATION
#
# - csv_file: default CSV filename used when no command-line argument is given
# - api_keys: optional inline API keys; leave blank to use environment variables
#   (X_CP_API_ID, X_CP_API_KEY, X_ECM_API_ID, X_ECM_API_KEY) instead.
# ============================================================================

# Default CSV filename (used if no filename is passed on the command line)
csv_file = 'groups.csv'

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

n2 = ncm.NcmClientv2(api_keys=api_keys)

def build_config(row_data):
    """Return group configuration with values from CSV row.

    To update this configuration:
    1. Go to NCM group-level Edit Config screen
    2. Make your changes and view pending config
    3. Copy the pending config JSON and paste below the return line
    4. Replace static values with row_data.get('column_name') for CSV columns

    Args:
        row_data (dict): Dictionary with CSV column headers as keys.

    Returns:
        list: Group configuration list.
    """
    return \
        [
        {
            "wlan": {
                "radio": {
                    "0": {
                        "bss": {
                            "1": {
                                "enabled": True,
                                "ssid": row_data.get('ssid_1', '')
                            }
                        },
                        "enabled": True
                    },
                    "1": {
                        "bss": {
                            "1": {
                                "enabled": True,
                                "ssid": row_data.get('ssid_2', '')
                            }
                        },
                        "enabled": True
                    }
                }
            }
        },
        []
    ]


def load_csv(filename):
    """Return a dictionary of group_ids containing config values from csv.

    Args:
        filename: Name of csv file.

    Returns:
        Dictionary of group configs keyed by group_id.
    """
    group_configs = {}
    try:
        with open(filename, 'rt', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    group_id = int(row['id'])
                    group_configs[group_id] = row
                except (ValueError, KeyError) as e:
                    print(f'Skipping invalid row: {row}, error: {e}')
    except Exception as e:
        print(f'Exception reading csv file: {e}')
    return group_configs


def main():
    """Main function to process group configurations.
    
    Processes each group in the CSV file by:
    1. Applying group configuration using patch_group_configuration
    """
    # Get CSV filename from command-line argument if provided, otherwise use default
    csv_filename = csv_file
    if len(sys.argv) >= 2:
        csv_filename = sys.argv[1]
    
    # Check if CSV file exists
    if not os.path.exists(csv_filename):
        print(f"Error: CSV file not found: {csv_filename}")
        sys.exit(1)
    
    print(f"Processing CSV file: {csv_filename}")
    rows = load_csv(csv_filename)

    for group_id, row_data in rows.items():
        try:
            config = {'configuration': build_config(row_data)}
            
            n2.patch_group_configuration(
                group_id=group_id, config_json=config)
            
            print(f'Successfully updated group {group_id}')
        except Exception as e:
            print(f'Error patching config for group {group_id}: {e}')

    print('Done!')


if __name__ == '__main__':
    main()
