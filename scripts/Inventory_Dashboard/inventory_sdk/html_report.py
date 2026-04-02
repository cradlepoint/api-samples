"""Generate a self-contained interactive HTML inventory report."""

from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .models import LicenseStatus, SoftwareLicense

# Maps each display column to its API source and field name.
# Format: "Column Name": ("api_endpoint", "field_name", "description")
FIELD_SOURCE_MAP: dict[str, tuple[str, str, str]] = {
    "Router ID": ("v2 /routers/", "id", "Unique router identifier in NCM"),
    "Router Name": ("v2 /routers/", "name", "User-assigned device name"),
    "Account": ("v2 /accounts/", "name", "NCM account the device belongs to"),
    "Group": ("v2 /groups/", "name", "Device group for configuration management"),
    "MAC": ("v2 /routers/ + v3 /asset_endpoints", "mac / mac_address", "Hardware MAC address (normalized to AA:BB:CC:DD:EE:FF)"),
    "Serial Number": ("v3 /asset_endpoints", "serial_number", "Manufacturer serial number"),
    "Hardware Series": ("v3 /asset_endpoints", "hardware_series", "Hardware product line (e.g. E300, IBR900)"),
    "Product": ("v2 /routers/", "full_product_name", "Full product model name"),
    "Device Type": ("v2 /routers/", "device_type", "Device category (router, adapter)"),
    "State": ("v2 /routers/", "state", "Current device state (online, offline, initialized)"),
    "Config Status": ("v2 /routers/", "config_status", "Configuration sync status (synched, pending)"),
    "IP Address": ("v2 /routers/", "ipv4_address", "Current WAN IPv4 address"),
    "Locality": ("v2 /routers/", "locality", "Timezone / region of the device"),
    "Firmware": ("v2 /routers/", "actual_firmware", "Currently running firmware version"),
    "Target Firmware": ("v2 /routers/", "target_firmware", "Firmware version the device should upgrade to"),
    "Upgrade Pending": ("v2 /routers/", "upgrade_pending", "Whether a firmware upgrade is queued"),
    "Reboot Required": ("v2 /routers/", "reboot_required", "Whether the device needs a reboot"),
    "IMEI": ("v2 /net_devices/", "imei", "Modem International Mobile Equipment Identity"),
    "ICCID": ("v2 /net_devices/", "iccid", "SIM card Integrated Circuit Card Identifier"),
    "IMSI": ("v2 /net_devices/", "imsi", "SIM International Mobile Subscriber Identity"),
    "MDN": ("v2 /net_devices/", "mdn", "Mobile Directory Number (phone number)"),
    "MEID": ("v2 /net_devices/", "meid", "Mobile Equipment Identifier"),
    "Carrier": ("v2 /net_devices/", "carrier", "Current cellular carrier name"),
    "Carrier ID": ("v2 /net_devices/", "carrier_id", "Carrier identifier code"),
    "Modem Name": ("v2 /net_devices/", "name", "Modem interface name"),
    "Modem FW": ("v2 /net_devices/", "modem_fw", "Modem firmware version"),
    "Modem Model": ("v2 /net_devices/", "mfg_model", "Modem manufacturer model"),
    "Modem Product": ("v2 /net_devices/", "mfg_product", "Modem manufacturer product name"),
    "Connection State": ("v2 /net_devices/", "connection_state", "Modem connection status (connected, disconnected)"),
    "Service Type": ("v2 /net_devices/", "service_type", "Cellular service type (LTE, 5G-NR, etc.)"),
    "RF Band": ("v2 /net_devices/", "rfband", "Active radio frequency band"),
    "LTE Bandwidth": ("v2 /net_devices/", "ltebandwidth", "LTE channel bandwidth"),
    "Home Carrier": ("v2 /net_devices/", "homecarrid", "Home carrier identifier (vs. roaming)"),
    "Description": ("v2 /routers/", "description", "User-assigned device description"),
    "Custom1": ("v2 /routers/", "custom1", "Custom field 1"),
    "Custom2": ("v2 /routers/", "custom2", "Custom field 2"),
    "Licensed": ("SDK derived", "is_licensed", "Whether the device has an active license"),
    "License State": ("SDK derived", "license_state", "License status: licensed, grace-period, or unlicensed"),
    "License State Date": ("SDK derived", "license_state_date", "Date the device entered its current license state"),
    "Previous State": ("SDK derived", "previous_license_state", "What the license state was before the last change"),
    "Last State Change": ("v2 /routers/", "state_updated_at", "Last time the device online/offline state changed"),
    "Base Subscription": ("v3 /subscriptions", "name → subscription_types mapping", "Customer-facing subscription type name"),
    "Base Start": ("v3 /subscriptions", "start_time", "Base subscription activation date"),
    "Base Expiration": ("v3 /subscriptions", "end_time", "Base subscription expiration date"),
    "Created": ("v2 /routers/", "created_at", "When the device was first added to NCM"),
    "Updated": ("v2 /routers/", "updated_at", "Last time the device record was modified"),
}


