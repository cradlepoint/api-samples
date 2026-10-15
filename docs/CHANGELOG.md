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

## 2026-06-08 — Documented NCM SDK SSL verification failure behind proxies

- Added known issue: NCM SDK's `requests.Session` uses default SSL verification, which fails behind corporate TLS-intercepting proxies. Workaround: set `client.session.verify = False` after constructing the client, or set `REQUESTS_CA_BUNDLE` env var to the proxy CA bundle path.

## 2026-06-09 — Documented NCM SDK + FastAPI event loop blocking pattern

- Added common pattern: NCM SDK uses synchronous `requests.Session` which blocks the async event loop when called from FastAPI `async def` handlers. Must wrap in `run_in_executor()` to keep the server responsive. Applies to all dashboard apps using FastAPI + NCM SDK.

## 2026-08-04 — Documented venv activation gap for long-running servers

- Added known issue: `setup_env.py` injects credentials as `export` statements into `.venv/bin/activate`, not always into `.env`. Running long-running servers with `.venv/bin/python serve.py` (without sourcing `activate`) uses the correct venv interpreter but skips those exported credentials, causing silent per-request auth failures with no startup error. Workaround: launch servers with `source .venv/bin/activate && python serve.py`.
## 2026-08-13 — SDK config-write gotchas and group config-copy pattern
- Added known issue: `NcmClientv2.put_group_configuration()` calls the name-mangled `self.__return_handler`, which does not exist, so it raises `AttributeError` — but only *after* the HTTP PUT has already been sent. The group config is already modified when the caller sees the error, so retrying double-applies the write. Workaround: use `patch_group_configuration()`, or issue the PUT via `client.session.put()` directly. Every other config method uses the correct `_return_handler`.
- Corrected known issue: the 2026-04-07 `_return_handler` entry claimed it returns error strings (`"ERROR: 400: ..."`) instead of raising. The SDK now raises `requests.exceptions.HTTPError` for 400/401/404/500, so `try/except` around SDK calls does work. Documented the actual per-status-code behavior in a table, and kept the two traps that remain real: unhandled status codes (403, 409, 429) log and return `None`, and v2's `__get_json` still `break`s out of pagination on non-2xx before the handler runs, returning partial results with no error.
- Added common pattern: "Copying a Config Subtree Between Groups" — NCM returns config arrays as index-keyed objects on read but PATCH replaces real arrays while merging objects, which is the lever for choosing mirror vs merge semantics when copying a config branch to many groups. Includes subtree extraction, entry normalization, and per-group error isolation.
## 2026-08-13 — UUID-keyed vs index-keyed config collections when copying
- Extended the "Copying a Config Subtree Between Groups" pattern in `common-patterns.md` with a section on UUID-keyed collections. The original example covered index-keyed arrays only. Because PATCH merges objects by key, a PATCH copy of a UUID-keyed collection (`identities.ip`, `lan`, `vpn.tunnels`, `security.zfw.zones`, ...) is additive — destination-only entries have no matching key and survive, so no PATCH body can make the destination exactly equal the source. Real subtrees nest both styles (UUID-keyed `identities.ip` whose entries each hold an index-keyed `members` array), so the outer level is always a merge while the mirror/merge choice applies to the inner array. Also documented keying the output dict by `_id_` rather than the key it was read under.
- Added a caveat to the "PATCH Cannot Remove Config Items" known issue: the standard "use PUT with the removals list" advice is unsafe at `/groups/{id}/` scope, because PUT resets unmentioned fields to defaults and would wipe every other group-level setting. Pruning one branch of a group config requires a PUT carrying the group's entire existing configuration plus the removals list. Noted the consequence that copying UUID-keyed collections between groups is therefore inherently additive.
## 2026-08-14 — Correction: PATCH CAN remove config items via the removals list
Supersedes the relevant parts of the 2026-08-13 entries below. A user supplied NCM UI request traffic showing that removing a single address from a host identity is sent as a PATCH with an empty updates dict and a populated removals list. The repo's documentation had asserted the opposite since the initial import.
- Rewrote the `known-issues.md` entry "PATCH Cannot Remove Config Items" (now "PATCH CAN Remove Config Items — via the Removals List"). The old text claimed PATCH only adds or updates and that removal requires PUT. Also retracted the 2026-08-13 caveat that was built on top of that error. Documented both observed wire formats, that both diff slots can be populated in one PATCH, and that removing a whole entry means stopping the path at its UUID.
- Documented a format asymmetry that is easy to get wrong: **removal paths address array positions with integer indices, while the updates dict uses string keys for the same positions** (`{"members": {"2": {...}}}` to set, `[..., "members", 2]` to remove).
- Updated the PUT vs PATCH table in `api-configuration.md`, which listed "Can remove items: PATCH — No", and expanded the "Removals List" section with the PATCH usage, the integer-index rule, and whole-entry removal.
- Corrected `common-patterns.md`: the UUID-keyed subsection added on 2026-08-13 claimed "no PATCH body can make the destination exactly equal the source." Replaced with a "Mirroring a collection" section showing how to diff against the destination and emit removals, noting it costs one extra GET per destination because the payload is no longer identical across groups.
- Guidance reversal: prefer PATCH with removals over PUT for pruning a branch of a group config. PUT resets unmentioned fields to defaults, which at `/groups/{id}/` scope wipes unrelated group settings.
- Unconfirmed: whether NCM resolves removal paths against the pre-change config or applies them sequentially with reindexing. Emit multiple indices from the same array highest-first, which is correct either way.
## 2026-08-14 — Credential drift between .env and activate scripts
- Added known issue: `setup_env.py` writes credentials to both `.env` and the venv activate scripts, and the two can drift — as can individual activate scripts from each other. Confirmed instance: all four vars in `activate`/`activate.fish`/`activate.csh`, zero in `Activate.ps1`, and no `.env`, because the credential run predated the commit that added PowerShell injection (`8be9817`, 2026-08-04). Nothing fails at setup time, so a bash/zsh user never notices; the failure lands on a PowerShell user (activated venv, no credentials, no warning) or on any non-activated `.venv/bin/python` run when `.env` is absent. Documented the `--check` diagnostics and both repair paths.
- Related behavior change in `setup_env.py`: `update_activate_scripts()` now reports each activate script by name with its outcome, reads values back to confirm the injection landed, and warns when a script that exists did not receive the credentials. Previously a skipped or unwritten script was silent unless every script failed. `--check` gained `.env` presence and per-script credential reporting.
- Related steering change in `.kiro/steering/project-setup.md`: the default for running project code is now `source .venv/bin/activate && python3 ...` (`;` instead of `&&` in PowerShell), with the full interpreter path demoted to a documented fallback. The previous "prefer the full interpreter path" default silently skipped credentials that exist only in the activate script.
## 2026-08-14 — Web app Settings modals as a third credential store
- Added known issue: every web app with a Settings modal persists typed credentials in plaintext to a per-app file beside its `serve.py` (`profiles.json` for the dashboards, `config.json` for `host_identity_copier`). This is a third credential location alongside `.env` and the venv activate scripts. These files survive `rm -rf .venv`, so an app can keep authenticating after the venv-injected credentials are gone — convenient, and easy to miss when trying to remove every copy of a key.
- Documented that `.gitignore` does not retroactively untrack: `web_apps/*/config.json` and `web_apps/*/profiles.json` were added on 2026-08-13, but `web_apps/cellular_health_dashboard/profiles.json` and `web_apps/inventory_dashboard/profiles.json` remain in the index (`git check-ignore` returns false for both). Clearing them requires `git rm --cached`. **The rotation advice originally in this bullet was wrong and was retracted on 2026-08-14 — see the `.gitignore` audit entry below. Committed history is clean.**
- Added guidance for new Settings modals: gitignored filename, `0600` on POSIX, mask secrets on read-back (`"***"`), never echo values into logs or responses.

