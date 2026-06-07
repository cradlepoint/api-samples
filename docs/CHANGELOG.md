# Documentation Changelog

This file tracks updates made to the documentation, especially those made
automatically by the reflexion system.

## 2026-03-31 — Initial Documentation

- Created consolidated API documentation from developer.cradlepoint.com
- Created api-overview.md with auth, pagination, filtering details
- Created api-v2-endpoints.md with all v2 endpoint reference
- Created api-v3-endpoints.md with all v3 endpoint reference
- Created api-configuration.md with device/group config management details
- Created api-webhooks.md with webhook setup and validation
- Created api-deprecations.md with deprecated endpoints/fields
- Created ncm-sdk-reference.md with Python SDK method reference
- Created common-patterns.md with reusable code patterns
- Created known-issues.md with gotchas and workarounds

## 2026-04-02 — Web UI Template Standards

- Created `.kiro/steering/web-ui-standards.md` — steering rule requiring all web apps to use `web_app_template` (`scripts/script_manager/static/`) as the style foundation
- Added "Web UI Template" section to `docs/common-patterns.md` with reference files and light/dark mode requirements
- All new web interfaces must include light mode and dark mode support with `localStorage` persistence

## 2026-03-31 — Reflexion: Post-Build Discoveries

- Added known issue: SDK vs Session utility use different credential key naming conventions (HTTP header names vs snake_case). Mixing them causes silent auth failures.
- Added known issue: `__in` filter parameters are limited to 100 values per API call. SDK auto-chunks, but raw calls must handle this manually.

## 2026-03-31 — Reflexion: Env Check and Credential Bridging

- Updated common-patterns.md: manual `requests` pagination pattern now uses `get_api_keys_from_env()` instead of hardcoded placeholder headers, ensuring consistency with the env var system and avoiding the SDK/session credential key mismatch.

## 2026-03-31 — Documented venv pip workaround and missing Flask dependency
- Added known issue: `.venv/bin/pip` has bad interpreter after repo move; use `python -m pip` instead
- Added known issue: Flask not installed despite being in requirements.txt; run full pip install after clone

## 2026-03-31 — Documented venv --clear credential loss
- Added known issue: recreating venv with --clear wipes API credentials injected by setup_env.py; must re-run setup_env.py afterward

## 2026-03-31 — Documented SDK `fields` parameter limitation
- Added known issue: `fields` kwarg only works on SDK methods that explicitly include it in `allowed_params` (e.g. `get_routers`), not on `get_groups`, `get_products`, `get_firmwares`

## 2026-03-31 — Added `fields` support to SDK `get_groups()`
- Updated `ncm/ncm/ncm.py`: added `'fields'` to `get_groups()` `allowed_params`
- Updated known-issues.md to reflect `get_groups()` now supports `fields`

## 2026-04-01 — Documented v2 relational field URLs, v3 subscription status, and Flask fields bug
- Added known issue: v2 relational fields (group, product, firmware) are URLs, not values; use expand or lookup
- Added known issue: v3 subscriptions have no status field; derive from end_time
- Added known issue: SDK fields parameter returns empty results inside Flask; omit fields as workaround

## 2026-04-01 — Reflexion: Inventory Dashboard review discoveries
- Added known issue: v2 and v3 use different MAC address formats (`mac` with colons vs `mac_address` bare hex); normalize before joining
- Added known issue: v3 exchange_sites endpoint lives at `/beta/exchange_sites`, not `/exchange_sites`; beta contract may change
- Added known issue: v2 net_devices `is_asset=true` filter returns only physical modem interfaces, useful for skipping virtual/logical entries
- Added common pattern: v3 cursor-based pagination (`page[size]`, `links.next`) with code example

## 2026-04-01 — Reflexion: Rate limit and transient error discoveries
- Added known issue: v3 API returns 409 Conflict ("invalid app-key") as a rate limit instead of 429; treat as retryable
- Added known issue: v2 API returns transient 500 "cp internal error shard-router-N" during heavy pagination; retry with backoff
- Updated common-patterns.md: error handling retry pattern now includes 409, 500, 502 in retryable set and respects Retry-After header

## 2026-04-01 — Fixed infinite pagination loop caused by httpx params={}
- Added known issue: passing `params={}` to httpx/requests strips query params from pagination URLs, causing infinite loops; use `params=None` instead
- Fixed common-patterns.md v3 pagination example to use `params=None`
- Fixed Inventory Dashboard SDK: all four pagination methods (`_get_paged`, `_async_get_paged`, `_get_paged_v3`, `_async_get_paged_v3`) updated

