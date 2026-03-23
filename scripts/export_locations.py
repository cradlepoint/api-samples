#!/usr/bin/env python3
"""
Export Locations - Standalone Script

Reads a CSV file with router IDs, retrieves location data from NCM API v2,
and adds/updates location columns in the same CSV file.

Usage:
    Double-click on Windows, or run: python export_locations.py
    Optionally pass a CSV filename: python export_locations.py my_routers.csv

Configuration:
    Set your API keys below, or as environment variables.
"""

import os
import sys
import csv

# Add the repo root to path so ncm can be imported
script_dir = os.path.dirname(os.path.abspath(__file__))
repo_root = os.path.dirname(script_dir)
sys.path.insert(0, repo_root)

try:
    import ncm
except ImportError:
    print("Error: 'ncm' library not found. Make sure the ncm folder is in the repo root.")
    input("Press Enter to exit...")
    sys.exit(1)

# ============================================================================
# CONFIGURATION - Set your API keys here
# ============================================================================

api_keys = {
    "X-CP-API-ID": "",
    "X-CP-API-KEY": "",
    "X-ECM-API-ID": "",
    "X-ECM-API-KEY": "",
}

CSV_FILENAME = "router_grid.csv"  # Default CSV filename

# ============================================================================

def load_api_keys():
    """Load API keys from config or environment variables."""
    keys = {}
    env_map = {
        "X-CP-API-ID": "X_CP_API_ID",
        "X-CP-API-KEY": "X_CP_API_KEY",
        "X-ECM-API-ID": "X_ECM_API_ID",
        "X-ECM-API-KEY": "X_ECM_API_KEY",
    }
    for header, env_var in env_map.items():
        val = api_keys.get(header, "") or os.environ.get(env_var, "")
        if val:
            keys[header] = val
    return keys


def find_id_column(fieldnames):
    """Find the router ID column from common variants."""
    candidates = ["id", "router", "routerid", "router id", "router_id"]
    normalized = {
        col.lower().strip().replace(" ", "").replace("_", ""): col
        for col in fieldnames
    }
    for name in candidates:
        key = name.lower().strip().replace(" ", "").replace("_", "")
        if key in normalized:
            return normalized[key]
    return None


def extract_router_id(value):
    """Extract router ID from a value that might be a URL or plain ID."""
    value = str(value).strip()
    if "/" in value:
        return value.rstrip("/").split("/")[-1]
    return value


def main():
    # Resolve CSV path relative to the script's own directory
    csv_filename = sys.argv[1] if len(sys.argv) > 1 else CSV_FILENAME
    filepath = os.path.join(script_dir, csv_filename) if not os.path.isabs(csv_filename) else csv_filename

    if not os.path.exists(filepath):
        print(f"Error: File not found: {filepath}")
        input("Press Enter to exit...")
        sys.exit(1)

    # Load and validate API keys
    keys = load_api_keys()
    if not keys:
        print("Error: No API keys found. Set them in the script or as environment variables:")
        print("  X_CP_API_ID, X_CP_API_KEY, X_ECM_API_ID, X_ECM_API_KEY")
        input("Press Enter to exit...")
        sys.exit(1)

    # Initialize NCM client
    n2 = ncm.NcmClientv2(api_keys=keys, log_events=False)

    # Read CSV
    with open(filepath, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        original_fieldnames = list(reader.fieldnames)

    if not rows:
        print("Error: CSV file is empty.")
        input("Press Enter to exit...")
        sys.exit(1)

    id_column = find_id_column(original_fieldnames)
    if not id_column:
        print(f"Error: Could not find router ID column. Available: {', '.join(original_fieldnames)}")
        print("Expected one of: id, router, routerid, router id, router_id (case-insensitive)")
        input("Press Enter to exit...")
        sys.exit(1)

    router_ids = [extract_router_id(row[id_column]) for row in rows]
    print(f"Processing {len(router_ids)} routers...", flush=True)

    # Fetch locations in batches with progress
    batch_size = 100
    locations = []
    total = len(router_ids)
    total_batches = (total + batch_size - 1) // batch_size

    for i in range(0, total, batch_size):
        batch = router_ids[i:i + batch_size]
        batch_num = i // batch_size + 1
        print(f"Fetching locations batch {batch_num}/{total_batches} ({len(batch)} routers)...", flush=True)
        try:
            batch_locations = n2.get_locations(router__in=batch)
            locations.extend(batch_locations)
        except Exception as e:
            print(f"  Warning: Batch {batch_num} failed: {e}", flush=True)

    print(f"Retrieved {len(locations)} locations.", flush=True)

    # Build lookup by router ID
    location_map = {}
    for loc in locations:
        router_url = loc.get("router", "")
        rid = extract_router_id(router_url) if router_url else ""
        if rid:
            location_map[rid] = loc

    # Location columns to add/update
    loc_columns = ["latitude", "longitude", "altitude_meters", "accuracy", "method"]

    # Build fieldnames: add new columns only if they don't already exist
    all_fieldnames = list(original_fieldnames)
    for col in loc_columns:
        if col not in all_fieldnames:
            all_fieldnames.append(col)

    # Merge location data into rows
    for row in rows:
        rid = extract_router_id(row[id_column])
        loc = location_map.get(rid, {})
        for col in loc_columns:
            row[col] = loc.get(col, "")

    # Write back
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=all_fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"\nDone! Location columns added/updated in: {filepath}", flush=True)
    input("Press Enter to exit...")


if __name__ == "__main__":
    main()
