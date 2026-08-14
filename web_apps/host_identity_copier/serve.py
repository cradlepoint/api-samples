#!/usr/bin/env python3
"""
Host Identity Copier — copy the host address identities (identities.ip) from a
master NCM group to any number of destination groups.

Defaults:
    Source      — the group whose name contains "Base" (case-insensitive). If
                  exactly one matches it is selected automatically; if several
                  match you pick one.
    Destinations — every group whose name contains "(R)" (restricted).

Workflow:
    1. Enter API credentials in the Settings modal (gear icon). They are saved
       to config.json so the next run picks them up automatically.
    2. The Base group is detected and submitted, reading the group config and
       extracting the identities.ip subtree.
    3. The "(R)" groups are pre-selected as destinations. Adjust, then copy.

The source group, destination groups and the destination search pattern are
saved to config.json so the same job can be repeated on the next run. Saved
selections take precedence over the defaults.

Usage:
    .venv/bin/python web_apps/host_identity_copier/serve.py      # macOS/Linux
    .venv\\Scripts\\python.exe web_apps\\host_identity_copier\\serve.py   # Windows

Then open http://localhost:8070 in your browser.
"""

import os
import sys
import json
import asyncio
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    from dotenv import load_dotenv
    load_dotenv()
    load_dotenv(Path(__file__).resolve().parent.parent.parent / '.env')
except ImportError:
    pass

from fastapi import FastAPI, HTTPException
from fastapi.requests import Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

# Add project root to path for the vendored ncm SDK
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / 'ncm'))

import ncm  # noqa: E402

PORT = 8070

APP_DIR = Path(__file__).resolve().parent
CONFIG_PATH = APP_DIR / "config.json"

CRED_KEYS = ['X_CP_API_ID', 'X_CP_API_KEY', 'X_ECM_API_ID', 'X_ECM_API_KEY']
SECRET_KEYS = {'X_CP_API_KEY', 'X_ECM_API_KEY'}

# Default group-name matching. Both are plain case-insensitive substring
# matches, so "(R)" is treated literally rather than as a regex group.
SOURCE_DEFAULT_PATTERN = "Base"
DESTINATION_DEFAULT_PATTERN = "(R)"


# --- Config file -------------------------------------------------------------

DEFAULT_CONFIG: Dict[str, Any] = {
    "credentials": {k: "" for k in CRED_KEYS},
    "profiles": {},
    "source_group": None,          # {"id": 123, "name": "..."}
    "destination_groups": [],      # [{"id": 456, "name": "..."}]
    "destination_filter": "",      # last search pattern, e.g. "(R)"
    "push_mode": "mirror",         # "mirror" | "additive"
}


def load_config() -> Dict[str, Any]:
    """Read config.json, falling back to defaults for missing keys."""
    config = json.loads(json.dumps(DEFAULT_CONFIG))  # deep copy
    if CONFIG_PATH.exists():
        try:
            stored = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
            if isinstance(stored, dict):
                config.update(stored)
                creds = dict(DEFAULT_CONFIG["credentials"])
                creds.update(stored.get("credentials") or {})
                config["credentials"] = creds
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: could not read {CONFIG_PATH.name}: {e}", file=sys.stderr)
    return config


def save_config(config: Dict[str, Any]) -> None:
    """Write config.json with restrictive permissions (it holds API keys)."""
    CONFIG_PATH.write_text(json.dumps(config, indent=2), encoding="utf-8")
    if os.name != 'nt':
        try:
            os.chmod(CONFIG_PATH, 0o600)
        except OSError:
            pass


def update_config(**fields: Any) -> Dict[str, Any]:
    """Merge fields into config.json and return the updated config."""
    config = load_config()
    config.update(fields)
    save_config(config)
    return config


def apply_credentials_to_env(credentials: Dict[str, str], override: bool = False) -> None:
    """Copy stored credentials into os.environ. Real env vars win by default."""
    for key in CRED_KEYS:
        value = (credentials or {}).get(key, '')
        if value and (override or not os.environ.get(key)):
            os.environ[key] = value


