# Common Code Patterns

## Authentication Setup

### Always validate env vars first
```python
from utils.env_check import check_env, get_api_keys_from_env

check_env()  # Exits with OS-specific instructions if vars missing
api_keys = get_api_keys_from_env()  # Returns SDK-compatible dict
```

### Using the NCM SDK
```python
from ncm import ncm
from utils.env_check import check_env, get_api_keys_from_env

check_env()
client = ncm.NcmClient(api_keys=get_api_keys_from_env())
```

### Using the Session Utility (for direct API calls)
```python
import os
from utils.env_check import check_env
from utils.session import APISession
from utils.logger import get_logger

check_env()
logger = get_logger('my_script')
session = APISession(
    logger=logger,
    cp_api_id=os.environ['CP_API_ID'],
    cp_api_key=os.environ['CP_API_KEY'],
    ecm_api_id=os.environ['ECM_API_ID'],
    ecm_api_key=os.environ['ECM_API_KEY'],
)
```

## Pagination

### With NCM SDK (automatic)
```python
# SDK methods handle pagination internally
routers = client.get_routers()  # returns all routers
```

### With requests (manual)
```python
import requests
from utils.env_check import check_env, get_api_keys_from_env

check_env()
api_keys = get_api_keys_from_env()

base_url = 'https://www.cradlepointecm.com/api/v2'
headers = {k: v for k, v in api_keys.items() if k != 'token'}
headers['Content-Type'] = 'application/json'

def get_all(endpoint, params=None):
    url = f'{base_url}/{endpoint}/'
    results = []
    while url:
        resp = requests.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()
        results.extend(data.get('data', []))
        url = data.get('meta', {}).get('next')
        params = None  # params already in next URL
    return results
```

### With Session Utility (automatic via generator)
```python
with APISession(logger=logger, **creds) as session:
    for router in session.get('routers'):
        process(router)
```

## Pagination (v3 — cursor-based)

API v3 uses cursor-based pagination, not offset-based like v2. The max page
size is 50. Follow `links.next` until it's absent.

```python
import httpx

def get_all_v3(path, headers, params=None):
    """Fetch all pages from a v3 cursor-paginated endpoint."""
    base = "https://api.cradlepointecm.com/api/v3"
    params = params or {}
    params.setdefault("page[size]", 50)
    results = []
    url = f"{base}{path}"

    while url:
        resp = httpx.get(url, headers=headers, params=params)
        resp.raise_for_status()
        body = resp.json()
        for item in body.get("data", []):
            record = {"id": item["id"], **item.get("attributes", {})}
            results.append(record)
        url = body.get("links", {}).get("next")
        params = None  # params are baked into the cursor URL
    return results

# Usage
headers = {
    "Authorization": "Bearer <token>",
    "Accept": "application/vnd.api+json",
}
assets = get_all_v3("/asset_endpoints", headers)
subscriptions = get_all_v3("/subscriptions", headers)
```

## Error Handling

```python
import requests
from time import sleep

def api_call_with_retry(func, max_retries=5, backoff=2):
    for attempt in range(max_retries):
        try:
            return func()
        except requests.exceptions.HTTPError as e:
            if e.response.status_code in (408, 409, 429, 500, 502, 503, 504):
                wait = backoff ** attempt
                if e.response.status_code == 429:
                    wait = float(e.response.headers.get("Retry-After", wait))
                sleep(wait)
                continue
            raise
    raise Exception(f"Failed after {max_retries} retries")
```

## CSV Export Pattern

```python
import csv

def export_to_csv(data, filename, fields):
    with open(filename, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(data)
```

## Filtering Routers

```python
# By state
online_routers = client.get_routers(state='online')

# By group
group_routers = client.get_routers_for_group(group_id=123)

# By account
account_routers = client.get_routers_for_account(account_id=456)

# Specific fields only
routers = client.get_routers(fields='id,name,state,mac')
```

## Configuration Push Pattern

```python
def push_config_to_routers(client, router_ids, config):
    """Push a configuration to multiple routers."""
    results = []
    for router_id in router_ids:
        try:
            result = client.patch_configuration_managers(router_id, config)
            results.append({'router_id': router_id, 'status': 'success'})
        except Exception as e:
            results.append({'router_id': router_id, 'status': 'error', 'error': str(e)})
    return results
```

## Date Filtering Pattern

```python
from datetime import datetime, timedelta

# Get alerts from last 24 hours
yesterday = (datetime.utcnow() - timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M:%S')
alerts = client.get_router_alerts(created_at__gt=yesterday)
```

## Batch Operations

```python
def batch_operation(items, batch_size=50, operation=None):
    """Process items in batches."""
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        for item in batch:
            operation(item)
```

## Web UI Template

When building any web interface in this project, use the `web_app_template` located at
`scripts/script_manager/static/` as the style foundation. It provides a complete, consistent
design system including layout, components, and theming.

Reference files:
- `scripts/script_manager/static/index.html` — HTML structure
- `scripts/script_manager/static/css/style.css` — Full CSS with light/dark mode
- `scripts/script_manager/static/js/app.js` — JS patterns (dark mode toggle, sidebar, etc.)

All web apps must support light mode and dark mode:
- Use CSS custom properties (`var(--*)`) for all colors
- Toggle via `body.dark-mode` class
- Persist preference in `localStorage`
- Include both `logo.png` and `logo_dark.png` with automatic swap

See `.kiro/steering/web-ui-standards.md` for the full checklist and CSS variable reference.
