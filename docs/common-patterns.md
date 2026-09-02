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
    cp_api_id=os.environ['X_CP_API_ID'],
    cp_api_key=os.environ['X_CP_API_KEY'],
    ecm_api_id=os.environ['X_ECM_API_ID'],
    ecm_api_key=os.environ['X_ECM_API_KEY'],
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

## Copying a Config Subtree Between Groups

Copying one branch of a group config (a MAC filter, an identity set, WAN rules)
from a "master" group to others. Two asymmetries make this trickier than it looks:

1. **On read, NCM returns config arrays as index-keyed objects** —
   `{"0": {...}, "1": {...}}`, not `[{...}, {...}]`. Normalize before reasoning
   about the list.
2. **On write, PATCH merges objects but replaces arrays entirely.** That is the
   lever for choosing mirror-vs-merge semantics: send the same data as a JSON
   array to replace the destination list outright, or as an index-keyed object to
   overwrite position-by-position and leave extra destination entries in place.

```python
def extract_subtree(configuration, *path):
    """Pull a branch out of a group's [updates, removals] config diff."""
    if not isinstance(configuration, list) or not configuration:
        return None
    node = configuration[0]
    for key in path:
        if not isinstance(node, dict):
            return None
        node = node.get(key)
    return node if isinstance(node, dict) else None


def normalize_entries(value):
    """Index-keyed object OR real array -> ordered list of dicts."""
    if isinstance(value, dict):
        keys = sorted(value, key=lambda k: (0, int(k)) if str(k).isdigit() else (1, k))
        return [dict(value[k]) for k in keys if isinstance(value[k], dict)]
    if isinstance(value, list):
        return [dict(v) for v in value if isinstance(v, dict)]
    return []


# Read the source branch
src = client.get_groups(id=master_id, fields='id,name,configuration')[0]
macfilter = extract_subtree(src['configuration'], 'firewall', 'macfilter')
entries = normalize_entries(macfilter.get('macs'))

# mirror: array -> destination list is replaced wholesale
# merge:  index-keyed object -> per-index overwrite, extras survive
macs = entries if mirror else {str(i): e for i, e in enumerate(entries)}

payload = {'configuration': [{'firewall': {'macfilter': {
    'enabled': macfilter.get('enabled'),
    'whitelist': macfilter.get('whitelist'),
    'macs': macs,
}}}, []]}

for gid in destination_ids:
    try:
        client.patch_group_configuration(gid, payload)
    except Exception as e:      # keep going; one bad group must not abort the batch
        log_failure(gid, e)
```

Send only the branch you intend to copy. Building the payload from the extracted
subtree (rather than forwarding the whole `configuration[0]`) keeps unrelated
source settings from riding along into the destinations.

### UUID-keyed collections copy differently than index-keyed ones

The example above is an index-keyed array. Collections that support `_id_`
(`identities.ip`/`mac`/`port`, `lan`, `vpn.tunnels`, `security.zfw.zones`,
`wan.rules`, and the rest of the list in `api-configuration.md`) are keyed by
UUID instead, and that changes what a copy means:

- **Index-keyed** (`macs`, `members`): positions are meaningful, so sending an
  array replaces the list.
- **UUID-keyed** (`identities.ip`): PATCH merges by key, so the updates dict alone
  only *adds* the source entries and overwrites any sharing a UUID. Entries
  existing only in the destination have no matching key and would survive.

An updates-only PATCH is therefore additive. To make a destination *equal* the
source, add a removals list (second diff element) — PATCH honors it, so an exact
mirror is achievable without PUT. See "Mirroring a collection" below.

Real subtrees nest the two styles, so one copy touches both levels. In
`identities.ip` the outer collection is UUID-keyed while each entry's `members`
is an index-keyed array — the outer level is always a merge, and the mirror/merge
choice applies to the inner address list:

```python
identities = extract_subtree(src['configuration'], 'identities')['ip']

out = {}
for key, entry in identities.items():
    identity_id = entry.get('_id_') or key      # _id_ wins if they disagree
    copied = dict(entry)
    copied['_id_'] = identity_id                # required inside the object too
    members = normalize_entries(entry.get('members'))
    copied['members'] = members if mirror else {str(i): m for i, m in enumerate(members)}
    out[identity_id] = copied                   # key must equal _id_

payload = {'configuration': [{'identities': {'ip': out}}, []]}
```