# --- NCM client -------------------------------------------------------------

def get_api_keys_from_env() -> Dict[str, str]:
    """Build the SDK header dict from environment variables."""
    return {
        'X-CP-API-ID': os.environ.get('X_CP_API_ID', ''),
        'X-CP-API-KEY': os.environ.get('X_CP_API_KEY', ''),
        'X-ECM-API-ID': os.environ.get('X_ECM_API_ID', ''),
        'X-ECM-API-KEY': os.environ.get('X_ECM_API_KEY', ''),
    }


def _build_client():
    """Create an NCM v2 client, raising a clear error if credentials are missing."""
    api_keys = get_api_keys_from_env()
    missing = [
        env_name for env_name, header in (
            ('X_CP_API_ID', 'X-CP-API-ID'),
            ('X_CP_API_KEY', 'X-CP-API-KEY'),
            ('X_ECM_API_ID', 'X-ECM-API-ID'),
            ('X_ECM_API_KEY', 'X-ECM-API-KEY'),
        ) if not api_keys.get(header)
    ]
    if missing:
        raise RuntimeError(
            f"Missing required API credentials: {', '.join(missing)}. "
            "Open Settings (gear icon) to enter your NCM API keys."
        )
    return ncm.NcmClient(api_keys=api_keys, log_events=False)


def credentials_present() -> bool:
    return all(get_api_keys_from_env().values())


# --- Host address identity extraction ---------------------------------------

def extract_ip_identities(configuration: Any) -> Optional[Dict[str, Any]]:
    """
    Pull the identities.ip subtree out of a group configuration diff.

    A group configuration is a two element list: [updates_dict, removals_list].
    identities.ip is keyed by the identity's UUID, and each entry repeats that
    UUID in an _id_ field. Returns None when the group defines no ip identities.
    """
    if not isinstance(configuration, list) or not configuration:
        return None
    updates = configuration[0]
    if not isinstance(updates, dict):
        return None
    identities = updates.get('identities')
    if not isinstance(identities, dict):
        return None
    ip_identities = identities.get('ip')
    if not isinstance(ip_identities, dict) or not ip_identities:
        return None
    return ip_identities


def _index_sort_key(key: Any) -> Tuple[int, Any]:
    """Sort numeric-string keys ("0", "1", "10") numerically, others last."""
    text = str(key)
    if text.isdigit():
        return (0, int(text))
    return (1, text)


def normalize_members(members: Any) -> List[Dict[str, Any]]:
    """
    Return an identity's members as an ordered list of dicts.

    NCM stores config arrays either as real JSON arrays or as objects keyed by
    their index ("0", "1", ...). members is an array in the DTD, so it comes
    back index-keyed on read.
    """
    entries: List[Dict[str, Any]] = []
    if isinstance(members, dict):
        for key in sorted(members.keys(), key=_index_sort_key):
            value = members[key]
            if isinstance(value, dict):
                entries.append(dict(value))
            elif isinstance(value, str):
                entries.append({'address': value})
    elif isinstance(members, list):
        for value in members:
            if isinstance(value, dict):
                entries.append(dict(value))
            elif isinstance(value, str):
                entries.append({'address': value})
    return entries


