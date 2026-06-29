"""
Custom Alert Dashboard — displays custom alerts from NCM API with
configurable timeframe, auto-refresh, and export capabilities.

Usage:
    .venv/bin/python web_apps/custom_alert_dashboard/serve.py

Then open http://localhost:8060 in your browser.
"""

import os
import sys
import json
import ssl
import asyncio

from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from ncm import ncm


# --- Configuration ---
PORT = 8065
APP_DIR = Path(__file__).parent
PROFILES_PATH = APP_DIR / "profiles.json"
SETTINGS_PATH = APP_DIR / "settings.json"

# Shared static directory for logos
STATIC_DIR = Path(__file__).parent.parent / "script_manager" / "static"

# --- SSL verification state ---
_ssl_verify = True


def _load_settings():
    """Load persisted settings from disk."""
    global _ssl_verify
    if SETTINGS_PATH.exists():
        try:
            settings = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            _ssl_verify = settings.get("ssl_verify", True)
            if not _ssl_verify:
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        except (json.JSONDecodeError, KeyError):
            pass


def _save_settings():
    """Persist settings to disk."""
    try:
        settings = {}
        if SETTINGS_PATH.exists():
            try:
                settings = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, KeyError):
                pass
        settings["ssl_verify"] = _ssl_verify
        SETTINGS_PATH.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    except Exception:
        pass


_load_settings()


# --- Helper functions ---

def check_env():
    """Check that required v2 API env vars are set. Returns missing list."""
    required = ["X_CP_API_ID", "X_CP_API_KEY", "X_ECM_API_ID", "X_ECM_API_KEY"]
    missing = [v for v in required if not os.environ.get(v)]
    return missing


def get_api_keys_from_env() -> dict:
    """Build SDK-compatible API keys dict from environment variables."""
    keys = {
        'X-CP-API-ID': os.environ.get('X_CP_API_ID', ''),
        'X-CP-API-KEY': os.environ.get('X_CP_API_KEY', ''),
        'X-ECM-API-ID': os.environ.get('X_ECM_API_ID', ''),
        'X-ECM-API-KEY': os.environ.get('X_ECM_API_KEY', ''),
    }
    token = os.environ.get('NCM_API_TOKEN')
    if token:
        keys['token'] = token
    return keys


def _build_client():
    """Create an NCM SDK client from environment variables."""
    global _ssl_verify
    api_keys = get_api_keys_from_env()
    if not api_keys.get('X-CP-API-ID') or not api_keys.get('X-ECM-API-ID'):
        raise RuntimeError(
            "Missing required API credentials. Use the Settings panel (gear icon) "
            "to configure credentials, or set X_CP_API_ID, X_CP_API_KEY, "
            "X_ECM_API_ID, X_ECM_API_KEY environment variables."
        )
    client = ncm.NcmClient(api_keys=api_keys)
    if not _ssl_verify:
        client.session.verify = False
    return client


