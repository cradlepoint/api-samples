# NCM Python SDK Reference

## Installation

```bash
pip install ncm
```

Or use the local SDK in `ncm/` (`pip install -e ncm`). As of 0.1, the code is split
by API version: `ncm/ncm/_v2.py` (`NcmClientv2`), `ncm/ncm/_v3.py` (`NcmClientv3`),
`ncm/ncm/ncm.py` (combined client, singleton, module-level `ncm.get_routers()`), and
`ncm/ncm/_base.py` (HTTP plumbing and the masked-secret filter). Every 0.0.x import
and method still works.

### What changed in 0.1

- **Config writes never send masked secrets.** Every PUT/PATCH/POST to
  `/configuration_managers/` or `/groups/` has `"*"` values stripped from its
  `configuration`, so the target keeps its existing secret. The filter is in the
  client's session, so it also covers direct `client.session.put/patch` calls. The
  helper is public as `ncm.strip_masked_secrets()`.
- **`copy_router_configuration()` gains `replace=False`.** The default still merges
  (PATCH); `replace=True` replaces (PUT). Both modes now strip every masked secret
  correctly (details below).
- **Upgrade caution:** code that PUTs back a full config it read changes how it
  fails. On 0.0.x, NCM rejects that PUT (`wpapsk ... too short`). On 0.1 the filter
  removes the `"*"` values, the PUT succeeds, and the device's own secrets reset.
  Port such code to a PATCH removal before bumping it to `ncm>=0.1`
  (`web_apps/revert_device_firewall/` was ported this way on 2026-11-27).
- **New:** `ncm.v2` / `ncm.v3` (explicit API version), `ncm.set_v2_keys()` /
  `ncm.set_v3_key()` / `ncm.set_keys()`, the v2 short aliases (`rename_router`,
  `delete_group`, ...), the v3 `get_private_cellular_*` methods, and
  `delete_exchange_resources_for_site()`.
- Tests are in `ncm/tests/`. `test_parity.py` checks every method against 0.0.74,
  read from git history.

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
- `put_group_configuration(group_id, config_json)`: replaces the whole group config.
  Only use it when the user explicitly asks for that.

### Configuration
- `get_configuration_managers(**kwargs)`
- `get_configuration_manager_id(router_id)` — get config manager ID for a router
- `patch_configuration_managers(router_id, config_json)`: the default for every config
  change. Send only the settings being changed; delete one with
  `{"configuration": [{}, [[...path]]]}`.
- `put_configuration_managers(router_id, config_json)`: replaces the device's whole
  config. Only use it when the user explicitly asks for that, and never with a config
  you read back, because its secrets come back as `"*"`.
- `copy_router_configuration(src_router_id, dst_router_id, replace=False)`: copies the
  source's device-level config to the destination, always without masked `"*"`
  secrets.
  - **`replace=False` (default):** a PATCH merge, as in 0.0.x. Settings only the
    destination has survive, and so do its secrets. The destination therefore does
    not necessarily end up identical to the source.
  - **`replace=True`:** a PUT, so the destination ends up matching the source. Its
    device-level secrets reset to group or default values; set them again in
    cleartext if needed. Pass this only when the user explicitly wants a full
    replacement.
  - **0.0.x stripped secrets badly.** It removed only `wpapsk`/`password`, so
    certificate `key`/`x509` and NTP `key` were copied as a literal `*`. Its string
    replacement also produced invalid JSON (`{, "username": ...}`) when a secret was
    the first key in its object.
  - `replace` needs `ncm>=0.1`.
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
Calls `/api/v3/users`. Before 2026-11-19 these used a trailing slash and failed
(`JSONDecodeError` on an HTML 404); fixed in the repo copy, still broken in PyPI
`ncm` 0.0.73. See `known-issues.md`.
- `get_users(**kwargs)`
- `create_user(email, first_name, last_name, **kwargs)`
- `update_user(email, **kwargs)` — sends PATCH; the spec documents PUT (unverified)
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
- `get_exchange_resources(site_id=, exchange_network_id=, resource_id=, site_name=, **kwargs)`
  — the list call needs a site or network (the API requires one)
- `create_exchange_resource(resource_name, resource_type, site_id=, ...)`
- `update_exchange_resource(resource_id, **kwargs)`
- `delete_exchange_resource(resource_id=, site_name=, site_id=)`

The exchange_resources methods called a URL without `/api/v3` (Cloudflare `530`)
until 2026-11-19; fixed in the repo copy, still broken in PyPI `ncm` 0.0.73.

### Public SIM Management
- `get_public_sim_mgmt_assets(**kwargs)`, `get_public_sim_mgmt_rate_plans(**kwargs)`
  — both endpoints are `404` live (2026-11-19); expect these to fail.

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
