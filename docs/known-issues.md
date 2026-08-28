# Known Issues and Gotchas

This file is automatically maintained by the reflexion system. When the AI discovers
issues, workarounds, or corrections while building applications, they are logged here.

## API Gotchas

### Trailing Slash Required (v2 only)
All v2 endpoint URLs MUST end with `/`. Without it, the server redirects (301),
causing two API calls to be counted against your rate limit.

### v3 Beta Endpoints Must NOT Have Trailing Slashes (discovered 2026-04-02)
Unlike v2, the v3 beta endpoints (`/api/v3/beta/...`) return `404 Resource
not found` if the URL ends with a trailing slash. Omit the slash entirely.
For example, use `/api/v3/beta/modem_software_versions` not
`/api/v3/beta/modem_software_versions/`. Non-beta v3 endpoints (e.g.
`/api/v3/subscriptions/`) still accept trailing slashes.

### Configuration Manager ID ≠ Router ID
The `configuration_managers` endpoint has its own `id` field that may differ from the
router's `id`. Always use `get_configuration_manager_id(router_id)` to look up the
correct config manager ID before making PUT/PATCH calls.

### PATCH CAN Remove Config Items — via the Removals List (corrected 2026-08-14)
**This entry previously said the opposite.** It claimed "PATCH only adds or
updates. To remove config items, you must use PUT with the removals list," and a
2026-08-13 caveat built further on that mistake. Both were wrong.

PATCH accepts the removals list, and NCM's own web UI uses it. Removing a single
address from a host identity produces this PATCH body — empty updates dict, one
removal path:

```json
[
    {},
    [["identities", "ip", "0897fa24-b4a4-4aa2-9cab-0bed9507c233", "members", 2]]
]
```

Adding or changing addresses in the same identity produces an updates-only PATCH:

```json
[
    {
        "identities": {
            "ip": {
                "0897fa24-b4a4-4aa2-9cab-0bed9507c233": {
                    "members": {"2": {"address": "4.5.6.7"}, "3": {"address": "5.6.7.8"}},
                    "_id_": "0897fa24-b4a4-4aa2-9cab-0bed9507c233"
                }
            }
        }
    },
    []
]
```

Both slots can be populated in one PATCH: set values via updates and prune via
removals in a single call.

**Array elements are addressed by integer index in removal paths, not by string
key.** Note the asymmetry against updates, where the same array position is a
string key:

- update: `{"members": {"2": {...}}}` — string `"2"`
- removal: `["identities", "ip", "<uuid>", "members", 2]` — integer `2`

Practical consequences:

- You do **not** need PUT to delete one branch of a group config. Prefer PATCH
  with removals — PUT resets unmentioned fields to defaults, which at
  `/groups/{id}/` scope wipes every other group-level setting.
- UUID-keyed collections (`identities.*`, `lan`, `vpn.tunnels`,
  `security.zfw.zones`, ...) **can** be mirrored exactly between groups. Remove a
  whole entry with a path ending at its UUID: `["identities", "ip", "<uuid>"]`.
- When removing several elements from the same array, emit the indices
  highest-first. Whether NCM resolves removal paths against the pre-change config
  or applies them sequentially with reindexing is unconfirmed, and descending
  order is correct under either interpretation.

Source: NCM UI request traffic reported by a user on 2026-08-14. The formats above
are what the UI sends; they have not been independently replayed against the API
from this repo.

### Arrays in PATCH Replace Entirely
When using arrays (not objects) in a PATCH body, the entire array is replaced.
Use objects with string keys for partial array updates.

### _id_ Must Be Included Twice
When using a UUID `_id_` as the key for an array element, you must also include
the `_id_` field inside the object body, or you get a validation error.

### Passwords Return "*"
Password fields always return `"*"` on GET. You cannot read existing passwords.
Set new passwords by sending cleartext — they are encrypted automatically.

### Config Rollback After 15 Minutes
If a device applies a config but can't reach NCM within 15 minutes, it rolls back
and suspends sync. Check the "Configuration Rejected" alert for details.

### v3 Content-Type
API v3 requires both `Content-Type: application/vnd.api+json` AND
`Accept: application/vnd.api+json`. Missing either causes errors.

### Deprecated: overlay_network_bindings
This endpoint and the `routers.overlay_network_binding` field were deprecated 09/30/2024.
Remove all references.

### Deprecated: net_devices.is_upgrade_available
This field still appears in responses but returns inaccurate data since 12/31/2023.

---

## SDK Gotchas

### NcmClient Auto-Detection
`NcmClient()` returns different class instances based on what keys you provide:
- Only v2 keys → `NcmClientv2`
- Only v3 token → `NcmClientv3`
- Both → `NcmClientv2v3`

### Environment Variable Loading
The SDK checks `CP_BASE_URL` for v2 and `CP_BASE_URL_V3` for v3 base URLs.

### Module-Level SDK Delegation Hangs with v3-Only Credentials (discovered 2026-04-07)
Using the SDK's module-level method delegation (`import ncm; ncm.get_routers(...)`)
auto-initializes a singleton via `get_ncm_instance()`. If only a v3 token is set
(no v2 API keys), the singleton is a `NcmClientv3`. Calling a v2-only method like
`get_routers()` on it will not raise an error — instead, the v2 `__get_json`
pagination loop sends requests to the v2 base URL without proper auth headers.
The SDK's retry adapter (5 retries, exponential backoff on 408/503/504) causes
the script to appear to hang indefinitely with no output.

Workaround: in v3-only scripts, do NOT use module-level delegation for v2 methods.
Either instantiate `NcmClientv3` directly and use v3 equivalents (e.g.
`get_asset_endpoints()` instead of `get_routers()`), or ensure all four v2 API
keys are set in the environment.

### SDK `_return_handler` Error Behavior (discovered 2026-04-07, corrected 2026-08-13)
**Correction:** this entry previously stated that `_return_handler` returns error
strings like `"ERROR: 400: {...}"` instead of raising. That is no longer true —
the SDK now **raises `requests.exceptions.HTTPError`** for 400, 401, 404 and 500.
Verified by calling `_return_handler` directly across status codes:

