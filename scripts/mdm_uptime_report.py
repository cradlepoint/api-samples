#!/usr/bin/env python3
"""
MDM (Modem) Uptime Report

Generates a report of modem uptime for all net_devices with is_asset=True (modems),
grouped by router. Uses the uptime field from net_device_usage_samples which is
cumulative seconds since the modem connected. A null uptime means disconnected.

Each modem is listed by its carrier name under its parent router.

Usage:
    python mdm_uptime_report.py
    python mdm_uptime_report.py --csv output.csv

Requirements:
    - NCM API v2 keys set as environment variables
      (CP_API_ID, CP_API_KEY, ECM_API_ID, ECM_API_KEY)
    - Run setup_env.py or export them manually before running
"""

import os
import sys
import csv
from datetime import datetime

# Add parent dir so utils is importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.env_check import check_env, get_api_keys_from_env

try:
    import ncm
except ImportError:
    print("Error: 'ncm' library not found. Install it with: pip install ncm")
    sys.exit(1)


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


def main():
    check_env()
    api_keys = get_api_keys_from_env()

    csv_output = None
    if "--csv" in sys.argv:
        idx = sys.argv.index("--csv")
        if idx + 1 < len(sys.argv):
            csv_output = sys.argv[idx + 1]
        else:
            print("Error: --csv requires a filename argument")
            sys.exit(1)

    client = ncm.NcmClient(api_keys=api_keys)

    # 1. Fetch all modem net_devices (is_asset=True returns physical modems)
    print("Fetching mdm net_devices...", flush=True)
    mdm_devices = client.get_net_devices(is_asset=True)
    if not mdm_devices:
        print("No mdm net_devices found.")
        return

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
        samples = client.get_net_device_usage_samples(
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
    router_info = {}  # router_id -> {name, group_name}
    router_id_list = list(router_ids)
    for i in range(0, len(router_id_list), batch_size):
        batch = router_id_list[i:i + batch_size]
        id_str = ",".join(batch)
        routers = client.get_routers(id__in=id_str, expand="group")
        for r in routers:
            rid = str(r["id"])
            group = r.get("group", {})
            group_name = group.get("name", "Ungrouped") if isinstance(group, dict) else "Ungrouped"
            router_info[rid] = {
                "name": r.get("name", f"Router {rid}"),
                "group_name": group_name,
            }

    # 4. Group devices by router
    by_router = {}
    for dev in device_map.values():
        rid = dev["router_id"] or "Unknown"
        by_router.setdefault(rid, []).append(dev)

    # 5. Print report
    print("\n" + "=" * 70)
    print("  MDM (Modem) Uptime Report")
    print(f"  Generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC")
    print("=" * 70)

    csv_rows = []

    for rid in sorted(by_router.keys(), key=lambda x: router_info.get(x, {}).get("name", x)):
        devices = by_router[rid]
        info = router_info.get(rid, {})
        router_name = info.get("name", f"Router {rid}")
        group_name = info.get("group_name", "Ungrouped")

        print(f"\n  Router: {router_name} (ID: {rid})  |  Group: {group_name}")
        print(f"  {'-' * 60}")

        for dev in sorted(devices, key=lambda d: d["carrier"] or ""):
            carrier = dev["carrier"] or "Unknown"
            uptime_str = format_uptime(dev["uptime"])
            status = "Connected" if dev["uptime"] is not None else "Disconnected"
            print(f"    Carrier: {carrier:<25} Uptime: {uptime_str:<20} [{status}]")

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

    print(f"\n{'=' * 70}")
    print(f"  Total: {len(device_map)} modem(s) across {len(by_router)} router(s)")
    print(f"  Connected: {connected}  |  Disconnected: {disconnected}")
    print(f"{'=' * 70}\n")

    # 6. Optional CSV export
    if csv_output:
        fieldnames = [
            "router_id", "router_name", "group_name", "net_device_id",
            "net_device_name", "carrier", "status", "uptime_seconds",
            "uptime_formatted", "sample_timestamp",
        ]
        with open(csv_output, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(csv_rows)
        print(f"CSV exported to: {csv_output}")


if __name__ == "__main__":
    main()
