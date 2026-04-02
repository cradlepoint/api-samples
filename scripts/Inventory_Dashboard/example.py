"""Inventory SDK — tabular output, one row per router."""

import csv
import logging
import os
from datetime import datetime

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed; rely on system env vars
from inventory_sdk import (
    InventoryClient,
    enrich_from_snapshot,
    load_snapshot,
    save_snapshot,
    generate_html_report,
    generate_loading_html,
    update_progress_html,
)

# Show progress logs during API calls
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(message)s", datefmt="%H:%M:%S")


def fmt_date(dt) -> str:
    """Format a datetime as MM/DD/YYYY, or empty string if None."""
    if dt is None:
        return ""
    if isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except ValueError:
            return dt
    if isinstance(dt, datetime):
        return dt.strftime("%m/%d/%Y")
    return str(dt)

client = InventoryClient(
    cp_api_id=os.environ["CP_API_ID"],
    cp_api_key=os.environ["CP_API_KEY"],
    ecm_api_id=os.environ["ECM_API_ID"],
    ecm_api_key=os.environ["ECM_API_KEY"],
    v3_bearer_token=os.environ.get("V3_BEARER_TOKEN"),
)

with client:
    # Write loading page immediately so users can open it in a browser
    html_path = "inventory_report.html"
    generate_loading_html(html_path)
    print(f"Loading page written to {html_path} — open it in your browser now")

    def on_progress(step: int, detail: str) -> None:
        update_progress_html(step, detail, html_path)

    statuses, sw_licenses = client.get_license_status(progress_callback=on_progress)

    # Enrich from previous snapshot (restore lost v2 data, detect state changes)
    previous = load_snapshot()
    statuses = enrich_from_snapshot(statuses, previous)
    save_snapshot(statuses)

    max_addons = max((len(s.add_ons) for s in statuses), default=0)

    header = [
        "Router ID",
        "Router Name",
        "Account",
        "Group",
        "MAC",
        "Serial Number",
        "Hardware Series",
        "Product",
        "Device Type",
        "State",
        "Created",
        "Updated",
        "Config Status",
        "IP Address",
        "Locality",
        "Firmware",
        "Target Firmware",
        "Upgrade Pending",
        "Reboot Required",
        "IMEI",
        "ICCID",
        "IMSI",
        "MDN",
        "MEID",
        "Carrier",
        "Carrier ID",
        "Modem Name",
        "Modem FW",
        "Modem Model",
        "Modem Product",
        "Connection State",
        "Service Type",
        "RF Band",
        "LTE Bandwidth",
        "Home Carrier",
        "Description",
        "Custom1",
        "Custom2",
        "Licensed",
        "License State",
        "License State Date",
        "Previous State",
        "Last State Change",
        "Base Subscription",
        "Base Start",
        "Base Expiration",
    ]
    for i in range(1, max_addons + 1):
        header.append(f"Add-on {i}")
        header.append(f"Add-on {i} Expiration")

    rows = []
    for s in statuses:
        row = [
            s.router_id,
            s.router_name or "",
            s.account_name or "",
            s.group_name or "",
            s.mac or "",
            s.serial_number or "",
            s.hardware_series or "",
            s.full_product_name or "",
            s.device_type or "",
            s.state or "",
            fmt_date(s.created_at),
            fmt_date(s.updated_at),
            s.config_status or "",
            s.ipv4_address or "",
            s.locality or "",
            s.actual_firmware or "",
            s.target_firmware or "",
            "Yes" if s.upgrade_pending else "No",
            "Yes" if s.reboot_required else "No",
            s.imei or "",
            s.iccid or "",
            s.imsi or "",
            s.mdn or "",
            s.meid or "",
            s.carrier or "",
            s.carrier_id or "",
            s.modem_name or "",
            s.modem_fw or "",
            s.mfg_model or "",
            s.mfg_product or "",
            s.connection_state or "",
            s.service_type or "",
            s.rfband or "",
            s.ltebandwidth or "",
            s.homecarrid or "",
            s.description or "",
            s.custom1 or "",
            s.custom2 or "",
            "Yes" if s.is_licensed else "No",
            s.license_state or "",
            fmt_date(s.license_state_date),
            s.previous_license_state or "",
            fmt_date(s.state_updated_at),
            s.subscription_type or "",
            fmt_date(s.subscription_start),
            fmt_date(s.subscription_end),
        ]
        for i in range(max_addons):
            if i < len(s.add_ons):
                addon = s.add_ons[i]
                row.append(addon.subscription_type or "")
                row.append(fmt_date(addon.end_time))
            else:
                row.append("")
                row.append("")
        rows.append(row)

    # Print as aligned table
    col_widths = [len(h) for h in header]
    for row in rows:
        for i, val in enumerate(row):
            col_widths[i] = max(col_widths[i], len(val))

    def print_row(values):
        print(" | ".join(v.ljust(col_widths[i]) for i, v in enumerate(values)))

    print_row(header)
    print("-+-".join("-" * w for w in col_widths))
    for row in rows:
        print_row(row)

    # Save as CSV (try fallback filename if file is locked)
    csv_file = "inventory_report2.csv"
    try:
        with open(csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)
    except PermissionError:
        csv_file = "inventory_report3.csv"
        with open(csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(header)
            writer.writerows(rows)
        print(f"(inventory_report2.csv was locked, saved to {csv_file} instead)")

    print(f"\nTotal: {len(rows)} routers")
    print(f"CSV saved to {csv_file}")

    # Generate interactive HTML report (with Software Licenses tab)
    html_file = generate_html_report(statuses, "inventory_report.html", software_licenses=sw_licenses)
    print(f"HTML report saved to {html_file}")

    # Save software licenses CSV
    sw_csv_file = "software_licenses.csv"
    sw_header = ["Subscription Type", "Quantity", "Assigned", "Start Date", "Expiration"]
    try:
        with open(sw_csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(sw_header)
            for sl in sw_licenses:
                assigned_str = "Data not available" if sl.assigned < 0 else str(sl.assigned)
                writer.writerow([
                    sl.subscription_type or "",
                    sl.quantity if sl.quantity is not None else "",
                    assigned_str,
                    fmt_date(sl.start_time),
                    fmt_date(sl.end_time),
                ])
    except PermissionError:
        sw_csv_file = "software_licenses2.csv"
        with open(sw_csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(sw_header)
            for sl in sw_licenses:
                assigned_str = "Data not available" if sl.assigned < 0 else str(sl.assigned)
                writer.writerow([
                    sl.subscription_type or "",
                    sl.quantity if sl.quantity is not None else "",
                    assigned_str,
                    fmt_date(sl.start_time),
                    fmt_date(sl.end_time),
                ])
        print(f"(software_licenses.csv was locked, saved to {sw_csv_file} instead)")
    print(f"Software licenses CSV saved to {sw_csv_file} ({len(sw_licenses)} subscriptions)")
