# API v2 Endpoint Reference

Base URL: `https://www.cradlepointecm.com/api/v2/`

## Endpoint Quick Reference

| Category | Endpoint(s) |
|----------|-------------|
| Account Information | `accounts` |
| User Information | `users` |
| Router Information | `routers` |
| Device Locations | `locations`, `historical_locations` |
| Log Information | `activity_logs`, `router_logs` |
| Online/Offline Status | `router_state_samples` |
| Firmware | `firmwares`, `routers` |
| Alerts | `alerts`, `router_alerts`, `alert_rules`, `alert_push_destinations`, `test_alert_push_destination` |
| Groups | `groups` |
| SDK Apps | `device_apps`, `device_app_bindings`, `device_app_states`, `device_app_versions` |
| Device Configurations | `configuration_managers` |
| E100 Battery | `batteries` |
| Network Interfaces | `net_devices`, `net_device_health`, `net_device_metrics`, `net_device_signal_samples`, `net_device_usage_samples` |
| Failover | `failovers` |
| Products | `products` |
| Reboot | `reboot_activity` |
| Speed Test | `speed_test` |

## accounts

```
GET /api/v2/accounts/
GET /api/v2/accounts/{id}/
POST /api/v2/accounts/    (create subaccount)
PUT /api/v2/accounts/{id}/
DELETE /api/v2/accounts/{id}/
```

Key fields: `id`, `name`, `account`, `resource_url`

## routers

```
GET /api/v2/routers/
GET /api/v2/routers/{id}/
PUT /api/v2/routers/{id}/
PATCH /api/v2/routers/{id}/
DELETE /api/v2/routers/{id}/
```

Key fields:
- `id` — router ID
- `name` — router name
- `mac` — MAC address
- `state` — online/offline/initialized
- `group` — URL to group (expandable)
- `account` — URL to account (expandable)
- `firmware_version` — current firmware
- `product` — URL to product (expandable)
- `config_status` — synched/suspended/pending
- `description`, `asset_id`, `custom1`, `custom2` — user-defined fields
- `actual_firmware` — firmware currently running
- `target_firmware` — firmware targeted for upgrade
- `resource_url` — self-referential URL

Filters: `account`, `group`, `id`, `id__in`, `mac`, `mac__in`, `name`, `name__in`, `state`, `state__in`

## groups

```
GET /api/v2/groups/
GET /api/v2/groups/{id}/
POST /api/v2/groups/
PUT /api/v2/groups/{id}/
PATCH /api/v2/groups/{id}/
DELETE /api/v2/groups/{id}/
```

Key fields: `id`, `name`, `account`, `configuration`, `product`, `resource_url`, `target_firmware`

The `configuration` field holds the group-level config diff (see api-configuration.md).

## configuration_managers

```
GET /api/v2/configuration_managers/
GET /api/v2/configuration_managers/{id}/
PUT /api/v2/configuration_managers/{id}/
PATCH /api/v2/configuration_managers/{id}/
```

Key fields:
- `id` — config manager ID (may differ from router ID)
- `account` — account URL
- `router` — router URL (expandable)
- `configuration` — individual device config diff (read/write)
- `actual` — last config received from device (readonly)
- `target` — layered config = group + individual (readonly)
- `pending` — pending changes waiting to sync (readonly)
- `synched` — true if device is in sync
- `suspended` — true if sync is paused
- `version_number` — increments on each config change

Filters: `id`, `id__in`, `router`, `router__in`, `synched`, `suspended`, `version_number`, `version_number__gt`, `version_number__lt`

**Important**: PUT replaces entire config. PATCH merges changes. See `docs/api-configuration.md` for details.

## locations

```
GET /api/v2/locations/
GET /api/v2/locations/{id}/
POST /api/v2/locations/
DELETE /api/v2/locations/{id}/
```

## historical_locations

```
GET /api/v2/historical_locations/
```

Filters: `router`, `created_at`, `created_at__gt`, `created_at__lt`

Note: Uses TimeUUID-based pagination for large datasets. See `scripts/utils/timeuuid_endpoint.py`.

## net_devices

```
GET /api/v2/net_devices/
GET /api/v2/net_devices/{id}/
```

Key fields: `id`, `router`, `name`, `mode` (wan/lan/mdm), `carrier`, `type`, `is_connected`

Filters: `router`, `router__in`, `mode`, `mode__in`, `id`, `id__in`

**Deprecated field**: `is_upgrade_available` (as of 12/31/2023)

## net_device_metrics

```
GET /api/v2/net_device_metrics/
```

Filters: `net_device`, `net_device__in`, `created_at`, `created_at__gt`, `created_at__lt`

## net_device_signal_samples

```
GET /api/v2/net_device_signal_samples/
```

Filters: `net_device`, `net_device__in`, `created_at`, `created_at__gt`, `created_at__lt`

## net_device_usage_samples

```
GET /api/v2/net_device_usage_samples/
```

Filters: `net_device`, `net_device__in`, `created_at`, `created_at__gt`, `created_at__lt`

## net_device_health

```
GET /api/v2/net_device_health/
```

## alerts

```
GET /api/v2/alerts/
```

## router_alerts

```
GET /api/v2/router_alerts/
```

Filters: `router`, `created_at`, `created_at__gt`, `created_at__lt`, `detected_at`

## alert_rules

```
GET /api/v2/alert_rules/
POST /api/v2/alert_rules/
PUT /api/v2/alert_rules/{id}/
DELETE /api/v2/alert_rules/{id}/
```

## alert_push_destinations

```
GET /api/v2/alert_push_destinations/
POST /api/v2/alert_push_destinations/
PUT /api/v2/alert_push_destinations/{id}/
DELETE /api/v2/alert_push_destinations/{id}/
```

## test_alert_push_destination

```
POST /api/v2/test_alert_push_destination/
```

## router_state_samples

```
GET /api/v2/router_state_samples/
```

## router_logs

```
GET /api/v2/router_logs/
```

Filters: `router`, `created_at`, `created_at__gt`, `created_at__lt`

## activity_logs

```
GET /api/v2/activity_logs/
```

## firmwares

```
GET /api/v2/firmwares/
GET /api/v2/firmwares/{id}/
```

## products

```
GET /api/v2/products/
GET /api/v2/products/{id}/
```

## failovers

```
GET /api/v2/failovers/
```

## reboot_activity

```
POST /api/v2/reboot_activity/
```

Body: `{"router": "<router_url>"}`

## speed_test

```
POST /api/v2/speed_test/
GET /api/v2/speed_test/{id}/
```

## device_apps / device_app_bindings / device_app_states / device_app_versions

```
GET /api/v2/device_apps/
GET /api/v2/device_app_bindings/
GET /api/v2/device_app_states/
GET /api/v2/device_app_versions/
```

## router_stream_usage_samples

```
GET /api/v2/router_stream_usage_samples/
```

## Deprecated Endpoints (DO NOT USE)

| Endpoint | Deprecated Date |
|----------|----------------|
| `overlay_network_bindings` | 09/30/2024 |
| `forwarding_lan_details` | 09/30/2024 |
| `routers.overlay_network_binding` field | 09/30/2024 |
