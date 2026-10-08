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

Those reference files are **copy-from** sources, read while authoring and copied
into the new app. They are not runtime paths — see "Apps must be self-contained"
below.

### Apps must be self-contained

Each app serves assets only from its own directory:

```python
STATIC_DIR = Path(__file__).resolve().parent / "static"      # own folder
if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
```

Give every new app its own `static/logo.png` and `static/logo_dark.png` (copy them
from any existing app) and its own `requirements.txt`. Never mount a sibling app's
folder: it works in a repo checkout and breaks the moment anyone copies the app
directory on its own.

### Favicon

Reuse the app's own logo — no new binary asset, no server change:

```html
<link rel="icon" type="image/png" href="/static/logo.png">
<link rel="apple-touch-icon" href="/static/logo.png">
```

`logo.png` is 92x80 RGBA with transparency, near enough to square to scale
acceptably to 16/32px. Works in any app that mounts its own `static/` per above.
Most apps still fall back to the browser default, so add these two lines when
building a new app rather than assuming the template covers it.

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

## Parallel Speculative Offset Pagination (No Total Count)

The previous pattern parallelizes chunks whose IDs you already know. This one covers
the other case: pulling an entire large collection when you don't know how big it is.

v2 `meta` gives you `limit`, `offset`, `next`, and `previous` — but **no total count**.
So you can't compute the offsets up front and fan them out. Following `meta.next` works
but is strictly serial: each response tells you the next URL, so the requests can't
overlap. On `/firmwares/` (~17,700 records at `limit=500`, 60 pages) that measured
**53.9 seconds**.

Since offsets are predictable (`0, 500, 1000, …`), request a *round* of them
speculatively, then stop on the first empty page. Same data, **9.2 seconds** — about 6x
faster:

```python
from concurrent.futures import ThreadPoolExecutor

PAGE_LIMIT = 500      # v2 maximum
WORKERS = 10

def fetch_all_parallel(session, url):
    """Pull an entire v2 collection using parallel offset rounds.

    Dedupes by `id` — several v2 endpoints repeat records across pages.
    """
    records = {}
    offset = 0
    finished = False

    def fetch_page(page_offset):
        resp = session.get(url, params={"limit": PAGE_LIMIT, "offset": page_offset},
                           timeout=60)
        resp.raise_for_status()
        return resp.json().get("data", [])

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        while not finished:
            offsets = [offset + i * PAGE_LIMIT for i in range(WORKERS)]
            for data in pool.map(fetch_page, offsets):
                if not data:
                    finished = True          # past the end; drain the round
                for item in data:
                    records[str(item["id"])] = item
            offset += PAGE_LIMIT * WORKERS
    return list(records.values())
```

Notes:
- **Always dedupe by `id`.** `/firmwares/` returns ~20,000 rows for 17,677 distinct
  records (see known-issues). Without deduping, the overshoot looks like real data.
- **Drain the whole round** rather than breaking on the first empty page, so results
  already in flight aren't discarded.
- Overshoot is bounded and cheap: at most `WORKERS - 1` wasted requests, which return
  empty `data` quickly.
- Keep `WORKERS` modest (8–10). This is a deliberate burst against a rate-limited API;
  pair it with retry/backoff on 408/429/503/504.
- Only worth it for full-collection pulls. If a server-side filter narrows the result
  to a page or two, filter instead.

## Downloading Firmware Images (and Verifying Them)

Firmware **metadata** is in the v2 API; the **images** are on a CDN. Each
`/firmwares/` record carries:

- `url` — a *path*, not a full URL: `/IBR600C-2026-09-16T00%3A34%3A43.bin`
- `hash` — the **SHA-1 of the image**, so downloads can be verified
- `product` — a URL to `/products/{id}/`; the model name is not on the record

Prepend the CDN base to `url` to fetch the image. Stream it, hash as you go, write to a
temporary name, and only move it into place once the hash checks out — a failed check
should not leave a corrupt image where a good one is expected:

