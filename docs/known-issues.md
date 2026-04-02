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

### PATCH Cannot Remove Config Items
PATCH only adds or updates. To remove config items, you must use PUT with the
removals list in the diff.

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
The v2 `/net_devices/` endpoint supports an undocumented `is_asset` boolean
filter. Setting `is_asset=true` returns only the primary modem interfaces
(the physical cellular modems), filtering out virtual/logical interfaces.
This is useful when you only need modem-level details (IMEI, ICCID, carrier)
and want to avoid processing hundreds of non-modem net_device records.

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
Then validate v3-specific vars (`V3_BEARER_TOKEN`, etc.) separately.

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
