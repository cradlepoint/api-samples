# Ericsson NetCloud Manager Inventory SDK

Python SDK for querying Ericsson NetCloud Manager inventory — routers, network devices, accounts, groups, products, firmware, subscriptions, exchange sites, and license status.

Combines the NCM [v2 API](https://developer.cradlepoint.com) (API key auth) and [v3 API](https://developer.cradlepoint.com) (bearer token auth) into a single unified client.

<img width="1718" height="856" alt="image" src="https://github.com/user-attachments/assets/30e4e868-ea99-4465-bd13-c3d3773ef6c2" />

## Features

- Full v2 + v3 API coverage with typed Pydantic models
- Automatic pagination (v2 offset-based, v3 cursor-based)
- Combined license status report — one row per device with all data joined
- License state detection: licensed, grace-period, unlicensed
- NetCloud Exchange site detection — shows which Exchange network a device belongs to
- 324+ subscription type codes mapped to customer-facing friendly names
- Snapshot cache preserves device history when devices lose v2 data after unlicensing
- Rate limiting with exponential backoff and Retry-After support
- Concurrent async fetching — all data sources fetched in parallel
- Interactive HTML dashboard with search, sort, filter, and CSV export
- Optional live server with in-browser refresh

## Installation

```bash
pip install -e .
```

Or install from a Git repo:

```bash
pip install git+https://github.com/mschultz-21/Inventory-SDK.git
```

Dependencies: `httpx`, `pydantic`

## Authentication

You need two sets of credentials:

- **v2 API keys** (4 keys): `X-CP-API-ID`, `X-CP-API-KEY`, `X-ECM-API-ID`, `X-ECM-API-KEY`
- **v3 Bearer token**: Required for asset_endpoints, subscriptions, and exchange_sites

```python
from inventory_sdk import InventoryClient

client = InventoryClient(
    cp_api_id="your-cp-api-id",
    cp_api_key="your-cp-api-key",
    ecm_api_id="your-ecm-api-id",
    ecm_api_key="your-ecm-api-key",
    v3_bearer_token="your-v3-bearer-token",
)
```

## Quick Start

```python
with InventoryClient(
    cp_api_id="...", cp_api_key="...",
    ecm_api_id="...", ecm_api_key="...",
    v3_bearer_token="...",
) as client:
    statuses = client.get_license_status()
    for s in statuses:
        print(f"{s.router_name} ({s.mac}) — {s.license_state}")
        if s.exchange_site_name:
            print(f"  Exchange Site: {s.exchange_site_name}")
        if s.is_licensed:
            print(f"  Base: {s.subscription_type} (expires {s.subscription_end})")
            for addon in s.add_ons:
                print(f"  Add-on: {addon.subscription_type} (expires {addon.end_time})")
```

## Outputs

### Static HTML + CSV (no server needed)

```bash
py example.py
```

Generates:
- `inventory_report.html` — interactive dashboard (open in any browser)
- `inventory_report2.csv` — machine-readable export
- `inventory_snapshot.json` — device history cache

The HTML dashboard includes:
- Summary cards (total, licensed, grace-period, unlicensed)
- Full-text search across all columns
- License state filter dropdown
- Column visibility toggles (hides modem detail by default)
- Click-to-sort on any column
- Export filtered data as CSV
- Color-coded rows by license state

### Live Dashboard (with refresh)

```bash
py serve.py
```

Opens a local server at `http://localhost:8050` with the same dashboard plus a **Refresh** button that re-fetches all data from the API without restarting.

Requires: `fastapi`, `uvicorn` (`pip install fastapi uvicorn`)

## Snapshot Cache

The SDK saves device state to `inventory_snapshot.json` after each run. This enables:

- **Data preservation**: When a device is unlicensed and loses v2 data, the last known router name, account, group, firmware, modem info, and exchange site membership are restored from the snapshot.
- **State change tracking**: The `license_state_date` field records when a device entered its current license state (licensed, grace-period, or unlicensed).

```python
from inventory_sdk import enrich_from_snapshot, load_snapshot, save_snapshot

previous = load_snapshot()
statuses = enrich_from_snapshot(statuses, previous)
save_snapshot(statuses)
```

## License State Logic

| Condition | `license_state` | `is_licensed` |
|---|---|---|
| Valid subscription | `licensed` | `True` |
| NON-COMPLIANT subscription + in v2 | `grace-period` | `False` |
| NON-COMPLIANT subscription + not in v2 | `unlicensed` | `False` |
| No subscription | `unlicensed` | `False` |

## Filtering

The `FilterBuilder` supports NCM's query syntax:

```python
from inventory_sdk import FilterBuilder

filters = (
    FilterBuilder()
    .field("state", "online")
    .field_in("id", [100, 200, 300])
    .field_gt("updated_at", "2025-01-01T00:00:00")
    .order_by("name")
    .fields("id", "name", "state")
    .page(limit=100, offset=0)
)
routers = client.get_routers(filters=filters)
```

## Available Methods

| Method | API | Description |
|---|---|---|
| `get_routers()` | v2 | List routers with 30+ fields |
| `get_router_by_id()` | v2 | Single router lookup |
| `get_router_by_name()` | v2 | Single router by name |
| `get_net_devices()` | v2 | List network devices (50+ modem fields) |
| `get_net_devices_for_router()` | v2 | Modem info for a specific router |
| `get_accounts()` | v2 | List accounts |
| `get_account_by_id()` | v2 | Single account lookup |
| `get_groups()` | v2 | List device groups |
| `get_group_by_id()` | v2 | Single group lookup |
| `get_group_by_name()` | v2 | Single group by name |
| `get_products()` | v2 | List product models |
| `get_product_by_id()` | v2 | Single product lookup |
| `get_firmwares()` | v2 | List firmware versions |
| `get_asset_endpoints()` | v3 | List physical devices |
| `get_subscriptions()` | v3 | List subscriptions/licenses |
| `get_exchange_sites()` | v3 | List NetCloud Exchange sites |
| `get_license_status()` | v2+v3 | Combined inventory report |

## Performance

- **Concurrent fetching**: All 6 data sources (asset_endpoints, subscriptions, exchange_sites, routers, net_devices, groups/accounts) are fetched in parallel using asyncio
- **Rate limiting**: Automatic retry with exponential backoff on 429 responses, respects `Retry-After` headers
- **Progress logging**: Enable with `logging.basicConfig(level=logging.INFO)` to see per-step timing
- **Large accounts**: Tested for 100K+ device accounts. v2 pages at 500/request, v3 at 50/request

## Field Reference

Each column in the inventory report maps to a specific API endpoint and field. In the HTML dashboard, hover over any column header to see its source.

| Column | API Source | API Field | Description |
|---|---|---|---|
| Router ID | v2 /routers/ | `id` | Unique router identifier in NCM |
| Router Name | v2 /routers/ | `name` | User-assigned device name |
| Account | v2 /accounts/ | `name` | NCM account the device belongs to |
| Group | v2 /groups/ | `name` | Device group for configuration management |
| MAC | v2 /routers/ + v3 /asset_endpoints | `mac` / `mac_address` | Hardware MAC address (normalized to AA:BB:CC:DD:EE:FF) |
| Serial Number | v3 /asset_endpoints | `serial_number` | Manufacturer serial number |
| Hardware Series | v3 /asset_endpoints | `hardware_series` | Hardware product line (e.g. E300, IBR900) |
| Product | v2 /routers/ | `full_product_name` | Full product model name |
| Device Type | v2 /routers/ | `device_type` | Device category (router, adapter) |
| State | v2 /routers/ | `state` | Current device state (online, offline, initialized) |
| Config Status | v2 /routers/ | `config_status` | Configuration sync status (synched, pending) |
| IP Address | v2 /routers/ | `ipv4_address` | Current WAN IPv4 address |
| Locality | v2 /routers/ | `locality` | Timezone / region of the device |
| Firmware | v2 /routers/ | `actual_firmware` | Currently running firmware version |
| Target Firmware | v2 /routers/ | `target_firmware` | Firmware version the device should upgrade to |
| Upgrade Pending | v2 /routers/ | `upgrade_pending` | Whether a firmware upgrade is queued |
| Reboot Required | v2 /routers/ | `reboot_required` | Whether the device needs a reboot |
| IMEI | v2 /net_devices/ | `imei` | Modem International Mobile Equipment Identity |
| ICCID | v2 /net_devices/ | `iccid` | SIM card Integrated Circuit Card Identifier |
| IMSI | v2 /net_devices/ | `imsi` | SIM International Mobile Subscriber Identity |
| MDN | v2 /net_devices/ | `mdn` | Mobile Directory Number (phone number) |
| MEID | v2 /net_devices/ | `meid` | Mobile Equipment Identifier |
| Carrier | v2 /net_devices/ | `carrier` | Current cellular carrier name |
| Carrier ID | v2 /net_devices/ | `carrier_id` | Carrier identifier code |
| Modem Name | v2 /net_devices/ | `name` | Modem interface name |
| Modem FW | v2 /net_devices/ | `modem_fw` | Modem firmware version |
| Modem Model | v2 /net_devices/ | `mfg_model` | Modem manufacturer model |
| Modem Product | v2 /net_devices/ | `mfg_product` | Modem manufacturer product name |
| Connection State | v2 /net_devices/ | `connection_state` | Modem connection status (connected, disconnected) |
| Service Type | v2 /net_devices/ | `service_type` | Cellular service type (LTE, 5G-NR, etc.) |
| RF Band | v2 /net_devices/ | `rfband` | Active radio frequency band |
| LTE Bandwidth | v2 /net_devices/ | `ltebandwidth` | LTE channel bandwidth |
| Home Carrier | v2 /net_devices/ | `homecarrid` | Home carrier identifier (vs. roaming) |
| Description | v2 /routers/ | `description` | User-assigned device description |
| Custom1 | v2 /routers/ | `custom1` | Custom field 1 |
| Custom2 | v2 /routers/ | `custom2` | Custom field 2 |
| Exchange Site | v3 /beta/exchange_sites | `name` | NetCloud Exchange site the device belongs to |
| Licensed | SDK derived | `is_licensed` | Whether the device has an active license |
| License State | SDK derived | `license_state` | License status: licensed, grace-period, or unlicensed |
| License State Date | SDK derived | `license_state_date` | Date the device entered its current license state |
| Base Subscription | v3 /subscriptions | `name` → type mapping | Customer-facing subscription type name |
| Base Expiration | v3 /subscriptions | `end_time` | Base subscription expiration date |
| Created | v2 /routers/ | `created_at` | When the device was first added to NCM |
| Updated | v2 /routers/ | `updated_at` | Last time the device record was modified |
| Add-on N | v3 /subscriptions | `name` → type mapping | Additional subscription type name |
| Add-on N Expiration | v3 /subscriptions | `end_time` | Add-on subscription expiration date |

## License

MIT