```python
import hashlib

FIRMWARE_CDN = "https://d251cfg5d9gyuq.cloudfront.net"

def download_firmware(session, firmware, dest_dir):
    """Stream a firmware image to disk, verifying its SHA-1."""
    target = dest_dir / f"{firmware['model']}-{firmware['version']}.bin"
    part = target.with_suffix(target.suffix + ".part")

    resp = session.get(FIRMWARE_CDN + firmware["url"], stream=True, timeout=300)
    resp.raise_for_status()

    digest = hashlib.sha1()
    with open(part, "wb") as handle:
        for chunk in resp.iter_content(chunk_size=1 << 20):   # 1 MiB
            handle.write(chunk)
            digest.update(chunk)

    actual = digest.hexdigest()
    if firmware.get("hash") and actual != firmware["hash"]:
        part.unlink(missing_ok=True)
        raise ValueError(f"SHA-1 mismatch: expected {firmware['hash']}, got {actual}")

    part.replace(target)      # atomic on the same filesystem
    return target
```

`url` needs normalizing first, though — 41 records carry a fully-qualified URL rather
than a path, and not every image is a `.bin`:

```python
def image_url(url):
    """Absolute URL for an image, whether `url` is a path or already qualified."""
    if url.lower().startswith(("http://", "https://")):
        return url
    return FIRMWARE_CDN + url

def image_extension(url):
    """Real extension — mostly .bin, but CR4250 ships .vmp."""
    name = urllib.parse.unquote(url).split("?")[0].rsplit("/", 1)[-1]
    return Path(name).suffix.lower() or ".bin"

def image_variant(url):
    """'multiimage' or '' — the only thing separating some same-version builds."""
    return "multiimage" if "-multiimage-" in urllib.parse.unquote(url).lower() else ""
```

Notes:
- **Don't key files by `model`+`version`.** The same model and version routinely ship
  as several distinct builds — see known-issues. Most pairs are a standard image plus a
  `multiimage` one, so include the variant, and add `built_at` plus a short `hash`
  prefix when a variant still has several builds. Otherwise you silently overwrite.
- Images are 20–30 MB. Stream them; don't use `resp.content`, and don't hold them in
  memory to hash afterwards.
- The CDN returned 200 **without** auth headers in testing, so it appears public.
  Sending the headers anyway is harmless and keeps one code path.
- `built_at` is UTC. Render it as UTC anywhere you also show a filename containing the
  build date, or the two will appear to disagree.
- Use a generous timeout (300s) and `raise_for_status()` before writing anything.

Working implementation: `web_apps/ncos_downloader/serve.py`.

## Toggling Visibility: the `hidden` Attribute vs. the Template CSS

The `hidden` attribute is the idiomatic way to show and hide a region, and it reads
cleanly when a panel has several mutually exclusive states (loading / empty / no-results
/ table):

```javascript
function showState(which) {
  const states = {loading: 'loadingEl', empty: 'emptyEl', none: 'noResultsEl', table: 'tableEl'};
  Object.entries(states).forEach(([key, id]) => {
    document.getElementById(id).hidden = (key !== which);
  });
}
```

**It silently does nothing on the template's components.** `hidden` works by way of a
user-agent rule, `[hidden] { display: none }`, which *any* author `display` declaration
outranks. The shared style foundation sets `display` on exactly the elements you want to
toggle:

```css
.center-state { display: flex; }     /* empty states, loading states, spinners */
table.data    { display: table; }    /* any table                              */
.modal        { display: none; }     /* … and .modal.show { display: flex }    */
```

So `el.hidden = true` on an empty state leaves it on screen. The failure is confusing
because the JS is correct and the states stack on top of each other — a spinner and an
"empty" message and a populated table all visible at once, which reads as a data bug
rather than a CSS one.

Two fixes, either is fine:

```css
/* 1. Make the attribute authoritative — one line, near the top of the sheet */
[hidden] { display: none !important; }
```

```javascript
/* 2. Or use the class convention the template already uses for modals */
el.classList.toggle('show', isVisible);
```

Prefer (1) when you have multi-state panels: it keeps the readable `hidden` idiom
working everywhere and costs one rule. `!important` is warranted here — it restores the
behavior the attribute is supposed to have rather than overriding a real design choice.

Worth knowing even if you use `style.display` directly, since it explains why mixing the
two approaches in one app produces elements that refuse to hide.

