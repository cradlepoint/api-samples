# NCM API Documentation Gaps

Issues found while auto-documenting the API.

Generated: 2026-06-06

## Endpoints That Require Filters (409 Without)

These time-series endpoints return `409 Conflict` if called without a required
`router` or `net_device` filter. They do not support unfiltered listing.

| Endpoint | Required Filter |
|----------|----------------|
| `historical_locations` | `router` |
| `net_device_signal_samples` | `net_device` or `net_device__in` |
| `net_device_usage_samples` | `net_device` or `net_device__in` |
| `router_logs` | `router` |
| `router_state_samples` | `router` or `router__in` |
| `router_stream_usage_samples` | `router` or `router__in` |

Note: The 409 response is NOT a rate limit in this case — it's a validation
error requiring a filter. These endpoints use TimeUUID-based pagination
(`created_at_timeuuid` fields) and are optimized for per-device queries.

## POST-Only Endpoints (405 on GET)

| Endpoint | Notes |
|----------|-------|
| `reboot_activity` | POST only — sends reboot command to a device |
| `speed_test` | POST to create, GET by ID to check results |

## Response Schema Gaps

The Swagger specs at `developer.cradlepoint.com/swagger/spec/{endpoint}.json`
do NOT include response models/schemas — only query parameters and headers.
Response field documentation must be obtained empirically via sample GET requests.

## Endpoints With Empty Data in This Account

These endpoints returned valid 200 responses but with empty `data` arrays,
meaning their response fields could not be documented from this account:

- `historical_locations` (requires specific router with location history)
- `net_device_signal_samples` (requires active device with recent samples)
- `net_device_usage_samples` (requires active device with recent samples)
- `router_state_samples` (requires active router with state changes)
- `router_logs` (requires active router)
- `router_stream_usage_samples` (requires active router)

To document these, use a router ID of an actively online device.