Key the output dict by `_id_` rather than by whatever key you read it under. The
two normally agree, but if they ever diverge, NCM validates against the `_id_`
inside the object.

### Mirroring a collection (not just copying it)

To make the destination *equal* the source, read the destination too and emit
removals for whatever it has that the source does not. This is the same shape
NCM's own UI sends. Remember that removal paths address array positions with
**integer** indices, while the updates dict uses **string** keys for the same
positions:

```python
def build_mirror_payload(src_identities, dst_identities):
    """-> (payload, plan). Mirrors identities.ip onto one destination group."""
    src = {e.get('_id_') or k: e for k, e in (src_identities or {}).items()}
    dst = {e.get('_id_') or k: e for k, e in (dst_identities or {}).items()}

    updates, removals = {}, []

    for identity_id, entry in src.items():
        members = normalize_entries(entry.get('members'))
        copied = {k: v for k, v in entry.items() if k != 'members'}
        copied['_id_'] = identity_id
        copied['members'] = {str(i): m for i, m in enumerate(members)}   # string keys
        updates[identity_id] = copied

        dst_entry = dst.get(identity_id)
        if dst_entry:
            dst_members = normalize_entries(dst_entry.get('members'))
            # Drop surplus positions, highest index first
            for index in range(len(dst_members) - 1, len(members) - 1, -1):
                removals.append(['identities', 'ip', identity_id, 'members', index])

    # Drop destination-only entries wholesale
    for identity_id in dst:
        if identity_id not in src:
            removals.append(['identities', 'ip', identity_id])

    return {'configuration': [{'identities': {'ip': updates}}, removals]}
```

This costs one extra GET per destination, since removals depend on each
destination's current contents — the payload is no longer identical across groups.
Skip the PATCH entirely when a destination already matches, and compute a per-group
summary of what changed so a dry-run mode can show it before anything is sent.

Prefer PATCH over PUT here even when removing things: PATCH honors the removals
list, whereas PUT additionally resets every unmentioned field to defaults, which at
`/groups/{id}/` scope means wiping unrelated group settings. If you do need a real
PUT, note that `put_group_configuration()` raises `AttributeError` after the write
lands; see the entry in `known-issues.md`.

### Consolidating (fan-in) a UUID-keyed collection from many sources into one

The reverse of mirroring: instead of one master feeding many destinations, many
source groups feed one destination. Two extra rules make this safe to repeat:

1. **Merge by the collection's natural key (e.g. `name`), not by `_id_`.** UUIDs
   are per-source-group and unrelated across groups — the "IPs" identity in group
   A and the "IPs" identity in group B do not share a UUID, but they should merge
   into one bucket. Bucket by the lowercased/trimmed name instead.
2. **When writing the merged result, match the destination by the same natural
   key and reuse its existing UUID for that name.** Only mint a fresh UUID for a
   name that doesn't exist on the destination yet. Otherwise every run replaces
   every identity with a new UUID, which is not just wasteful — anything on the
   device referencing the old UUID (rules, other config sections) breaks.

```python
import uuid

def merge_by_name(sources):
    """sources: list of raw identities.ip dicts (one per source group)."""
    buckets = {}   # lower(name) -> {'name', 'addresses': [...], 'seen': set()}
    for ip_identities in sources:
        for _, entry in (ip_identities or {}).items():
            name = (entry.get('name') or '').strip() or '(unnamed)'
            key = name.lower()
            bucket = buckets.setdefault(key, {'name': name, 'addresses': [], 'seen': set()})
            for member in normalize_entries(entry.get('members')):
                addr = member.get('address')
                addr_key = (addr or '').strip().lower()
                if addr and addr_key not in bucket['seen']:
                    bucket['seen'].add(addr_key)
                    bucket['addresses'].append(addr)
    return list(buckets.values())


def build_consolidate_payload(merged, destination_identities):
    """Push the merged list onto one destination, matched by name to keep UUIDs stable."""
    dst_by_name = {
        (e.get('name') or '').strip().lower(): (k, e)
        for k, e in (destination_identities or {}).items()
    }
    updates, removals, matched = {}, [], set()

    for bucket in merged:
        key = bucket['name'].strip().lower()
        existing = dst_by_name.get(key)
        identity_id = existing[0] if existing else str(uuid.uuid4())   # reuse, don't regenerate
        matched.add(identity_id)
        updates[identity_id] = {
            '_id_': identity_id,
            'name': bucket['name'],
            'members': {str(i): {'address': a} for i, a in enumerate(bucket['addresses'])},
        }

    for identity_id, entry in (destination_identities or {}).items():
        if identity_id not in matched:
            removals.append(['identities', 'ip', identity_id])   # destination-only name, prune it

    return {'configuration': [{'identities': {'ip': updates}}, removals]}
```