## Resolving net_device IDs to Router Names

Several endpoints identify a cellular modem only by its `net_device` ID — v2
`net_device_health`, `net_device_metrics`, `net_device_signal_samples`, and the v3
`modem_upgrades` child records all do this. A bare ID is meaningless in a report or
a dashboard, so it has to be joined back to the modem's parent router.

`expand=router` does the work in one call: the `router` field comes back as an
inline object (id, name, state, full_product_name, group URL) instead of a URL, so
no second `/routers/` fetch is needed.

```python
def resolve_net_devices(client, net_device_ids):
    """Map net_device IDs to router name/model plus the modem's own details."""
    resolved = {}
    ids = [str(i) for i in net_device_ids if i]
    # __in filters accept at most 100 IDs per call.
    for i in range(0, len(ids), 100):
        chunk = ','.join(ids[i:i + 100])
        for nd in client.get_net_devices(id__in=chunk, expand='router',
                                         limit='all') or []:
            router = nd.get('router')
            # expand=router yields null when the net_device has no router,
            # so this must handle a dict, a URL string, and None.
            if isinstance(router, dict):
                router_id = str(router.get('id') or '')
                router_name = router.get('name') or ''
                router_model = router.get('full_product_name') or ''
            else:
                router_id = _extract_id(router)   # trailing ID from the URL
                router_name = router_model = ''
            resolved[str(nd['id'])] = {
                'router_id': router_id,
                'router_name': router_name,
                'router_model': router_model,
                'net_device_name': nd.get('name') or '',     # e.g. mdm-b530a072
                'port': nd.get('port') or '',                # e.g. modem1, int1
                'model': nd.get('model') or '',              # modem model
                'carrier': nd.get('carrier') or '',
                # Current MODEM firmware — not the router's NCOS version.
                'current_version': nd.get('version') or nd.get('ver_pkg') or '',
                'connection_state': nd.get('connection_state') or '',
            }
    return resolved
```

Points that cost time if missed:

- **Chunk at 100 IDs.** `__in` filters cap there; a longer list is silently
  truncated or rejected. Chunks are independent calls, so fan them out across a
  thread pool (see "Parallelizing Chunked `__in` Requests").
- **`expand=router` can still be null** when a net_device has no associated router.
  Handle dict, URL string, and None.
- **Cache the result.** The ID→router mapping does not change during a job or a
  refresh cycle, so resolve once per process and reuse. This matters when polling:
  re-resolving on every poll multiplies API calls for no benefit.
- **Modem firmware is `version` / `ver_pkg`**, which is the modem's own package
  (e.g. `24.01.521_Verizon,2013`) — unrelated to the router's NCOS version.
  `modem_fw` is a *carrier/variant* label (e.g. `Verizon Wireless`), not a version
  number, despite the name.
- **Do not use `is_upgrade_available`** to decide whether a modem needs updating; it
  is deprecated (12/31/2023). Compare the current version against the available
  package instead.
- **Add `is_asset=true`** when you only want physical modems. It filters out virtual
  and logical interfaces, which otherwise dominate the result set.

### Getting a group's modems

`net_devices` has **no group filter**. Go through routers:

```python
routers = client.get_routers_for_group(group_id, limit='all') or []
net_devices = []
router_ids = [str(r['id']) for r in routers]
for i in range(0, len(router_ids), 100):
    net_devices += client.get_net_devices(
        router__in=','.join(router_ids[i:i + 100]),
        is_asset=True, expand='router', limit='all') or []
```

Keep the router list as a fallback source of names for any net_device whose
`expand=router` came back null.

### Crossing API versions

When the IDs come from a v3 endpoint (as with `modem_upgrades` children), this join
spans both APIs: the v3 Bearer token fetches the records, and the v2 header
credentials resolve the names. An app that does this needs **both** credential sets
configured, which is unusual for this repo — most tools need only one. Fail soft:
if the v2 lookup breaks, fall back to showing the raw ID (`(net_device 49050139)`)
rather than a blank cell or an aborted refresh, so the primary operation still
reports progress.

## Verifying an Endpoint Against Its Official Swagger Spec