## 2026-04-01 — Discovered v3 subscription ID mismatch between asset_endpoints and subscriptions
- Added known issue: v3 asset_endpoint `subscription_ids` are assignment-level IDs, not parent subscription IDs; must resolve via `filter[id]`
- Added known issue: v3 `/subscriptions/{id}` returns 404 for assignment IDs but `filter[id]` works; supports comma-separated batching
- Fixed Inventory Dashboard SDK: subscription resolution now batch-fetches assignment IDs via `filter[id]` for correct license status

## 2026-04-02 — Generalized v3 /beta/ prefix documentation

- Updated known-issues.md: Generalized the `exchange_sites` beta prefix entry to cover all v3 beta endpoints (`modem_software_versions`, `modem_upgrades`). The `/api/v3/beta/` prefix is a pattern, not a one-off.

## 2026-04-02 — Documented check_env() gotcha for v3-only scripts

- Added known issue: `check_env()` prints misleading v2 credential errors in v3-only scripts. Documented stderr suppression workaround.

## 2026-04-02 — v3 beta trailing slash 404 discovery

- Added known issue: v3 beta endpoints return 404 when URLs include a trailing slash. Clarified the existing trailing-slash rule as v2-only.

## 2026-04-02 — Modem Management API spec-vs-reality discrepancies

- Added known issue: POST modem_upgrades returns 200, not 201 as spec claims.
- Added known issue: Request body `data.type` must be `"modem_upgrades"` (collection name), not `"modem_upgrade_parent"` as spec documents. Response still uses `"modem_upgrade_parent"`.
- Added known issue: 409 Conflict is overloaded — rate limit (retryable) vs JSON:API validation error (not retryable). Check for `errors` array in body to distinguish.

## 2026-04-07 — Documented SDK module-level delegation hang with v3-only credentials

- Added known issue: calling v2 methods (e.g. `get_routers()`) via module-level SDK delegation (`import ncm; ncm.get_routers(...)`) silently hangs when only v3 credentials are set. The auto-initialized v3 singleton sends unauthenticated requests to the v2 base URL, and the retry adapter causes indefinite blocking. Use `NcmClientv3` directly with v3 equivalents instead.

## 2026-04-07 — Documented v2 router ID vs v3 asset endpoint ID mismatch

- Added known issue: v2 router IDs and v3 asset endpoint IDs are completely different ID spaces for the same physical device. Using a v2 router ID with `get_asset_endpoints(id=...)` returns wrong results or nothing. Use `mac_address` or `serial_number` as the cross-reference key instead.

## 2026-04-07 — SDK review: error handling, regrade header bug, MAC normalization

- Added known issue: SDK `_return_handler` returns error strings instead of raising exceptions. API errors are invisible to try/except. v2 `__get_json` silently returns empty/partial results on non-2xx; v3 returns a string where a list is expected.
- Added known issue: SDK `regrade()` is missing the JSON:API atomic extension Content-Type/Accept headers that `unlicense_devices()` correctly sets. This can cause 400 errors even when the payload is correct.
- Added known issue: SDK `regrade()` MAC normalization only strips colons for 17-char strings. Dash-separated, dot-separated, and lowercase MACs pass through malformed. Always pre-normalize to bare uppercase hex.

## 2026-04-09 — Documented expand=group performance advantage over separate /groups/ fetch

- Added known issue: on large accounts, fetching `/groups/` separately can return 4000+ groups across many paginated requests, taking minutes. Using `expand=group` on the `/routers/` call inlines group data directly and is dramatically faster. Always prefer `expand` over separate lookup fetches.

## 2026-04-09 — Documented v3 regrades batch validation rules

- Added known issue: v3 regrades endpoint rejects entire batch if duplicate MAC addresses appear in a single request. Deduplicate before sending.
- Added known issue: v3 regrades endpoint requires MAC addresses to be exactly 12 hex digits with no separators. Validate format before sending.

## 2026-04-28 — Documented v2/v3 architectural separation (no cross-referencing)

- Added known issue: v2 and v3 are fully separate API systems with different auth, ID types, specs, and relationship models. v3 relationships only reference other v3 resources — you cannot resolve them via v2 endpoints. When migrating, all related resource lookups must also move to v3.

