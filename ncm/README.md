# NCM API Client Documentation

## Overview

The NCM_Client provides easy access to the Cradlepoint NCM API, supporting both the v2 and v3 APIs, with v3 coverage substantially expanded relative to the prior v2-centric documentation. It includes a singleton pattern for simple usage and module-level function access for convenience.

## Installation

> pip install -U ncm  

## Requirements

Cradlepoint NCM API Keys are required to make API calls:
- **For v2 API**: X-CP-API-ID, X-CP-API-KEY, X-ECM-API-ID, X-ECM-API-KEY
- **For v3 API**: Bearer token

## Usage Options

### 1. Zero-Configuration Usage (Recommended)

```python
import ncm

# Set these environment variables once:
# export X_CP_API_ID="b89a24a3"
# export X_CP_API_KEY="4b1d77fe271241b1cfafab993ef0891d"
# export X_ECM_API_ID="c71b3e68-33f5-4e69-9853-14989700f204"
# export X_ECM_API_KEY="f1ca6cd41f326c00e23322795c063068274caa30"
# export NCM_API_TOKEN="your-bearer-token"  # For v3 API

# Then just use it - no setup required!
accounts = ncm.get_accounts()
routers = ncm.get_routers()
net_devices = ncm.get_net_devices()
```

### 2. Explicit Configuration (Alternative)

```python
import ncm

# Option A: Set up API keys explicitly
api_keys = {
   'X-CP-API-ID': 'b89a24a3',
   'X-CP-API-KEY': '4b1d77fe271241b1cfafab993ef0891d',
   'X-ECM-API-ID': 'c71b3e68-33f5-4e69-9853-14989700f204',
   'X-ECM-API-KEY': 'f1ca6cd41f326c00e23322795c063068274caa30'
}
ncm.set_api_keys(api_keys)

# Option B: Manual environment variable loading
ncm.set_api_keys()  # Manually loads from environment
```

### 3. Traditional Class Instantiation

```python
import ncm
api_keys = {...}  # Same as above
client = ncm.NcmClient(api_keys=api_keys)
accounts = client.get_accounts()
```

### 4. Mixed v2/v3 API Usage

```python
import ncm
api_keys = {
   'X-CP-API-ID': 'b89a24a3',
   'X-CP-API-KEY': '4b1d77fe271241b1cfafab993ef0891d',
   'X-ECM-API-ID': 'c71b3e68-33f5-4e69-9853-14989700f204',
   'X-ECM-API-KEY': 'f1ca6cd41f326c00e23322795c063068274caa30',
   'token': 'your-v3-bearer-token'  # For v3 API
}
client = ncm.NcmClient(api_keys=api_keys)
# Methods will automatically route to the appropriate API version
```

### 5. Backward Compatibility (Legacy Scripts)

```python
import os
from ncm import ncm  # Old import pattern still works!
# `ncm.NcmClientv3` is the same v3 client type as the current `NcmClientv3`;
# both import forms resolve to the same class.

# Fail fast if the v3 token is missing, before any v3 request is dispatched.
token = os.environ.get("NCM_API_TOKEN")
if not token:
    raise RuntimeError("NCM_API_TOKEN is not set; a v3 Bearer token is required.")

api_keys = {
    'X-ECM-API-ID': os.environ.get("X_ECM_API_ID"),
    'X-ECM-API-KEY': os.environ.get("X_ECM_API_KEY"),
    'X-CP-API-ID': os.environ.get("X_CP_API_ID"),
    'X-CP-API-KEY': os.environ.get("X_CP_API_KEY"),
    'token': token  # v3 Bearer token, same 'token' key used in Pattern 4
}

# All existing patterns work unchanged:
# NcmClientv3(api_key=...) takes the raw v3 token directly.
ncm_client = ncm.NcmClientv3(api_key=token, log_events=True)
ncm_client.set_api_keys(api_keys)  # Instance method still works

# New convenience pattern also available:
ncm.set_api_keys(api_keys)  # Module-level method
routers = ncm.get_routers()  # Direct method access
```

## Features

