#!/usr/bin/env python3
"""
Script to generate a CSV report of licensed routers from subscriptions
and identify unlicensed routers.

This script:
1. Gets all subscriptions with end_time later than yesterday
2. Gets all asset_endpoints from the system
3. Correlates asset_endpoints with subscriptions by matching subscription IDs
4. Creates a CSV report with router MAC, serial, subscription details
5. Identifies unlicensed routers (not in any subscription)
"""

import csv
import time
from datetime import datetime, timedelta, timezone
import ncm

# Optional: Set your NCM API v3 token here, or use NCM_API_TOKEN/TOKEN environment variable
NCM_API_TOKEN = None  # Set to your token string if you want to hardcode it

def get_yesterday_iso():
    """Get yesterday's date in ISO format (YYYY-MM-DDTHH:MM:SSZ)"""
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    return yesterday.strftime("%Y-%m-%dT00:00:00Z")


def _get_v3_client():
    """Get the v3 client from the singleton."""
    client = ncm.get_ncm_instance()
    if hasattr(client, 'v3'):
        return client.v3
    if isinstance(client, ncm.NcmClientv3):
        return client
    raise RuntimeError("NCM v3 client not available. Please set NCM_API_TOKEN or TOKEN environment variable.")


def get_subscriptions_with_asset_endpoints(end_time_gt):
    """
    Get all subscriptions with end_time greater than the specified date.
    Returns subscriptions with their asset_endpoints relationship links.
    """
    start_time = time.time()
    client = _get_v3_client()
    print(f"Fetching subscriptions with end_time > {end_time_gt}...")
    subscriptions = client.get_subscriptions(end_time__gt=end_time_gt, limit=0)
    elapsed = time.time() - start_time
    
    if not subscriptions:
        print("No subscriptions found.")
        return []
    
    print(f"Found {len(subscriptions)} subscriptions in {elapsed:.2f} seconds.")
    return subscriptions


def get_all_asset_endpoints():
    """
    Get all asset_endpoints from the system.
    """
    start_time = time.time()
    client = _get_v3_client()
    print("Fetching all asset_endpoints...")
    asset_endpoints = client.get_asset_endpoints(limit=0)
    elapsed = time.time() - start_time
    print(f"Found {len(asset_endpoints)} total asset_endpoints in {elapsed:.2f} seconds.")
    return asset_endpoints


def correlate_subscriptions_and_asset_endpoints(subscriptions, asset_endpoints):
    """
    Correlate asset_endpoints with subscriptions by matching subscription IDs.
    Returns:
        - List of CSV rows with subscription data
        - Set of (mac_address, serial_number) tuples for licensed routers
    """
    start_time = time.time()
    
    # Build a map of subscription_id -> subscription details
    subscription_map = {}
    for subscription in subscriptions:
        sub_id = subscription.get('id', '')
        attributes = subscription.get('attributes', {})
        subscription_map[sub_id] = {
            'name': attributes.get('name', ''),
            'start_time': attributes.get('start_time', ''),
            'end_time': attributes.get('end_time', ''),
            'id': sub_id
        }
    
    print(f"Built subscription map with {len(subscription_map)} subscriptions")
    
    # Process asset_endpoints and match them to subscriptions
    csv_rows = []
    licensed_combos = set()
    
    for asset_endpoint in asset_endpoints:
        asset_attrs = asset_endpoint.get('attributes', {})
        relationships = asset_endpoint.get('relationships', {})
        
        mac_address = asset_attrs.get('mac_address', '')
        serial_number = asset_attrs.get('serial_number', '')
        
        if not mac_address or not serial_number:
            continue
        
        # Check if this asset_endpoint has subscriptions in relationships
        subscription_ids = []
        if 'subscriptions' in relationships:
            subscriptions_data = relationships['subscriptions']
            if 'data' in subscriptions_data:
                if isinstance(subscriptions_data['data'], list):
                    subscription_ids = [sub.get('id') for sub in subscriptions_data['data'] if sub.get('id')]
                elif isinstance(subscriptions_data['data'], dict):
                    sub_id = subscriptions_data['data'].get('id')
                    if sub_id:
                        subscription_ids = [sub_id]
        
        # Match to subscriptions that have end_time > yesterday
        for sub_id in subscription_ids:
            if sub_id in subscription_map:
                sub_info = subscription_map[sub_id]
                csv_rows.append({
                    'mac_address': mac_address,
                    'serial_number': serial_number,
                    'subscription_start_time': sub_info['start_time'],
                    'subscription_end_time': sub_info['end_time'],
                    'subscription_name': sub_info['name'],
                    'id': sub_id
                })
                licensed_combos.add((mac_address.lower(), serial_number))
    
    elapsed = time.time() - start_time
    print(f"Correlated {len(asset_endpoints)} asset_endpoints with subscriptions in {elapsed:.2f} seconds.")
    print(f"Found {len(csv_rows)} licensed router entries.")
    return csv_rows, licensed_combos


