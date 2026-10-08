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

## users

```
GET /api/v2/users/
```

**GET only.** This is a v2 endpoint (four `X-` header keys), despite `users` also
existing in NCM's UI as an account-management feature. It was previously
mis-documented as a v3 CRUD endpoint — it is not.

Filters: `id`, `username`, `email`, plus `limit` / `offset`.

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
PUT /api/v2/locations/{id}/
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

Filters: `router`, `router__in`, `mode`, `mode__in`, `id`, `id__in`, `account`, `account__in`, `connection_state`, `connection_state__in`, `is_asset`, `ipv4_address`, `ipv4_address__in`

`connection_state` enum (per the official spec): `connected`, `connecting`,
`disconnecting`, `disconnected`, `error`, `ready`, `configuring`, `unplugged`.
Note: live accounts have also returned `standby` and `standby_connecting`, which
the spec omits — treat only `connected` as online and everything else as offline
(see `known-issues.md`).

Expand: `router`, `account`

**Deprecated field**: `is_upgrade_available` (as of 12/31/2023)

## net_device_metrics

```
GET /api/v2/net_device_metrics/
```

Key fields: `id` (same as net_device ID), `net_device` (URL), `rsrp`, `rsrq`, `rssi`, `rssnr`, `sinr`, `dbm`, `cinr`, `ecio`, `signal_strength` (0–100), `service_type` (LTE/WiFi/Ethernet), `cell_id`, `mcc`, `mnc`, `tac`, `lac`, `bytes_in`, `bytes_out`, `update_ts`, `bmask_applied`

Filters: `net_device`, `net_device__in`, `update_ts__gt`, `update_ts__lt`, `bmask_applied`

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

Key fields: `id`, `net_device` (URL), `cellular_health_category` (poor/fair/good/excellent), `cellular_health_score` (0–100), `resource_url`

Filters: `net_device`, `id__gt`, `id__gte`, `id__lt`, `id__lte`

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

Parameters: `id`, `id__in`, `version`, `version__in`, `limit`, `offset`.
**There is no `product` filter** — narrowing to one model means pulling the collection
and filtering client-side. `version` is the only useful server-side filter.

Key fields:

| Field | Notes |
|---|---|
| `id` | The firmware identity. `model`+`version` is **not** unique — see below |
| `version` | NCOS version string, e.g. `7.26.100` |
| `url` | CDN **path** to the image, e.g. `/IBR600C-2026-09-16T00%3A34%3A43.bin` |
| `hash` | SHA-1 of the image — use it to verify downloads |
| `product` | URL to `/products/{id}/`; the model **name** is not on this record |
| `built_at` | UTC build timestamp |
| `released_at`, `expires_at` | UTC; `expires_at` is typically `built_at` + 2 years |
| `is_deprecated` | Boolean |
| `default_configuration` | URL to the firmware's default config |

Resolving the model name: extract the id from `product` and join against `/products/`
(single page). Prefer this join. Parsing the model out of `url` instead looks equivalent
but fails for ~2.8% of records and returns stale legacy names (`NCSG-KVM` for the product
`NCXSG-KVM`), so keep it as a fallback only — which you do need, since ~1.6% of firmware
records reference a product id absent from `/products/`. See known-issues.

Downloading an image: prepend the CDN base
(`https://d251cfg5d9gyuq.cloudfront.net`) to `url`. See
`common-patterns.md` → "Downloading Firmware Images".

Two behaviors that will bite you, both documented in `known-issues.md`:

- **Records repeat across pages.** A full pull returns roughly 20,000 rows for 17,677
  distinct `id` values. Dedupe by `id`.
- **The same model + version has many distinct builds.** About two thirds of
  model/version pairs have more than one `hash`. Never use `model`+`version` as a
  filename, cache key, or identity.

## products

```
GET /api/v2/products/
GET /api/v2/products/{id}/
```

Fields: `id`, `name` (e.g. `IBR600C`), `series`, `device_type`, `resource_url`.
Small collection, so a single `limit=500` request covers it — handy as a lookup table for
the `product` URLs on routers and firmwares.

**Dedupe by `id`.** Like `/firmwares/`, this endpoint repeats records — a single
`?limit=500` response returned **154 rows for 102 unique ids**, so the duplication is
within one response, not a pagination artifact. Build `{id: record}` rather than counting
rows. Also note the collection is not exhaustive: ~1.6% of firmware records reference a
product id that is absent here, so joins need a fallback.

## failovers

```
GET /api/v2/failovers/
```

## reboot_activity

```
POST /api/v2/reboot_activity/
```

Body: a **router** URI or a **group** URI (choose one, not both):
- `{"router": "<router_url>"}` — reboot a single router
- `{"group": "<group_url>"}` — reboot every router in a group

Returns `201 Created` when the request is accepted (not a guarantee the device
started rebooting). An invalid target ID typically returns `403 Forbidden`.

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
