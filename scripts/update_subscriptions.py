#!/usr/bin/env python3
"""
Update Subscriptions - Standalone Script

Reads a CSV file with device identifiers and subscription IDs, then applies
or regrades subscriptions to the corresponding devices in NCM.

Devices are processed in chunks of 100 and grouped by subscription ID for
efficient batch processing.

Usage:
    Double-click on Windows, or run: python update_subscriptions.py
    Optional args: python update_subscriptions.py [csv_filename] [token]

CSV Format:
    Required columns (case-insensitive):
        - mac: Device MAC address
        - subscription_id: Subscription ID (or "subscription")

    MAC column variants: "mac", "mac address", "mac_address", "macaddress"

    Example CSV:
        mac,subscription_id
        00:30:44:1A:2B:3C,BA-NCADV
        003044AABBCC,BA-NCADV

Configuration:
    Set your API token below, or as an environment variable.
"""

import os
import sys
import csv

script_dir = os.path.dirname(os.path.abspath(__file__))

try:
    from ncm import ncm
except ImportError:
    print("Error: 'ncm' library not found. Install it with: pip install ncm")
    input("Press Enter to exit...")
    sys.exit(1)

# ============================================================================
# CONFIGURATION - Set your API token here
# ============================================================================

TOKEN = ""  # APIv3 token (or set TOKEN / NCM_API_TOKEN env var, or pass as 2nd arg)

CSV_FILENAME = "devices.csv"  # Default CSV filename

# ============================================================================


def load_token():
    """Load APIv3 token from arg, config, or environment variables."""
    if len(sys.argv) >= 3:
        return sys.argv[2]
    return TOKEN or os.environ.get("TOKEN") or os.environ.get("NCM_API_TOKEN") or os.environ.get("token")


def find_column(fieldnames, candidates):
    """Find a column from common name variants, handling BOM and whitespace."""
    normalized = {
        col.lstrip('\ufeff').lower().strip().replace(" ", "").replace("_", ""): col
        for col in fieldnames
    }
    for name in candidates:
        key = name.lower().strip().replace(" ", "").replace("_", "")
        if key in normalized:
            return normalized[key]
    return None


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def main():
    # Resolve CSV path
    csv_filename = sys.argv[1] if len(sys.argv) > 1 else CSV_FILENAME
    filepath = os.path.join(script_dir, csv_filename) if not os.path.isabs(csv_filename) else csv_filename

    if not os.path.exists(filepath):
        print(f"Error: File not found: {filepath}")
        input("Press Enter to exit...")
        sys.exit(1)

    # Load and validate APIv3 token
    token = load_token()
    if not token:
        print("Error: No APIv3 token found. Set TOKEN in the script or as an environment variable.")
        input("Press Enter to exit...")
        sys.exit(1)

    # Initialize v3 client for regrades
    ncm_v3 = ncm.NcmClientv3(api_key=token, log_events=True)

    # Read CSV
    with open(filepath, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        if not fieldnames:
            print("Error: CSV file is empty or has no headers.")
            input("Press Enter to exit...")
            sys.exit(1)

        # Find MAC column
        mac_col = find_column(fieldnames, ['mac', 'mac address', 'mac_address', 'macaddress'])
        if not mac_col:
            print(f"Error: No MAC address column found. Available: {', '.join(fieldnames)}")
            print("Expected one of: mac, mac address, mac_address (case-insensitive)")
            input("Press Enter to exit...")
            sys.exit(1)

        # Find subscription column
        sub_col = find_column(fieldnames, ['subscription_id', 'subscription', 'subscription id'])
        if not sub_col:
            print(f"Error: No subscription_id column found. Available: {', '.join(fieldnames)}")
            input("Press Enter to exit...")
            sys.exit(1)

        rows = list(reader)

    print(f"Processing {len(rows)} rows...", flush=True)

    devices = []
    for i, row in enumerate(rows, 1):
        sub_id = row[sub_col].strip()
        mac = row[mac_col].strip()
        if not sub_id or not mac:
            print(f"  Row {i}: Skipping, missing mac or subscription_id")
            continue
        mac = mac.lower().replace(':', '')
        devices.append({'mac': mac, 'subscription_id': sub_id})

    print(f"\nFound {len(devices)} devices to regrade", flush=True)

    if not devices:
        print("No devices to process.")
        input("Press Enter to exit...")
        sys.exit(0)

    # Group by subscription_id
    subscription_groups = {}
    for device in devices:
        sub_id = device['subscription_id']
        if sub_id not in subscription_groups:
            subscription_groups[sub_id] = []
        subscription_groups[sub_id].append(device['mac'])

    # Process regrades in chunks of 100
    for subscription_id, mac_addresses in subscription_groups.items():
        print(f"\nProcessing {len(mac_addresses)} devices with subscription: {subscription_id}")
        for chunk in chunks(mac_addresses, 100):
            try:
                result = ncm_v3.regrade(subscription_id, chunk)
                print(f"  Chunk result: {result}")
            except Exception as e:
                print(f"  Error: {e}")

    print("\nDone!", flush=True)
    input("Press Enter to exit...")


if __name__ == "__main__":
    main()