def _get_tooltip(header: str) -> str:
    """Return a tooltip string for a column header."""
    info = FIELD_SOURCE_MAP.get(header)
    if info:
        return f"{info[0]} → {info[1]}"
    # Dynamic add-on columns
    if header.startswith("Add-on") and header.endswith("Expiration"):
        return "v3 /subscriptions → end_time"
    if header.startswith("Add-on"):
        return "v3 /subscriptions → name → subscription_types mapping"
    return ""


def _fmt_date(dt: Any) -> str:
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


def _status_to_row(s: LicenseStatus, max_addons: int) -> list[str]:
    """Convert a LicenseStatus to a flat list of display strings."""
    row = [
        s.router_id or "",
        s.router_name or "",
        s.account_name or "",
        s.group_name or "",
        s.mac or "",
        s.serial_number or "",
        s.hardware_series or "",
        s.full_product_name or "",
        s.device_type or "",
        s.state or "",
        _fmt_date(s.created_at),
        _fmt_date(s.updated_at),
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
        _fmt_date(s.license_state_date),
        s.previous_license_state or "",
        _fmt_date(s.state_updated_at),
        s.subscription_type or "",
        _fmt_date(s.subscription_start),
        _fmt_date(s.subscription_end),
    ]
    for i in range(max_addons):
        if i < len(s.add_ons):
            addon = s.add_ons[i]
            row.append(addon.subscription_type or "")
            row.append(_fmt_date(addon.end_time))
        else:
            row.append("")
            row.append("")
    return row


def _build_headers(max_addons: int) -> list[str]:
    headers = [
        "Router ID", "Router Name", "Account", "Group", "MAC",
        "Serial Number", "Hardware Series", "Product", "Device Type",
        "State", "Created", "Updated", "Config Status", "IP Address", "Locality",
        "Firmware", "Target Firmware", "Upgrade Pending", "Reboot Required",
        "IMEI", "ICCID", "IMSI", "MDN", "MEID",
        "Carrier", "Carrier ID", "Modem Name", "Modem FW",
        "Modem Model", "Modem Product", "Connection State", "Service Type",
        "RF Band", "LTE Bandwidth", "Home Carrier",
        "Description", "Custom1", "Custom2",
        "Licensed", "License State", "License State Date",
        "Previous State", "Last State Change",
        "Base Subscription", "Base Start", "Base Expiration",
    ]
    for i in range(1, max_addons + 1):
        headers.append(f"Add-on {i}")
        headers.append(f"Add-on {i} Expiration")
    return headers


# ---------------------------------------------------------------------------
# Loading / progress page
# ---------------------------------------------------------------------------

_STEPS = [
    "Fetching v3 asset endpoints",
    "Fetching v3 subscriptions",
    "Fetching v2 routers",
    "Fetching v2 net devices",
    "Fetching v2 groups & accounts",
    "Joining data",
]


def generate_loading_html(
    output_path: str | Path = "inventory_report.html",
) -> Path:
    """Write an initial loading page that auto-refreshes every 3 seconds."""
    output_path = Path(output_path)
    now = html.escape(datetime.now().strftime("%m/%d/%Y %I:%M %p"))
    steps_html = "\n".join(
        f'    <div class="step pending" id="step-{i}">'
        f'<span class="icon">○</span> {html.escape(s)}</div>'
        for i, s in enumerate(_STEPS)
    )
    page = _LOADING_TEMPLATE.replace("{{GENERATED}}", now)
    page = page.replace("{{STEPS}}", steps_html)
    page = page.replace("{{TOTAL_STEPS}}", str(len(_STEPS)))
    output_path.write_text(page, encoding="utf-8")
    return output_path


def update_progress_html(
    step_index: int,
    detail: str = "",
    output_path: str | Path = "inventory_report.html",
) -> None:
    """Rewrite the loading page with the given step marked complete."""
    output_path = Path(output_path)
    now = html.escape(datetime.now().strftime("%m/%d/%Y %I:%M %p"))
    lines: list[str] = []
    for i, s in enumerate(_STEPS):
        label = html.escape(s)
        if i < step_index:
            lines.append(
                f'    <div class="step done" id="step-{i}">'
                f'<span class="icon">✓</span> {label}</div>'
            )
        elif i == step_index:
            extra = f' — {html.escape(detail)}' if detail else ""
            lines.append(
                f'    <div class="step active" id="step-{i}">'
                f'<span class="icon spin">↻</span> {label}{extra}</div>'
            )
        else:
            lines.append(
                f'    <div class="step pending" id="step-{i}">'
                f'<span class="icon">○</span> {label}</div>'
            )
    steps_html = "\n".join(lines)
    page = _LOADING_TEMPLATE.replace("{{GENERATED}}", now)
    page = page.replace("{{STEPS}}", steps_html)
    page = page.replace("{{TOTAL_STEPS}}", str(len(_STEPS)))
    output_path.write_text(page, encoding="utf-8")


# ---------------------------------------------------------------------------
# Final report
# ---------------------------------------------------------------------------

