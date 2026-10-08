---
inclusion: fileMatch
fileMatchPattern: "{scripts/**/*.py,ncm/**/*.py,ncm2/**/*.py,web_apps/**/*.py}"
description: NCM API development — endpoint routing, SDK usage, critical rules. Pull in #reflexion-workflow for the full self-improving docs loop.
---

# NetCloud Manager API Development Guide

## Documentation Lookup

Before writing code, consult `docs/`:
- `api-overview.md` — auth, base URLs, pagination, filtering
- `api-v2-endpoints.md` / `api-v3-endpoints.md` — endpoint details
- `api-v2-full-reference.md` — full v2 reference
- `api-configuration.md` — device/group config push
- `api-webhooks.md` — webhook setup
- `ncm-sdk-reference.md` — Python SDK methods
- `common-patterns.md` — reusable code patterns
- `known-issues.md` — gotchas and workarounds
- `api-deprecations.md` — deprecated endpoints to avoid

## Approach Selection

1. **NCM SDK** (`from ncm import ncm`) — preferred. Handles pagination, retries, auth. Always read `ncm/ncm/ncm.py` to discover methods before writing custom code.
2. **`scripts/utils/session.py`** — direct API calls with auto retry/pagination.
3. **Raw `requests`** — only when SDK/session don't cover the use case.

## Endpoint Routing (Task → Doc → SDK)

| Task | Doc | SDK Methods |
|------|-----|-------------|
| Routers | v2 → routers | `get_routers()`, `get_router_by_id()` |
| Router state | v2 → router_state_samples | `get_router_state_samples()` |
| Push device config | api-configuration | `patch_configuration_managers()`, `put_configuration_managers()` |
| Push group config | api-configuration | `patch_group_configuration()`, `put_group_configuration()` |
| Locations | v2 → locations | `get_locations()`, `get_historical_locations()` |
| Alerts | v2 → alerts | `get_alerts()`, `get_router_alerts()` |
| Webhooks | api-webhooks | Direct API: `alert_push_destinations` |
| Groups | v2 → groups | `get_groups()`, `create_group_by_parent_id()` |
| Net devices | v2 → net_devices | `get_net_devices()`, `get_net_device_metrics()` |
| Cellular health | v2 → net_device_health | `get_net_device_health()` |
| Cellular metrics | v2 → net_device_metrics | `get_net_devices_metrics_for_wan()`, `get_net_devices_metrics_for_mdm()` |
| Signal/usage | v2 → net_device_signal/usage | `get_net_device_signal_samples()`, `get_net_device_usage_samples()` |
| Firmware | v2 → firmwares | `get_firmwares()` |
| Reboot | v2 → reboot_activity | `reboot_device()`, `reboot_group()` |
| Speed tests | v2 → speed_test | `create_speed_test()` |
| Users | **v2** → users (GET only) | `get_users()` |
| Subscriptions | v3 → subscriptions (`/api/v3/subscriptions`, GET only) | `get_subscriptions()` |
| Regrades | v3 → `/api/v3/asset_endpoints/regrades` | `regrade()` |
| Private cellular | v3 → `/api/v3/beta/private_cellular_*` | `get_private_cellular_networks()` |
| NCX sites/resources | v3 → `/api/v3/beta/exchange_*` | `get_exchange_sites()`, `create_exchange_site()` |
| CSV export | common-patterns | `export_to_csv()` pattern |
| Batch ops | common-patterns | `batch_operation()` pattern |

v3 endpoints require `NCM_API_TOKEN`. If it is absent, say so rather than letting the
call fail opaquely.

## Critical Rules

1. **Trailing slash**: ALL v2 URLs must end with `/`
2. **Config manager ID ≠ Router ID**: Look up config manager ID first
3. **PATCH vs PUT**: PATCH merges, PUT replaces — use PATCH for incremental changes
4. **`_id_` fields**: Include UUID `_id_` inside the object when using UUID keys
5. **Deprecations**: Verify endpoint isn't deprecated before using
6. **Retries**: Exponential backoff on transient errors
7. **Pagination**: Always handle for list endpoints (SDK does this automatically)

## Quality Gates

Before considering an NCM app complete:
1. Runs without errors
2. Proper auth on all API calls
3. Trailing slashes on v2 URLs
4. Pagination handled for lists
5. Retry logic implemented
6. No deprecated endpoints used

## After Completion — Reflexion

Evaluate whether you discovered anything generally applicable: new API behavior, a
gotcha, a reusable pattern, or a doc error. If so, update the relevant `docs/` file and
log it in `docs/CHANGELOG.md`. Skip it when the discovery is app-specific, a
user-specific config issue, or already documented.

Target files, entry formats and the full loop: `#reflexion-workflow`. The
`reflexion-update-docs` Stop hook also prompts this automatically.