def summarize_identities(ip_identities: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Flatten identities.ip into a display-friendly list."""
    summary = []
    for key, entry in ip_identities.items():
        if not isinstance(entry, dict):
            continue
        members = normalize_members(entry.get('members'))
        summary.append({
            'id': entry.get('_id_') or key,
            'name': entry.get('name', '') or '(unnamed)',
            'friendly_name': entry.get('friendly_name', ''),
            'member_count': len(members),
            'addresses': [m.get('address') for m in members if m.get('address')],
        })
    summary.sort(key=lambda i: str(i['name']).lower())
    return summary


def key_by_id(ip_identities: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """
    Re-key an identities.ip collection by each entry's _id_.

    The outer key and the inner _id_ normally agree, but NCM validates against
    the _id_ inside the object, so that is what we trust.
    """
    out: Dict[str, Dict[str, Any]] = {}
    for key, entry in (ip_identities or {}).items():
        if not isinstance(entry, dict):
            continue
        out[entry.get('_id_') or key] = entry
    return out


def empty_plan() -> Dict[str, Any]:
    """An empty change plan. Error results carry one so callers can sum blindly."""
    return {'added': [], 'updated': [], 'unchanged': [], 'removed': [],
            'addresses_removed': 0}


def build_mirror_payload(source_identities: Dict[str, Any],
                         destination_identities: Optional[Dict[str, Any]],
                         remove_extras: bool = True) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Build the PATCH body that makes a destination group's identities.ip match
    the source, using the same diff format NCM's own UI sends.

    A group configuration is a two element diff: [updates, removals].

    Updates set each source identity, with its members as an index-keyed object
    so the object-merge applies per position:

        {"identities": {"ip": {"<uuid>": {"_id_": "<uuid>",
                                          "members": {"0": {...}, "1": {...}}}}}}

    Removals prune whatever the destination has that the source does not. Each
    removal is a path into the config, and array elements are addressed by
    integer index (not a string):

        ["identities", "ip", "<uuid>", "members", 2]   # drop the 3rd address
        ["identities", "ip", "<uuid>"]                 # drop the whole identity

    Surplus member indices are emitted highest-first so the paths stay valid
    whether NCM resolves them against the original config or applies them in
    sequence with reindexing.

    :param remove_extras: when False, no removals are emitted — the copy only
        adds and updates, leaving destination-only entries in place.
    :return: (payload, plan) where plan summarizes what the payload will do.
    """
    src = key_by_id(source_identities)
    dst = key_by_id(destination_identities)

    updates: Dict[str, Any] = {}
    removals: List[List[Any]] = []
    plan = empty_plan()

    for identity_id, entry in src.items():
        src_members = normalize_members(entry.get('members'))

        copied = {k: v for k, v in entry.items() if k != 'members'}
        copied['_id_'] = identity_id
        copied['members'] = {str(i): m for i, m in enumerate(src_members)}
        updates[identity_id] = copied

        name = entry.get('name', '') or identity_id
        dst_entry = dst.get(identity_id)

        if dst_entry is None:
            plan['added'].append(name)
            continue

        dst_members = normalize_members(dst_entry.get('members'))
        surplus = len(dst_members) - len(src_members)

        # Compare only the fields we actually send
        same_fields = all(
            dst_entry.get(k) == v for k, v in entry.items() if k != 'members'
        )
        if same_fields and dst_members == src_members:
            plan['unchanged'].append(name)
        else:
            plan['updated'].append(name)

        if remove_extras and surplus > 0:
            for index in range(len(dst_members) - 1, len(src_members) - 1, -1):
                removals.append(['identities', 'ip', identity_id, 'members', index])
                plan['addresses_removed'] += 1

    if remove_extras:
        for identity_id, dst_entry in dst.items():
            if identity_id not in src:
                removals.append(['identities', 'ip', identity_id])
                plan['removed'].append(dst_entry.get('name', '') or identity_id)

    payload = {'configuration': [{'identities': {'ip': updates}}, removals]}
    return payload, plan


# --- FastAPI app -----------------------------------------------------------

app = FastAPI(title="Host Identity Copier")

STATIC_DIR = APP_DIR.parent / "script_manager" / "static"
if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the main page."""
    return HTMLResponse((APP_DIR / "index.html").read_text(encoding="utf-8"))


@app.get("/api/config")
async def get_saved_config():
    """Return the saved job config (credentials masked) plus the default patterns."""
    config = load_config()
    return JSONResponse({
        "source_group": config.get("source_group"),
        "destination_groups": config.get("destination_groups", []),
        "destination_filter": config.get("destination_filter", ""),
        "push_mode": config.get("push_mode", "mirror"),
        "has_credentials": credentials_present(),
        "source_default_pattern": SOURCE_DEFAULT_PATTERN,
        "destination_default_pattern": DESTINATION_DEFAULT_PATTERN,
    })


@app.post("/api/config")
async def post_saved_config(request: Request):
    """
    Persist the current job selection so the next run can repeat it.
    Body: {source_group, destination_groups, destination_filter, push_mode}
    """
    body = await request.json()
    fields = {}
    if "source_group" in body:
        fields["source_group"] = body["source_group"]
    if "destination_groups" in body:
        fields["destination_groups"] = body["destination_groups"] or []
    if "destination_filter" in body:
        fields["destination_filter"] = body["destination_filter"] or ""
    if "push_mode" in body:
        fields["push_mode"] = "additive" if body["push_mode"] == "additive" else "mirror"
    if fields:
        update_config(**fields)
    return JSONResponse({"status": "saved"})


@app.delete("/api/config")
async def clear_saved_config():
    """Forget the saved job selection so the defaults apply again."""
    update_config(source_group=None, destination_groups=[], destination_filter="")
    return JSONResponse({"status": "cleared"})


@app.get("/api/groups")
async def get_groups():
    """Return all NCM groups for the autocomplete pickers."""
    def _fetch():
        client = _build_client()
        groups = client.get_groups(limit='all')
        try:
            accounts = client.get_accounts(limit='all')
        except Exception:
            accounts = []
        return groups, accounts

    loop = asyncio.get_event_loop()
    try:
        groups, accounts = await loop.run_in_executor(None, _fetch)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to load groups: {e}")

    account_map: Dict[str, str] = {}
    for a in accounts:
        name = a.get('name', '')
        account_map[str(a.get('id'))] = name
        res_url = a.get('resource_url', '')
        if res_url:
            account_map[res_url] = name

    result = []
    for g in groups:
        account_url = g.get('account', '')
        account_name = account_map.get(account_url, '')
        account_id = ''
        if account_url:
            parts = str(account_url).rstrip('/').split('/')
            account_id = parts[-1] if parts else ''
            if not account_name:
                account_name = account_map.get(account_id, '')
        result.append({
            'id': g.get('id'),
            'name': g.get('name', 'Unknown'),
            'product': g.get('product_name', ''),
            'device_count': g.get('device_count', 0),
            'account_name': account_name,
            'account_id': account_id,
        })

    result.sort(key=lambda g: str(g['name']).lower())
    return JSONResponse(result)


@app.post("/api/extract-identities")
async def extract_identities(request: Request):
    """
    Read the source group config and extract identities.ip.
    Body: {"group_id": 123, "group_name": "Base Group"}
    """
    body = await request.json()
    group_id = body.get('group_id')
    if group_id in (None, ''):
        raise HTTPException(status_code=400, detail="No source group selected")

    def _fetch():
        client = _build_client()
        rows = client.get_groups(id=group_id, fields='id,name,configuration')
        if not rows:
            raise LookupError(f"Group {group_id} not found")
        return rows[0]

    loop = asyncio.get_event_loop()
    try:
        group = await loop.run_in_executor(None, _fetch)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to read group config: {e}")

    group_name = group.get('name') or body.get('group_name') or str(group_id)
    ip_identities = extract_ip_identities(group.get('configuration'))

    if ip_identities is None:
        return JSONResponse({
            "found": False,
            "group_id": group_id,
            "group_name": group_name,
            "message": (
                f'No host address identities (identities.ip) found in group '
                f'"{group_name}". Create them on this group in NCM first.'
            ),
        })

    identities = summarize_identities(ip_identities)

    # Remember the source group for next run
    update_config(source_group={"id": group_id, "name": group_name})

    return JSONResponse({
        "found": True,
        "group_id": group_id,
        "group_name": group_name,
        "identity_count": len(identities),
        "address_count": sum(i['member_count'] for i in identities),
        "identities": identities,
        "raw": ip_identities,
    })


@app.post("/api/push-identities")
async def push_identities(request: Request):
    """
    Mirror the source group's host address identities onto the destination groups.

    Each destination's current config is read first so surplus addresses and
    destination-only identities can be pruned via the diff's removals list. That
    means one GET plus one PATCH per destination group.

    Body: {"source_group_id": 1, "destination_group_ids": [2, 3],
           "mode": "mirror"|"additive", "dry_run": false}
    """
    body = await request.json()
    source_group_id = body.get('source_group_id')
    destination_ids = body.get('destination_group_ids') or []
    mode = "additive" if body.get('mode') == "additive" else "mirror"
    remove_extras = (mode == "mirror")
    dry_run = bool(body.get('dry_run'))

    if source_group_id in (None, ''):
        raise HTTPException(status_code=400, detail="No source group selected")
    if not destination_ids:
        raise HTTPException(status_code=400, detail="No destination groups selected")

    # Never push a group's config onto itself. The source group can legitimately
    # match the destination pattern too (a Base group named "... (R)"), so this
    # guard matters rather than being merely defensive.
    destination_ids = [gid for gid in destination_ids if str(gid) != str(source_group_id)]
    if not destination_ids:
        raise HTTPException(
            status_code=400,
            detail="The only destination selected was the source group itself"
        )

    def _push():
        client = _build_client()
        rows = client.get_groups(id=source_group_id, fields='id,name,configuration')
        if not rows:
            raise LookupError(f"Source group {source_group_id} not found")
        source_identities = extract_ip_identities(rows[0].get('configuration'))
        if source_identities is None:
            raise ValueError("Source group has no host address identities (identities.ip)")

        results = []
        for gid in destination_ids:
            # Read the destination so removals can be computed against it
            try:
                dst_rows = client.get_groups(id=gid, fields='id,name,configuration')
            except Exception as e:
                results.append({'group_id': gid, 'status': 'error', 'plan': empty_plan(),
                                'detail': f'Could not read destination config: {e}'})
                continue
            if not dst_rows:
                results.append({'group_id': gid, 'status': 'error', 'plan': empty_plan(),
                                'detail': 'Destination group not found'})
                continue

            dst_identities = extract_ip_identities(dst_rows[0].get('configuration'))
            payload, plan = build_mirror_payload(source_identities, dst_identities,
                                                 remove_extras=remove_extras)

            entry = {
                'group_id': gid,
                'group_name': dst_rows[0].get('name', ''),
                'plan': plan,
                'payload': payload,
            }

            nothing_to_do = (not plan['added'] and not plan['updated']
                             and not plan['removed'] and not plan['addresses_removed'])

            if dry_run:
                entry.update(status='skipped', detail='Dry run — nothing sent')
            elif nothing_to_do:
                entry.update(status='success', detail='Already in sync — nothing sent')
            else:
                try:
                    detail = client.patch_group_configuration(gid, payload)
                    entry.update(status='success', detail=str(detail) if detail else 'OK')
                except Exception as e:
                    entry.update(status='error', detail=str(e))

            results.append(entry)

        return source_identities, results

    loop = asyncio.get_event_loop()
    try:
        source_identities, results = await loop.run_in_executor(None, _push)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except LookupError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Push failed: {e}")

    # Save the job for next run
    saved_destinations = body.get('destination_groups')
    fields: Dict[str, Any] = {"push_mode": mode}
    if isinstance(saved_destinations, list) and saved_destinations:
        fields["destination_groups"] = saved_destinations
    if body.get('destination_filter') is not None:
        fields["destination_filter"] = body.get('destination_filter') or ""
    update_config(**fields)

    identities = summarize_identities(source_identities)

    return JSONResponse({
        "results": results,
        "succeeded": sum(1 for r in results if r['status'] == 'success'),
        "failed": sum(1 for r in results if r['status'] == 'error'),
        "identity_count": len(identities),
        "address_count": sum(i['member_count'] for i in identities),
        "identities_removed": sum(len(r.get('plan', {}).get('removed', [])) for r in results),
        "addresses_removed": sum(r.get('plan', {}).get('addresses_removed', 0) for r in results),
        "mode": mode,
        "dry_run": dry_run,
    })


# --- Credentials / profiles -------------------------------------------------

@app.get("/api/profiles")
async def list_profiles():
    """List saved credential profile names."""
    return JSONResponse(sorted(load_config().get("profiles", {}).keys()))


@app.post("/api/profiles")
async def save_profile(request: Request):
    """Save a named credential profile into config.json."""
    body = await request.json()
    name = (body.get('name') or '').strip()
    if not name:
        raise HTTPException(status_code=400, detail="Profile name required")
    config = load_config()
    profiles = config.get("profiles", {})
    existing = profiles.get(name, {})
    profile = {}
    for key in CRED_KEYS:
        value = body.get(key, '')
        # Blank secret fields keep the previously stored value
        profile[key] = value if value else existing.get(key, '')
    profiles[name] = profile
    config["profiles"] = profiles
    save_config(config)
    return JSONResponse({"status": "saved"})


@app.post("/api/profiles/load")
async def load_profile(request: Request):
    """Load a named profile into the environment and make it the active config."""
    body = await request.json()
    name = (body.get('name') or '').strip()
    config = load_config()
    profiles = config.get("profiles", {})
    if name not in profiles:
        raise HTTPException(status_code=404, detail="Profile not found")
    profile = profiles[name]
    apply_credentials_to_env(profile, override=True)
    config["credentials"] = {k: profile.get(k, '') for k in CRED_KEYS}
    save_config(config)
    return JSONResponse({"status": "loaded"})


@app.delete("/api/profiles/{name}")
async def delete_profile(name: str):
    """Delete a named credential profile."""
    config = load_config()
    profiles = config.get("profiles", {})
    if name in profiles:
        del profiles[name]
        config["profiles"] = profiles
        save_config(config)
    return JSONResponse({"status": "deleted"})


@app.get("/api/profiles/current")
async def current_credentials():
    """Return the active credentials with secrets masked."""
    return JSONResponse({
        'X_CP_API_ID': os.environ.get('X_CP_API_ID', ''),
        'X_CP_API_KEY': '***' if os.environ.get('X_CP_API_KEY') else '',
        'X_ECM_API_ID': os.environ.get('X_ECM_API_ID', ''),
        'X_ECM_API_KEY': '***' if os.environ.get('X_ECM_API_KEY') else '',
        'has_credentials': credentials_present(),
    })


@app.post("/api/credentials/apply")
async def apply_credentials(request: Request):
    """
    Apply credentials to the running process and persist them to config.json.
    Blank secret fields leave the stored value untouched.
    """
    body = await request.json()
    config = load_config()
    stored = config.get("credentials", {})

    for key in CRED_KEYS:
        value = body.get(key, '')
        if value:
            os.environ[key] = value
            stored[key] = value
        elif key not in SECRET_KEYS:
            # IDs can be cleared explicitly; secrets cannot (blank means "keep")
            if key in body:
                os.environ.pop(key, None)
                stored[key] = ''

    config["credentials"] = stored
    save_config(config)
    return JSONResponse({"status": "applied", "has_credentials": credentials_present()})


# --- Startup ---------------------------------------------------------------

_startup_config = load_config()
apply_credentials_to_env(_startup_config.get("credentials", {}))


if __name__ == "__main__":
    print("=" * 60)
    print("Host Identity Copier")
    print("=" * 60)
    print(f"Server running at: http://localhost:{PORT}")
    if credentials_present():
        print("API credentials: loaded")
    else:
        missing = [k for k in CRED_KEYS if not os.environ.get(k)]
        print(f"API credentials: MISSING — {', '.join(missing)}")
        print("  Enter them in the Settings panel (gear icon) in the UI")
    src = _startup_config.get("source_group")
    dests = _startup_config.get("destination_groups") or []
    if src:
        print(f"Saved source group: {src.get('name')} (id {src.get('id')})")
    else:
        print(f'Source default: groups matching "{SOURCE_DEFAULT_PATTERN}"')
    if dests:
        print(f"Saved destination groups: {len(dests)}")
    else:
        print(f'Destination default: groups matching "{DESTINATION_DEFAULT_PATTERN}"')
    print("Press Ctrl+C to stop the server")
    print("=" * 60)
    uvicorn.run(app, host="0.0.0.0", port=PORT)