Before trusting the repo docs (or your memory) for an endpoint's exact path, methods,
filters, or field names, fetch the authoritative spec. Each endpoint on
`developer.cradlepoint.com` is backed by a raw JSON spec you can retrieve directly —
no browser or auth needed:

```
https://developer.cradlepoint.com/swagger/spec/{endpoint}.json
```

For example: `swagger/spec/subscriptions.json`, `swagger/spec/routers.json`,
`swagger/spec/exchange_sites.json`. If you don't know the exact filename, open the
Swagger UI page (`developer.cradlepoint.com/Swagger_UI?ep={endpoint}`) and read the
spec URL out of its network requests.

What the spec settles definitively:

- **Version and base URL.** The `servers[].url` (v3) or `basePath` (v2) tells you
  which API an endpoint belongs to. This is how `users` was confirmed to be a **v2**
  endpoint (`basePath https://www.cradlepointecm.com/api/v2`) despite once being
  documented as v3.
- **Real path, including prefixes.** `paths` keys are the truth. v3 PCN/NCX live
  under `/api/v3/beta/...`; `regrades` lives under `/api/v3/asset_endpoints/regrades`
  — none of which you'd guess from the endpoint name.
- **Trailing slash.** v2 paths end in `/`; v3 spec paths do **not**. Match the spec.
- **Methods, required filters, enums, page-size limits.** e.g. the v3 `regrades` GET
  requires `filter[action]` and `filter[status]` with fixed enum values; `page[size]`
  maximums vary per endpoint (subscriptions 50, exchange_sites 500).

Precedence when sources disagree: **spec > SDK (`ncm/ncm/ncm.py`) > repo docs >
Postman collection.** The Postman collection and some older scripts have drifted
(wrong prefixes, renamed params); treat them as historical. When the repo's endpoint
reference and its own `known-issues.md` disagree, the known-issues log has usually
been verified against a live call — believe it over the reference, and reconcile the
reference. Guessing a field name when a spec was available is how `package_version`
once became `available_version` (a silent failure that produces blank columns, not an
error).

## Restoring Group Inheritance by Removing a Device-Level Branch

The inverse of pushing config: a device has a root-level override (say `security`,
the zone firewall branch) that shadows its group, and you want the device to inherit
the group again. Read `known-issues.md` → "The Removals List Means Different Things
at Group and Device Scope" first — the intuitive approach of adding the key to the
removals list does the opposite of what you want at device scope.

Read, modify, PUT. One batched read for the whole selection, since
`configuration_managers` returns the config manager `id` and the `configuration`
together, so there is no need for a separate `get_configuration_manager_id()` call
per router:

```python
TARGET_KEY = 'security'

def _removal_root(path):
    """First segment of a removals entry (array-of-segments, or a string)."""
    if isinstance(path, (list, tuple)):
        return str(path[0]) if path else None
    if isinstance(path, str):
        return path.split('.')[0] or None
    return None


def strip_root_key(configuration, key=TARGET_KEY):
    """Drop `key` from a device diff so the device inherits its group.

    Removes it from the updates dict AND drops any `key`-rooted path from the
    removals list — those entries are themselves device-level suppressions of
    the group's value, so leaving them keeps blocking inheritance.
    """
    updates = copy.deepcopy(configuration[0]) if configuration else {}
    removals = copy.deepcopy(configuration[1]) if len(configuration or []) > 1 else []
    had = key in updates or any(_removal_root(p) == key for p in removals)
    new_updates = {k: v for k, v in updates.items() if k != key}
    new_removals = [p for p in removals if _removal_root(p) != key]
    return [new_updates, new_removals], had, updates.get(key)


# One batched read: the SDK chunks __in into groups of 100 and paginates.
records = client.get_configuration_managers(
    router__in=','.join(router_ids),
    fields='id,router,configuration,suspended,synched',
    limit='all',
)

for rec in records:
    new_config, had, removed_branch = strip_root_key(rec['configuration'])
    if not had:
        continue        # nothing to do — do NOT write a no-op
    # Log removed_branch: it is what you would need to restore by hand.
    resp = client.session.put(
        f"{client.base_url}/configuration_managers/{rec['id']}/",   # trailing slash
        json={'configuration': new_config},
    )
    resp.raise_for_status()
    # Confirm by re-reading; a 2xx alone does not prove the branch is gone.
    after = client.get_configuration_managers(id=rec['id'], fields='id,configuration')
    assert TARGET_KEY not in (after[0]['configuration'][0] or {})
```

