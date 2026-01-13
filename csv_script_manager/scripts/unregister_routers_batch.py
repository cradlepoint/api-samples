#!/usr/bin/env python3
"""
Unregister routers from NCM by reading router IDs from a CSV file with batch processing.

This script reads router IDs from a CSV file and unregisters them using the NCM API
in batches with configurable delays between batches.

Usage:
    python unregister_routers_batch.py <csv_file> [--batch-size BATCH_SIZE] [--delay DELAY]

Options:
    --batch-size: Number of routers to process per batch (default: 20)
    --delay: Delay in seconds between batches (default: 3)

Requirements:
    - CSV file with router IDs (handles columns: 'router_id', 'router id', 'id', 'routerId')
    - NCM API keys set as environment variables or configured in the script
"""

import csv
import sys
import os
import argparse
import time
from datetime import datetime
from ncm import ncm

# ============================================================================
# CONFIGURATION - Enter your NCM API keys here (or leave as None to use environment variables)
# ============================================================================
X_CP_API_ID = None  # Enter your Cradlepoint API ID here, or leave as None
X_CP_API_KEY = None  # Enter your Cradlepoint API Key here, or leave as None
X_ECM_API_ID = None  # Enter your ECM API ID here, or leave as None
X_ECM_API_KEY = None  # Enter your ECM API Key here, or leave as None
# ============================================================================


def read_router_ids_from_csv(csv_filename):
    """
    Read router IDs from a CSV file, automatically detecting the column.
    
    Args:
        csv_filename: Path to the CSV file
    
    Returns:
        List of router IDs (as strings)
    """
    router_ids = []
    
    if not os.path.exists(csv_filename):
        print(f"Error: CSV file '{csv_filename}' not found.")
        sys.exit(1)
    
    with open(csv_filename, 'r', encoding='utf-8') as file:
        csv_reader = csv.DictReader(file)
        
        # Get column names
        columns = csv_reader.fieldnames
        if not columns:
            print("Error: CSV file appears to be empty or has no headers.")
            sys.exit(1)
        
        print(f"Found columns in CSV: {', '.join(columns)}")
        
        # Try common column names (case-insensitive)
        common_names = ['router_id', 'router id', 'id', 'routerId']
        id_column = None
        
        # Normalize column names for comparison (lowercase, strip spaces)
        normalized_columns = {col.lower().strip().replace(' ', '_').replace('-', '_'): col 
                             for col in columns}
        
        for name in common_names:
            normalized_name = name.lower().strip().replace(' ', '_').replace('-', '_')
            if normalized_name in normalized_columns:
                id_column = normalized_columns[normalized_name]
                break
        
        if not id_column:
            print("Error: Could not find router ID column.")
            print(f"Available columns: {', '.join(columns)}")
            print("Please ensure your CSV has a column named: router_id, router id, id, etc.")
            sys.exit(1)
        
        print(f"Using column '{id_column}' for router IDs")
        
        # Read router IDs
        for row_num, row in enumerate(csv_reader, start=2):  # Start at 2 (header is row 1)
            router_id = row.get(id_column, '').strip()
            if router_id:
                router_ids.append(router_id)
            else:
                print(f"Warning: Row {row_num} has empty router ID, skipping.")
    
    return router_ids


