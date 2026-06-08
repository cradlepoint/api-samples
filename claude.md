# CLAUDE.md — Project Instructions for Claude Code

## Workflow: Reflexion Loop

When building any application that uses the Cradlepoint NetCloud Manager API, follow this workflow:

1. **Consult Docs First** — Before writing code, read relevant docs in `docs/` (see Endpoint Routing Guide below)
2. **Check Known Issues** — Read `docs/known-issues.md` for gotchas
3. **Check Common Patterns** — Read `docs/common-patterns.md` for established patterns
4. **Build and Test** — Write code, run it, fix errors iteratively until clean
5. **Reflect and Update Docs** — If you discover new API behaviors, gotchas, or reusable patterns not already documented, update `docs/known-issues.md`, `docs/common-patterns.md`, or `docs/CHANGELOG.md`. Only update for generally applicable discoveries, not app-specific ones.

After every shell command that produces errors, diagnose the root cause and fix the code. Re-run until clean.

---

## Code Standards for NCM Scripts

### Virtual Environment

Always use the project `.venv`. Never run scripts with system Python.

```bash
.venv/bin/python scripts/my_script.py
.venv/bin/pip install -r requirements.txt
```

### Required Environment Variables

All scripts require these for API authentication:

| Variable | Description |
|----------|-------------|
| `X_CP_API_ID` | Cradlepoint API ID |
| `X_CP_API_KEY` | Cradlepoint API Key |
| `X_ECM_API_ID` | ECM API ID |
| `X_ECM_API_KEY` | ECM API Key |

Optional (for v3 API):

| Variable | Description |
|----------|-------------|
| `NCM_API_TOKEN` | Bearer token for API v3 |

**Important**: Env var names use the `X_` prefix (matching HTTP header names with dashes replaced by underscores). Do NOT use unprefixed `CP_API_ID` form.

If env vars are not set, scripts must detect this and print setup instructions. Use `scripts/utils/env_check.py` to validate at startup.

### File Structure Template

All new scripts should follow this structure:

```python
"""
Script description.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.env_check import check_env
from utils.credentials import get_credentials
from utils.session import APISession
from utils.logger import get_logger

def main():
    """Main entry point."""
    check_env()  # Always call first
    # ... implementation

if __name__ == '__main__':
    main()
```

### Authentication

- Never hardcode API keys in source files
- Use environment variables (preferred) or `scripts/utils/credentials.py` as fallback
- For NCM SDK: pass keys as a dictionary
- For direct API calls: use `scripts/utils/session.py`

### Error Handling

- Always wrap API calls in try/except
- Implement retry logic for transient errors (408, 429, 500, 502, 503, 504)
- Log errors with context (which endpoint, what parameters)

### Output

- Use CSV for tabular data exports
- Use JSON for structured data
- Print progress for long-running operations
- Store output files in `scripts/script_manager/csv_files/` when using script_manager

### Dependencies

- Core: `requests`, `ncm` (SDK)
- Check `requirements.txt` before adding new dependencies
- If a new dependency is needed, add it to `requirements.txt`

### Web Servers (socketserver / http.server)

Always set `allow_reuse_address = True` before creating the server instance:

```python
socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("", PORT), MyHandler) as httpd:
    httpd.serve_forever()
```

---

## NetCloud Manager API Development Guide

### Choose the Right Approach

- Use the NCM SDK (`from ncm import ncm`) when possible — it handles pagination, retries, auth
- **Always read the SDK source** at `ncm/ncm/ncm.py` to discover available methods before writing code
- Use `scripts/utils/session.py` for direct API calls with automatic retry/pagination
- Use raw `requests` only when SDK/session don't cover the use case

### Endpoint Routing Guide

| Task | Doc File | SDK Methods |
|------|----------|-------------|
| List/manage routers | api-v2-endpoints.md → routers | `get_routers()`, `get_router_by_id()` |
| Router online/offline status | api-v2-endpoints.md → router_state_samples | `get_router_state_samples()` |
| Push device config | api-configuration.md | `patch_configuration_managers()`, `put_configuration_managers()` |
| Push group config | api-configuration.md | `patch_group_configuration()`, `put_group_configuration()` |
| Get/set locations | api-v2-endpoints.md → locations | `get_locations()`, `get_historical_locations()` |
| Manage alerts | api-v2-endpoints.md → alerts | `get_alerts()`, `get_router_alerts()` |
| Setup webhooks | api-webhooks.md | Direct API calls to `alert_push_destinations` |
| Manage groups | api-v2-endpoints.md → groups | `get_groups()`, `create_group_by_parent_id()` |
| Network device info | api-v2-endpoints.md → net_devices | `get_net_devices()`, `get_net_device_metrics()` |
| Cellular health scores | api-v2-endpoints.md → net_device_health | `get_net_device_health()` |
| Cellular metrics (WAN) | api-v2-endpoints.md → net_device_metrics | `get_net_devices_metrics_for_wan()`, `get_net_devices_metrics_for_mdm()` |
| Signal/usage data | api-v2-endpoints.md → net_device_signal/usage | `get_net_device_signal_samples()`, `get_net_device_usage_samples()` |
| Firmware info | api-v2-endpoints.md → firmwares | `get_firmwares()` |
| Reboot devices | api-v2-endpoints.md → reboot_activity | `reboot_device()`, `reboot_group()` |
| Speed tests | api-v2-endpoints.md → speed_test | `create_speed_test()` |
| Manage users | api-v3-endpoints.md → users | `get_users()`, `create_user()` |
| Subscriptions | api-v3-endpoints.md → subscriptions | `get_subscriptions()`, `regrade()` |
| Private cellular | api-v3-endpoints.md → private_cellular_* | `get_private_cellular_networks()`, etc. |
| NCX sites/resources | api-v3-endpoints.md → exchange_* | `get_exchange_sites()`, `create_exchange_site()` |
| Export data to CSV | common-patterns.md | `export_to_csv()` pattern |
| Batch operations | common-patterns.md | `batch_operation()` pattern |

