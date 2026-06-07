#!/usr/bin/env python3
"""
MDM (Modem) Uptime Report

Generates a CSV report of modem uptime for all net_devices (is_asset=True),
grouped by router. Uses the uptime field from net_device_usage_samples which
is cumulative seconds since the modem connected. A null uptime means the
modem is disconnected.

Each modem is listed by its carrier name under its parent router.

CSV Format:
    No input CSV required.

    Output columns:
        - router_id: Router ID
        - router_name: Router name
        - group_name: Group the router belongs to
        - net_device_id: Net device ID
        - net_device_name: Net device name
        - carrier: Carrier/provider name
        - status: Connected or Disconnected
        - uptime_seconds: Cumulative uptime in seconds (empty if disconnected)
        - uptime_formatted: Human-readable uptime (e.g. "3d 4h 12m 5s")
        - sample_timestamp: Timestamp of the usage sample

    Example output:
        router_id,router_name,group_name,net_device_id,net_device_name,carrier,status,uptime_seconds,uptime_formatted,sample_timestamp
        1234567,HQ-Router,Main Office,9876543,mdm-abc,Verizon,Connected,345600,4d 0h 0m 0s,2026-04-13T16:43:41

Usage:
    python "MDM Uptime Report.py"

Requirements:
    - NCM API v2 keys set as environment variables
      (X_CP_API_ID, X_CP_API_KEY, X_ECM_API_ID, X_ECM_API_KEY)
      You can set them in the API Keys tab of the Script Manager
"""

import os
import csv
import sys
from datetime import datetime
import ncm

# Get API keys from environment
api_keys = {
    "X-CP-API-ID": os.environ.get("X_CP_API_ID", ""),
    "X-CP-API-KEY": os.environ.get("X_CP_API_KEY", ""),
    "X-ECM-API-ID": os.environ.get("X_ECM_API_ID", ""),
    "X-ECM-API-KEY": os.environ.get("X_ECM_API_KEY", ""),
}

api_keys = {k: v for k, v in api_keys.items() if v}

if not api_keys:
    print("Error: Please set NCM API v2 keys as environment variables")
    print("  You can set them in the API Keys tab of the Script Manager")
    sys.exit(1)

ncm.set_api_keys(api_keys=api_keys, log_events=True)


def format_uptime(seconds):
    """Convert uptime seconds to a human-readable string."""
    if seconds is None:
        return "Disconnected"
    seconds = int(seconds)
    days, remainder = divmod(seconds, 86400)
    hours, remainder = divmod(remainder, 3600)
    minutes, secs = divmod(remainder, 60)
    parts = []
    if days:
        parts.append(f"{days}d")
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    parts.append(f"{secs}s")
    return " ".join(parts)


def extract_id_from_url(url):
    """Extract resource ID from an NCM API resource URL."""
    if not url:
        return None
    return url.rstrip("/").split("/")[-1]


# 1. Fetch all modem net_devices (is_asset=True returns physical modems)
print("Fetching mdm net_devices...", flush=True)
mdm_devices = ncm.get_net_devices(is_asset=True)
if not mdm_devices:
    print("No mdm net_devices found.")
    sys.exit(0)

print(f"Found {len(mdm_devices)} mdm net_device(s).", flush=True)

# Build lookup: net_device_id -> device info
device_map = {}
router_ids = set()
for dev in mdm_devices:
    dev_id = dev["id"]
    router_id = extract_id_from_url(dev.get("router", ""))
    device_map[dev_id] = {
        "id": dev_id,
        "name": dev.get("name", ""),
        "carrier": dev.get("carrier", "Unknown"),
        "router_id": router_id,
        "uptime": None,
        "sample_ts": None,
    }
    if router_id:
        router_ids.add(router_id)

# 2. Get latest usage sample per net_device for uptime
print("Fetching latest usage samples...", flush=True)
dev_ids = list(device_map.keys())
batch_size = 100
for i in range(0, len(dev_ids), batch_size):
    batch = dev_ids[i:i + batch_size]
    id_str = ",".join(str(x) for x in batch)
    samples = ncm.get_net_device_usage_samples(
        net_device__in=id_str,
        order_by="-created_at_timeuuid",
        limit=len(batch),
    )
    # Keep only the most recent sample per net_device
    seen = set()
    for s in samples:
        nd_url = s.get("net_device", "")
        nd_id_str = extract_id_from_url(nd_url)
        nd_id = int(nd_id_str) if nd_id_str else None
        if nd_id and nd_id not in seen and nd_id in device_map:
            seen.add(nd_id)
            device_map[nd_id]["uptime"] = s.get("uptime")
            device_map[nd_id]["sample_ts"] = s.get("created_at", "")

# 3. Get router names (use expand=group to get group name inline)
print("Fetching router info...", flush=True)
router_info = {}
router_id_list = list(router_ids)
for i in range(0, len(router_id_list), batch_size):
    batch = router_id_list[i:i + batch_size]
    id_str = ",".join(batch)
    routers = ncm.get_routers(id__in=id_str, expand="group")
    for r in routers:
        rid = str(r["id"])
        group = r.get("group", {})
        group_name = group.get("name", "Ungrouped") if isinstance(group, dict) else "Ungrouped"
        router_info[rid] = {
            "name": r.get("name", f"Router {rid}"),
            "group_name": group_name,
        }

# 4. Group devices by router and build CSV rows
by_router = {}
for dev in device_map.values():
    rid = dev["router_id"] or "Unknown"
    by_router.setdefault(rid, []).append(dev)

csv_rows = []
for rid in sorted(by_router.keys(), key=lambda x: router_info.get(x, {}).get("name", x)):
    devices = by_router[rid]
    info = router_info.get(rid, {})
    router_name = info.get("name", f"Router {rid}")
    group_name = info.get("group_name", "Ungrouped")

    for dev in sorted(devices, key=lambda d: d["carrier"] or ""):
        carrier = dev["carrier"] or "Unknown"
        uptime_str = format_uptime(dev["uptime"])
        status = "Connected" if dev["uptime"] is not None else "Disconnected"

        print(f"  {router_name} | {carrier:<25} | {uptime_str:<20} | {status}")

        csv_rows.append({
            "router_id": rid,
            "router_name": router_name,
            "group_name": group_name,
            "net_device_id": dev["id"],
            "net_device_name": dev["name"],
            "carrier": carrier,
            "status": status,
            "uptime_seconds": dev["uptime"] if dev["uptime"] is not None else "",
            "uptime_formatted": uptime_str,
            "sample_timestamp": dev["sample_ts"] or "",
        })

connected = sum(1 for d in device_map.values() if d["uptime"] is not None)
disconnected = len(device_map) - connected

# 5. Write CSV
os.makedirs("csv_files", exist_ok=True)
timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
filename = f"mdm_uptime_report_{timestamp}.csv"
filepath = os.path.join("csv_files", filename)

fieldnames = [
    "router_id", "router_name", "group_name", "net_device_id",
    "net_device_name", "carrier", "status", "uptime_seconds",
    "uptime_formatted", "sample_timestamp",
]
with open(filepath, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(csv_rows)

print(f"\nTotal: {len(device_map)} modem(s) across {len(by_router)} router(s)")
print(f"Connected: {connected}  |  Disconnected: {disconnected}")
print(f"CSV exported to: {filepath}")