Points that matter:

- **Skip clean devices.** Writing a no-op diff still counts as a config push and can
  bump the device's sync state for no reason.
- **Send the complete diff minus the branch**, never a fragment. That is what makes
  PUT safe here despite its reset-unmentioned-fields behavior.
- **Log the removed branch as JSON.** It is the only record of what was there, and
  the only practical way to put it back.
- **Verify with a re-read.** The PUT returning 2xx means accepted, not applied.
- Use `client.session.put` directly rather than the SDK's
  `put_configuration_managers(router_id, ...)`, which performs its own
  `?router.id=` lookup on every call — wasteful when you already hold the config
  manager ID, and doubly so under concurrency.
- Root-level `firewall` and root-level `security` are different branches. Zone
  firewall config lives under `security`; `firewall` is port forwarding. Many devices
  have both.

Worked example: `web_apps/revert_device_firewall/` (`config_surgery.py` holds the
transform, dependency-free and separately testable).

## Stacked Panels in `.content-area`: Scroll, Don't Crush

The standard layout (`app-main → sidebar + content-area`) pins everything to the
viewport: `body` is `overflow: hidden`, `.app-main` is `overflow: hidden`, and the
content area is a flex column. That is right for a single panel, which should fill the
area and scroll its own table. It fails as soon as a second or third panel appears
below the first — results, progress, logs — because flex items shrink by default:

```css
.content-area { flex: 1; display: flex; flex-direction: column; min-height: 0; }
.panel.grow   { flex: 1; min-height: 0; }      /* shrinks to nothing */
```

The grown panel gives up all its height to the new siblings, so the picker or table
that owns the search box, the select-all buttons, and the selection count collapses to
a sliver of header. Nothing is clipped or hidden, and the panel is still technically on
screen, so it reads as "the new panel took over the page" rather than as a flex
sizing bug. `min-height: 0` makes it worse: it is required to let an *inner* scroll
region work, and it also removes the implicit floor that would have kept the panel
usable.

Let the content area scroll and give the primary panel a floor:

```css
.content-area { flex: 1; display: flex; flex-direction: column; gap: 1rem;
                min-width: 0; min-height: 0; overflow-y: auto; }
.panel        { /* … */ flex-shrink: 0; }
.panel.grow   { flex: 1 0 auto; min-height: 340px; }
```

- `overflow-y: auto` on the container turns the overflow into a scroll instead of
  pressure on the siblings.
- `flex-shrink: 0` on `.panel` stops the secondary panels from being squeezed too, so
  each keeps its natural height and the container's `scrollHeight` is honest.
- `flex: 1 0 auto` keeps the fill-the-area behavior when the primary panel is alone
  (grow 1), while `flex-basis: auto` plus `min-height` sets the floor. Keep the inner
  `min-height: 0` on the scrolling body (`.panel-body.flush`, `.list-container`) —
  the floor belongs on the panel, not on its scroll region.

If a panel appears in response to an action, scroll it into view once rather than
forcing it on screen by layout:

```javascript
$('progressPanel').style.display = 'flex';
$('progressPanel').scrollIntoView({ behavior: 'smooth', block: 'nearest' });
```

`block: 'nearest'` scrolls the content area by the minimum needed, and because the
container now scrolls, everything above stays reachable. Verify with the container
rather than by eye — `scrollHeight > clientHeight` and the primary panel's measured
height are the two facts that matter:

```javascript
const ca = document.querySelector('.content-area');
({ scrolls: ca.scrollHeight > ca.clientHeight,
   pickHeight: document.getElementById('pickPanel').getBoundingClientRect().height });
```

Applies to any app that reveals panels below a persistent picker or table. Worked
example: `web_apps/revert_device_firewall/index.html` (Routers picker above Scan
results and Progress).