### Critical Rules (Always Follow)

1. **Trailing slash**: ALL v2 URLs must end with `/`
2. **v3 beta endpoints**: Must NOT have trailing slashes
3. **Config manager ID ≠ Router ID**: Always look up the config manager ID first
4. **PATCH vs PUT**: PATCH merges, PUT replaces. Use PATCH for incremental changes
5. **`_id_` fields**: When using UUID keys, include `_id_` inside the object too
6. **Check deprecations**: Before using any endpoint, verify it's not deprecated in `docs/api-deprecations.md`
7. **Error handling**: Always implement retry logic with exponential backoff
8. **Pagination**: Always handle pagination for list endpoints (SDK does this automatically)
9. **v2 and v3 are separate**: Different auth, different ID spaces, no cross-referencing

---

## Web UI Standards

When creating any web UI in this project, use `web_apps/web_app_template/` as the style foundation.

### Required for All Web Apps

1. Use template HTML structure (app-container → app-header → app-main → sidebar + content-area)
2. Include template CSS or copy relevant portions
3. Implement dark mode toggle with localStorage persistence
4. Use CSS custom properties for all colors — never hardcode
5. Include both `logo.png` and `logo_dark.png` with swap rule
6. Ensure responsive behavior at 1024px and 768px breakpoints

### Dark Mode Implementation

- Toggle via `body.dark-mode` class
- Persist preference in `localStorage`
- On page load, check `localStorage` and apply saved preference
- Use `var(--*)` custom properties rather than hardcoded colors

### Key CSS Variables

```css
--primary-color: #4f46e5;
--primary-dark: #3730a3;
--secondary-color: #6b7280;
--success-color: #059669;
--warning-color: #d97706;
--danger-color: #dc2626;
--info-color: #0284c7;
--dark-bg: #111827;
--dark-surface: #1f2937;
--light-bg: #f9fafb;
--light-surface: #ffffff;
--text-primary: #111827;
--text-secondary: #6b7280;
--text-light: #9ca3af;
--border-color: #d1d5db;
```

### Dashboard Template

For data-driven dashboards, use `dashboards/cellular_health/` as reference. Every dashboard must include:

1. **Settings modal** — API key inputs, named profiles (save/load/delete), stored in `profiles.json`
2. **Sortable columns** — Click to sort ascending/descending with arrow indicators
3. **Search box** — Full-text search, clicking text cells auto-populates search
4. **Stat cards as filters** — Summary cards that filter table on click
5. **Export buttons** — CSV download + PDF via jsPDF/AutoTable
6. **Grouping** (where applicable) — Toggle in Display Options, persisted in localStorage

### Backend Pattern (FastAPI)

```python
# Routes: GET / (index.html), GET /api/data, GET/POST/DELETE /api/profiles, POST /api/credentials/apply
# All @app route definitions must come BEFORE `if __name__ == "__main__"` block
```

### Frontend Libraries (CDN)

- jsPDF: `https://cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js`
- jsPDF-AutoTable: `https://cdnjs.cloudflare.com/ajax/libs/jspdf-autotable/3.8.2/jspdf.plugin.autotable.min.js`
- Google Fonts Inter: `https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap`

---

## Documentation Update Format

When appending to `docs/known-issues.md`:
```markdown
### [Short Title] (discovered YYYY-MM-DD)
[Description of the issue and workaround]
```

When appending to `docs/CHANGELOG.md`:
```markdown
## YYYY-MM-DD — [Brief Description]
- [What changed and why]
```

## Official API Documentation

The full Cradlepoint NCM API documentation is available at:
- **Documentation portal**: https://developer.cradlepoint.com/documentation

Most endpoints have an OpenAPI spec available at:
- **OpenAPI spec URL pattern**: `https://developer.cradlepoint.com/swagger/spec/ENDPOINT.json`

For example:
- `https://developer.cradlepoint.com/swagger/spec/routers.json`
- `https://developer.cradlepoint.com/swagger/spec/net_devices.json`
- `https://developer.cradlepoint.com/swagger/spec/groups.json`
- `https://developer.cradlepoint.com/swagger/spec/accounts.json`

When working with an unfamiliar endpoint, fetch the OpenAPI spec to get the full schema, available filters, allowed methods, and response formats. Replace `ENDPOINT` with the endpoint name (e.g. `routers`, `net_devices`, `alerts`, `configuration_managers`, etc.).

---

## Quality Gates

Before considering any NCM application complete:
1. Code runs without errors
2. All API calls use proper authentication
3. All v2 URLs have trailing slashes (v3 beta does NOT)
4. Pagination is handled for list operations
5. Error handling with retries is implemented
6. No deprecated endpoints are used
7. Documentation has been updated if applicable
