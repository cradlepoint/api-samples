# NCM Python SDK Reference

## Installation

```bash
pip install ncm
```

Or use the local SDK at `ncm/ncm/ncm.py`.

## Quick Start

### v2 Only
```python
from ncm import ncm

api_keys = {
    'X-CP-API-ID': 'your_cp_api_id',
    'X-CP-API-KEY': 'your_cp_api_key',
    'X-ECM-API-ID': 'your_ecm_api_id',
    'X-ECM-API-KEY': 'your_ecm_api_key'
}
client = ncm.NcmClient(api_keys=api_keys)
```

### v3 Only
```python
from ncm import ncm

client = ncm.NcmClient(api_key='your_bearer_token')
```

### Both v2 and v3
```python
from ncm import ncm

api_keys = {
    'X-CP-API-ID': 'your_cp_api_id',
    'X-CP-API-KEY': 'your_cp_api_key',
    'X-ECM-API-ID': 'your_ecm_api_id',
    'X-ECM-API-KEY': 'your_ecm_api_key',
    'token': 'your_bearer_token'
}
client = ncm.NcmClient(api_keys=api_keys)
```

## Client Classes

| Class | API Version | Auth |
|-------|------------|------|
| `NcmClientv2` | v2 only | 4 API keys |
| `NcmClientv3` | v3 only | Bearer token |
| `NcmClientv2v3` | Both | Both |
| `NcmClient` | Auto-detects | Based on keys provided |

## v2 Methods

### Accounts
- `get_accounts(**kwargs)` — list accounts
- `get_account_by_id(account_id)` — get single account
- `get_account_by_name(account_name)` — find by name
- `create_subaccount_by_parent_id(parent_id, subaccount_name, ...)`
- `delete_subaccount_by_id(subaccount_id)`

### Routers
- `get_routers(**kwargs)` — list routers (supports `state`, `fields`, `group`, etc.)
- `get_router_by_id(router_id, **kwargs)`
- `get_router_by_name(router_name, **kwargs)`
- `get_routers_for_account(account_id, **kwargs)`
- `get_routers_for_group(group_id, **kwargs)`
- `rename_router_by_id(router_id, new_name)`
- `assign_router_to_group(router_id, group_id)`
- `remove_router_from_group(router_id=None, router_name=None)`
- `delete_router_by_id(router_id)`
- `reboot_device(router_id)`
- `reboot_group(group_id)`
- `set_router_fields(router_id, name=, description=, asset_id=, custom1=, custom2=)`

### Groups
- `get_groups(**kwargs)`
- `get_group_by_id(group_id)`
- `get_group_by_name(group_name)`
- `create_group_by_parent_id(parent_account_id, group_name, product, firmware)`
- `delete_group_by_id(group_id)`
- `patch_group_configuration(group_id, config_json)`
- `put_group_configuration(group_id, config_json)`

### Configuration
- `get_configuration_managers(**kwargs)`
- `get_configuration_manager_id(router_id)` — get config manager ID for a router
- `patch_configuration_managers(router_id, config_json)` — PATCH config by router ID
- `put_configuration_managers(router_id, config_json)` — PUT config by router ID
- `copy_router_configuration(src_router_id, dst_router_id)`
- `resume_updates_for_router(router_id)`
- `set_lan_ip_address(router_id, lan_ip, netmask=, lan_id=)`
- `set_custom1(router_id, text)` / `set_custom2(router_id, text)`
- `set_admin_password(router_id, new_password)`
- `set_ethernet_wan_ip(router_id, new_wan_ip, new_netmask, new_gateway)`
- `add_custom_apn(router_id, new_carrier, new_apn)`

### Locations
- `get_locations(**kwargs)`
- `get_historical_locations(router_id, **kwargs)`
- `get_historical_locations_for_date(router_id, date, ...)`
- `create_location(account_id, latitude, longitude, router_id)`
- `delete_location_for_router(router_id)`

### Network Devices
- `get_net_devices(**kwargs)`
- `get_net_devices_for_router(router_id, **kwargs)`
- `get_net_devices_for_router_by_mode(router_id, mode, **kwargs)`
- `get_net_device_health(**kwargs)`
- `get_net_device_metrics(**kwargs)`
- `get_net_device_signal_samples(**kwargs)`
- `get_net_device_usage_samples(**kwargs)`

### Alerts
- `get_alerts(**kwargs)`
- `get_router_alerts(**kwargs)`
- `get_router_alerts_last_24hrs(tzoffset_hrs=0, **kwargs)`
- `get_router_alerts_for_date(date, tzoffset_hrs=0, **kwargs)`

### Logs
- `get_activity_logs(**kwargs)`
- `get_router_logs(router_id, **kwargs)`
- `get_router_logs_last_24hrs(router_id, tzoffset_hrs=0)`

### Other
- `get_firmwares(**kwargs)`
- `get_products(**kwargs)`
- `get_failovers(**kwargs)`
- `create_speed_test(net_device_ids, ...)`
- `get_router_state_samples(**kwargs)`

## v3 Methods

### Users
- `get_users(**kwargs)`
- `create_user(email, first_name, last_name, **kwargs)`
- `update_user(email, **kwargs)`
- `delete_user(email)`
- `update_user_role(email, new_role)`

### Subscriptions
- `get_subscriptions(**kwargs)`
- `regrade(subscription_id, mac, action="UPGRADE")`
- `unlicense_devices(mac_addresses)`
- `get_regrades(**kwargs)`

### Private Cellular
- `get_private_cellular_networks(**kwargs)`
- `create_private_cellular_network(name, core_ip, ...)`
- `get_private_cellular_radios(**kwargs)`
- `get_private_cellular_sims(**kwargs)`
- `get_private_cellular_radio_groups(**kwargs)`

### NCX (NetCloud Exchange)
- `get_exchange_sites(**kwargs)`
- `create_exchange_site(name, exchange_network_id, router_id, **kwargs)`
- `update_exchange_site(site_id=, name=, **kwargs)`
- `delete_exchange_site(site_id=, site_name=)`
- `get_exchange_resources(**kwargs)`
- `create_exchange_resource(resource_name, resource_type, site_id=, ...)`
- `update_exchange_resource(resource_id, **kwargs)`
- `delete_exchange_resource(resource_id=, site_name=, site_id=)`

## Common kwargs

Most GET methods accept:
- `fields` — comma-separated list of fields to return
- `limit` — page size
- `offset` — pagination offset
- Endpoint-specific filters (e.g., `state`, `group`, `router`, etc.)

## Using the Session Utility

For direct API calls without the SDK, use `scripts/utils/session.py`:

```python
from scripts.utils.session import APISession
from scripts.utils.credentials import get_credentials

creds = get_credentials()
with APISession(logger=my_logger, **creds) as session:
    for router in session.get('routers', filter={'state': 'online'}):
        print(router['name'])
```

The session utility handles retries, pagination, and authentication automatically.