## 2026-05-13 — Documented Cradlepoint .bin file compression variance
- Added known issue: Cradlepoint config .bin files use varying compression formats (zlib, raw deflate, gzip); must try multiple wbits values when decoding
- Added known issue: Cradlepoint .bin config files contain both "config" and "state" top-level keys; only "config" is needed for templating
- Added known issue: Cradlepoint config JSON contains raw control characters (newlines in YAML/PEM strings); use json.loads(strict=False)

## 2026-05-14 — Documented v2 resource_url hostname variance and device_apps string IDs

- Added known issue: v2 `resource_url` fields can use different base hostnames across regional shards (e.g. `www.us0.cradlepointecm.com` vs `www.cradlepointecm.com`). Match on extracted numeric ID, not full URL strings.
- Added known issue: v2 `device_apps` endpoint returns `id` as a string, not an integer. Use string keys in lookup dictionaries.

## 2026-05-14 — Corrected: expand=account IS supported on /groups/

- Corrected known-issues.md: `expand=account` works on `/groups/` — inlines account object with `name`, `id`, etc. Updated list of endpoints known to support `expand`.

## 2026-06-05 — Documented net_device_health returns all device types

- Added known issue: `net_device_health` endpoint returns records for ALL net_device modes (wan, lan, mdm), not just cellular/WAN. Filtering `get_net_devices(mode='wan')` when joining causes silent data loss. Always fetch all net_devices when correlating with health data.

## 2026-06-06 — Documented net_device_health, net_devices, and metrics relationship

- Added known issue: `net_device_health` only returns `cellular_health_category` and `cellular_health_score` — no signal metrics. Use `net_device_metrics` for RSSI/RSRP/RSRQ/SINR.
- Added known issue: `net_devices` do not contain signal fields; those are only on `net_device_metrics`.
- Added known issue: `net_devices` `router` field can be null for orphaned/unassigned modems.
- Added known issue: v2 API IDs are returned as strings, not integers. Normalize to strings for lookups.
- Documented the correct 4-endpoint pattern for building cellular health dashboards.

## 2026-06-06 — Corrected is_asset documentation, documented expand=router on net_devices

- Corrected known-issues.md: `is_asset` on `/net_devices/` is officially documented in the Swagger spec, not "undocumented".
- Added known issue: `/net_devices/` supports `expand=router` and `expand=account`, inlining the full router/account object. Eliminates separate fetch.

## 2026-06-06 — Documented net_device_metrics response schema and expand limitations

- Added known issue: `net_device_metrics` full response schema documented (signal_strength not signal_percent, cell info, usage fields). ID equals net_device ID.
- Added known issue: `expand=router` on `/net_devices/` only expands one level — nested relations (group, account) remain as URLs. Must resolve separately.

## 2026-06-06 — Full API documentation generated, documented 409 filter requirement

- Generated `docs/api-v2-full-reference.md` — complete endpoint reference with query params and response fields for all 30 v2 endpoints.
- Generated `docs/api-documentation-gaps.md` — documents endpoints that require filters, POST-only endpoints, and missing response schemas in Swagger specs.
- Added known issue: v2 time-series endpoints (signal_samples, usage_samples, state_samples, logs, historical_locations) return 409 Conflict without a required `router` or `net_device` filter. This is a validation error, not a rate limit.

## 2026-06-06 — Documented v3 token env var naming inconsistency

- Added known issue: v3 bearer token env var name is not standardized across the project. Scripts use `TOKEN`, `NCM_API_TOKEN`, or `V3_BEARER_TOKEN` depending on the script. `CP_API_TOKEN` in env_check.py isn't used by any actual script.

## 2026-06-06 — Standardized v3 token env var name to `NCM_API_TOKEN`

- Refactored all scripts to use `NCM_API_TOKEN` as the single env var for the v3 bearer token.
- Removed `TOKEN` fallback from: Create NCX Resources, Create NCX Sites, Unlicense Devices, Update Subscriptions, script_manager scripts.
- Changed `V3_BEARER_TOKEN` to `NCM_API_TOKEN` in Inventory Dashboard files.
- Changed `CP_API_TOKEN` to `NCM_API_TOKEN` in scripts/utils/env_check.py and steering files.
- Updated known-issues.md to reflect the standardization.