def generate_html_report(
    statuses: list[LicenseStatus],
    output_path: str | Path = "inventory_report.html",
    software_licenses: list[SoftwareLicense] | None = None,
) -> str:
    """Generate a self-contained HTML dashboard and write it to disk.

    Returns the path written to.
    """
    output_path = Path(output_path)
    max_addons = max((len(s.add_ons) for s in statuses), default=0)
    headers = _build_headers(max_addons)
    rows = [_status_to_row(s, max_addons) for s in statuses]

    total = len(statuses)
    licensed = sum(1 for s in statuses if s.license_state == "licensed")
    grace = sum(1 for s in statuses if s.license_state == "grace-period")
    unlicensed = sum(1 for s in statuses if s.license_state == "unlicensed")

    data_json = json.dumps({"headers": headers, "rows": rows}, default=str)
    tooltips = {h: _get_tooltip(h) for h in headers if _get_tooltip(h)}
    tooltips_json = json.dumps(tooltips)

    # Software licenses data
    sw_headers = ["Subscription Type", "Quantity", "Assigned", "Start Date", "Expiration"]
    sw_rows = []
    for sl in (software_licenses or []):
        assigned_str = "Data not available" if sl.assigned < 0 else str(sl.assigned)
        sw_rows.append([
            sl.subscription_type or "",
            str(sl.quantity) if sl.quantity is not None else "",
            assigned_str,
            _fmt_date(sl.start_time),
            _fmt_date(sl.end_time),
        ])
    sw_data_json = json.dumps({"headers": sw_headers, "rows": sw_rows}, default=str)

    report_html = _HTML_TEMPLATE.replace("{{TOOLTIPS_JSON}}", tooltips_json)
    report_html = report_html.replace("{{DATA_JSON}}", data_json)
    report_html = report_html.replace("{{SW_DATA_JSON}}", sw_data_json)
    report_html = report_html.replace("{{TOTAL}}", str(total))
    report_html = report_html.replace("{{LICENSED}}", str(licensed))
    report_html = report_html.replace("{{GRACE}}", str(grace))
    report_html = report_html.replace("{{UNLICENSED}}", str(unlicensed))
    report_html = report_html.replace("{{SW_TOTAL}}", str(len(sw_rows)))
    report_html = report_html.replace(
        "{{GENERATED}}",
        html.escape(datetime.now().strftime("%m/%d/%Y %I:%M %p")),
    )

    output_path.write_text(report_html, encoding="utf-8")
    return str(output_path)


# ---------------------------------------------------------------------------
# Loading page template (auto-refreshes every 3s)
# ---------------------------------------------------------------------------

_LOADING_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta http-equiv="refresh" content="3">
<title>Inventory Report — Loading…</title>
<style>
  :root {
    --bg: #0f1117; --surface: #1a1d27; --border: #2a2d3a;
    --text: #e1e4ed; --text-dim: #8b8fa3; --accent: #6c8cff;
    --green: #34d399; --yellow: #fbbf24;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg); color: var(--text); display: flex;
    align-items: center; justify-content: center; min-height: 100vh;
  }
  .card {
    background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
    padding: 40px 48px; max-width: 480px; width: 100%;
  }
  h1 { font-size: 20px; font-weight: 600; margin-bottom: 6px; }
  .meta { color: var(--text-dim); font-size: 12px; margin-bottom: 28px; }
  .progress-bar {
    height: 4px; background: var(--border); border-radius: 2px;
    margin-bottom: 24px; overflow: hidden;
  }
  .progress-fill {
    height: 100%; background: var(--accent); border-radius: 2px;
    transition: width 0.3s ease;
  }
  .step { padding: 8px 0; font-size: 14px; display: flex; align-items: center; gap: 10px; }
  .step .icon { width: 18px; text-align: center; flex-shrink: 0; }
  .step.done { color: var(--green); }
  .step.active { color: var(--yellow); }
  .step.pending { color: var(--text-dim); }
  .hint { color: var(--text-dim); font-size: 11px; margin-top: 20px; text-align: center; }
  @keyframes spin { to { transform: rotate(360deg); } }
  .spin { display: inline-block; animation: spin 1s linear infinite; }
</style>
</head>
<body>
<div class="card">
  <h1>Ericsson Inventory Report</h1>
  <div class="meta">Started {{GENERATED}}</div>
  <div class="progress-bar"><div class="progress-fill" id="pbar"></div></div>
  <div id="steps">
{{STEPS}}
  </div>
  <div class="hint">This page refreshes automatically every 3 seconds</div>
</div>
<script>
  const total = {{TOTAL_STEPS}};
  const done = document.querySelectorAll('.step.done').length;
  const active = document.querySelectorAll('.step.active').length;
  const pct = Math.round(((done + active * 0.5) / total) * 100);
  document.getElementById('pbar').style.width = pct + '%';
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Final report template (no auto-refresh) — tabbed: Device Inventory + Software Licenses
# ---------------------------------------------------------------------------

_HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Inventory Report</title>
<style>
  :root {
    --bg: #0f1117; --surface: #1a1d27; --border: #2a2d3a;
    --text: #e1e4ed; --text-dim: #8b8fa3; --accent: #6c8cff;
    --green: #34d399; --yellow: #fbbf24; --red: #f87171; --hover: #22253a;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    background: var(--bg); color: var(--text); font-size: 13px;
    height: 100vh; overflow: hidden;
  }
  .header {
    padding: 20px 24px 16px; border-bottom: 1px solid var(--border);
    display: flex; align-items: center; justify-content: space-between; flex-wrap: wrap; gap: 12px;
  }
  .header h1 { font-size: 20px; font-weight: 600; }
  .header .meta { color: var(--text-dim); font-size: 12px; }
  /* Tabs */
  .tabs {
    display: flex; gap: 0; padding: 0 24px; border-bottom: 1px solid var(--border);
  }
  .tab-btn {
    background: none; border: none; border-bottom: 2px solid transparent;
    color: var(--text-dim); padding: 12px 20px; font-size: 14px; font-weight: 500;
    cursor: pointer; transition: all 0.2s;
  }
  .tab-btn:hover { color: var(--text); }
  .tab-btn.active { color: var(--accent); border-bottom-color: var(--accent); }
  .tab-content { display: none; }
  .tab-content.active { display: block; }
  /* Stats */
  .stats {
    display: flex; gap: 12px; padding: 16px 24px; flex-wrap: wrap;
  }
  .stat {
    background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
    padding: 12px 20px; min-width: 140px; text-align: center;
  }
  .stat .num { font-size: 28px; font-weight: 700; }
  .stat .label { font-size: 11px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.5px; margin-top: 2px; }
  .stat.licensed .num { color: var(--green); }
  .stat.grace .num { color: var(--yellow); }
  .stat.unlicensed .num { color: var(--red); }
  .stat.total-sw .num { color: var(--accent); }
  .info-note {
    margin: 0 24px; padding: 10px 16px; font-size: 12px; color: var(--text-dim);
    background: var(--surface); border: 1px solid var(--border); border-radius: 6px;
    border-left: 3px solid var(--yellow);
  }
  .toolbar {
    padding: 12px 24px; display: flex; gap: 10px; align-items: center; flex-wrap: wrap;
  }
  .toolbar input[type="text"] {
    background: var(--surface); border: 1px solid var(--border); border-radius: 6px;
    color: var(--text); padding: 7px 12px; font-size: 13px; width: 280px; outline: none;
  }
  .toolbar input[type="text"]:focus { border-color: var(--accent); }
  .toolbar select {
    background: var(--surface); border: 1px solid var(--border); border-radius: 6px;
    color: var(--text); padding: 7px 10px; font-size: 13px; outline: none;
  }
  .btn {
    background: var(--surface); border: 1px solid var(--border); border-radius: 6px;
    color: var(--text); padding: 7px 14px; font-size: 13px; cursor: pointer;
  }
  .btn:hover { background: var(--hover); border-color: var(--accent); }
  .table-wrap { overflow: auto; padding: 0 24px 0; margin-top: 4px; height: calc(100vh - 420px); min-height: 200px; }
  .table-wrap::-webkit-scrollbar { width: 10px; height: 10px; background: var(--bg); }
  .table-wrap::-webkit-scrollbar-track { background: var(--bg); }
  .table-wrap::-webkit-scrollbar-thumb { background: var(--border); border-radius: 5px; }
  .table-wrap::-webkit-scrollbar-thumb:hover { background: var(--text-dim); }
  .table-wrap::-webkit-scrollbar-corner { background: var(--bg); }
  table { width: 100%; border-collapse: collapse; white-space: nowrap; }
  thead th {
    background: var(--surface); border-bottom: 2px solid var(--border);
    padding: 8px 10px; text-align: left; font-weight: 600; font-size: 11px;
    text-transform: uppercase; letter-spacing: 0.3px; color: var(--text-dim);
    cursor: pointer; user-select: none; position: sticky; top: 0; z-index: 2;
  }
  thead th:hover { color: var(--accent); }
  thead th[title] { text-decoration: underline dotted var(--text-dim); text-underline-offset: 3px; }
  thead th .arrow { margin-left: 4px; font-size: 10px; }
  tbody td { padding: 6px 10px; border-bottom: 1px solid var(--border); }
  tbody tr:hover { background: var(--hover); }
  tbody tr.licensed td:nth-child(1) { border-left: 3px solid var(--green); }
  tbody tr.grace-period td:nth-child(1) { border-left: 3px solid var(--yellow); }
  tbody tr.unlicensed td:nth-child(1) { border-left: 3px solid var(--red); }
  .showing { color: var(--text-dim); font-size: 12px; padding: 0 24px 16px; }
  .pagination {
    display: flex; align-items: center; gap: 8px; padding: 8px 24px 16px;
    color: var(--text-dim); font-size: 13px;
  }
  .pagination button {
    background: var(--surface); border: 1px solid var(--border); border-radius: 6px;
    color: var(--text); padding: 5px 12px; font-size: 13px; cursor: pointer;
  }
  .pagination button:hover:not(:disabled) { background: var(--hover); border-color: var(--accent); }
  .pagination button:disabled { opacity: 0.4; cursor: default; }
  .pagination select {
    background: var(--surface); border: 1px solid var(--border); border-radius: 6px;
    color: var(--text); padding: 5px 8px; font-size: 13px;
  }
  .pagination .page-info { min-width: 120px; text-align: center; }
  .col-toggle { position: relative; display: inline-block; }
  .col-menu {
    display: none; position: absolute; top: 100%; left: 0; z-index: 10;
    background: var(--surface); border: 1px solid var(--border); border-radius: 8px;
    padding: 8px; max-height: 400px; overflow-y: auto; width: 260px; margin-top: 4px;
  }
  .col-menu.open { display: block; }
  .col-menu label {
    display: block; padding: 3px 6px; font-size: 12px; cursor: pointer; border-radius: 4px;
  }
  .col-menu label:hover { background: var(--hover); }
  .col-menu input { margin-right: 6px; }
  .gear-btn { background: none; border: none; color: var(--text-dim); font-size: 20px; cursor: pointer; padding: 4px 8px; }
  .gear-btn:hover { color: var(--text); }
  .modal-overlay {
    display: none; position: fixed; inset: 0; background: rgba(0,0,0,0.6);
    z-index: 100; align-items: center; justify-content: center;
  }
  .modal-overlay.open { display: flex; }
  .modal {
    background: var(--surface); border: 1px solid var(--border); border-radius: 12px;
    padding: 28px 32px; width: 460px; max-width: 90vw;
  }
  .modal h2 { font-size: 16px; font-weight: 600; margin-bottom: 16px; }
  .modal label { display: block; font-size: 12px; color: var(--text-dim); margin-bottom: 4px; margin-top: 12px; }
  .modal input[type="text"], .modal input[type="password"] {
    width: 100%; background: var(--bg); border: 1px solid var(--border); border-radius: 6px;
    color: var(--text); padding: 7px 10px; font-size: 13px; font-family: monospace; outline: none; box-sizing: border-box;
  }
  .modal input:focus { border-color: var(--accent); }
  .modal .actions { display: flex; gap: 8px; margin-top: 20px; justify-content: flex-end; }
  .modal .actions button { padding: 8px 16px; border-radius: 6px; font-size: 13px; cursor: pointer; border: 1px solid var(--border); }
  .modal .save-btn { background: var(--accent); color: #fff; border-color: var(--accent); }
  .modal .save-btn:hover { opacity: 0.9; }
  .modal .cancel-btn { background: var(--surface); color: var(--text); }
  .modal .cancel-btn:hover { background: var(--hover); }
  .modal .save-file-row { display: flex; align-items: center; gap: 6px; margin-top: 16px; font-size: 12px; color: var(--text-dim); }
  .modal .save-file-row input[type="checkbox"] { width: auto; }
  .modal .status { font-size: 11px; margin-top: 8px; }
</style>
</head>
<body>

<div class="header">
  <div>
    <h1>Ericsson Inventory Report</h1>
    <div class="meta">Generated {{GENERATED}}</div>
  </div>
  <button class="gear-btn" id="settingsBtn" title="API Settings">⚙</button>
</div>

<div class="modal-overlay" id="settingsModal">
  <div class="modal">
    <h2>API Credentials</h2>
    <label>CP API ID</label>
    <input type="text" id="s_cp_api_id" placeholder="X-CP-API-ID">
    <label>CP API Key</label>
    <input type="password" id="s_cp_api_key" placeholder="X-CP-API-KEY">
    <label>ECM API ID</label>
    <input type="text" id="s_ecm_api_id" placeholder="X-ECM-API-ID">
    <label>ECM API Key</label>
    <input type="password" id="s_ecm_api_key" placeholder="X-ECM-API-KEY">
    <label>v3 Bearer Token</label>
    <input type="password" id="s_v3_token" placeholder="Bearer token for v3 endpoints">
    <div class="save-file-row">
      <input type="checkbox" id="s_save_file" checked>
      <label for="s_save_file" style="margin:0;display:inline">Save to .env file for next time</label>
    </div>
    <div class="status" id="settingsStatus"></div>
    <div class="actions">
      <button class="cancel-btn" id="settingsCancel">Cancel</button>
      <button class="save-btn" id="settingsSave">Save</button>
    </div>
  </div>
</div>

<div class="tabs">
  <button class="tab-btn active" onclick="switchTab('devices')">Device Inventory</button>
  <button class="tab-btn" onclick="switchTab('licenses')">Software Licenses</button>
</div>

<!-- ==================== DEVICE INVENTORY TAB ==================== -->
<div class="tab-content active" id="tab-devices">

<div class="stats">
  <div class="stat"><div class="num">{{TOTAL}}</div><div class="label">Total Devices</div></div>
  <div class="stat licensed"><div class="num">{{LICENSED}}</div><div class="label">Licensed</div></div>
  <div class="stat grace"><div class="num">{{GRACE}}</div><div class="label">Grace Period</div></div>
  <div class="stat unlicensed"><div class="num">{{UNLICENSED}}</div><div class="label">Unlicensed</div></div>
</div>

<div class="info-note">ℹ Unlicensed devices may show cached data from their last known update. These devices are no longer reporting to NCM.</div>

<div class="toolbar">
  <input type="text" id="search" placeholder="Search all columns…">
  <select id="stateFilter">
    <option value="">All States</option>
    <option value="licensed">Licensed</option>
    <option value="grace-period">Grace Period</option>
    <option value="unlicensed">Unlicensed</option>
  </select>
  <div class="col-toggle">
    <button class="btn" id="colBtn">Columns ▾</button>
    <div class="col-menu" id="colMenu"></div>
  </div>
  <button class="btn" id="exportBtn">Export CSV</button>
  <button class="btn" id="refreshBtn" style="display:none">↻ Refresh</button>
</div>

<div class="showing" id="showing"></div>
<div class="pagination" id="pagination">
  <button id="pgFirst" title="First page">«</button>
  <button id="pgPrev" title="Previous page">‹</button>
  <span class="page-info" id="pgInfo"></span>
  <button id="pgNext" title="Next page">›</button>
  <button id="pgLast" title="Last page">»</button>
  <select id="pgSize">
    <option value="50">50 / page</option>
    <option value="100" selected>100 / page</option>
    <option value="250">250 / page</option>
    <option value="500">500 / page</option>
    <option value="0">Show all</option>
  </select>
</div>
<div class="table-wrap" id="tableWrap">
  <table><thead><tr id="thead"></tr></thead><tbody id="tbody"></tbody></table>
</div>

</div>

<!-- ==================== SOFTWARE LICENSES TAB ==================== -->
<div class="tab-content" id="tab-licenses">

<div class="stats">
  <div class="stat total-sw"><div class="num">{{SW_TOTAL}}</div><div class="label">Total Subscriptions</div></div>
</div>

<div class="toolbar">
  <input type="text" id="swSearch" placeholder="Search subscriptions…">
  <button class="btn" id="swExportBtn">Export CSV</button>
</div>

<div class="showing" id="swShowing"></div>
<div class="table-wrap">
  <table><thead><tr id="swThead"></tr></thead><tbody id="swTbody"></tbody></table>
</div>

</div>

<script>
/* ---- Tab switching ---- */
function switchTab(tab) {
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
  if (tab === 'devices') {
    document.querySelectorAll('.tab-btn')[0].classList.add('active');
    document.getElementById('tab-devices').classList.add('active');
  } else {
    document.querySelectorAll('.tab-btn')[1].classList.add('active');
    document.getElementById('tab-licenses').classList.add('active');
  }
}

/* ==================== DEVICE INVENTORY ==================== */
const DATA = {{DATA_JSON}};
const TOOLTIPS = {{TOOLTIPS_JSON}};
const headers = DATA.headers;
const allRows = DATA.rows;
const stateIdx = headers.indexOf("License State");

const defaultHidden = new Set([
  "IMSI","MDN","MEID","Carrier ID","Modem FW","Modem Model",
  "Modem Product","RF Band","LTE Bandwidth","Home Carrier",
  "Custom1","Custom2","Description","Target Firmware",
  "Upgrade Pending","Reboot Required","Config Status"
]);
let colVisible = headers.map(h => !defaultHidden.has(h));
let sortCol = -1, sortAsc = true;
let filtered = [...allRows];
let currentPage = 0, pageSize = 100;

function totalPages() { return pageSize === 0 ? 1 : Math.max(1, Math.ceil(filtered.length / pageSize)); }

function renderPagination() {
  const tp = totalPages();
  document.getElementById("pgInfo").textContent = pageSize === 0 ? "All" : "Page " + (currentPage + 1) + " of " + tp;
  document.getElementById("pgFirst").disabled = currentPage === 0;
  document.getElementById("pgPrev").disabled = currentPage === 0;
  document.getElementById("pgNext").disabled = currentPage >= tp - 1;
  document.getElementById("pgLast").disabled = currentPage >= tp - 1;
}

function render() {
  const thead = document.getElementById("thead");
  thead.innerHTML = "";
  headers.forEach((h, i) => {
    if (!colVisible[i]) return;
    const th = document.createElement("th");
    if (TOOLTIPS[h]) th.title = TOOLTIPS[h];
    let arrow = "";
    if (sortCol === i) arrow = '<span class="arrow">' + (sortAsc ? "▲" : "▼") + '</span>';
    th.innerHTML = h + arrow;
    th.onclick = () => { if (sortCol === i) sortAsc = !sortAsc; else { sortCol = i; sortAsc = true; } doSort(); render(); };
    thead.appendChild(th);
  });
  const start = pageSize === 0 ? 0 : currentPage * pageSize;
  const end = pageSize === 0 ? filtered.length : Math.min(start + pageSize, filtered.length);
  const pageRows = filtered.slice(start, end);
  const tbody = document.getElementById("tbody");
  tbody.innerHTML = "";
  pageRows.forEach(row => {
    const tr = document.createElement("tr");
    const state = stateIdx >= 0 ? (row[stateIdx] || "").toLowerCase() : "";
    if (state) tr.className = state;
    headers.forEach((_, i) => {
      if (!colVisible[i]) return;
      const td = document.createElement("td");
      td.textContent = row[i] || "";
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  const showStart = filtered.length === 0 ? 0 : start + 1;
  document.getElementById("showing").textContent = "Showing " + showStart + "–" + end + " of " + filtered.length + " devices" + (filtered.length < allRows.length ? " (filtered from " + allRows.length + ")" : "");
  renderPagination();
}

function doFilter() {
  const q = document.getElementById("search").value.toLowerCase();
  const sf = document.getElementById("stateFilter").value;
  filtered = allRows.filter(row => {
    if (sf && stateIdx >= 0 && row[stateIdx] !== sf) return false;
    if (q && !row.some(c => (c || "").toLowerCase().includes(q))) return false;
    return true;
  });
  currentPage = 0;
  doSort(); render();
}

function doSort() {
  if (sortCol < 0) return;
  filtered.sort((a, b) => {
    const va = (a[sortCol] || "").toLowerCase();
    const vb = (b[sortCol] || "").toLowerCase();
    return va < vb ? (sortAsc ? -1 : 1) : va > vb ? (sortAsc ? 1 : -1) : 0;
  });
}

function buildColMenu() {
  const menu = document.getElementById("colMenu");
  menu.innerHTML = "";
  headers.forEach((h, i) => {
    const lbl = document.createElement("label");
    const cb = document.createElement("input");
    cb.type = "checkbox"; cb.checked = colVisible[i];
    cb.onchange = () => { colVisible[i] = cb.checked; render(); };
    lbl.appendChild(cb); lbl.appendChild(document.createTextNode(h));
    menu.appendChild(lbl);
  });
}

document.getElementById("colBtn").onclick = (e) => { e.stopPropagation(); document.getElementById("colMenu").classList.toggle("open"); };
document.addEventListener("click", () => document.getElementById("colMenu").classList.remove("open"));
document.getElementById("colMenu").onclick = (e) => e.stopPropagation();

document.getElementById("exportBtn").onclick = () => {
  const visIdx = headers.map((_, i) => i).filter(i => colVisible[i]);
  const lines = [visIdx.map(i => '"' + headers[i].replace(/"/g, '""') + '"').join(",")];
  filtered.forEach(row => { lines.push(visIdx.map(i => '"' + (row[i] || "").replace(/"/g, '""') + '"').join(",")); });
  const blob = new Blob([lines.join("\n")], { type: "text/csv" });
  const a = document.createElement("a"); a.href = URL.createObjectURL(blob);
  a.download = "inventory_export.csv"; a.click();
};

document.getElementById("search").oninput = doFilter;
document.getElementById("stateFilter").onchange = doFilter;
document.getElementById("pgFirst").onclick = () => { currentPage = 0; render(); };
document.getElementById("pgPrev").onclick = () => { if (currentPage > 0) currentPage--; render(); };
document.getElementById("pgNext").onclick = () => { if (currentPage < totalPages() - 1) currentPage++; render(); };
document.getElementById("pgLast").onclick = () => { currentPage = totalPages() - 1; render(); };
document.getElementById("pgSize").onchange = (e) => { pageSize = parseInt(e.target.value); currentPage = 0; render(); };
buildColMenu(); render();

/* Size table to fit viewport */
(function() {
  const wrap = document.getElementById("tableWrap");
  if (!wrap) return;
  function sizeWrap() {
    const rect = wrap.getBoundingClientRect();
    wrap.style.height = (window.innerHeight - rect.top - 8) + "px";
  }
  sizeWrap();
  window.addEventListener("resize", sizeWrap);
})();

/* Settings modal */
if (window.location.protocol.startsWith("http")) {
  const modal = document.getElementById("settingsModal");
  const btn = document.getElementById("settingsBtn");
  const statusEl = document.getElementById("settingsStatus");
  btn.onclick = async () => {
    statusEl.textContent = "";
    try {
      const resp = await fetch("/api/settings");
      const data = await resp.json();
      const map = {CP_API_ID:"s_cp_api_id",CP_API_KEY:"s_cp_api_key",ECM_API_ID:"s_ecm_api_id",ECM_API_KEY:"s_ecm_api_key",V3_BEARER_TOKEN:"s_v3_token"};
      for (const [k,id] of Object.entries(map)) {
        const el = document.getElementById(id);
        el.value = "";
        el.placeholder = data[k] && data[k].set ? data[k].masked + " (set)" : "not set";
      }
    } catch(e) {}
    modal.classList.add("open");
  };
  document.getElementById("settingsCancel").onclick = () => modal.classList.remove("open");
  modal.onclick = (e) => { if (e.target === modal) modal.classList.remove("open"); };
  document.getElementById("settingsSave").onclick = async () => {
    const creds = {
      CP_API_ID: document.getElementById("s_cp_api_id").value,
      CP_API_KEY: document.getElementById("s_cp_api_key").value,
      ECM_API_ID: document.getElementById("s_ecm_api_id").value,
      ECM_API_KEY: document.getElementById("s_ecm_api_key").value,
      V3_BEARER_TOKEN: document.getElementById("s_v3_token").value,
    };
    const saveFile = document.getElementById("s_save_file").checked;
    try {
      const resp = await fetch("/api/settings", {
        method: "POST", headers: {"Content-Type":"application/json"},
        body: JSON.stringify({credentials: creds, save_to_file: saveFile})
      });
      const result = await resp.json();
      statusEl.style.color = "var(--green)";
      statusEl.textContent = "Saved" + (result.saved_to_file ? " (written to .env)" : " (session only)");
      setTimeout(() => modal.classList.remove("open"), 1200);
    } catch(e) {
      statusEl.style.color = "var(--red)";
      statusEl.textContent = "Error: " + e.message;
    }
  };
}

/* Refresh button — only visible when served from the local server */
if (window.location.protocol.startsWith("http")) {
  const btn = document.getElementById("refreshBtn");
  btn.style.display = "";
  btn.onclick = async () => {
    btn.disabled = true; btn.textContent = "↻ Refreshing…";
    try {
      const resp = await fetch("/api/refresh");
      const fresh = await resp.json();
      headers.length = 0; fresh.headers.forEach(h => headers.push(h));
      allRows.length = 0; fresh.rows.forEach(r => allRows.push(r));
      let lt=0,gp=0,ul=0;
      const si = headers.indexOf("License State");
      allRows.forEach(r => { const st=(r[si]||"").toLowerCase(); if(st==="licensed")lt++; else if(st==="grace-period")gp++; else if(st==="unlicensed")ul++; });
      document.querySelectorAll("#tab-devices .stat .num")[0].textContent = allRows.length;
      document.querySelectorAll("#tab-devices .stat .num")[1].textContent = lt;
      document.querySelectorAll("#tab-devices .stat .num")[2].textContent = gp;
      document.querySelectorAll("#tab-devices .stat .num")[3].textContent = ul;
      document.querySelector(".header .meta").textContent = "Generated " + new Date().toLocaleString();
      buildColMenu(); doFilter();
    } catch(e) { alert("Refresh failed: " + e.message); }
    btn.disabled = false; btn.textContent = "↻ Refresh";
  };
}

/* ==================== SOFTWARE LICENSES ==================== */
const SW_DATA = {{SW_DATA_JSON}};
const swHeaders = SW_DATA.headers;
const swAllRows = SW_DATA.rows;
let swSortCol = -1, swSortAsc = true;
let swFiltered = [...swAllRows];

function swRender() {
  const thead = document.getElementById("swThead");
  thead.innerHTML = "";
  swHeaders.forEach((h, i) => {
    const th = document.createElement("th");
    let arrow = "";
    if (swSortCol === i) arrow = '<span class="arrow">' + (swSortAsc ? "▲" : "▼") + '</span>';
    th.innerHTML = h + arrow;
    th.onclick = () => { if (swSortCol === i) swSortAsc = !swSortAsc; else { swSortCol = i; swSortAsc = true; } swDoSort(); swRender(); };
    thead.appendChild(th);
  });
  const tbody = document.getElementById("swTbody");
  tbody.innerHTML = "";
  swFiltered.forEach(row => {
    const tr = document.createElement("tr");
    swHeaders.forEach((_, i) => {
      const td = document.createElement("td");
      td.textContent = row[i] || "";
      tr.appendChild(td);
    });
    tbody.appendChild(tr);
  });
  document.getElementById("swShowing").textContent = "Showing " + swFiltered.length + " of " + swAllRows.length + " subscriptions";
}

function swDoFilter() {
  const q = document.getElementById("swSearch").value.toLowerCase();
  swFiltered = swAllRows.filter(row => {
    if (q && !row.some(c => (c || "").toLowerCase().includes(q))) return false;
    return true;
  });
  swDoSort(); swRender();
}

function swDoSort() {
  if (swSortCol < 0) return;
  swFiltered.sort((a, b) => {
    let va = (a[swSortCol] || "").toLowerCase();
    let vb = (b[swSortCol] || "").toLowerCase();
    /* Numeric sort for Quantity and Assigned columns */
    const na = parseFloat(va), nb = parseFloat(vb);
    if (!isNaN(na) && !isNaN(nb)) { va = na; vb = nb; }
    return va < vb ? (swSortAsc ? -1 : 1) : va > vb ? (swSortAsc ? 1 : -1) : 0;
  });
}

document.getElementById("swSearch").oninput = swDoFilter;

document.getElementById("swExportBtn").onclick = () => {
  const lines = [swHeaders.map(h => '"' + h.replace(/"/g, '""') + '"').join(",")];
  swFiltered.forEach(row => { lines.push(row.map(c => '"' + (c || "").replace(/"/g, '""') + '"').join(",")); });
  const blob = new Blob([lines.join("\n")], { type: "text/csv" });
  const a = document.createElement("a"); a.href = URL.createObjectURL(blob);
  a.download = "software_licenses.csv"; a.click();
};

swRender();
</script>
</body>
</html>"""