| Status | Behavior |
|--------|----------|
| 200 | returns `"<obj_type> operation successful."` |
| 201, 204 | returns the response text |
| 400, 401, 404, 500 | raises `requests.exceptions.HTTPError` as `"<code>: <body>"` |
| anything else (403, 409, 429, 418, ...) | logs, then returns `None` |

So `try/except` around SDK calls **does** catch those four error codes. Two
traps remain:

1. **Unhandled status codes return `None`,** silently. 403, 409 and 429 all fall
   through the `else` branch — notably 429 (rate limit) and 409 (which v3 uses
   for both rate limiting and validation errors). Code that assumes a truthy
   return value or a list will misread these as success.
2. **v2's `__get_json` still swallows errors independently of
   `_return_handler`.** It checks `if not (200 <= status < 300): break` *before*
   calling the handler, so a mid-pagination failure exits the loop and returns
   partial (possibly empty) results with no exception and no indication. An
   unexpectedly empty or short list from a v2 GET may be a silent error.

Workaround: wrap SDK calls in `try/except requests.exceptions.HTTPError` (or bare
`except Exception`) to catch 4xx/5xx on writes, and additionally treat `None` and
suspiciously empty list results as failures.

### SDK `regrade()` Missing JSON:API Atomic Extension Header (discovered 2026-04-07)
The `regrade()` method sends an `atomic:operations` payload but does not set
the required JSON:API atomic extension Content-Type header. Compare with
`unlicense_devices()`, which correctly sets:
```
Content-Type: application/vnd.api+json;ext="https://jsonapi.org/ext/atomic"
Accept: application/vnd.api+json;ext="https://jsonapi.org/ext/atomic"
```
The missing header can cause the API to reject the request with a 400 error
(e.g. `"mac_address must be specified"`) even when the field is present in
the payload, because the server doesn't parse the atomic operations format
without the extension header.

### SDK `regrade()` MAC Normalization Only Handles Colons (discovered 2026-04-07)
The `regrade()` method normalizes MAC addresses by stripping colons only when
the input is exactly 17 characters (`len(smac) == 17`). This misses:
- Dash-separated MACs (`00-30-44-1A-2B-3C`, 17 chars) — colons are stripped
  (finding none), dashes pass through
- Dot-separated Cisco format (`0030.441A.2B3C`, 14 chars) — passes through
  with dots intact
- Lowercase MACs — passed through as-is (API may expect uppercase)

Workaround: always normalize MACs to bare uppercase hex before passing to
`regrade()`: `mac.upper().replace(':', '').replace('-', '').replace('.', '')`

### v3 Regrades Endpoint Rejects Duplicate MACs in a Single Batch (discovered 2026-04-09)
The `POST /asset_endpoints/regrades` atomic operations endpoint rejects the
entire batch with a `400 Bad Request` if the same `mac_address` value appears
more than once across operations in a single request. The error message is:
`"mac_address values must only occur once"`. This applies per-request, not
globally — the same MAC can appear in separate requests. Always deduplicate
MAC addresses within each batch before sending.

### v3 Regrades Endpoint Requires Exactly 12 Hex Digits for MAC (discovered 2026-04-09)
The `POST /asset_endpoints/regrades` endpoint strictly validates that
`mac_address` is exactly 12 hexadecimal characters (uppercase or lowercase,
no separators). Any other format — including MACs with colons, dashes, dots,
or fewer/more than 12 characters — returns `400 Bad Request` with:
`"mac_address must be 12 digit hexadecimal with optional colons"`. Despite
the error message mentioning "optional colons", bare 12-digit hex is the
safest format. Validate with `^[0-9A-Fa-f]{12}$` before sending.

---

## Discovered Issues Log

<!-- New issues discovered during development are appended below -->

### SDK vs Session Utility Credential Key Names (discovered 2026-03-31)
The NCM SDK and the `scripts/utils/session.py` utility use different key naming
conventions for credentials. Mixing them up causes silent auth failures.
- SDK (`NcmClient`): `{'X-CP-API-ID': '...', 'X-CP-API-KEY': '...', 'X-ECM-API-ID': '...', 'X-ECM-API-KEY': '...'}`
- Session utility (`APISession`): `cp_api_id='...', cp_api_key='...', ecm_api_id='...', ecm_api_key='...'`
- `credentials.py`: uses snake_case keys matching the session utility, NOT the SDK

If using `get_credentials()` with the SDK, you must remap the keys to HTTP header names.

### v3 Bearer Token Environment Variable Name Is Standardized as `NCM_API_TOKEN` (discovered 2026-06-06)
The standard env var name for the v3 bearer token in this project is `NCM_API_TOKEN`.
All scripts have been refactored to use this name. Historical names that may
appear in older code or external references:
- `TOKEN` — legacy name (removed from scripts)
- `V3_BEARER_TOKEN` — Inventory Dashboard legacy (migrated to NCM_API_TOKEN)
- `CP_API_TOKEN` — never used by any actual script

When building new scripts/dashboards that need v3, use `NCM_API_TOKEN`.

### __in Filter 100-Value Limit (discovered 2026-03-31)
The NCM API limits `__in` filter parameters to 100 comma-separated values per request.
The SDK auto-chunks these transparently, but if you're making raw API calls with
`requests` or the session utility, you must chunk manually or the API will error.

### Venv pip Bad Interpreter After Repo Move (discovered 2026-03-31)
If the repo is cloned or moved to a different path than where the `.venv` was
originally created, the `pip` (and other scripts in `.venv/bin/`) will have a
stale shebang pointing to the old Python path. Running `.venv/bin/pip install ...`
fails with `bad interpreter: no such file or directory`.
Workaround: use `.venv/bin/python -m pip install ...` instead, or recreate the venv.

### Flask Not Installed Despite Being in requirements.txt (discovered 2026-03-31)
The `requirements.txt` lists `flask` but it may not be installed in the venv if
dependencies were never fully installed. Always run
`.venv/bin/python -m pip install -r requirements.txt` after cloning or setting up
the project for the first time.