## 2026-08-14 — Agent tool calls have a tty; bare `setup_env.py` hangs there
Corrects a wrong inference made and reverted within the same session, recorded because the mistake is an easy one to repeat and the misleading evidence is still sitting in the tool output.
- Added known issue: `setup_env.py` gates prompting on `sys.stdin.isatty() and not args.skip_credentials`. Measured inside an agent tool call, **stdin and stdout are both ttys**, so the bare form enters the interactive branch and blocks in `getpass` until the tool timeout. The user never sees the prompt, because command output only returns to the agent when the command exits.
- Documented the trap: `--skip-credentials` printing "Skipping credentials (non-interactive mode)" is **not** evidence of a missing tty. The flag forces `interactive` to False on its own, so that message appears regardless of whether a terminal is present. Mistaking it for an `isatty` result is what produced the bad inference.
- Contrasted hook `command` actions, which receive the session JSON on stdin: stdin is a pipe there, so the non-interactive branch runs and nothing hangs, but nothing is collected either beyond what `os.environ` already holds. Labeled in the doc as reasoned from the hook contract rather than measured.
- Recorded the consequence: credentials cannot be collected by automation at all — not from a tool call, not from a manual hook. Working paths are a human terminal (the IDE's integrated terminal counts), pre-exported env vars plus `--skip-credentials`, or a web app Settings modal with the plaintext caveats already documented.
- Steering reverted in `project-setup.md` and `setup-environment.md`. Mid-session both files were edited to claim the bare form "does not actually hang," replacing accurate guidance with inaccurate guidance. The original warning was right. Both now carry the `isatty` mechanism and an explicit note not to treat the `--skip-credentials` message as evidence.
- Clarified the `setup_env.py` module docstring, whose "safe to run from automation and from Kiro hooks" is true for hooks but invites exactly this error when read as covering agent tool calls.

## 2026-08-14 — Steering: auto-run setup when `.venv` is missing
- Added a "Missing `.venv`: set it up, do not ask" section to `.kiro/steering/project-setup.md` (`inclusion: always`). Triggers on the session-start check reporting `venv: MISSING`, on `.venv/` being absent when project Python or a web app is about to run, or on reported import failures. Procedure: system launcher, `setup_env.py --skip-credentials`, fix and re-run on failure, confirm with `--check`, then return to the original request.
- The rule stops at dependencies by design and forbids describing the environment as "ready" while credentials are missing, since `--credentials-only` requires a terminal and keys must not pass through chat.
- Cross-referenced from `setup-environment.md` so the manual walkthrough and the automatic path do not drift.
## 2026-08-14 — `.gitignore` audit: retracted a rotation recommendation, added the check-ignore trap
Retracts a claim made in the 2026-08-14 Settings-modal entry above. Recorded because the error pointed at an irreversible action (rotating production API keys) on the strength of an unverified premise.
- **Retracted:** "the values are in committed history, the keys should be rotated." Committed history is clean. Verified three ways: only one commit (`426d2fa`) ever touched either `profiles.json` and the blob is `{}` in both; `git log --all --full-history -p` over both paths adds no credential-valued lines; all 645 blobs across all 262 commits were searched for the four exact secret strings from the working-tree file, with zero matches. The live keys exist only in `web_apps/cellular_health_dashboard/profiles.json` in the working tree. `inventory_dashboard/profiles.json` is `{}`. The exposure is prospective (`git add -A` would commit them), not historical.
- Added to `known-issues.md`: **`git check-ignore` reports tracked files as not-ignored.** It skips paths in the index, which reads as a broken pattern when the pattern is correct. Separate the questions with `git check-ignore -v --no-index <path>` (is the pattern right?) and `git ls-files -c <path>` (is it tracked?). Confirmed here that `web_apps/*/profiles.json` matches correctly at `.gitignore:13` and tracking alone is the defect. Checking only the first form is what makes a tracked credential file look protected.
- Also noted: if `git` is absent from `PATH`, a bare `if git check-ignore -q "$f"` shell test fails open and reports every path as unignored. Hit during this audit and it produced a full page of false "EXPOSED" results, including for `.env`, which is in fact correctly ignored.
- Audit findings for `.gitignore` itself, not yet applied: `scripts/script_manager/csv_files/` and `scripts/script_manager/.last_file.txt` match nothing because the app lives at `web_apps/script_manager/`, leaving the real `csv_files/` (9 files) and `.last_file.txt` unignored; the `.gitignore` self-reference is inert since the file is tracked; several web app state files (`acks.json`, `settings.json`, `snapshot_cache.json`, `history.db`, `history/`, `inventory_snapshot.json`) are untracked and unignored. `settings.json` holds only `default_profile`, no secrets.
- Same stale path in `AGENTS.md` and `.kiro/steering/code-standards.md`: both instruct storing exports in `scripts/script_manager/csv_files/`, which does not exist.

## 2026-08-14 — Stale repo-layout claims in steering; one fileMatch pattern never matched
Found while rewriting `README.md`. Grouped because they share a cause: the repo moved things (`dashboards/` → `web_apps/`, `scripts/script_manager/` → `web_apps/script_manager/`) and the steering files were not updated with it.
- **Functional fix, not just docs:** `.kiro/steering/ncm-api-development.md` had `fileMatchPattern: "{scripts/**/*.py,ncm/**/*.py,ncm2/**/*.py,dashboards/**/*.py}"`. `dashboards/` does not exist and `web_apps/**/*.py` was missing, so the endpoint routing table, trailing-slash rule, pagination and deprecation rules never auto-loaded while editing web app Python — where most of this repo's API calls are. `AGENTS.md` advertised the section as covering `web_apps/`, so the mirror promised coverage the config did not provide. Pattern now `{scripts/**/*.py,ncm/**/*.py,ncm2/**/*.py,web_apps/**/*.py}`.
- Generalized in `known-issues.md`: a `fileMatchPattern` naming a nonexistent directory fails silently — no warning, the steering just never activates. Grep steering front matter when renaming a top-level directory.
- Corrected "Each has a `serve.py`" in `.kiro/steering/project-setup.md` (`inclusion: always`) and `AGENTS.md`. False for 5 of 12 apps: `config_builder.py`, `script_manager.py`, `ncm_api_key_encryptor.py`, `router_lookup.py`, `app.py`. Both now carry the entry-point table; `web_apps/README.md`'s generic `serve.py` command was fixed the same way.
- Corrected the dashboard reference path in `.kiro/steering/web-ui-standards.md` from `dashboards/cellular_health/` to `web_apps/cellular_health_dashboard/`, and dropped the dead `**/dashboards/**` clause from its `fileMatchPattern`.
- Corrected the CSV export path in `.kiro/steering/code-standards.md` and `AGENTS.md` from `scripts/script_manager/csv_files/` to `web_apps/script_manager/csv_files/`. Logged as a finding on 2026-08-14 in the `.gitignore` audit entry; now applied. The stale path still sits in `.gitignore`, protecting nothing.
- Recorded that `ncm2/` is untracked (`git ls-files ncm2/` → 0 files; `ncm/` → 11). It exists only in this working tree, so committed code must not import from it. Removed from the `README.md` project structure.
- Recorded that `web_apps/mac_whitelist_copier/` is an empty directory — not an app, and invisible to git.
- `README.md` rewritten for the fork-based workflow: fork, clone the fork via Kiro's `Git: Clone`, add an `upstream` remote, run setup, build by chatting, then open a PR. Web app table corrected to 12 entries with per-app entry points and source-verified ports; `alert_dashboard`, `geo_ip_blocker`, `host_identity_copier` and `web_app_template` were missing. Contribution section warns against `git add -A` because tracked credential files are still in the working tree.

## 2026-08-14 — profiles.json tracking resolved; stale "open problem" claims closed out
Mostly bookkeeping: fixes from earlier in the day landed, which left several entries describing problems that no longer exist. Recorded because a known-issues file that lists resolved problems as open costs the next reader a pointless investigation.
- **Resolved:** no `profiles.json` is tracked, in `HEAD`, or on disk. `web_apps/cellular_health_dashboard/profiles.json` and `web_apps/inventory_dashboard/profiles.json` were removed in commit `364fbff`. A third, `web_apps/geo_ip_blocker/profiles.json`, appeared later the same day with four real key values — never tracked, since the `.gitignore` pattern works for files that were not already in the index — and was deleted after confirming all four values were byte-identical to `.env`, so `geo_ip_blocker` continues to authenticate from environment variables.
- Retitled the Settings-modal known issue from "...and Two Are Committed" and rewrote the tracking section as mechanism-plus-resolution. Kept the mechanism: `.gitignore` never applies to already-tracked files, so `git rm --cached` is the fix.
- Added the caveat that makes the resolution durable: deleting `profiles.json` is **not** the protection. Any app with a Settings modal recreates it the moment a profile is saved. The `.gitignore` pattern is the protection, and it only works while the file is untracked. `git status` before committing is the check that matters.
- Corrected the history-is-clean paragraph to past tense — the live keys existed only in the working tree, never in a commit, so no rotation was needed and none was done.
- Closed out two stale notes in the repo-layout entry: the `scripts/script_manager/csv_files/` line has now been removed from `.gitignore`, and the `alert_dashboard` docstring is fixed.
- Promoted the `alert_dashboard` docstring note from an app-specific aside to item 7, "Entry-point docstrings drift too," after sweeping all twelve entry points: docstring path and port now match source everywhere, so a mismatch is a regression rather than the norm. Its usage line also switched from `.venv/bin/python` to the activate form, since a long-running server launched the bare way boots cleanly and then fails every API call.

## 2026-08-26 — Fan-in consolidation pattern for UUID-keyed collections

- Added a `common-patterns.md` section ("Consolidating (fan-in) a UUID-keyed
  collection from many sources into one") covering the reverse of the existing
  mirror pattern: merging a UUID-keyed collection like `identities.ip` from many
  source groups into one destination. Key generalizable points: merge by the
  collection's natural key (e.g. `name`), not by `_id_` (UUIDs are per-source-group
  and never shared across groups), and when writing the merged result back, match
  the destination by that same natural key and reuse its existing UUID rather than
  minting a new one — otherwise every run regenerates every identity's UUID, which
  breaks anything elsewhere in the config that references the old UUID. Discovered
  while building Consolidate Mode for `host_identity_copier`.

## 2026-08-28 — `locations` endpoint missing `router`/`router__in` in the generated reference

Found while answering a question about retrieving router lat/long. No code was written
and no API call was made; this is a doc-vs-shipped-code discrepancy only.

- Added `router` and `router__in` rows to the `locations` query-parameter table in
  `api-v2-full-reference.md`, which listed only `id`, `id__in`, `limit` and `offset`.
  Evidence is in-repo: `get_locations()` in `ncm/ncm/ncm.py` declares both in
  `allowed_params`, and `scripts/export_locations.py` plus
  `web_apps/script_manager/scripts/Export Locations.py` both batch on
  `router__in`. Every other router-scoped endpoint in that reference already
  documented `router__in`, so `locations` was the outlier.
- Marked the addition **UNVERIFIED against a live account** in the doc itself — the
  evidence is shipped code, not an observed response. The `in: int / out: url` type
  notation is inferred from the sibling endpoints' rows, and whether `router__in` has
  its own page-size ceiling on this endpoint is unknown.
- Added a `known-issues.md` entry generalizing the lesson: the generated query-param
  tables are a floor, not a ceiling. Before concluding a filter does not exist, grep
  the method's `allowed_params` in `ncm/ncm/ncm.py` and grep `scripts/` and
  `web_apps/` for existing callers. Recorded explicitly that only this one endpoint
  was found incomplete and the other 29 were not audited.

## 2026-08-27 — Parallelized chunked cellular health fetches; fixed online/offline to use connection_state

- Added known issue: `net_device_health` has no timestamp filter at all (confirmed against `docs/api-v2-full-reference.md` and the SDK's `allowed_params`), so it always requires a full `limit='all'` pull — incremental refresh is only possible for `net_device_metrics`, which does support `update_ts__gt/lt`.
- Added known issue: `net_devices.connection_state` (per-interface) and `routers.state` (per-router) are frequently conflated. A router can be `online` while a specific modem interface is `disconnected`, `connecting`, or `standby`. Documented observed `connection_state` values and a sampled account where 50 of 472 interfaces were miscounted as online under the old logic.
- Added common pattern: "Parallelizing Chunked `__in` Requests" — fan chunked `net_device_metrics`/`net_devices`/`asset_endpoints` calls out over a `ThreadPoolExecutor` instead of a sequential loop, since each 100-ID chunk is an independent request. Generalizes the pattern already used ad hoc in `assign_sdk/serve.py`.
- Fixed `web_apps/cellular_health_dashboard/serve.py`: `_get_cellular_health()` now fetches `net_device_metrics` and `net_devices` chunks concurrently (both across chunks within each call, and between the two calls) via `_fetch_chunks_parallel()`, cutting the ~600 sequential API calls needed for a 27k-device account down to a handful of concurrent batches. Also changed `router_state` derivation to be based on `net_devices.connection_state` (`connected` → online, `unplugged` → unplugged, everything else → offline) instead of the parent router's `state`, fixing devices being shown as online when their actual cellular interface was disconnected/connecting/standby.

## 2026-08-27 — Correction: per-interface online/offline is binary, not three-state

Supersedes part of the 2026-08-27 entry above, which had `unplugged` as a third state.

- Corrected `known-issues.md` ("`net_devices.connection_state` vs `routers.state`"): the guidance to keep `unplugged` as its own distinct badge was wrong in practice. A third bucket means the summary counts no longer sum to the total (7 unplugged interfaces on the sampled account were neither online nor offline), which reads as a bug in the dashboard. Treat `connection_state` as binary: `connected` is online, everything else — `disconnected`, `connecting`, `standby`, `standby_connecting`, `unplugged` — is offline.
- Updated `web_apps/cellular_health_dashboard/serve.py` accordingly: `iface_state = 'online' if connection_state == 'connected' else 'offline'`. Verified against the live account — 60 online / 410 offline / 470 total, sums correctly, and zero rows where the online flag disagrees with `connection_state == 'connected'`.

## 2026-08-27 — Cellular health data granularity is per-modem, not per-router

- Added known issue: `net_device_health`, `net_device_metrics` and `net_devices` are keyed by net_device (one record per network interface), not by router, so a router with two modems yields two records and `expand=router` duplicates the router name across them. Documented three consequences: router name/ID is not a unique row key (`(router_name, interface_name)` is the display key, net_device ID the real one); record counts are interface counts rather than device counts, so labeling such a total "Devices" in a UI overstates how many routers exist; and per-router rollups require explicit grouping by router ID plus a decision on how to combine multiple modems' scores. Also noted that `net_devices.model` is the modem model, not the router model.
- Surfaced while relabeling the cellular health dashboard UI: the ambiguity of "device" between the router level and the modem-interface level is what made the original labels misleading, and it is a data-modeling property of these endpoints rather than anything specific to that app.

## 2026-08-27 — Favicon pattern for web apps

- Added a "Favicon" subsection to the Web UI Template section of `common-patterns.md`. Any app that mounts the shared `script_manager/static` folder can declare a favicon by pointing `rel="icon"` and `rel="apple-touch-icon"` at the existing `/static/logo.png` — no new binary asset and no server change. Recorded that `logo.png` is 92x80 RGBA (near-square, so it scales acceptably to 16/32px), that apps serving their own `static/` need the path adjusted, and that browsers cache favicons harder than HTML, so verify by requesting the icon URL directly before assuming the markup is wrong.
- Context worth keeping: prior to this, **no** web app in the repo declared a favicon (checked all twelve), so this is an additive convention rather than a fix to an existing one. `cellular_health_dashboard` is currently the only app with one. Deliberately documented as an available pattern rather than added to `web-ui-standards.md` as a requirement, since mandating it implies touching the other eleven apps — that is a scope call for the maintainer, not something to assume.
- Applied to `web_apps/cellular_health_dashboard/index.html`. Verified the tags render and `/static/logo.png` returns HTTP 200 as `image/png`.

## 2026-08-27 — Two-stage filtering for dashboard stat cards that double as filters

- Added common pattern: "Dashboard Stat Cards That Double as Filters — Two-Stage Filtering". The dashboard standard requires stat cards to act as filters *and* requires display-option toggles plus a search box, and those requirements conflict unless filtering is split in two. Counting cards from the full dataset leaves them frozen when options change; counting from the fully-filtered dataset makes clicking one card zero out all the others. Documented the `getBaseRows()` (display options + search, excluding the card filter) / `applyFilters()` (card filter, table only) split, plus the invariants worth asserting — mutually exclusive cards summing to the total, category buckets never exceeding the total, and default total equalling raw dataset length.
- Fixed `web_apps/cellular_health_dashboard/index.html`: `updateStats()` counted from `healthData` and ran only once per fetch, so no Display Option or search ever moved the cards. Now computed from the base set on every `applyFilters()` call. Verified by extracting the real `getBaseRows`/`updateStats`/`getSignalQuality` from the page and executing them under node against live API data (471 rows) across five option combinations; all invariants held.
- **Recorded two latent instances not fixed:** `inventory_dashboard` (`updateStats()` counts from `inventoryData`) and `alert_dashboard` (counts from `alertsData`) have the same defect — their stat cards ignore search and display options. Left alone because they were outside the requested change, but noted in `common-patterns.md` so the next person touching either one sees it rather than rediscovering it.

## 2026-09-25 — Documented /firmwares/ behavior and added the NCOS Downloader app
- Added known issue: `/firmwares/` returns duplicate records across pages (~20,000 rows
  for 17,677 distinct ids); dedupe by `id`
- Added known issue: the same model + NCOS version has many distinct builds (3,426 of
  5,389 model/version pairs had more than one `hash`), so `model`+`version` is not an
  identity — noted the filename/cache-key trap and the UTC `built_at` detail
- Added known issue: `/firmwares/` has no `product`/model filter, and the model name is
  not on the record; join with `/products/` or parse the `url` path
- Added pattern: parallel speculative offset pagination for collections whose `meta`
  has no total count (measured 53.9s serial vs 9.2s parallel on `/firmwares/`)
- Added pattern: firmware image download from the CDN with SHA-1 verification
- Expanded the `firmwares` section of `api-v2-endpoints.md` with field details,
  parameters, and the model-resolution note
- New app `web_apps/ncos_downloader/` (port 8075) — browse and download NCOS images
  with verification; registered in the web app and entry-point tables

## 2026-09-25 — Corrected firmware build-identity guidance, added a UI visibility gotcha
- Corrected the "same model + version has many builds" known issue: `built_at` does
  **not** break the tie either. Measured 2,166 of 15,505 (model, version, built_at)
  triples mapping to more than one `hash`, and 681 of 5,389 model/version pairs where
  "newest build" is still ambiguous. The earlier advice to prefer the newest `built_at`
  was incomplete — only `hash`/`id` separates these images. Added the recommendation to
  surface the hash in any UI listing firmware, since same-timestamp rows otherwise look
  like duplicated data
- Added pattern: the `hidden` attribute silently fails on the template's components,
  because author `display` rules on `.center-state`, `table.data`, and `.modal` outrank
  the user-agent `[hidden]` rule — with both fixes

## 2026-09-25 — Identified the firmware `multiimage` variant and `url` shape traps
- Resolved the previously UNVERIFIED question of why the same model/version/build
  timestamp appears twice: NCM publishes a standard image **and** a `multiimage` build,
  distinguished only by a tag in the `url` filename. 1,963 of 17,677 records are
  multiimage, matching the 2,166 colliding triples exactly. Documented parsing the
  variant, treating it as part of the identity, and stripping it when deriving a model
  name from the URL (otherwise you invent a phantom `MODEL-MULTIIMAGE`)
- Added known issue: firmware `url` is not always a path and not always `.bin` —
  41 records are fully-qualified URLs (22 on a second CloudFront host that no longer
  resolves), and 450 are `.vmp`. Covers the doubled-URL bug, the silent-skip bug from
  guarding on a leading `/`, and per-object 403s
- Added the matching `image_url` / `image_extension` / `image_variant` helpers to the
  firmware download pattern in common-patterns.md

## 2026-09-25 — Corrected model-resolution advice; duplicates also affect /products/
- Corrected the earlier guidance that the model could simply be parsed from the firmware
  `url` as an alternative to joining `/products/`. Measured against a full catalog, a
  timestamp-anchored parse **fails outright for 491 records (2.8%)** — the 450 `.vmp`
  paths use a compact timestamp and the 41 absolute URLs don't match the shape — and
  **returns stale legacy names for 9** (`NCSG-KVM` where the product is `NCXSG-KVM`,
  which splits one model across two names). URL parsing is a fallback, not an equivalent
- But a fallback *is* required: **12 of the 113 product ids referenced by firmware
  records are absent from `/products/`**, covering 274 records (1.6%). Softened the
  "join is the only reliable source" wording accordingly
- Broadened the duplicate-records known issue beyond `/firmwares/`: `/products/` returns
  **154 rows for 102 unique ids within a single `limit=500` response**, so duplication is
  not a pagination artifact. Retitled the entry and added the advice to treat any v2 list
  response as a multiset and dedupe by `id` by default
- Noted in the `products` reference that the collection both repeats records and is not
  exhaustive with respect to firmware references

## 2026-09-28 — Modem upgrade API documented from the official spec; /beta/ claim corrected
Built `web_apps/modem_upgrades` and, in the process, checked the repo's modem
upgrade knowledge against the official OpenAPI spec
(`developer.cradlepoint.com/swagger/spec/Modem_Software_Upgrades.json`). Several
long-standing claims in these docs were wrong.

Corrections:
- **known-issues.md: `modem_software_versions` and `modem_upgrades` are NOT beta.**
  The "/beta/ prefix" entry listed them; the spec documents `/api/v3/modem_upgrades`
  and `/api/v3/modem_software_versions`. Removed them from that entry and added a
  correction note. The Postman collection (folder titled "BETA"),
  `scripts/test_modem_management_api.py`, and the SDK's commented-out older methods
  all use the beta path and are stale. The SDK's *live* methods were right.
- **known-issues.md: filter spelling settled.** Postman's `group` / `job_type`
  params do not exist in the spec. It is `filter[group]`, `filter[type]` and
  `filter[modem_upgrade_parent]`, and the first two are required.

New documentation:
- **api-v3-endpoints.md: added a "Modem Software Upgrades" section** — the file
  previously had no modem coverage at all. Paths, required filters, request schema,
  the `operation` enum (`preview`/`upgrade`/`cancel`), the `status` enum, the
  parent/child model, cursor pagination, and the 204 behavior.
- **known-issues.md: five new entries.**
  - Jobs cannot target individual routers — `group` is the only accepted target, so
    a device-level selection in a UI is a display filter, not a scope reduction.
  - Progress lives in child records, not the parent; and there is **no documented
    `GET /modem_upgrades/{id}`**, so a single job must be read via the filtered
    list.
  - `status` enum values are `created`/`queued`/`initializing`/`running`/
    `finished`/`error`/`canceled` — not `completed`, not `cancelled`.
  - `page[size]` caps at **50** (default 20); over that is a 400. Both endpoints
    return **204 No Content** rather than an empty 200 when nothing matches.
  - The version field is **`package_version`**, not `version`/`available_version`;
    `modem_software_versions` also returns `min_router_version`, the minimum NCOS
    build a router needs to accept the package.
  - Child records are under-documented: the spec reuses the parent schema and never
    says how a child identifies its modem. Extract `net_device` defensively and
    join to v2 `net_devices` for router names.

## 2026-09-28 — Swagger specs DO carry response schemas; net_device→router join pattern
Reflexion pass over the modem_upgrades session, covering two gaps left by the
earlier entry.

- **api-documentation-gaps.md: corrected the "Response Schema Gaps" section.** It
  claimed the Swagger specs at
  `developer.cradlepoint.com/swagger/spec/{Endpoint_Name}.json` contain "only query
  parameters and headers" and that response fields "must be obtained empirically".
  `Modem_Software_Upgrades.json` disproves that — it ships full
  `components.schemas` for both requests and responses, including field types,
  `enum` value lists, `required` markers, defaults, nullability and response
  examples. Coverage varies by endpoint family, so the rule is now "read the spec
  first, fall back to empirical discovery only for what it actually omits" rather
  than skipping the spec. Also recorded how to retrieve a spec (it is the JSON the
  Swagger UI page fetches) and that specs outrank the repo's Postman collection and
  scripts when they disagree.

  This matters because guessing beats reading only until it doesn't: assuming
  `available_version` instead of the real `package_version` produced no error, just
  a permanently blank version column.

- **common-patterns.md: added "Resolving net_device IDs to Router Names".** Several
  endpoints (`net_device_health`, `net_device_metrics`, `net_device_signal_samples`,
  and v3 `modem_upgrades` child records) identify a modem only by `net_device` ID.
  The pattern covers the `expand=router` one-call join, 100-ID chunking, the null
  `router` case, caching across polls, getting a group's modems via
  `get_routers_for_group` (there is no group filter on `net_devices`), the
  `version`/`ver_pkg` vs `modem_fw` distinction, and the cross-version case where
  v3 supplies the IDs and v2 resolves the names — which requires both credential
  sets and should fail soft to the raw ID.

## 2026-09-28 — Live verification of modem_upgrades: preview returns a count, not a modem list
Ran real preview (dry-run) jobs against a live account with a working
`NCM_API_TOKEN`. Confirmed the spec on paths and parameters, and found six
behaviors the spec does not describe — one of which invalidates the obvious design
for a preview UI.

Confirmed live:
- Paths are **non-beta**: the probe settled on `/api/v3` and the earlier
  `/beta/` correction is now empirically verified, not just spec-derived.
- Parameters are JSON:API `filter[...]`; the plain `group`/`job_type` fallback was
  never needed.
- `package_version` and `min_router_version` are the real field names (real values:
  `03.17.04.00_GENERIC,030.112_000`, `min_router_version: 7.21.91`).
- `POST` returns **200**, not the documented 201.

New entries in known-issues.md:
- **A preview returns a COUNT, not a modem list.** Preview jobs never create child
  activity records — the child query answers `200` with `data: []` indefinitely. The
  whole result of a dry run is the parent's `modem_count`. Any UI promising "here are
  the modems this would touch" must derive that itself, and must not poll waiting for
  children that never arrive.
- **A locally derived candidate list will disagree with `modem_count`.** Observed 3
  eligible per NCM vs 8 matched locally on modem type + differing version. The
  eligibility rule is undocumented and involves more than type and version. Treat
  `modem_count` as authoritative; label anything computed locally as indicative.
  Offline routers reported 0 eligible even with `overwrite: true`.
- **`status: "preview"` is missing from the documented enum,** and is a *settled*
  state despite not reading like one.
- **`GET /modem_upgrades/{id}` returns 403, not 404.** Mapping 403 to "bad token" on
  v3 is wrong — the same token works for the list and POST. Fallbacks keyed only on
  404 will not fire.
- **`filter[modem_upgrade_parent]` is enforced with a clear error message,** which an
  over-broad parameter-spelling retry will destroy. Keep such fallbacks narrow: retry
  only when the error names an unknown/invalid parameter, never a missing required
  one.
- **Empty collections can be `200` with `data: []` rather than the documented `204`.**
  Responses also include an undocumented `meta.pagination` block.

## 2026-09-28 — Refined the parameter-fallback guidance with the trap that broke it
Amendment to the `filter[modem_upgrade_parent]` entry in known-issues.md. The entry
already gave the right rule — only retry a 400 in a different parameter spelling when
the error names an unknown parameter, never a missing required one — but omitted the
trap encountered while implementing it.

Using `"filter"` as the discriminator does not work, even though it is the obvious
choice: the word appears both in errors worth retrying (`invalid filter: group`) and
in the one that must not be retried (`filter[...] is required`), so keying on it
recreates the bug the rule exists to prevent. Recorded the two things that do work —
matching only unambiguous unknown-parameter wording, and bailing out on `required` —
plus the point that a fallback should only be considered while the correct spelling
is still undetermined.

Nothing else from this round needed documenting: the preview-returns-a-count
behavior, the 403 on the item read, `status: "preview"`, the enforced parent filter,
and the `200`-with-empty-`data` response were all recorded in the previous entry.

## 2026-09-28 — connection_states enum is narrower than the states modems report
One entry added to known-issues.md, found by cross-referencing the modem upgrade
spec against the existing `net_devices.connection_state` entry.

The `connection_states` filter on `POST /modem_upgrades` accepts three values
(`connected`, `disconnected`, `standby`), but `net_devices.connection_state` has six
observed values — `connecting`, `standby_connecting` and `unplugged` have no
expressible equivalent in the filter. How NCM treats modems in those three states is
**unknown and untested**; every preview run during this work sent
`connection_states: null`. Also flagged as untested: whether the filter is evaluated
once at job creation or re-checked per modem as a job runs.

Recorded the practical upshot — don't map an unrepresentable state onto one of the
three and hope, and note that filtering on modem connection state is not the same as
filtering on router state, since a live group of 4 `online` routers had all 8 modems
`disconnected`.

## 2026-09-28 — Cross-checked API docs against official Swagger specs; fixed v3 reference drift
Verified repo docs against `developer.cradlepoint.com/documentation` and the raw
Swagger specs at `developer.cradlepoint.com/swagger/spec/{endpoint}.json`. The v3
endpoint reference had drifted from the specs and from this repo's own known-issues
log. Corrections:

- `docs/api-v3-endpoints.md`:
  - Added a "Path Conventions" preamble (v3 uses **no** trailing slash; PCN/NCX are
    under `/api/v3/beta/`, regrades under `/api/v3/asset_endpoints/`).
  - Removed `users` (it is a v2 endpoint, not v3).
  - Fixed `regrades` path to `/api/v3/asset_endpoints/regrades` (+`/{id}`), with the
    required `filter[action]`/`filter[status]` values and the JSON:API atomic POST.
  - Rewrote PCN and NCX sections to `/api/v3/beta/...` with no trailing slash; added
    exchange filters and page-size limits; noted POST 201 / DELETE 204.
  - Fixed `subscriptions` to `GET /api/v3/subscriptions` (no trailing slash, GET
    only), documented `page[size]` max 50 and `filter[start_time]`/`filter[end_time]`.
  - Removed trailing slashes from Public SIM Management paths (base unverified).
- `docs/api-v2-endpoints.md`:
  - Added a dedicated `users` section (v2, GET only, filters id/username/email).
  - Added `PUT` to `locations` supported methods.
  - Documented that `reboot_activity` accepts a router **or** group URI (201 on
    accept, 403 on invalid target).
  - Added the `net_devices.connection_state` spec enum, noting live-observed
    `standby`/`standby_connecting` extras.
- `docs/api-overview.md`: scoped the trailing-slash Critical Rule to v2 and noted v3
  has no trailing slash; updated the v3 base-URL bullet (beta paths, `users` is v2).
- `.kiro/steering/ncm-api-development.md` and `AGENTS.md`: fixed the endpoint routing
  table — `users` → v2; subscriptions/regrades/PCN/NCX rows now show real paths.
- `docs/known-issues.md`: added "v3 Endpoint Reference Had Drifted From the Verified
  Path Conventions" documenting the four corrections and the spec-is-authoritative
  lesson.

Confirmed correct and left unchanged: v2/v3 base URLs and auth in api-overview.md,
v2 pagination (max 500), the carefully-documented Modem Software Upgrades section
(genuinely not beta, per its own spec).

## 2026-09-28 — Added reusable pattern: verifying endpoints against the Swagger spec
Added "Verifying an Endpoint Against Its Official Swagger Spec" to
`docs/common-patterns.md`. Captures the reusable technique used to audit the v3 docs
this session: fetch the raw spec at `developer.cradlepoint.com/swagger/spec/{ep}.json`
to settle version/base URL, real path (including `/beta/` and `/asset_endpoints/`
prefixes), trailing-slash convention, methods, required filters, enums, and page-size
limits. Documents the source-precedence order (spec > SDK > repo docs > Postman) and
the known-issues-log-beats-reference rule.

## 2026-10-05 — Config removals list is scope-dependent; added revert_device_firewall

Built `web_apps/revert_device_firewall/` (port 8090) to strip device-level `security`
(zone firewall) overrides so devices inherit their group's firewall config. The build
surfaced a documentation gap that would have produced exactly the wrong behavior.

- `known-issues.md` — new entry "The Removals List Means Different Things at Group
  and Device Scope". The diff's second element is persisted state, not a one-time
  delete. At group scope it prunes the group's own contribution; at device scope it
  suppresses what the **group** supplies. So restoring group inheritance on a device
  means deleting the key from the updates dict (element 0), not adding it to the
  removals list — which would persist a new override that blocks the group entirely.
  PATCH cannot do it, since PATCH merges `updates`; the operation is read-modify-write
  with PUT of the complete diff minus one branch. Also records that root-level
  `firewall` (port forwarding) and root-level `security` (zone firewall, IPS, app
  sets) are different branches that many devices carry simultaneously.
- `api-configuration.md` — added the scope caveat to the "Removals List" section,
  which previously described it only as "paths to remove from defaults". That
  phrasing is what makes the device-scope case easy to get backwards.
- `common-patterns.md` — new pattern "Restoring Group Inheritance by Removing a
  Device-Level Branch": one batched `configuration_managers` read (the record carries
  both the CM `id` and the `configuration`, so no per-router
  `get_configuration_manager_id()` call), skip clean devices rather than writing
  no-ops, log the removed branch as JSON since it is the only restore record, verify
  with a re-read because 2xx means accepted not applied, and call `session.put`
  directly instead of `put_configuration_managers()` which re-looks-up the CM ID on
  every call.

Note on verification: the read, diff and payload-construction paths were exercised
against 400 live devices (74 carried device-level `security`). The PUT was verified
against a stubbed session, not live devices, so the write path remains unconfirmed
against the real API — consistent with the existing caveat that the removal-path
formats were captured from UI traffic and never replayed from this repo.

## 2026-10-05 — Routers can lack a configuration_managers record

- `known-issues.md` — new entry "Not Every Router Has a `configuration_managers`
  Record". A batched `get_configuration_managers(router__in=…)` can return fewer
  records than router IDs requested: observed 399 of 400 on a live account, with one
  CR4250 having no record. Zipping or positionally indexing the response against the
  request list misaligns silently at the gap, which in a config-writing script means
  pushing one device's config onto another. Documents mapping explicitly on each
  record's `router` field (a resource URL needing parsing, not a bare ID) and
  treating absence as a skip. Complements the existing "Configuration Manager ID ≠
  Router ID" entry — that one is about IDs not matching, this one about the record
  not existing.

Considered and deliberately not added: the absence of a substring name filter on
`/routers/` and `/groups/` (only exact `name`/`name__in`, so multiselect UIs must
filter client-side). Already derivable from the filter list in
`api-v2-endpoints.md` and covered by the existing "grep `allowed_params` before
concluding a filter does not exist" guidance.

## 2026-10-06 — Standalone distribution of a single web app
- Added `docs/known-issues.md` → "Shipping one web app folder standalone loses the shared `/static` mount". All fourteen `web_apps/` apps mount `../script_manager/static` for their logo, so a zipped single-app folder 404s on `/static/logo.png`. Startup is unaffected (the mount is guarded by `if STATIC_DIR.is_dir()`); only the header image breaks, and without an `onerror` handler it renders as a broken-image icon. Remedy is the one-line `onerror="this.style.display='none'"` already used in `ncos_downloader/index.html`.
- Same entry records that the Python floor for any FastAPI app here is **3.10**, not the 3.9 stated in the repo standards: `fastapi`, `uvicorn`, `starlette`, `python-dotenv` and `urllib3` all publish `Requires-Python >=3.10`, so pip refuses to install on 3.9.
- Also records that a per-app `requirements.txt` should be derived from the app's actual imports, not copied from the root file, which is the union across all apps.
- Applied to `web_apps/revert_device_firewall/`: added a pinned per-app `requirements.txt` (`ncm`, `fastapi`, `uvicorn`, `python-dotenv`, `urllib3`), added the `onerror` handler to the header logo, and expanded the README with an end-to-end setup walkthrough (Python install incl. the Windows "Add python.exe to PATH" checkbox, venv, requirements, launch, browser) plus a troubleshooting table. Verified by copying the folder to a clean directory, installing the pins into a fresh venv, and booting with no credentials in the environment: `GET /` returned HTTP 200 and `/api/config` reported `credentials_set: false`.

## 2026-10-06 — Web apps are now self-contained (no cross-app file reads)
- **Principle, now recorded in steering:** no app may read files from another app at runtime. An app folder must be copyable on its own. Added as a required section at the top of `.kiro/steering/web-ui-standards.md` and the mirrored Web UI Standards section of `AGENTS.md`, ahead of the style-foundation list.
- Reframed the style-foundation references (`web_app_template/index.html`, `script_manager/static/css/style.css`, `js/app.js`, the logos) as explicit **copy-from** sources for authoring time, not runtime paths. That ambiguity is what propagated the shared mount into seven apps.
- Converted all seven apps that mounted `web_apps/script_manager/static` to serve their own `static/`: `alert_dashboard`, `cellular_health_dashboard`, `geo_ip_blocker`, `host_identity_copier`, `inventory_dashboard`, `ncos_downloader`, `revert_device_firewall`. Each received its own `static/logo.png` and `static/logo_dark.png`. `ncos_downloader` previously preferred its own folder but kept a fallback to the shared one; the fallback is gone. `config_builder` and `netcloud_router_lookup` already complied.
- Reverted the `onerror="this.style.display='none'"` band-aid added earlier the same day to `revert_device_firewall/index.html`. Hiding a missing shared asset treats the symptom; the asset now ships with the app.
- Rewrote the `docs/known-issues.md` entry accordingly ("Web apps must not mount a sibling app's static folder"), including the note that the old failure was silent — the mounts were guarded by `if STATIC_DIR.is_dir()`, so servers started clean with no log signal.
- Updated `docs/common-patterns.md`: the Favicon section no longer shows the sibling-mount snippet, and a new "Apps must be self-contained" subsection carries the correct mount.
- Verified: no `script_manager` reference remains in any other app's `.py` or `.html`; all seven apps import cleanly with `mount=True`, their own directory, and both logos resolving; a copy of `revert_device_firewall` in an isolated directory with a fresh venv serves `/`, `/static/logo.png` and `/static/logo_dark.png` all HTTP 200.
- **Known remaining gap:** `geo_ip_blocker` and `host_identity_copier` still do `sys.path.insert(0, str(PROJECT_ROOT / 'ncm'))` and read `.env` from the repo root. Repo-level rather than cross-app, but it breaks a standalone copy the same way. Not changed here because it alters import failure modes for repo users who have not run `setup_env.py`.

## 2026-10-06 — Reflexion: backgrounded-app output buffering and a false-clean grep
- Added `docs/known-issues.md` → "Backgrounding a web app silently loses its stdout startup banner". Every `web_apps/` entry point prints its URL with plain `print()` before `uvicorn.run()`; with stdout redirected to a file it is block-buffered (4 KB) and a ~150 byte banner never lands, while uvicorn's lines still appear because they go through `logging` to stderr. Kill the process and the buffered stdout is discarded outright. Measured on `revert_device_firewall`: `grep -c "Open http"` returns 0 under default buffering, 1 with `-u`. Fix is `python -u` or `PYTHONUNBUFFERED=1`.
- The load-bearing part of that entry is the inference, not the missing text: absence of the banner is **not** evidence the app failed to start. Confirm startup from uvicorn's stderr line or by hitting the port. Same reason a `print()` debug statement added to a backgrounded app may never show up — use `flush=True`, stderr, or `-u`.
- Propagated the `-u` guidance to the "Running web apps" section of `.kiro/steering/project-setup.md` and the mirrored section of `AGENTS.md`, since that is where the instruction to background these apps lives.
- Added `docs/known-issues.md` → "Unquoted `--include=*.py` makes a zsh grep report a false clean result". zsh globs `--include=*.py`, matches nothing, and aborts the command under the default `nomatch` option; a trailing `|| echo "NONE - clean"` then reports a verified-looking negative for a grep that never ran. This produced a brief false all-clear during the cross-app dependency audit earlier in the same session. Quote the pattern or use the dedicated grep tool, and when absence of output is the evidence for a claim, confirm the command actually executed.

## 2026-10-07 — Stacked panel layout pattern

- Added "Stacked Panels in `.content-area`: Scroll, Don't Crush" to
  `common-patterns.md`. The standard viewport-pinned layout lets a grown panel shrink
  to nothing when sibling panels appear below it, which reads as the new panel taking
  over the page. Documents the fix (`overflow-y: auto` on the container,
  `flex-shrink: 0` on panels, `flex: 1 0 auto` plus a `min-height` floor on the
  primary panel), the one-time `scrollIntoView({ block: 'nearest' })` reveal, and how
  to verify it from `scrollHeight`/`clientHeight`.

## 2026-10-07 — Stale NodeList gotcha when verifying list UIs

- Added "A cached NodeList goes stale on every selection click, so loops select one
  row" to `known-issues.md`. The pickers re-render via `innerHTML` on each click, so a
  loop over a pre-captured NodeList clicks detached nodes and silently selects one —
  and can make a verification step pass if the resulting count is never asserted.
  Records the re-query-in-loop fix and the related technique of driving the real
  frontend against a throwaway stub backend when the live inventory fetch is too slow
  to populate rows.

## 2026-10-08 — Steering deduplicated; `AGENTS.md` removed as an always-on duplicate
- Consolidated `.kiro/steering/`: the setup procedure existed twice nearly verbatim
  (`project-setup.md`'s "Missing `.venv`" steps against `setup-environment.md`), as did
  the `isatty`/`getpass` hang rationale; venv interpreter paths and the credential
  variable list appeared in three files; the reflexion doc-update rules in three places
  (two steering files plus the `reflexion-update-docs` Stop hook). Each now has one
  owner: `project-setup.md` for environment facts, `setup-environment.md` for the full
  procedure and failure remedies, `reflexion-workflow.md` for the docs loop. The others
  carry `#pointer` references.
- `project-setup.md` is `inclusion: always`, so its size is a per-request cost: 196 → 111
  lines (8.5 KB → 5.0 KB). Steering overall 555 → 478 lines.
- Replaced the hardcoded web-app entry-point table in always-on steering with a pointer
  to `web_apps/README.md` plus "run `ls`, don't guess". The table had drifted to 14
  named apps against 16 on disk; `web_apps/README.md` has its own drift (lists
  `modem_upgrades`, which is absent from disk and from git; omits the empty
  `mac_whitelist_copier/`) — reported, not changed.
- Carried a security note out of the deleted mirror into
  `.kiro/steering/web-ui-standards.md` so it was not lost: dashboards bind a local port
  with **no authentication**, so Settings-panel credentials are reachable by anyone who
  can hit the port; apps that push firmware or config should bind `127.0.0.1`.
- Deleted `AGENTS.md`. Kiro injects a root `AGENTS.md` into every request, so it was a
  second always-on copy of `project-setup.md`. Added `known-issues.md` → "A root
  `AGENTS.md` is loaded into every Kiro request, duplicating `inclusion: always`
  steering" with the confirming observation and the always-on-versus-mirror distinction.
- `claude.md` is now the self-contained cross-agent entry point (essentials + a
  which-file-when index into `.kiro/steering/`) instead of `@AGENTS.md`. It had been
  importing `AGENTS.md` while that file was deleted from the working tree but still
  tracked in git, so the import resolved to nothing.
- Confirmed no API-behavior findings this session needed documenting: the one candidate,
  the `users` v2-versus-v3 discrepancy between steering and the stale mirror, is already
  corrected in `docs/api-v2-endpoints.md` and `docs/api-v3-endpoints.md`.

## 2026-10-15 — Reflexion: Starlette TemplateResponse signature
- Added entry to `docs/known-issues.md`: Starlette ≥0.29 requires `TemplateResponse(request, name, context)`; the legacy `TemplateResponse(name, {"request": ...})` form now raises `TypeError: unhashable type: 'dict'` (observed on Starlette 1.6.0). Fixed the occurrence in `web_apps/ncm_api_key_encryptor/ncm_api_key_encryptor.py` and noted this is a repo-wide migration risk for any app rendering Jinja templates.

## 2026-10-15 — Reflexion: unpinned Starlette is the root cause
- Extended the `docs/known-issues.md` TemplateResponse entry with root-cause analysis: Starlette is unpinned and only transitive (both `requirements.txt` files list bare `fastapi`, no Starlette), so the installed version floats to whatever PyPI served when the venv was last built — producing "worked then broke with no code change." Added two general takeaways: trust package/`dist-info` mtimes over memory when diagnosing such failures (the startup banner is not evidence a per-request route works), and pin the framework per app since each web app owns its own `requirements.txt`.

## 2026-10-15 — Reflexion: pinning fastapi alone doesn't pin Starlette
- Corrected the remediation takeaway in the `docs/known-issues.md` Starlette entry. The earlier wording ("pin the framework and let the transitive pin follow") was wrong: `fastapi==0.141.1` still resolves a range of Starlette versions, so an explicit `starlette==<version>` line is required alongside the `fastapi` pin. Recorded the applied fix (`fastapi==0.141.1`, `starlette==1.6.0`, `uvicorn==0.52.3` pinned in all five FastAPI requirements files, including two apps that pinned fastapi/uvicorn but had remained exposed), and added the `pip install --dry-run` no-op check as the way to confirm pins match the verified venv.
