---
inclusion: auto
---

# NetCloud Manager API Development Guide

## Reflexion Workflow

When building any application that uses the Cradlepoint NetCloud Manager API, follow this workflow:

### 1. Consult Documentation First
Before writing any code, read the relevant documentation in `docs/`:
- `docs/api-overview.md` — for auth, base URLs, pagination, filtering
- `docs/api-v2-endpoints.md` — for v2 endpoint details
- `docs/api-v3-endpoints.md` — for v3 endpoint details
- `docs/api-configuration.md` — for device/group configuration
- `docs/api-webhooks.md` — for webhook setup
- `docs/ncm-sdk-reference.md` — for Python SDK methods
- `docs/common-patterns.md` — for reusable code patterns
- `docs/known-issues.md` — for gotchas and workarounds

### 2. Choose the Right Approach
- Use the NCM SDK (`from ncm import ncm`) when possible — it handles pagination, retries, auth
- Use `scripts/utils/session.py` for direct API calls with automatic retry/pagination
- Use raw `requests` only when SDK/session don't cover the use case

### 3. Build and Test
- Write the code following patterns in `docs/common-patterns.md`
- Run the code and check for errors
- Fix errors iteratively until clean

### 4. Reflexion — Update Documentation
After completing any task, evaluate whether you discovered anything new:
- **New API behavior** not documented → update the relevant `docs/*.md` file
- **Bug or gotcha** discovered → append to `docs/known-issues.md`
- **New reusable pattern** → add to `docs/common-patterns.md`
- **Documentation was wrong** → fix it and log the change in `docs/CHANGELOG.md`
- **Only applies to this specific app** → do NOT update docs (keep docs general)

## Endpoint Routing Guide

Use this to quickly find which doc and SDK method to use for a given task:

| Task | Doc File | SDK Methods |
|------|----------|-------------|
| List/manage routers | api-v2-endpoints.md → routers | `get_routers()`, `get_router_by_id()` |
| Router online/offline status | api-v2-endpoints.md → router_state_samples | `get_router_state_samples()` |
| Push device config | api-configuration.md | `patch_configuration_managers()`, `put_configuration_managers()` |
| Push group config | api-configuration.md | `patch_group_configuration()`, `put_group_configuration()` |
| Get/set locations | api-v2-endpoints.md → locations | `get_locations()`, `get_historical_locations()` |
| Manage alerts | api-v2-endpoints.md → alerts | `get_alerts()`, `get_router_alerts()` |
| Setup webhooks | api-webhooks.md | Direct API calls to `alert_push_destinations` |
| Manage groups | api-v2-endpoints.md → groups | `get_groups()`, `create_group_by_parent_id()` |
| Network device info | api-v2-endpoints.md → net_devices | `get_net_devices()`, `get_net_device_metrics()` |
| Signal/usage data | api-v2-endpoints.md → net_device_signal/usage | `get_net_device_signal_samples()`, `get_net_device_usage_samples()` |
| Firmware info | api-v2-endpoints.md → firmwares | `get_firmwares()` |
| Reboot devices | api-v2-endpoints.md → reboot_activity | `reboot_device()`, `reboot_group()` |
| Speed tests | api-v2-endpoints.md → speed_test | `create_speed_test()` |
| Manage users | api-v3-endpoints.md → users | `get_users()`, `create_user()` |
| Subscriptions | api-v3-endpoints.md → subscriptions | `get_subscriptions()`, `regrade()` |
| Private cellular | api-v3-endpoints.md → private_cellular_* | `get_private_cellular_networks()`, etc. |
| NCX sites/resources | api-v3-endpoints.md → exchange_* | `get_exchange_sites()`, `create_exchange_site()` |
| Export data to CSV | common-patterns.md | `export_to_csv()` pattern |
| Batch operations | common-patterns.md | `batch_operation()` pattern |

## Critical Rules (Always Follow)

1. **Trailing slash**: ALL v2 URLs must end with `/`
2. **Config manager ID ≠ Router ID**: Always look up the config manager ID first
3. **PATCH vs PUT**: PATCH merges, PUT replaces. Use PATCH for incremental changes
4. **_id_ fields**: When using UUID keys, include `_id_` inside the object too
5. **Check deprecations**: Before using any endpoint, verify it's not deprecated in `docs/api-deprecations.md`
6. **Error handling**: Always implement retry logic with exponential backoff
7. **Pagination**: Always handle pagination for list endpoints (SDK does this automatically)