### Recreating Venv Wipes Injected API Credentials (discovered 2026-03-31)
Running `python3 -m venv .venv --clear` to fix a broken venv also deletes the
API credentials that `setup_env.py` injected into `.venv/bin/activate`. After
recreating the venv, you must re-run `setup_env.py` and then `source .venv/bin/activate`
to restore the environment variables. This affects all scripts that rely on `check_env()`.

### SDK `fields` Parameter Not Universally Supported (discovered 2026-03-31)
The NCM API v2 supports `?fields=` on most endpoints for partial responses, but
the Python SDK only allows `fields` on methods where it's explicitly in the
`allowed_params` list. Before using `fields` with any SDK method, check its
`allowed_params` in the source.
Methods known to support `fields`: `get_routers()`, `get_groups()` (added 2026-03-31).
Methods known to NOT support `fields`: `get_products()`, `get_firmwares()`.

### v2 Router Relational Fields Are URLs, Not Values (discovered 2026-04-01)
When fetching routers without the `fields` parameter, relational fields like `group`,
`product`, `actual_firmware`, and `target_firmware` return full API URLs
(e.g. `https://www.cradlepointecm.com/api/v2/groups/12345/`), not names or IDs.
To get human-readable values, either use `expand=group` on the request, or build
a lookup dict from a separate `get_groups()` call. The `full_product_name` field
does return the model name directly (e.g. "AER1600").

### Prefer `expand=group` Over Separate `/groups/` Fetch (discovered 2026-04-09)
On large accounts the `/groups/` endpoint can return thousands of groups (4000+),
requiring many paginated requests that take minutes to complete. Using
`expand=group` on the `/routers/` call is dramatically faster because the API
inlines the group object (with `name`, `id`, etc.) directly into each router
response, eliminating the separate fetch entirely. The same applies to
`expand=account`. Always prefer `expand` over a separate lookup fetch when you
only need the related resource's name or ID.

### v3 Subscriptions Have No `status` Field (discovered 2026-04-01)
The v3 `/subscriptions/` endpoint returns `attributes.start_time` and
`attributes.end_time` but no explicit `status` field. To determine if a
subscription is active or expired, compare `end_time` against the current UTC time.
The subscription type is in `relationships.subscription_type.data.id`.

### SDK `fields` Parameter Returns Empty in Flask Context (discovered 2026-04-01)
When using the NCM SDK's `get_routers(fields='...')` inside a Flask application,
it returns an empty list, even though the same call works correctly in a standalone
Python script. The root cause is unclear but may relate to how Flask's request
context interacts with the SDK's session/urllib. Workaround: omit the `fields`
parameter and fetch full objects instead.

### v2 and v3 MAC Address Formats Differ (discovered 2026-04-01)
The v2 `/routers/` endpoint returns MAC addresses in the `mac` field using
colon-separated format (e.g. `00:30:44:1A:2B:3C`), while the v3
`/asset_endpoints` endpoint returns them in the `mac_address` field using
bare uppercase hex (e.g. `0030441A2B3C`). When joining data across v2 and v3,
you must normalize both to the same format (e.g. strip colons/dashes and
upper-case) before matching.

### v3 Beta Endpoints Use /beta/ Prefix (discovered 2026-04-01, updated 2026-04-02)
Several v3 endpoints are served under `/api/v3/beta/` rather than `/api/v3/`.
Requests without the `/beta/` prefix may 404. Known beta endpoints include
`exchange_sites`, `modem_software_versions`, and `modem_upgrades`. Because
these are beta endpoints, their contracts may change without notice. Always
check the OpenAPI spec or release notes for the correct path prefix.

### net_devices `is_asset` Filter (discovered 2026-04-01)
The v2 `/net_devices/` endpoint supports an `is_asset` boolean
filter. Setting `is_asset=true` returns only the primary modem interfaces
(the physical cellular modems), filtering out virtual/logical interfaces.
This is useful when you only need modem-level details (IMEI, ICCID, carrier)
and want to avoid processing hundreds of non-modem net_device records.

### net_devices Supports `expand=router` and `expand=account` (discovered 2026-06-06)
The v2 `/net_devices/` endpoint supports `expand=router` and `expand=account`.
When using `expand=router`, the `router` field becomes an inline object with
the full router record (id, name, state, mac, group URL, etc.) instead of a
URL. This eliminates the need for a separate `/routers/` fetch when building
per-modem views. Note: if the net_device has no associated router, the field
remains `null` even with expand.

### `net_device_health` Returns Records for All Net Device Types (discovered 2026-06-05)
The `/net_device_health/` endpoint returns health records for net_devices of
ALL modes (wan, lan, mdm), not just WAN or modem interfaces. When joining
health data to net_devices, do NOT filter by `mode='wan'` or you will silently
miss most records. Fetch all net_devices (no mode filter) and join by
net_device ID to get complete results.

### `net_device_health` Only Contains Score, Not Signal Metrics (discovered 2026-06-06)
The `/net_device_health/` endpoint returns only:
- `cellular_health_category` — string: "poor", "fair", "good", or "excellent"
- `cellular_health_score` — integer: 0–100
- `net_device` — URL reference to the net_device
- `id`, `resource_url`

It does NOT contain signal metrics (RSSI, RSRP, RSRQ, SINR, etc.). For actual
signal data, use `/net_device_metrics/` filtered by the same net_device IDs.
The typical pattern for a cellular health dashboard is:
1. `GET /net_device_health/` → health scores + net_device URLs
2. `GET /net_device_metrics/?net_device__in=id1,id2,...` → signal metrics
3. `GET /net_devices/?id__in=id1,id2,...` → carrier, model, router ref
4. `GET /routers/?expand=group` → device names, groups, state

### `net_devices` Do Not Contain Signal Fields (discovered 2026-06-06)
The `/net_devices/` endpoint does NOT return signal strength fields (rssi,
rsrp, rsrq, sinr, signal_percent). These fields only exist on the
`/net_device_metrics/` endpoint. The `/net_devices/` response includes modem
hardware info: carrier, model, mfg_model, mfg_product, connection_state,
imei, iccid, apn, modem_fw, etc.

