"""
Cellular Health Dashboard — shows cellular health metrics for all devices
in a sub-account.

Usage:
    .venv/bin/python scripts/cellular_health_dashboard/serve.py

Then open http://localhost:8055 in your browser.
"""

import os
import sys
import json

from datetime import datetime, timezone
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

import ncm


# --- Credential helpers (replaces scripts.utils.env_check dependency) ---

_REQUIRED_KEYS = [
    ("X_CP_API_ID", "Cradlepoint API ID"),
    ("X_CP_API_KEY", "Cradlepoint API Key"),
    ("X_ECM_API_ID", "ECM API ID"),
    ("X_ECM_API_KEY", "ECM API Key"),
]


def check_env():
    """Check that required v2 API environment variables are set."""
    missing = [(k, d) for k, d in _REQUIRED_KEYS if not os.environ.get(k)]
    if missing:
        names = ", ".join(k for k, _ in missing)
        print(f"WARNING: Missing environment variables: {names}", file=sys.stderr)
        print("Use the Settings panel (gear icon) to configure credentials.", file=sys.stderr)
        raise SystemExit(1)


def get_api_keys_from_env() -> dict:
    """Build an API keys dict from environment variables (NCM SDK format)."""
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

app = FastAPI(title="Cellular Health Dashboard")

# Serve logos from the shared static folder
STATIC_DIR = Path(__file__).resolve().parent.parent / "script_manager" / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Profiles storage
PROFILES_PATH = Path(__file__).parent / "profiles.json"


def _load_profiles():
    """Load saved credential profiles."""
    if PROFILES_PATH.exists():
        return json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
    return {}


def _save_profiles(profiles):
    """Save credential profiles to disk."""
    PROFILES_PATH.write_text(json.dumps(profiles, indent=2), encoding="utf-8")


def _build_client():
    """Create an NCM SDK client from environment variables."""
    api_keys = get_api_keys_from_env()
    if not api_keys.get('X-CP-API-ID') or not api_keys.get('X-ECM-API-ID'):
        raise RuntimeError(
            "Missing required API credentials. Use the Settings panel (gear icon) "
            "to configure credentials, or set X_CP_API_ID, X_CP_API_KEY, "
            "X_ECM_API_ID, X_ECM_API_KEY environment variables."
        )
    return ncm.NcmClient(api_keys=api_keys)


def _extract_id_from_url(url):
    """Extract numeric ID from a v2 API resource URL or bare ID string."""
    if not url:
        return None
    if isinstance(url, (int, float)):
        return int(url)
    url = str(url)
    if '/' in url:
        parts = url.rstrip('/').split('/')
        try:
            return int(parts[-1])
        except (ValueError, IndexError):
            return None
    try:
        return int(url)
    except ValueError:
        return None


def _get_cellular_health():
    """Fetch cellular health data for all devices.

    Flow:
    1. Get net_device_health records (health score + net_device ref)
    2. Get net_device_metrics for those IDs (signal data: RSRP, SINR, dBm, etc.)
    3. Get net_devices with expand=router (carrier, model, inline router object)
    4. Get groups for group name lookup (router.group is a URL, not expanded)
    5. Join everything by net_device ID (string)
    """
    client = _build_client()

    # Get account name
    accounts = client.get_accounts()
    account_name = accounts[0].get('name', 'Unknown Account') if accounts else 'Unknown Account'

    # Step 1: Get net_device_health records
    health_data = client.get_net_device_health()
    if not health_data:
        return {"account_name": account_name, "devices": []}

    # Extract net_device IDs from health records (as strings)
    health_by_nd = {}
    nd_ids = []
    for h in health_data:
        nd_id = _extract_id_from_url(h.get('net_device'))
        if nd_id is not None:
            nd_id_str = str(nd_id)
            health_by_nd[nd_id_str] = h
            nd_ids.append(nd_id_str)

    # Step 2: Fetch net_device_metrics for signal data (chunked to 100)
    metrics_by_nd = {}
    for i in range(0, len(nd_ids), 100):
        chunk = nd_ids[i:i+100]
        id_str = ','.join(chunk)
        metrics = client.get_net_device_metrics(net_device__in=id_str)
        for m in metrics:
            m_nd_id = _extract_id_from_url(m.get('net_device'))
            if m_nd_id is not None:
                metrics_by_nd[str(m_nd_id)] = m

    # Step 3: Fetch net_devices with expand=router (chunked to 100)
    nd_lookup = {}
    for i in range(0, len(nd_ids), 100):
        chunk = nd_ids[i:i+100]
        id_str = ','.join(chunk)
        devices = client.get_net_devices(id__in=id_str, expand='router')
        for nd in devices:
            nd_lookup[str(nd.get('id', ''))] = nd

    # Step 4: Combine everything
    results = []
    for nd_id_str, h in health_by_nd.items():
        nd = nd_lookup.get(nd_id_str, {})
        metrics = metrics_by_nd.get(nd_id_str, {})
        router = nd.get('router') if isinstance(nd.get('router'), dict) else {}

        # Device name: prefer router name, fall back to hostname or net_device name
        device_name = ''
        router_id = ''
        if router:
            device_name = router.get('name', '')
            router_id = str(router.get('id', ''))
        if not device_name:
            device_name = nd.get('hostname') or nd.get('name') or 'Unknown'

        results.append({
            'router_name': device_name,
            'router_id': router_id,
            'router_state': router.get('state', '') if router else nd.get('connection_state', 'unknown'),
            'model': nd.get('model', ''),
            'mac': router.get('mac', '') if router else '',
            'interface_name': nd.get('name', ''),
            'carrier': nd.get('carrier', ''),
            'connection_state': nd.get('connection_state', ''),
            'service_type': metrics.get('service_type', nd.get('service_type', '')),
            # Health score
            'health_category': h.get('cellular_health_category', ''),
            'health_score': h.get('cellular_health_score'),
            # Signal metrics from net_device_metrics
            'dbm': metrics.get('dbm'),
            'rssi': metrics.get('rssi'),
            'rsrp': metrics.get('rsrp'),
            'rsrq': metrics.get('rsrq'),
            'sinr': metrics.get('sinr'),
            'rssnr': metrics.get('rssnr'),
            'signal_strength': metrics.get('signal_strength'),
            'cinr': metrics.get('cinr'),
            'ecio': metrics.get('ecio'),
            'updated_at': metrics.get('update_ts') or nd.get('updated_at', ''),
        })

    # Sort by router name to group net_devices belonging to the same router
    results.sort(key=lambda r: (r.get('router_name', '').lower(), r.get('interface_name', '')))

    return {"account_name": account_name, "devices": results}