def _fetch_alerts(days=30):
    """Fetch all alerts from NCM API for the given time range.

    Uses direct session calls to /alerts/ with created_at__gt,
    bypassing the SDK's __get_json which silently swallows errors.
    """
    # Clamp days to max 90
    days = min(max(1, days), 90)

    client = _build_client()

    # Get account name
    accounts = client.get_accounts()
    account_name = accounts[0].get('name', 'Unknown') if accounts else 'Unknown'

    # Build account URL-to-name lookup
    account_names = {}
    for acc in (accounts or []):
        acc_id = str(acc.get('id', ''))
        acc_name = acc.get('name', '')
        if acc_id and acc_name:
            account_names[acc_id] = acc_name

    # Calculate time window — API expects full ISO format with tz offset
    start_time = (datetime.now(timezone.utc) - timedelta(days=days)).strftime(
        "%Y-%m-%dT%H:%M:%S.%f+00:00"
    )

    # Use the SDK's authenticated session directly
    base_url = client.base_url
    url = f"{base_url}/alerts/"
    params = {
        'created_at__gt': start_time,
        'limit': '500'
    }

    alerts = []
    from time import sleep

    while url:
        resp = client.session.get(url, params=params)
        if resp.status_code == 200:
            data = resp.json()
            alerts.extend(data.get('data', []))
            url = data.get('meta', {}).get('next')
            params = None  # params baked into next URL
        elif resp.status_code in (408, 429, 500, 502, 503, 504):
            sleep(2)
            continue
        else:
            raise RuntimeError(
                f"API error {resp.status_code}: {resp.text[:500]}"
            )

    # Sort by created_at descending (most recent first) — done client-side
    # since /alerts/ doesn't support order_by=created_at
    alerts.sort(key=lambda a: a.get('created_at', ''), reverse=True)

    # Collect unique router IDs from alert router URLs
    router_ids = set()
    for a in alerts:
        router_url = a.get('router', '')
        if router_url and '/' in str(router_url):
            rid = str(router_url).rstrip('/').split('/')[-1]
            if rid.isdigit():
                router_ids.add(rid)

    # Batch lookup router names using expand is not needed here —
    # just fetch routers by ID. Use __in filter (max 100 per chunk).
    router_names = {}
    if router_ids:
        id_list = list(router_ids)
        for i in range(0, len(id_list), 100):
            chunk = ','.join(id_list[i:i+100])
            routers = client.get_routers(id__in=chunk, fields='id,name')
            if isinstance(routers, list):
                for r in routers:
                    router_names[str(r.get('id', ''))] = r.get('name', '')

    # Enrich alerts with router_name, account_name, and title extracted from info
    for a in alerts:
        # Resolve router name
        router_url = a.get('router', '')
        if router_url and '/' in str(router_url):
            rid = str(router_url).rstrip('/').split('/')[-1]
            a['router_name'] = router_names.get(rid, f'Router {rid}')
            a['router_id'] = rid
        else:
            a['router_name'] = ''
            a['router_id'] = ''

        # Resolve account name from URL
        account_url = a.get('account', '')
        if account_url and '/' in str(account_url):
            aid = str(account_url).rstrip('/').split('/')[-1]
            a['account_name'] = account_names.get(aid, account_names.get(account_url, f'Account {aid}'))
        else:
            # No account URL — assign the primary account name
            a['account_name'] = account_name

        # Extract title from info (info can be a dict or JSON string)
        info = a.get('info', '')
        title = ''
        if isinstance(info, dict):
            title = info.get('title', '')
        elif isinstance(info, str):
            try:
                info_obj = json.loads(info)
                if isinstance(info_obj, dict):
                    title = info_obj.get('title', '')
            except (json.JSONDecodeError, TypeError):
                pass
        a['alert_title'] = title

    return {"account_name": account_name, "alerts": alerts, "days": days}


def _fetch_alerts_since(since_ts):
    """Fetch only new alerts since the given ISO timestamp.

    Used for incremental refresh — much faster than re-fetching the full range.
    """
    from time import sleep

    client = _build_client()

    # Get account name
    accounts = client.get_accounts()
    account_name = accounts[0].get('name', 'Unknown') if accounts else 'Unknown'

    # Build account URL-to-name lookup
    account_names = {}
    for acc in (accounts or []):
        acc_id = str(acc.get('id', ''))
        acc_name = acc.get('name', '')
        if acc_id and acc_name:
            account_names[acc_id] = acc_name

    # Use the SDK's authenticated session directly
    base_url = client.base_url
    url = f"{base_url}/alerts/"
    params = {
        'created_at__gt': since_ts,
        'limit': '500'
    }

    alerts = []

    while url:
        resp = client.session.get(url, params=params)
        if resp.status_code == 200:
            data = resp.json()
            alerts.extend(data.get('data', []))
            url = data.get('meta', {}).get('next')
            params = None
        elif resp.status_code in (408, 429, 500, 502, 503, 504):
            sleep(2)
            continue
        else:
            raise RuntimeError(
                f"API error {resp.status_code}: {resp.text[:500]}"
            )

    # Sort newest first
    alerts.sort(key=lambda a: a.get('created_at', ''), reverse=True)

    # Resolve router names for new alerts
    router_ids = set()
    for a in alerts:
        router_url = a.get('router', '')
        if router_url and '/' in str(router_url):
            rid = str(router_url).rstrip('/').split('/')[-1]
            if rid.isdigit():
                router_ids.add(rid)

    router_names = {}
    if router_ids:
        id_list = list(router_ids)
        for i in range(0, len(id_list), 100):
            chunk = ','.join(id_list[i:i+100])
            routers = client.get_routers(id__in=chunk, fields='id,name')
            if isinstance(routers, list):
                for r in routers:
                    router_names[str(r.get('id', ''))] = r.get('name', '')

    for a in alerts:
        router_url = a.get('router', '')
        if router_url and '/' in str(router_url):
            rid = str(router_url).rstrip('/').split('/')[-1]
            a['router_name'] = router_names.get(rid, f'Router {rid}')
            a['router_id'] = rid
        else:
            a['router_name'] = ''
            a['router_id'] = ''

        # Resolve account name
        account_url = a.get('account', '')
        if account_url and '/' in str(account_url):
            aid = str(account_url).rstrip('/').split('/')[-1]
            a['account_name'] = account_names.get(aid, account_name)
        else:
            a['account_name'] = account_name

        info = a.get('info', '')
        title = ''
        if isinstance(info, dict):
            title = info.get('title', '')
        elif isinstance(info, str):
            try:
                info_obj = json.loads(info)
                if isinstance(info_obj, dict):
                    title = info_obj.get('title', '')
            except (json.JSONDecodeError, TypeError):
                pass
        a['alert_title'] = title

    return {"account_name": account_name, "alerts": alerts}