Because matching is by name rather than by UUID, re-running the consolidation
after a small change (one new address added to one source) only touches the
affected identity's `members` — it does not regenerate every UUID on the
destination, so nothing else that references those UUIDs is disturbed.

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
`web_apps/web_app_template/` as the style foundation. It provides a complete, consistent
design system including layout, components, and theming.

Reference files:
- `web_apps/web_app_template/index.html` — HTML structure
- `web_apps/script_manager/static/css/style.css` — Full CSS with light/dark mode
- `web_apps/script_manager/static/js/app.js` — JS patterns (dark mode toggle, sidebar, etc.)

All web apps must support light mode and dark mode:
- Use CSS custom properties (`var(--*)`) for all colors
- Toggle via `body.dark-mode` class
- Persist preference in `localStorage`
- Include both `logo.png` and `logo_dark.png` with automatic swap

See `.kiro/steering/web-ui-standards.md` for the full checklist and CSS variable reference.

### Favicon

Apps that mount the shared static folder get a favicon for free by reusing the
existing logo — no new binary asset, no server change:

```html
<link rel="icon" type="image/png" href="/static/logo.png">
<link rel="apple-touch-icon" href="/static/logo.png">
```

`logo.png` is 92x80 RGBA with transparency, near enough to square to scale
acceptably to 16/32px. This works in any app whose `serve.py` already has:

```python
STATIC_DIR = Path(__file__).resolve().parent.parent / "script_manager" / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
```

Apps serving their own `static/` directory need the path adjusted to wherever
their logo lives. Note that as of 2026-08-27 only `cellular_health_dashboard`
declares a favicon; the rest fall back to the browser default, so add these two
lines when building a new app rather than assuming the template covers it.

Browsers cache favicons more aggressively than HTML — if a change doesn't show,
request the icon URL directly or hard-reload before assuming the tag is wrong.

## Dashboard Stat Cards That Double as Filters — Two-Stage Filtering

The dashboard pattern in `web-ui-standards.md` requires both "stat cards as
filters" and display-option toggles plus a search box. Those two requirements
conflict unless the filtering is split into two stages, and getting it wrong
produces one of two bugs:

- **Count from the full dataset** → the cards never react to the display options
  or the search box. Toggling "only show connected" changes the table but the
  numbers above it sit still, so they look broken or stale.
- **Count from the fully-filtered dataset** → clicking one card zeroes every
  other card, because the card filter is included in its own input. You then
  cannot see the other counts or click between them.

The fix is a base set that includes the display options and search but excludes
the card filter:

```javascript
// Stage 1: display options + search. NOT the stat-card filter.
function getBaseRows() {
    const search = searchInput.value.toLowerCase().trim();
    return allData.filter(row => {
        if (hideZeroScore && row.health_score === 0) return false;
        if (onlyConnected && row.state !== 'online') return false;
        if (search) {
            const hay = [row.name, row.carrier, row.mac].join(' ').toLowerCase();
            if (!hay.includes(search)) return false;
        }
        return true;
    });
}

// Stage 2: the stat-card filter, applied to the table only.
function applyFilters() {
    const baseRows = getBaseRows();
    filteredData = baseRows.filter(row => {
        if (activeFilter === 'all') return true;
        if (activeFilter === 'online') return row.state === 'online';
        return getQuality(row) === activeFilter;
    });
    updateStats(baseRows);   // cards read stage 1
    doSort();
    renderTable();           // table reads stage 2
}

function updateStats(rows) {
    const data = rows || getBaseRows();
    document.getElementById('statTotal').textContent = data.length;
    // ...remaining cards counted from `data`
}
```

Have every option toggle call `applyFilters()` (they generally already do) and
the cards stay in sync for free — no separate wiring per toggle. Drop any
standalone `updateStats()` call on the fetch path, since `applyFilters()` now
covers it and calling both double-computes.

