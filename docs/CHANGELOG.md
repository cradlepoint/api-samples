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
