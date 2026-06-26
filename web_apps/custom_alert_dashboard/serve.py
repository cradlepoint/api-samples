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
PORT = 8060
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


def _fetch_custom_alerts(days=30):
    """Fetch custom alerts from NCM API for the given time range.

    Uses direct session calls to /alerts/ with type=custom_alert and
    created_at__gt, bypassing the SDK's __get_json which silently
    swallows errors and returns empty lists.
    """
    # Clamp days to max 90
    days = min(max(1, days), 90)

    client = _build_client()

    # Get account name
    accounts = client.get_accounts()
    account_name = accounts[0].get('name', 'Unknown') if accounts else 'Unknown'

    # Calculate time window — API expects full ISO format with tz offset
    start_time = (datetime.now(timezone.utc) - timedelta(days=days)).strftime(
        "%Y-%m-%dT%H:%M:%S.%f+00:00"
    )

    # Use the SDK's authenticated session directly to avoid the SDK's
    # silent error swallowing in __get_json pagination
    base_url = client.base_url
    url = f"{base_url}/alerts/"
    params = {
        'type': 'custom_alert',
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

    return {"account_name": account_name, "alerts": alerts, "days": days}


# --- FastAPI App ---

app = FastAPI(title="Custom Alert Dashboard")

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


@app.get("/api/alerts")
async def get_alerts(days: int = 30):
    """Return custom alerts as JSON.

    Query params:
        days: Number of days to look back (1-90, default 30)
    """
    days = min(max(1, days), 90)
    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _fetch_custom_alerts, days)
        return JSONResponse({
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "account_name": result["account_name"],
            "days": result["days"],
            "count": len(result["alerts"]),
            "data": result["alerts"],
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
    print("  Custom Alert Dashboard")
    print("=" * 60)
    print(f"  Server: http://localhost:{PORT}")
    print(f"  Press Ctrl+C to stop")
    print("=" * 60)

    uvicorn.run(app, host="0.0.0.0", port=PORT, log_level="info")