# --- FastAPI App ---

app = FastAPI(title="Alert Dashboard")

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


# --- Profile Management ---

def _load_profiles():
    """Load saved credential profiles."""
    if PROFILES_PATH.exists():
        return json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
    return {}


def _save_profiles(profiles):
    """Save credential profiles to disk."""
    PROFILES_PATH.write_text(json.dumps(profiles, indent=2), encoding="utf-8")


# --- Routes ---

@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the dashboard HTML."""
    html_path = APP_DIR / "index.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


# --- ACK Persistence ---
ACKS_PATH = APP_DIR / "acks.json"


def _load_acks():
    """Load acknowledged alert IDs from disk."""
    if ACKS_PATH.exists():
        try:
            return json.loads(ACKS_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def _save_acks(acks):
    """Save acknowledged alert IDs to disk."""
    ACKS_PATH.write_text(json.dumps(acks, indent=2), encoding="utf-8")


@app.get("/api/acks")
async def get_acks():
    """Return all acknowledged alert IDs."""
    return JSONResponse(_load_acks())


@app.post("/api/acks")
async def set_ack(request: Request):
    """Acknowledge or unacknowledge an alert.

    Body: {"id": "<alert_id>", "acked": true/false, "alert": {...}}
    Stores the full alert object and ack timestamp when acking.
    """
    body = await request.json()
    alert_id = str(body.get("id", ""))
    acked = body.get("acked", True)
    alert_data = body.get("alert", None)

    if not alert_id:
        return JSONResponse({"error": "id required"}, status_code=400)

    acks = _load_acks()
    if acked:
        acks[alert_id] = {
            "acked_at": datetime.now(timezone.utc).isoformat(),
            "alert": alert_data,
        }
    else:
        acks.pop(alert_id, None)
    _save_acks(acks)
    return JSONResponse({"status": "ok", "id": alert_id, "acked": acked})


@app.get("/api/alerts")
async def get_alerts(days: int = 30, since: str = None):
    """Return custom alerts as JSON.

    Query params:
        days: Number of days to look back (1-90, default 30) — used on first load
        since: ISO timestamp — if provided, only fetch alerts newer than this
               (used for incremental refresh)
    """
    days = min(max(1, days), 90)
    try:
        loop = asyncio.get_event_loop()
        if since:
            result = await loop.run_in_executor(None, _fetch_alerts_since, since)
        else:
            result = await loop.run_in_executor(None, _fetch_alerts, days)
        return JSONResponse({
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "account_name": result["account_name"],
            "days": result.get("days", days),
            "count": len(result["alerts"]),
            "data": result["alerts"],
            "incremental": since is not None,
            "filters": {
                "types": sorted(set(
                    a.get('type', '') for a in result["alerts"] if a.get('type')
                )),
                "accounts": sorted(set(
                    a.get('account_name', '') for a in result["alerts"] if a.get('account_name')
                )),
            },
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        err_str = str(e)

        # Detect SSL errors
        is_ssl_error = 'CERTIFICATE_VERIFY_FAILED' in err_str or (
            'SSL' in err_str.upper() and 'VERIFY' in err_str.upper()
        )
        if is_ssl_error:
            return JSONResponse(
                {"status": "error", "error_type": "ssl_error",
                 "message": "SSL certificate verification failed. Use the "
                            "Disable SSL Verify button in Settings."},
                status_code=502,
            )
        return JSONResponse(
            {"status": "error", "message": err_str},
            status_code=500,
        )


@app.get("/api/status")
async def status():
    """Quick health check."""
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}


@app.post("/api/ssl-noverify")
async def disable_ssl_verify():
    """Disable SSL certificate verification (persisted)."""
    global _ssl_verify
    _ssl_verify = False
    _save_settings()
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    return JSONResponse({"status": "ok", "ssl_verify": False})


# --- Profile Endpoints ---

@app.get("/api/profiles")
async def list_profiles():
    """List all saved credential profiles."""
    profiles = _load_profiles()
    result = {}
    for name, creds in profiles.items():
        result[name] = {k: v[:4] + "..." if v and len(v) > 4 else "" for k, v in creds.items()}
    return JSONResponse(result)


@app.post("/api/profiles")
async def save_profile(request: Request):
    """Save or overwrite a credential profile."""
    body = await request.json()
    name = body.get("name", "").strip()
    creds = body.get("credentials", {})
    overwrite = body.get("overwrite", False)

    if not name:
        return JSONResponse({"error": "Profile name required"}, status_code=400)

    profiles = _load_profiles()
    if name in profiles and not overwrite:
        return JSONResponse(
            {"error": "exists", "message": f"Profile '{name}' already exists"},
            status_code=409,
        )

    profiles[name] = {
        "X_CP_API_ID": creds.get("X_CP_API_ID", ""),
        "X_CP_API_KEY": creds.get("X_CP_API_KEY", ""),
        "X_ECM_API_ID": creds.get("X_ECM_API_ID", ""),
        "X_ECM_API_KEY": creds.get("X_ECM_API_KEY", ""),
    }
    _save_profiles(profiles)
    return JSONResponse({"status": "ok", "name": name})


@app.post("/api/profiles/load")
async def load_profile(request: Request):
    """Load a profile into the running environment."""
    body = await request.json()
    name = body.get("name", "").strip()

    profiles = _load_profiles()
    if name not in profiles:
        return JSONResponse({"error": f"Profile '{name}' not found"}, status_code=404)

    creds = profiles[name]
    for key, val in creds.items():
        if val:
            os.environ[key] = val

    return JSONResponse({"status": "ok", "name": name})


@app.delete("/api/profiles/{name}")
async def delete_profile(name: str):
    """Delete a saved profile."""
    profiles = _load_profiles()
    if name not in profiles:
        return JSONResponse({"error": f"Profile '{name}' not found"}, status_code=404)

    del profiles[name]
    _save_profiles(profiles)
    return JSONResponse({"status": "ok", "deleted": name})


@app.get("/api/profiles/current")
async def current_credentials():
    """Return current active credentials."""
    key_pairs = [
        ("X_CP_API_ID", "CP_API_ID"),
        ("X_CP_API_KEY", "CP_API_KEY"),
        ("X_ECM_API_ID", "ECM_API_ID"),
        ("X_ECM_API_KEY", "ECM_API_KEY"),
    ]
    result = {}
    for primary, fallback in key_pairs:
        val = os.environ.get(primary, "") or os.environ.get(fallback, "")
        result[primary] = {"set": bool(val), "value": val}
    return JSONResponse(result)


@app.post("/api/credentials/apply")
async def apply_credentials(request: Request):
    """Apply credentials to the running environment without saving."""
    body = await request.json()
    creds = body.get("credentials", {})
    for key in ["X_CP_API_ID", "X_CP_API_KEY", "X_ECM_API_ID", "X_ECM_API_KEY"]:
        val = creds.get(key, "").strip()
        if val:
            os.environ[key] = val
    return JSONResponse({"status": "ok"})


# --- Main ---

if __name__ == "__main__":
    missing = check_env()
    if missing:
        print("\n  Warning: Missing environment variables:", ", ".join(missing))
        print("  You can set them via the Settings panel in the dashboard.\n")

    print("=" * 60)
    print("  Alert Dashboard")
    print("=" * 60)
    print(f"  Server: http://localhost:{PORT}")
    print(f"  Press Ctrl+C to stop")
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