### `net_devices` `router` Field Can Be Null (discovered 2026-06-06)
The `router` field on `/net_devices/` can be `null` for orphaned or
unassigned modems. Code that assumes `router` is always a URL will fail.
Always check for null before extracting the router ID. For display purposes,
fall back to `hostname` or `name` from the net_device record.

### v2 API IDs Are Returned as Strings (discovered 2026-06-06)
Despite being numeric, v2 API responses return `id` fields as strings
(e.g. `"67468693"` not `67468693`). When building lookup dictionaries for
joining across endpoints, always normalize IDs to strings. Using `int()` for
lookups will cause key mismatches if the dict was keyed with the raw string
from the API response.

### `net_device_metrics` Response Schema (discovered 2026-06-06)
The `/net_device_metrics/` endpoint returns:
- Signal: `rsrp`, `rsrq`, `rssi`, `rssnr`, `sinr`, `dbm`, `cinr`, `ecio`,
  `signal_strength` (integer 0–100, NOT `signal_percent`)
- Cell info: `cell_id`, `mcc`, `mnc`, `tac`, `lac`, `service_type`
  (e.g. "LTE", "WiFi", "Ethernet", "Not Available")
- Usage: `bytes_in`, `bytes_out`
- Meta: `update_ts`, `bmask_applied`, `net_device` (URL), `id`, `resource_url`

Note: `id` matches the net_device ID (same value), making joins trivial.
Non-cellular interfaces (WiFi, Ethernet) have null signal fields.

### `expand=router` on net_devices Does NOT Expand Nested Relations (discovered 2026-06-06)
When using `expand=router` on `/net_devices/`, the inline router object's
relational fields (like `group`, `account`, `product`, `actual_firmware`) are
still URLs, not expanded objects. Only one level of expansion is supported.
To resolve group names when using this pattern, you must still call
`/groups/` separately and build a lookup by URL or ID.

### v3 API Returns 409 Conflict as a Rate Limit (discovered 2026-04-01)
When making concurrent requests to v3 endpoints (e.g. `/asset_endpoints`),
the API may return `409 Conflict` with the message "Conflict with internal
rules. i.e. invalid app-key." instead of the expected `429 Too Many Requests`.
This is effectively a rate limit response. Treat 409 as retryable with
exponential backoff, the same as 429. The NCM API enforces a limit of
approximately 500 calls per minute across all endpoints.

### v2 API Transient 500 "shard-router" Errors (discovered 2026-04-01)
During heavy pagination of v2 endpoints (especially `/net_devices/` and
`/routers/` on large accounts), the API may return `500 Internal Server Error`
with a body like `"cp internal error shard-router-3"`. This is a transient
server-side error, not a client issue. Retry with backoff. Include 500, 502,
503, and 504 in your retryable status code set.

### httpx `params={}` Strips Query Parameters from Pagination URLs (discovered 2026-04-01)
When using `httpx` (or `requests`) for pagination, passing `params={}` (empty
dict) to `client.get(url, params={})` strips any existing query parameters
from the URL. If the `meta.next` URL is
`https://...?limit=500&offset=500`, passing `params={}` turns it into
`https://.../routers/` — causing an infinite loop that re-fetches page 1
forever. Use `params=None` instead of `params={}` on subsequent pagination
requests where the query parameters are already embedded in the `next` URL.

### v3 asset_endpoint Subscription IDs Are Assignment-Level, Not Parent (discovered 2026-04-01)

### v2 and v3 Are Fully Separate API Systems — No Cross-Referencing (discovered 2026-04-28)
The v2 and v3 APIs are architecturally independent interfaces to the same
underlying data. They do NOT cross-reference each other:
- **Auth:** v2 uses 4 API key headers; v3 uses a single Bearer token.
- **IDs:** v2 uses integers; v3 uses strings. They are different ID spaces.
- **Spec:** v3 follows JSON:API; v2 does not.
- **Relationships:** v2 embeds full URLs to other v2 resources. v3 uses
  JSON:API `relationships` blocks with type/id references to other v3
  resources only.
- **Expand:** `?expand=` is v2-only. v3 uses JSON:API `?include=` (where
  supported) or you follow the relationship type/id to the v3 endpoint.

The key implication: v3 relationship references can only be resolved through
v3 endpoints. If a related resource doesn't have a v3 endpoint yet, that
relationship either won't appear in the v3 response or the data will be
flattened into attributes. You cannot use a v2 endpoint to resolve a v3
relationship reference (or vice versa). When migrating scripts from v2 to
v3, all related resource lookups must also be migrated to their v3
equivalents.

### v2 Router IDs and v3 Asset Endpoint IDs Are Different ID Spaces (discovered 2026-04-07)
The v2 `/routers/` endpoint assigns numeric IDs (e.g. `1234567`) to devices.
The v3 `/asset_endpoints` endpoint has its own `id` field that does NOT
correspond to the v2 router ID. Passing a v2 router ID to
`get_asset_endpoints(id=...)` (which becomes `filter[id]=1234567`) will
return the wrong device or no results. To cross-reference between v2 and v3,
use a shared natural key like `mac_address` or `serial_number` instead of
either system's internal ID.
The `subscription_ids` on v3 `/asset_endpoints` are per-device assignment IDs
(e.g. `4c03Hj1hALlWWvK`), NOT the parent subscription IDs returned by an
unfiltered `GET /subscriptions` (e.g. `55050000002xYV9`). These two ID spaces
do not overlap. To resolve assignment IDs to full subscription details (name,
start/end dates), use `GET /subscriptions?filter[id]=<assignment_id>`.
Multiple IDs can be comma-separated: `filter[id]=id1,id2,id3`.

### v3 `/subscriptions/{id}` Returns 404 for Assignment IDs (discovered 2026-04-01)
Looking up an assignment-level subscription ID by path
(`GET /subscriptions/4c03Hj1hALlWWvK`) returns 404, even though the ID is
valid. Use the query filter instead: `GET /subscriptions?filter[id]=4c03Hj1hALlWWvK`.
This is a JSON:API quirk — the filter endpoint resolves IDs that the direct
path lookup does not.