def identify_unlicensed_routers(asset_endpoints, licensed_combos):
    """
    Identify routers that are not in any subscription (unlicensed).
    """
    start_time = time.time()
    unlicensed_rows = []
    
    for asset_endpoint in asset_endpoints:
        asset_attrs = asset_endpoint.get('attributes', {})
        mac_address = asset_attrs.get('mac_address', '')
        serial_number = asset_attrs.get('serial_number', '')
        
        if mac_address and serial_number:
            combo = (mac_address.lower(), serial_number)
            if combo not in licensed_combos:
                unlicensed_rows.append({
                    'mac_address': mac_address,
                    'serial_number': serial_number,
                    'subscription_start_time': 'UNLICENSED',
                    'subscription_end_time': 'UNLICENSED',
                    'subscription_name': 'UNLICENSED',
                    'id': 'UNLICENSED'
                })
    
    elapsed = time.time() - start_time
    print(f"Identified unlicensed routers in {elapsed:.2f} seconds.")
    return unlicensed_rows


def write_csv_report(csv_rows, output_file='subscription_report.csv'):
    """
    Write the CSV report to a file.
    """
    if not csv_rows:
        print("No data to write to CSV.")
        return
    
    start_time = time.time()
    fieldnames = ['mac_address', 'serial_number', 'subscription_start_time', 
                  'subscription_end_time', 'subscription_name', 'id']
    
    print(f"Writing {len(csv_rows)} rows to {output_file}...")
    with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(csv_rows)
    
    elapsed = time.time() - start_time
    print(f"CSV report written to {output_file} in {elapsed:.2f} seconds.")


def main():
    """Main function to run the script."""
    script_start_time = time.time()
    
    # Initialize the singleton - use token from script variable or environment variables
    # If NCM_API_TOKEN is None, set_api_keys() will auto-load from environment variables
    ncm.set_api_keys(api_key=NCM_API_TOKEN)
    
    # Get yesterday's date in ISO format
    yesterday_iso = get_yesterday_iso()
    print(f"Filtering subscriptions with end_time > {yesterday_iso}\n")
    
    # Step 1: Get all subscriptions with end_time > yesterday
    subscriptions = get_subscriptions_with_asset_endpoints(yesterday_iso)
    
    if not subscriptions:
        print("No subscriptions found. Exiting.")
        return
    
    # Step 2: Get all asset_endpoints
    all_asset_endpoints = get_all_asset_endpoints()
    
    # Step 3: Correlate asset_endpoints with subscriptions
    csv_rows, licensed_combos = correlate_subscriptions_and_asset_endpoints(subscriptions, all_asset_endpoints)
    
    print(f"\nTotal licensed routers found: {len(csv_rows)}")
    print(f"Unique licensed MAC/serial combos: {len(licensed_combos)}")
    
    # Step 4: Identify unlicensed routers
    unlicensed_rows = identify_unlicensed_routers(all_asset_endpoints, licensed_combos)
    
    print(f"Unlicensed routers found: {len(unlicensed_rows)}")
    
    # Step 5: Combine licensed and unlicensed rows
    all_csv_rows = csv_rows + unlicensed_rows
    
    # Step 6: Write CSV report
    write_csv_report(all_csv_rows)
    
    total_elapsed = time.time() - script_start_time
    print(f"\n{'='*60}")
    print(f"Script completed successfully!")
    print(f"Total execution time: {total_elapsed:.2f} seconds ({total_elapsed/60:.2f} minutes)")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()