@app.get("/", response_class=HTMLResponse)
async def index():
    """Serve the dashboard HTML."""
    html_path = Path(__file__).parent / "index.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.get("/api/health")
async def get_health():
    """Return cellular health data as JSON."""
    try:
        result = _get_cellular_health()
        return JSONResponse({
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "account_name": result["account_name"],
            "count": len(result["devices"]),
            "data": result["devices"],
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=500,
        )


@app.get("/api/status")
async def status():
    """Quick health check."""
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}


@app.get("/api/debug")
async def debug():
    """Return raw samples from each endpoint for debugging joins."""
    try:
        client = _build_client()

        # Sample health record
        health = client.get_net_device_health()
        health_sample = health[:2] if health else []

        # Get net_device IDs from health
        nd_ids = []
        for h in health_sample:
            nd_id = _extract_id_from_url(h.get('net_device'))
            if nd_id:
                nd_ids.append(str(nd_id))

        # Fetch those net_devices with expand=router
        nd_sample = []
        if nd_ids:
            id_str = ','.join(nd_ids)
            nd_sample = client.get_net_devices(id__in=id_str, expand='router')

        # Fetch metrics for those net_devices
        metrics_sample = []
        if nd_ids:
            id_str = ','.join(nd_ids)
            metrics_sample = client.get_net_device_metrics(net_device__in=id_str)

        return JSONResponse({
            "health_count": len(health),
            "health_sample": health_sample,
            "net_device_sample": nd_sample,
            "metrics_sample": metrics_sample,
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": str(e)}, status_code=500)


# --- Profile Management Endpoints ---

@app.get("/api/profiles")
async def list_profiles():
    """List all saved credential profiles."""
    profiles = _load_profiles()
    # Return profile names and masked keys (don't expose full secrets)
    result = {}
    for name, creds in profiles.items():
        result[name] = {k: v[:4] + "…" if v and len(v) > 4 else "" for k, v in creds.items()}
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
        return JSONResponse({"error": "exists", "message": f"Profile '{name}' already exists"}, status_code=409)

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
    """Return current active credentials (actual values for local use).
    Checks both X_ prefixed names and legacy non-prefixed names.
    """
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
    """Apply credentials to the running environment (without saving to a profile)."""
    body = await request.json()
    creds = body.get("credentials", {})
    for key in ["X_CP_API_ID", "X_CP_API_KEY", "X_ECM_API_ID", "X_ECM_API_KEY"]:
        val = creds.get(key, "").strip()
        if val:
            os.environ[key] = val
    return JSONResponse({"status": "ok"})


if __name__ == "__main__":
    # Don't block startup if credentials aren't set — user can configure via Settings panel
    try:
        check_env()
    except SystemExit:
        print("WARNING: API credentials not set. Use the Settings panel (gear icon) "
              "to configure credentials, or set environment variables.")
    print("Cellular Health Dashboard starting...")
    print("Open http://localhost:8055 in your browser")
    uvicorn.run(app, host="0.0.0.0", port=8055, log_level="info")