### check_env() Prints v2 Errors in v3-Only Scripts (discovered 2026-04-02)
`check_env()` from `utils.env_check` always validates v2 API keys
(`CP_API_ID`, `CP_API_KEY`, `ECM_API_ID`, `ECM_API_KEY`). In v3-only
scripts that don't need v2 keys, it prints a misleading "Missing required
environment variables" message to stderr before calling `sys.exit(1)`.
Workaround: suppress stderr and catch the `SystemExit`:
```python
import io, sys
from utils.env_check import check_env
try:
    _stderr = sys.stderr
    sys.stderr = io.StringIO()
    check_env()
except SystemExit:
    pass
finally:
    sys.stderr = _stderr
```
Then validate v3-specific vars (`NCM_API_TOKEN`, etc.) separately.

### modem_upgrades POST Returns 200, Not 201 (discovered 2026-04-02)
The OpenAPI spec for `POST /api/v3/beta/modem_upgrades` documents a `201
Created` response, but the API actually returns `200 OK` with the created
resource in the body. Code that checks for `status_code == 201` to confirm
creation will incorrectly treat a successful POST as a failure. Check for
both 200 and 201.

### modem_upgrades Request Type Must Be Collection Name (discovered 2026-04-02)
The OpenAPI spec says the `data.type` field in POST/PUT request bodies for
`/api/v3/beta/modem_upgrades` should be `"modem_upgrade_parent"`. The API
rejects this with a `409 Conflict`: *"The resource object's type
(modem_upgrade_parent) is not the type that constitute the collection
represented by the endpoint (modem_upgrades)."* Use `"modem_upgrades"` in
the request body instead. Note: the response still returns
`"modem_upgrade_parent"` as the type — the asymmetry is intentional.

### v3 409 Conflict Is Overloaded: Rate Limit vs Validation Error (discovered 2026-04-02)
The existing documentation notes that v3 returns `409 Conflict` as a rate
limit. However, 409 is also used for JSON:API validation errors (e.g. wrong
`data.type`). To distinguish: if the 409 response body contains an `errors`
array, it is a real validation error and should NOT be retried. If it does
not contain `errors`, treat it as a rate limit and retry with backoff.

### v2 Time-Series Endpoints Return 409 Without Required Filter (discovered 2026-06-06)
Several v2 time-series endpoints return `409 Conflict` if called without a
mandatory `router` or `net_device` filter. This is NOT a rate limit — it's a
validation error requiring you to scope the query to specific device(s).

| Endpoint | Required Filter |
|----------|----------------|
| `historical_locations` | `router` |
| `net_device_signal_samples` | `net_device` or `net_device__in` |
| `net_device_usage_samples` | `net_device` or `net_device__in` |
| `router_logs` | `router` |
| `router_state_samples` | `router` or `router__in` |
| `router_stream_usage_samples` | `router` or `router__in` |

These endpoints use TimeUUID-based pagination and are optimized for
per-device queries. Always provide the filter or you'll get a 409.

### Cradlepoint Config .bin Files Use Varying Compression (discovered 2026-05-13)
Cradlepoint router configuration `.bin` files are compressed JSON, but the
compression format varies. Some use standard zlib (wbits=15), others use raw
deflate (no header, wbits=-15), and others use gzip (wbits=31). When decoding
`.bin` files, try multiple `zlib.decompress(data, wbits)` values in sequence:
`15`, `-15`, `31`, `47` (auto-detect). The first one that succeeds without a
`zlib.error` is the correct format. The decompressed content is always UTF-8
encoded JSON.

### Cradlepoint .bin Config Files Contain Both "config" and "state" Keys (discovered 2026-05-13)
When decompressing a Cradlepoint `.bin` configuration file, the resulting JSON
is an **array** structured as `[{"config": {...}, "state": {...}, "fw_info": {...}}, [[...], ...]]`.
The first element is an object containing `"config"` (the actual configuration),
`"state"` (runtime state data), and `"fw_info"` (firmware version). The second
element is an array of path references (e.g. `["config", "lan", 0, "devices", 2]`)
that appear to be deletion/override markers for the config tree.

When working with configs for templating or pushing to devices:
- **Reading:** Extract only `parsed[0]["config"]`
- **Writing:** Wrap config as `[{"config": <config_obj>}, []]` then zlib compress

The `.bin` files use standard zlib compression (magic bytes `78 9c`, wbits=15).
Config top-level keys include: certmgmt, container, ecm, identities, lan,
routing, security, stats, system, wan, wlan.

### Cradlepoint Config JSON Contains Raw Control Characters (discovered 2026-05-14)
Cradlepoint configuration JSON (extracted from `.bin` files or via API) contains
string values with raw newline characters (e.g. embedded YAML in container
project configs, PEM certificates). Python's `json.loads()` in strict mode
rejects these as "Invalid control character". Use `json.loads(content, strict=False)`
when parsing Cradlepoint config JSON to allow control characters in strings.

### NCM SDK SSL Verification Fails Behind Corporate Proxies (discovered 2026-06-08)
The NCM SDK uses `requests.Session()` with default SSL verification. Behind
corporate proxies that use TLS interception (MITM with custom CA certificates),
all API calls fail with `SSLCertVerificationError: CERTIFICATE_VERIFY_FAILED`.
The SDK does not expose a `verify` parameter, so callers must patch the session
directly after constructing the client:

```python
client = ncm.NcmClient(api_keys=api_keys)
client.session.verify = False  # Disable SSL verification
```

To also suppress the `InsecureRequestWarning` that `urllib3` emits on every
request when verify is disabled:
```python
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
```

Alternative (proper fix): set the `REQUESTS_CA_BUNDLE` env var to the path of
the proxy's CA certificate bundle:
```bash
export REQUESTS_CA_BUNDLE=/path/to/corporate-ca-bundle.crt
```

This affects ALL scripts and dashboards using the SDK, not just specific apps.