Useful invariants to check when verifying: mutually exclusive cards should sum to
the total card (e.g. Online + Offline == Total), category buckets should never
exceed the total, and with no options set the total should equal the raw dataset
length.

**Known latent instances (as of 2026-08-27):** only
`cellular_health_dashboard` implements the two-stage split. Both
`inventory_dashboard` (`updateStats()` counts from `inventoryData`) and
`alert_dashboard` (counts from `alertsData`) still count from the full dataset,
so their cards do not respond to search or display options. Same fix applies.

## NCM SDK with FastAPI (async) — Avoiding Event Loop Blocking

The NCM SDK uses synchronous `requests.Session` internally. Calling SDK methods
directly from `async def` FastAPI endpoints blocks the entire event loop, making
the server unresponsive to all requests (including health checks, static files,
and Ctrl+C) for the duration of the API call (often 10–30 seconds for large accounts).

**Always wrap SDK calls in `run_in_executor`:**

```python
import asyncio
from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

def _fetch_data():
    """Synchronous function that calls the NCM SDK."""
    client = ncm.NcmClient(api_keys=api_keys)
    return client.get_routers()

@app.get("/api/data")
async def get_data():
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, _fetch_data)
    return JSONResponse({"data": result})
```

This runs the blocking SDK call in a thread pool, keeping the event loop free
to serve other requests, handle WebSocket connections, and respond to shutdown
signals. Apply this pattern to ALL endpoints that call `_get_cellular_health()`
or any other function using the NCM SDK.

**Also applies to:** SQLite writes, file I/O on large files, or any other
blocking operation inside an async handler.

## Parallelizing Chunked `__in` Requests

The `__in` filter limit (100 IDs per request, see known-issues) means any join
across more than 100 IDs — `net_device_metrics`, `net_devices`, `asset_endpoints`,
etc. — becomes many chunked API calls. Each chunk is an independent request with
no shared state, so fetching them sequentially in a `for` loop wastes wall-clock
time for no benefit: on a 27,000-device account this is easily 250+ chunks per
endpoint at ~100-200ms each, which adds up fast when done one at a time.

Fan the chunks out over a thread pool instead. The NCM SDK's `requests.Session`
is thread-safe for concurrent GETs (it's not mutated per-request), so this is
safe with the synchronous SDK as-is — no async rewrite needed:

```python
from concurrent.futures import ThreadPoolExecutor, as_completed

def fetch_chunks_parallel(fetch_fn, ids, chunk_size=100, max_workers=8):
    """Run fetch_fn(id_str) over ids in chunks, concurrently.

    fetch_fn receives one comma-joined chunk and returns a list of records.
    """
    chunks = [','.join(ids[i:i + chunk_size]) for i in range(0, len(ids), chunk_size)]
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(fetch_fn, chunk) for chunk in chunks]
        for future in as_completed(futures):
            results.extend(future.result() or [])
    return results

# Usage
metrics = fetch_chunks_parallel(
    lambda id_str: client.get_net_device_metrics(net_device__in=id_str),
    nd_ids,
)
```

If two independent chunked calls need to run (e.g. `net_device_metrics` and
`net_devices` for the same ID list, as in the cellular health dashboard), submit
both to an outer pool so they overlap too, rather than running one fully before
starting the other:

```python
with ThreadPoolExecutor(max_workers=2) as outer:
    future_a = outer.submit(fetch_chunks_parallel, fetch_fn_a, ids)
    future_b = outer.submit(fetch_chunks_parallel, fetch_fn_b, ids)
    result_a, result_b = future_a.result(), future_b.result()
```

Keep `max_workers` modest (5-10). The API enforces an approximate 500
calls/minute limit account-wide (see the 409-as-rate-limit known issue) — too
much concurrency just shifts the bottleneck to retry/backoff instead of actually
finishing faster. This is the same pattern already used in `assign_sdk/serve.py`
for fetching independent endpoints (apps, versions, accounts) in parallel;
applying it to chunked `__in` pagination is the generalization.

**Does not help `net_device_health`.** That endpoint takes no `__in` filter at
all (only `net_device`, `id__gt/gte/lt/lte`, `limit`, `offset` — see
api-v2-full-reference.md), so there's nothing to chunk or parallelize; it's a
single sequential paginated pull regardless.