- ✅ Zero-configuration usage with automatic environment variable loading
- ✅ Singleton pattern for easy module-level access
- ✅ Automatic API version routing (v3 prioritized over v2)
- ✅ Module-level function access (`ncm.method_name()`)
- ✅ Automatic initialization on import if environment variables are set
- ✅ Full backward compatibility with existing scripts
- ✅ Support for both import patterns: `"import ncm"` and `"from ncm import ncm"`
- ✅ Optimized pagination (default limit 500 vs API default 20)
- ✅ Support for `limit='all'` to get all records without paging
- ✅ Automatic chunking of `"__in"` filters beyond 100 item limit
- ✅ Dual v2 and v3 API support with automatic version routing between the underlying clients
- ✅ Broad v3 endpoint coverage across many capability groups (see the API Coverage section)

## API Coverage

The client exposes roughly 90+ v2 methods and 50+ v3 methods. The tables below map
capability areas to a few representative methods each (not an exhaustive list) so you
can scan for what you need.

### v2 (NcmClientv2)

| Area | Representative methods |
|---|---|
| Accounts / subaccounts | `get_accounts`, `get_account_by_id`, `create_subaccount_by_parent_id` |
| Routers | `get_routers`, `get_router_by_id`, `rename_router_by_id` |
| Groups | `get_groups`, `create_group_by_parent_id`, `patch_group` |
| Config push | `patch_configuration_managers`, `put_group_configuration` |
| Net devices / metrics | `get_net_devices`, `get_net_device_metrics`, `get_net_device_health` |
| Alerts / logs / locations | `get_alerts`, `get_router_logs`, `get_locations` |
| Firmware / products | `get_firmwares`, `get_products` |
| Speed tests / reboot | `create_speed_test`, `reboot_device` |

### v3 (NcmClientv3)

| Area | Representative methods |
|---|---|
| Users / auth | `get_users`, `create_user`, `get_account_authorizations`, `update_user_role` |
| Tenants | `get_tenants`, `get_tenant_authorizations`, `update_tenant_authorization` |
| Subscriptions / regrades | `get_subscriptions`, `regrade`, `get_regrades`, `get_regrade`, `unlicense_devices` |
| Asset endpoints / SIM management | `get_asset_endpoints`, `get_public_sim_mgmt_assets`, `get_public_sim_mgmt_rate_plans` |
| Migrations | `get_migrations`, `create_migration` |
| Modem upgrades | `get_modem_software_versions`, `get_modem_upgrades`, `create_modem_upgrade`, `update_modem_upgrade` |
| eSIM profiles | `get_esim_profiles`, `get_esim_profiles_manage`, `get_esim_profile_activations`, `create_esim_profile_activation` |
| Starlink | `get_starlink_interfaces`, `create_starlink_interface_reboot`, `create_starlink_interface_stow`, `get_starlink_diagnostics` |
| LAN devices | `get_lan_devices`, `get_lan_product_infos` |
| Remote connect | `get_remote_connect_profiles`, `create_remote_connect_profile`, `get_lan_manager_options` |
| NCX exchange | `get_exchange_sites`, `create_exchange_site`, `get_exchange_resources`, `create_exchange_resource` |

### Combined client (NcmClientv2v3)

Supplying both the four v2 API keys and a v3 token yields an `NcmClientv2v3` instance
that composes the two underlying clients. It routes router-scoped methods to the v2
client first and routes all other methods to the v3 client first, so a single handle
reaches both API versions.

`NcmClientv2v3` exposes `has_v2_client()` and `has_v3_client()` to report which
underlying clients are present, and `get_available_methods()` to list the combined
method surface. When you supply only the v2 keys and omit the token, `has_v3_client()`
returns false and the instance provides v2 methods only.

### Discovering the method surface

The tables above are a representative map, not the whole list. To see every method
available on a client at runtime, introspect it directly:

```python
import ncm
client = ncm.NcmClient(api_keys=..., api_key=...)
print(client.get_available_methods())   # combined client: roughly 150 v2 + v3 methods
# or introspect a single client class directly:
print([m for m in dir(ncm.NcmClientv3) if not m.startswith('_')])
```

## Documentation

Full documentation of the Cradlepoint NCM API is available at: [https://developer.cradlepoint.com](https://developer.cradlepoint.com)