### v2 `device_apps` Returns IDs as Strings, Not Integers (discovered 2026-05-14)
The `/device_apps/` endpoint returns the `id` field as a string (e.g. `"83"`)
rather than an integer. This differs from most other v2 endpoints (like
`/routers/` and `/groups/`) which return integer IDs. When building lookup
dictionaries keyed by app ID — for example, to match `device_app_versions`
back to their parent app — use string keys or cast consistently. Attempting
`int()` conversion on the URL-extracted ID and comparing against the raw
response ID will fail silently (lookup miss) if one side is a string and the
other is an int.

### v2 `resource_url` Base Hostnames Vary Across Endpoints (discovered 2026-05-14)
The `resource_url` and relational URL fields in v2 API responses can use
different base hostnames depending on the account's regional shard (e.g.
`https://www.us0.cradlepointecm.com/api/v2/accounts/123/` vs
`https://www.cradlepointecm.com/api/v2/accounts/123/`). This means matching
a group's `account` URL against an account's `resource_url` by exact string
comparison will fail if the hostnames differ. Always extract the numeric ID
from the URL path (the last path segment before the trailing slash) and match
on that instead of comparing full URLs.

### `expand=account` IS Supported on `/groups/` Endpoint (discovered 2026-05-14)
The v2 `/groups/` endpoint DOES support `expand=account`. When used, the
`account` field becomes an inline object with `id`, `name`, `is_disabled`,
`resource_uri`, and `account` (parent account URL). This eliminates the need
for a separate `/accounts/` fetch to resolve group account names. Known
endpoints that support `expand`: `/routers/` (group, account), `/groups/`
(account).

### Long-Running Servers Need `source .venv/bin/activate`, Not Just `.venv/bin/python` (discovered 2026-08-04)
`setup_env.py` injects real credential values (`X_CP_API_ID`, `X_CP_API_KEY`,
`X_ECM_API_ID`, `X_ECM_API_KEY`) as `export` statements directly into
`.venv/bin/activate`. If `.env` is missing or incomplete (e.g. deleted,
partial setup), those exported values in `activate` are the only place the
credentials exist.

Calling `.venv/bin/python script.py` directly executes the interpreter
without sourcing `activate`, so those exported vars are never set in the
process environment — even though the venv itself (`sys.prefix`) is correctly
active. For one-shot scripts that call `check_env()` at startup, this fails
loudly and is easy to catch. For long-running servers (FastAPI/Flask
dashboards under `web_apps/`) that read `os.environ` lazily per-request
(e.g. via `_build_client()` on each API call) instead of validating at
startup, the server boots fine and returns 200 on static routes, but every
API call silently fails with a missing/empty credential error — there is no
startup-time signal that credentials are missing.

Workaround: always launch long-running dev servers with
`source .venv/bin/activate && python path/to/serve.py`, not
`.venv/bin/python path/to/serve.py`, whenever credentials may only be
present in the activate script rather than `.env`. This is safe to run in a
single non-interactive shell command (no prompts), unlike `setup_env.py`
with no flags.

### v2 `/alerts/` Endpoint Does Not Support `order_by` (discovered 2026-06-26)
The `/alerts/` endpoint returns `409 Conflict` with `"Invalid ordering field
specified: created_at"` when using `order_by=-created_at` or any `order_by`
parameter. The endpoint does not support ordering — results must be sorted
client-side. The endpoint does support `created_at__gt` for time filtering,
but requires full ISO 8601 format with microseconds and timezone offset
(e.g. `2026-06-26T15:00:37.703000+00:00`). The alert `type` field for
custom alerts is `custom_alert` (not `custom`).

### SDK `put_group_configuration()` Raises AttributeError After a Successful PUT (discovered 2026-08-13)
`NcmClientv2.put_group_configuration()` calls `self.__return_handler(...)` with
two leading underscores. Inside the class body that name-mangles to
`self._NcmClientv2__return_handler`, which does not exist — the real method is
`_return_handler` (defined on `BaseNcmClient`). Every other config method
(`patch_group_configuration`, `put_configuration_managers`,
`patch_configuration_managers`) uses the correct single-underscore name.

Verified by stubbing `session.put` and calling the method:

```
patch_group_configuration -> 'Configuration Manager operation successful.'
put_group_configuration   -> AttributeError: 'NcmClientv2' object has no
                             attribute '_NcmClientv2__return_handler'
```

The critical detail: **the HTTP PUT is sent before the exception is raised.**
The group config is already modified in NCM by the time the caller sees the
error, so treating the `AttributeError` as "the write failed" and retrying will
apply the PUT twice.

Workaround: use `patch_group_configuration()` when a merge is acceptable. When a
true PUT is required (the only way to honor the removals list and reset
unmentioned fields), issue it directly and skip the wrapper:

```python
resp = client.session.put(
    f'{client.base_url}/groups/{group_id}/',
    data=json.dumps({'configuration': [updates, removals]})
)
resp.raise_for_status()
```

### Credentials Can Drift Between `.env` and Individual Activate Scripts (discovered 2026-08-14)
`setup_env.py` stores credentials in two places: `.env`, which scripts read
directly, and the venv activate scripts, which only an activated shell picks up.
These can fall out of sync, and each activate script is independent — a venv can
have some populated and others not.

Confirmed instance: a venv whose credentials were last written on Jun 24 had all
four variables in `activate`, `activate.fish` and `activate.csh`, but zero in
`Activate.ps1` (no marker comments at all, file untouched since venv creation),
and no `.env` at all. `Activate.ps1` injection was added to `setup_env.py` on
2026-08-04 (`8be9817`), after that credential run — so any venv whose credentials
predate a change to the injection code will be missing whatever was added since.

Why it bites: nothing fails at setup time. A `bash`/`zsh` user sees a working
environment indefinitely. The failure lands on whoever uses a different shell — a
PowerShell user gets an activated venv with no credentials and no warning — or on
anyone running `.venv/bin/python` directly when `.env` is absent, which resolves
zero of four keys.

Diagnose with `setup_env.py --check`, which reports `.env` presence and per-script
credential status:

