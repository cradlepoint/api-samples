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

**Corrected 2026-09-28. This section previously claimed the Swagger specs contain
no response models. That is not true of all of them — check before assuming.**

The specs live at `developer.cradlepoint.com/swagger/spec/{Endpoint_Name}.json`,
which is the JSON the Swagger UI page
(`developer.cradlepoint.com/Swagger_UI?ep={Endpoint_Name}`) fetches. It is plain
JSON and directly retrievable — if you are unsure of the exact filename, load the
UI page and read the spec URL out of its network requests.

Coverage varies by endpoint family:

- **Some specs are complete.** `Modem_Software_Upgrades.json` carries full
  `components.schemas` — request *and* response models with field-level types,
  descriptions, `enum` value lists, `required` markers, defaults, nullability, and
  worked response examples. It documents things that are very hard to discover
  empirically, such as the exact `status` enum and the `page[size]` maximum.
- **Others really do omit response models,** which is what this section originally
  described. For those, response fields still have to be captured from sample
  requests.

So: **read the spec first, and only fall back to empirical discovery for the parts
it genuinely omits.** Guessing field names when a spec was available is how
`package_version` got mistaken for `available_version` (see `known-issues.md`) — a
mistake that fails silently, producing blank columns rather than an error.

The specs also beat the repo's own artifacts when they disagree. The Postman
collection and some scripts under `scripts/` have drifted from the live API (wrong
path prefixes, parameter names that no longer exist). Treat the spec as
authoritative, the SDK as good evidence, and the Postman collection as a historical
snapshot.

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