def unregister_routers_batch(router_ids, ncm_client, batch_size=100, delay=0, log_file=None):
    """
    Unregister routers using the NCM client in batches.
    
    Args:
        router_ids: List of router IDs to unregister
        ncm_client: Initialized NCM client instance
        batch_size: Number of routers to process per batch
        delay: Delay in seconds between batches
        log_file: File handle for logging
    
    Returns:
        Dictionary with summary statistics
    """
    total_routers = len(router_ids)
    num_batches = (total_routers + batch_size - 1) // batch_size  # Ceiling division
    
    print(f"\nStarting unregistration of {total_routers} routers in {num_batches} batch(es)...")
    print(f"Batch size: {batch_size}, Delay between batches: {delay} seconds")
    print("=" * 80)
    
    successful = 0
    failed = 0
    results = []
    
    for batch_num in range(num_batches):
        start_idx = batch_num * batch_size
        end_idx = min(start_idx + batch_size, total_routers)
        batch = router_ids[start_idx:end_idx]
        
        print(f"\n[Batch {batch_num + 1}/{num_batches}] Processing routers {start_idx + 1}-{end_idx} of {total_routers}...")
        
        for idx, router_id in enumerate(batch, start=1):
            batch_idx = start_idx + idx
            print(f"  [{batch_idx}/{total_routers}] Unregistering router ID: {router_id}...", end=' ', flush=True)
            
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            try:
                result = ncm_client.unregister_router_by_id(router_id)
                
                # Check if deletion was successful
                # _return_handler returns:
                # - Empty string or success message for 204 (successful DELETE)
                # - "ERROR: {status_code}: {message}" for error status codes
                # - None for unhandled status codes
                
                if result is None:
                    status = 'error'
                    message = 'Unknown error: No response from API'
                    print(f"✗ Failed: {message}")
                    failed += 1
                elif isinstance(result, str):
                    if result.startswith('ERROR:'):
                        status = 'error'
                        message = result
                        print(f"✗ Failed: {result}")
                        failed += 1
                    elif result == '' or 'deleted Successfully' in result or 'operation successful' in result:
                        status = 'success'
                        message = 'Router unregistered successfully'
                        print("✓ Success")
                        successful += 1
                    else:
                        # Unknown response format, treat as success if not an error
                        status = 'success'
                        message = f'Router unregistered (response: {result})'
                        print(f"✓ Success: {result}")
                        successful += 1
                elif hasattr(result, 'status_code'):
                    # Handle response object with status_code attribute
                    status_code = result.status_code
                    if status_code == 204 or (isinstance(result, dict) and result.get('success', False)):
                        status = 'success'
                        message = 'Router unregistered successfully'
                        print("✓ Success")
                        successful += 1
                    else:
                        status = 'error'
                        message = f"Failed: {result}"
                        print(f"✗ Failed: {result}")
                        failed += 1
                elif isinstance(result, dict):
                    # Handle dict response
                    if result.get('success', False) or result.get('status_code') == 204:
                        status = 'success'
                        message = 'Router unregistered successfully'
                        print("✓ Success")
                        successful += 1
                    else:
                        status = 'error'
                        message = f"Failed: {result}"
                        print(f"✗ Failed: {result}")
                        failed += 1
                else:
                    status = 'error'
                    message = f"Unexpected response type: {type(result)} - {result}"
                    print(f"✗ Failed: {message}")
                    failed += 1
                
                log_entry = f"[{timestamp}] Router ID: {router_id} - {status.upper()}: {message}\n"
                if log_file:
                    log_file.write(log_entry)
                    log_file.flush()
                
                results.append({
                    'router_id': router_id,
                    'status': status,
                    'message': message,
                    'timestamp': timestamp
                })
                
            except Exception as e:
                status = 'error'
                message = f"Exception: {str(e)}"
                print(f"✗ Error: {str(e)}")
                failed += 1
                
                log_entry = f"[{timestamp}] Router ID: {router_id} - ERROR: {message}\n"
                if log_file:
                    log_file.write(log_entry)
                    log_file.flush()
                
                results.append({
                    'router_id': router_id,
                    'status': status,
                    'message': message,
                    'timestamp': timestamp
                })
        
        # Delay between batches (except after the last batch)
        if batch_num < num_batches - 1:
            print(f"\n  Batch {batch_num + 1} complete. Waiting {delay} seconds before next batch...")
            time.sleep(delay)
    
    return {
        'total': total_routers,
        'successful': successful,
        'failed': failed,
        'results': results
    }


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description='Unregister routers from NCM by reading router IDs from a CSV file',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python unregister_routers_batch.py routers.csv
  python unregister_routers_batch.py routers.csv --batch-size 50
  python unregister_routers_batch.py routers.csv --batch-size 200 --delay 30
        """
    )
    
    parser.add_argument('csv_file', help='Path to CSV file containing router IDs')
    parser.add_argument('--batch-size', type=int, default=20,
                       help='Number of routers to process per batch (default: 20)')
    parser.add_argument('--delay', type=int, default=3,
                       help='Delay in seconds between batches (default: 3)')
    
    args = parser.parse_args()
    
    # Validate arguments
    if args.batch_size < 1:
        print("Error: batch-size must be at least 1")
        sys.exit(1)
    
    if args.delay < 0:
        print("Error: delay must be non-negative")
        sys.exit(1)
    
    print("=" * 80)
    print("NCM Router Batch Unregistration Script")
    print("=" * 80)
    print(f"CSV file: {args.csv_file}")
    print(f"Batch size: {args.batch_size}")
    print(f"Delay between batches: {args.delay} seconds")
    print()
    
    # Read router IDs from CSV
    print("Reading router IDs from CSV file...")
    router_ids = read_router_ids_from_csv(args.csv_file)
    
    if not router_ids:
        print("No router IDs found in CSV file.")
        sys.exit(1)
    
    print(f"Found {len(router_ids)} router IDs to unregister.")
    
    # Initialize NCM client
    print("\nInitializing NCM client...")
    try:
        # Get API keys from script configuration first, then fall back to environment variables
        api_keys = {
            'X-CP-API-ID': X_CP_API_ID or os.environ.get('X_CP_API_ID'),
            'X-CP-API-KEY': X_CP_API_KEY or os.environ.get('X_CP_API_KEY'),
            'X-ECM-API-ID': X_ECM_API_ID or os.environ.get('X_ECM_API_ID'),
            'X-ECM-API-KEY': X_ECM_API_KEY or os.environ.get('X_ECM_API_KEY'),
        }
        
        # Remove None values
        api_keys = {k: v for k, v in api_keys.items() if v}
        
        if api_keys:
            ncm_client = ncm.NcmClientv2(api_keys=api_keys, log_events=True)
        else:
            # Try using the module's automatic initialization
            ncm_client = ncm.NcmClientv2(log_events=True)
        
        print("NCM client initialized successfully.")
    except Exception as e:
        print(f"Error initializing NCM client: {str(e)}")
        print("\nPlease ensure NCM API keys are configured:")
        print("  Option 1: Set them at the top of this script (X_CP_API_ID, X_CP_API_KEY, etc.)")
        print("  Option 2: Set them as environment variables:")
        print("    - X_CP_API_ID")
        print("    - X_CP_API_KEY")
        print("    - X_ECM_API_ID")
        print("    - X_ECM_API_KEY")
        sys.exit(1)
    
    # Create log file with timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_filename = f'NCM_Unregister_Routers_Log_{timestamp}.txt'
    
    print(f"\nLog file: {log_filename}")
    
    # Confirm before unregistration
    print(f"\n⚠️  WARNING: This will unregister {len(router_ids)} routers from NCM!")
    response = input("Type 'yes' to continue, or anything else to cancel: ")
    
    if response.lower() != 'yes':
        print("Unregistration cancelled.")
        sys.exit(0)
    
    # Open log file and unregister routers
    with open(log_filename, 'w', encoding='utf-8') as log_file:
        log_file.write(f"NCM Router Unregistration Log\n")
        log_file.write(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        log_file.write(f"CSV file: {args.csv_file}\n")
        log_file.write(f"Total routers: {len(router_ids)}\n")
        log_file.write(f"Batch size: {args.batch_size}\n")
        log_file.write(f"Delay between batches: {args.delay} seconds\n")
        log_file.write("=" * 80 + "\n\n")
        
        summary = unregister_routers_batch(router_ids, ncm_client, args.batch_size, args.delay, log_file)
        
        # Write summary to log file
        log_file.write("\n" + "=" * 80 + "\n")
        log_file.write("SUMMARY\n")
        log_file.write("=" * 80 + "\n")
        log_file.write(f"Total routers processed: {summary['total']}\n")
        log_file.write(f"Successfully unregistered: {summary['successful']}\n")
        log_file.write(f"Failed: {summary['failed']}\n")
        log_file.write(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Print summary
    print("\n" + "=" * 80)
    print("UNREGISTRATION RESULTS SUMMARY")
    print("=" * 80)
    print(f"\nTotal routers processed: {summary['total']}")
    print(f"Successfully unregistered: {summary['successful']}")
    print(f"Failed: {summary['failed']}")
    print(f"\nLog file: {log_filename}")
    
    # Exit with appropriate code
    if summary['failed'] > 0:
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == '__main__':
    main()