```
[warn] .env: not found - only activated shells will have credentials
[warn] activate scripts without all credentials: Activate.ps1 (none)
```

Fix by re-running `setup_env.py --credentials-only` (prompts, hidden input), which
rewrites `.env` and every activate script with the current code. From a shell that
already has the credentials exported, `setup_env.py --skip-credentials` achieves
the same thing non-interactively by reusing what is in `os.environ`.

`update_activate_scripts()` now reports every script by name with its outcome,
reads the values back to confirm they landed, and warns when a script that exists
did not receive them, so this drift is visible at write time rather than silent.
Absence of `activate.bat` on macOS/Linux is expected — `python -m venv` only
creates it on Windows.

### Web App Settings Modals Are a Third Credential Store (discovered 2026-08-14, tracking resolved 2026-08-14)
Credentials live in more places than `.env` and the venv activate scripts. Every
web app with a Settings modal writes what you type into a per-app JSON file beside
its `serve.py`, in plaintext:

- `profiles.json` — named credential profiles (`alert_dashboard`,
  `cellular_health_dashboard`, `geo_ip_blocker`, `inventory_dashboard`)
- `config.json` — active credentials plus saved job state (`host_identity_copier`)

Consequences worth knowing:

- These files survive `rm -rf .venv`, so an app can keep authenticating after the
  venv-injected credentials are gone. Convenient, and easy to forget when you
  think you have removed every copy of a key.
- They are a plaintext credential store in the working tree. Apps that write them
  should `chmod 0600` on POSIX; not all do.

**`.gitignore` does not retroactively untrack — the mechanism, kept because it will
recur.** `web_apps/*/config.json` and `web_apps/*/profiles.json` were added to
`.gitignore` on 2026-08-13. That stops *new* files being committed but has no effect
on files already in the index, so
`web_apps/cellular_health_dashboard/profiles.json` and
`web_apps/inventory_dashboard/profiles.json` stayed tracked and unprotected. Fixing
that requires `git rm --cached <path>`; after that the pattern takes over.

**Resolved 2026-08-14.** No `profiles.json` is tracked, present in `HEAD`, or on disk
anywhere in the repo. The two above were removed in commit `364fbff`. A third,
`web_apps/geo_ip_blocker/profiles.json`, appeared later the same day holding four
real key values; it was never tracked (the pattern worked, because it was new) and
was deleted after confirming all four values were byte-identical to `.env`, so the
app keeps working from environment variables.

Do not read the resolution as "this cannot happen again." Any app with a Settings
modal recreates its `profiles.json` the moment someone saves a profile. Deleting the
file is not the protection — the `.gitignore` pattern is, and it only works for files
that are not already tracked. Before committing, `git status` is the check that
matters.

**Committed history is clean — do not rotate on this basis.** An earlier version of
this entry claimed the values were already in committed history and the keys should
be rotated. That was wrong, and it is an expensive thing to get wrong. Verified
2026-08-14:

- only one commit (`426d2fa`) ever touched either path, and the blob is `{}` in both
- `git log --all --full-history -p -- <both paths>` adds no credential-valued lines
- every one of the 645 blobs across all 262 commits was searched for the four exact
  secret strings from the working-tree file: zero matches

The live keys existed only in the working tree, never in a commit. The risk was
prospective — a `git add -A` or `git commit -a` would have committed them — not
historical. No rotation was needed, and none was done.

**Diagnostic subtlety: `git check-ignore` lies about tracked files.** It skips paths
present in the index and reports them as not-ignored, which reads as "your pattern
is broken" when the pattern is fine. Separate the two questions:

```bash
git check-ignore -v --no-index <path>   # is the PATTERN right?      -> yes, matches line 13
git ls-files -c <path>                  # is the file TRACKED?       -> yes, that's the problem
```

Checking only the first form is what makes a tracked credential file look protected.
Also note `git check-ignore` needs `git` on `PATH`; if it is missing, the command
fails and a naive `if git check-ignore -q "$f"` shell test silently reports every
path as unignored.

When adding a Settings modal to a new app: write to a gitignored filename, set
`0600` on POSIX, mask secrets on read-back (return `"***"` rather than the value),
and never echo values into logs or responses.

### Bare `setup_env.py` Hangs From an Agent Tool Call — Tool Calls Get a TTY (discovered 2026-08-14)
Interactivity in `setup_env.py` is gated on one line:

```python
interactive = sys.stdin is not None and sys.stdin.isatty() and not args.skip_credentials
```

Measured from inside an agent tool call in this repo:

```
stdin isatty: True
stdout isatty: True
```

So the bare form takes the interactive branch and blocks in `getpass`. Nobody is
on the other end of that tty — command output is only returned to the agent when
the command exits, so the user never sees the prompt and cannot answer it. The
run hangs until the tool timeout. It does not skip gracefully.

**The misleading evidence that makes this easy to get backwards.** Running
`setup_env.py --skip-credentials` prints:

```
[warn] Skipping credentials (non-interactive mode)
```

That message proves nothing about `isatty`. The flag sets `interactive` to False
by itself through the `and not args.skip_credentials` clause, so the
non-interactive branch is taken whether or not a terminal is present. Do not
read it as evidence that tool calls lack a tty. They have one.

The module docstring's "safe to run from automation and from Kiro hooks" is
correct for hooks but should not be extended to agent tool calls.

Hook `command` actions are the opposite case: they receive the session JSON piped
on stdin, so stdin is a pipe, `isatty()` is False, and the non-interactive branch
runs. A hook therefore will not hang — but it also collects nothing, beyond
reusing whatever `os.environ` already holds. (Reasoned from the hook contract;
the tty result above is measured, this is not.)

Consequence worth stating plainly: **credentials cannot be collected by
automation at all.** Not from a tool call, not from a manual hook. The working
paths are:

- a human terminal, including the IDE's integrated terminal:
  `setup_env.py --credentials-only` (input hidden by `getpass`)
- a shell that already exports the four variables, then
  `setup_env.py --skip-credentials`, which reuses `os.environ` non-interactively
- a web app's Settings modal — subject to the plaintext-storage caveats in the
  entry above

This is a useful boundary rather than only a limitation: any channel an agent
could prompt through would place API keys in the agent's context and in the
session transcript. The `isatty` gate is what keeps them out.
### Repo Layout Claims in Steering Are Stale — Wrong Entry Points, Dead fileMatch Patterns (discovered 2026-08-14)
Several always-loaded and fileMatch steering claims describe a layout the repo no
longer has. These matter more than ordinary doc rot, because agents act on them
without checking.

**1. Not every web app has a `serve.py`.** `project-setup.md` and `AGENTS.md` both
stated "Each has a `serve.py` and a fixed port." That is false for five of the
twelve apps in `web_apps/`:

| Entry point | Apps |
|---|---|
| `serve.py` | `inventory_dashboard`, `cellular_health_dashboard`, `alert_dashboard`, `geo_ip_blocker`, `host_identity_copier`, `assign_sdk`, `web_app_template` |
| `config_builder.py` | `config_builder` |
| `script_manager.py` | `script_manager` |
| `ncm_api_key_encryptor.py` | `ncm_api_key_encryptor` |
| `router_lookup.py` | `netcloud_router_lookup` |
| `app.py` | `cisco_to_cradlepoint_zfw_converter` |

`web_apps/README.md` compounded it with a generic
`python3 web_apps/<app_name>/serve.py`. Run `ls web_apps/<name>/` before launching.
Both files now carry the table.

**2. `ncm-api-development.md` never loaded for web app code.** Its pattern was:

```
fileMatchPattern: "{scripts/**/*.py,ncm/**/*.py,ncm2/**/*.py,dashboards/**/*.py}"
```

`dashboards/` does not exist, and `web_apps/**/*.py` was absent — so the endpoint
routing table, the trailing-slash rule, the pagination and deprecation rules did not
auto-load when editing web app Python, which is where most of this repo's API calls
live. `AGENTS.md` meanwhile advertised the section as applying to `web_apps/`, so the
mirror promised coverage the Kiro config did not deliver. Pattern corrected to
`{scripts/**/*.py,ncm/**/*.py,ncm2/**/*.py,web_apps/**/*.py}`.

Worth generalizing: a `fileMatchPattern` naming a directory that does not exist fails
silently. Nothing warns you; the steering simply never activates. When adding or
renaming a top-level directory, grep `.kiro/steering/*.md` front matter for the old
name.

**3. `dashboards/cellular_health/` does not exist.** `web-ui-standards.md` pointed
its dashboard reference implementation at that path; the real one is
`web_apps/cellular_health_dashboard/`. Its own `fileMatchPattern` also carried a dead
`**/dashboards/**` clause. Both fixed.

**4. `scripts/script_manager/csv_files/` does not exist.** `code-standards.md` and
`AGENTS.md` both instructed storing CSV exports there. The real path is
`web_apps/script_manager/csv_files/`. Both fixed. The same stale path was also sitting
in `.gitignore`, protecting nothing while the real `csv_files/` went unignored; removed
2026-08-14.

**5. `ncm2/` is untracked.** It is referenced by `ncm-api-development.md`'s
`fileMatchPattern` and by `AGENTS.md`, but `git ls-files ncm2/` returns zero files
while `ncm/` returns eleven. It exists only in this working tree, so a fresh clone
will not have it. Do not `import` from `ncm2` in committed code, and do not cite it
in docs as though contributors have it. Use `ncm/` — that is the packaged SDK.

**6. `web_apps/mac_whitelist_copier/` is an empty directory.** Zero files, so it is
not an app and git does not see it at all (git does not track empty directories).
Excluded from the README tables.

**7. Entry-point docstrings drift too.** `web_apps/alert_dashboard/serve.py`'s
docstring told you to run `web_apps/custom_alert_dashboard/serve.py` and open port
8060; the directory is `alert_dashboard` and `PORT = 8065`. Fixed 2026-08-14, and its
usage line now uses the activate form rather than `.venv/bin/python`, since a
long-running server launched the bare way boots fine and then fails every API call.
The other eleven entry points were swept the same day — docstring path and port now
match source in all twelve, so treat a mismatch as a regression rather than the norm.

### `api-v2-full-reference.md` Query-Param Tables Can Be Incomplete — Cross-Check `ncm.py` (discovered 2026-08-28)
The generated tables in `docs/api-v2-full-reference.md` are not guaranteed to list
every filter an endpoint accepts. Read them as a floor, not a ceiling.

**Confirmed instance: `locations`.** Its table listed only `id`, `id__in`, `limit`
and `offset` — no `router` or `router__in`. Meanwhile the shipped client and two
shipped scripts depend on a router filter:

- `ncm/ncm/ncm.py` → `get_locations()` declares
  `allowed_params = ['id', 'id__in', 'router', 'router__in', 'limit', 'offset']`
- `scripts/export_locations.py` and
  `web_apps/script_manager/scripts/Export Locations.py` both batch with
  `n2.get_locations(router__in=batch)`

Every other router-scoped endpoint in the same reference (`configuration_managers`,
`device_app_states`, `net_devices`, `router_alerts`, `router_state_samples`,
`router_stream_usage_samples`) does document `router__in`, so `locations` was the
outlier rather than the rule. The two rows have been added to the reference with a
note.

Why it costs you: a reader who trusts the table concludes there is no server-side
router filter for locations, and fetches the whole collection to filter client-side.
On a large account that is many paginated requests instead of a batched query.

**Verification status.** The discrepancy between the doc and the shipped code is
directly observed. Whether `router__in` behaves as expected against a live account is
**UNVERIFIED** — no request was made to `/api/v2/locations/` when this was written.
Also UNVERIFIED: whether any endpoint *other* than `locations` has an incomplete
table. One instance was found; the rest were not audited.

Practical check before concluding a filter does not exist: grep the matching method's
`allowed_params` in `ncm/ncm/ncm.py`, and grep `scripts/` and `web_apps/` for existing
callers. Working code that predates the generated doc is the stronger evidence.
