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
import ssl
import sqlite3
import asyncio

from contextlib import contextmanager, asynccontextmanager
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

import ncm


# --- SSL verification state ---
# Persisted to a settings file so it survives server restarts
_SETTINGS_PATH = Path(__file__).parent / "settings.json"
_ssl_verify = True


def _load_settings():
    """Load persisted settings from disk."""
    global _ssl_verify
    if _SETTINGS_PATH.exists():
        try:
            settings = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
            _ssl_verify = settings.get("ssl_verify", True)
            if not _ssl_verify:
                import urllib3
                urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        except (json.JSONDecodeError, KeyError):
            pass


def _save_settings():
    """Persist settings to disk (preserves other settings keys)."""
    try:
        settings = {}
        if _SETTINGS_PATH.exists():
            try:
                settings = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, KeyError):
                pass
        settings["ssl_verify"] = _ssl_verify
        _SETTINGS_PATH.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    except Exception:
        pass


# Load settings on module import
_load_settings()

# --- Data Snapshot Cache ---
# Stores the last successful API response so page loads are instant
# Persisted to disk so it survives server restarts
_SNAPSHOT_PATH = Path(__file__).parent / "snapshot_cache.json"
_snapshot_cache = {
    "data": None,       # Full response dict (status, timestamp, account_name, count, data)
    "timestamp": None,  # When it was cached
}


def _load_snapshot_from_disk():
    """Load cached snapshot from disk on startup."""
    global _snapshot_cache
    if _SNAPSHOT_PATH.exists():
        try:
            cached = json.loads(_SNAPSHOT_PATH.read_text(encoding="utf-8"))
            if cached.get("data"):
                _snapshot_cache["data"] = cached["data"]
                _snapshot_cache["timestamp"] = cached.get("timestamp")
        except (json.JSONDecodeError, KeyError):
            pass  # Corrupt cache file — ignore


def _save_snapshot_to_disk():
    """Persist current snapshot to disk."""
    if _snapshot_cache["data"] is not None:
        try:
            _SNAPSHOT_PATH.write_text(
                json.dumps({"data": _snapshot_cache["data"], "timestamp": _snapshot_cache["timestamp"]}),
                encoding="utf-8"
            )
        except Exception:
            pass  # Non-critical — cache is best-effort


# Load cache from disk immediately on module import
_load_snapshot_from_disk()


# --- History Database ---
HISTORY_DIR = Path(__file__).parent / "history"

METRIC_FIELDS = ['health_score', 'dbm', 'rssi', 'rsrp', 'rsrq', 'sinr', 'rssnr', 'signal_strength', 'cinr', 'ecio']


def _get_history_db_path():
    """Get the history DB path for the current credential set.
    Uses a hash of the API ID to keep each account's history separate.
    Falls back to 'default' if no credentials are set.
    """
    import hashlib
    api_id = os.environ.get('X_CP_API_ID', '') or os.environ.get('X_ECM_API_ID', '')
    if api_id:
        key = hashlib.md5(api_id.encode()).hexdigest()[:12]
    else:
        key = 'default'
    HISTORY_DIR.mkdir(exist_ok=True)
    return HISTORY_DIR / f"history_{key}.db"


def _get_db():
    """Get a SQLite connection (creates DB and tables if needed)."""
    db_path = _get_history_db_path()
    db = sqlite3.connect(str(db_path), timeout=10)
    db.execute("PRAGMA journal_mode=WAL")
    db.execute("PRAGMA busy_timeout=5000")
    db.execute("""
        CREATE TABLE IF NOT EXISTS hourly_samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            router_id TEXT NOT NULL,
            router_name TEXT,
            interface_name TEXT,
            timestamp TEXT NOT NULL,
            health_score REAL,
            health_category TEXT,
            dbm REAL,
            rssi REAL,
            rsrp REAL,
            rsrq REAL,
            sinr REAL,
            rssnr REAL,
            signal_strength REAL,
            cinr REAL,
            ecio REAL
        )
    """)
    db.execute("""
        CREATE TABLE IF NOT EXISTS daily_samples (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            router_id TEXT NOT NULL,
            router_name TEXT,
            interface_name TEXT,
            date TEXT NOT NULL,
            sample_count INTEGER DEFAULT 0,
            health_score REAL,
            health_category TEXT,
            dbm REAL,
            rssi REAL,
            rsrp REAL,
            rsrq REAL,
            sinr REAL,
            rssnr REAL,
            signal_strength REAL,
            cinr REAL,
            ecio REAL
        )
    """)
    # Indexes for fast lookups
    db.execute("CREATE INDEX IF NOT EXISTS idx_hourly_router_ts ON hourly_samples(router_id, timestamp)")
    db.execute("CREATE INDEX IF NOT EXISTS idx_daily_router_date ON daily_samples(router_id, date)")
    db.commit()
    return db


def _record_hourly_samples(devices, timestamp=None):
    """Store current device metrics as recent samples.
    Records on every scheduled refresh — the 'recent' tab shows all samples from the last 24h.
    """
    if not devices:
        return
    now = timestamp or datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    db = _get_db()
    try:
        rows = []
        for d in devices:
            # Use router_id if available, fall back to router_name as key
            rid = d.get('router_id', '') or d.get('router_name', '')
            if not rid:
                continue
            rows.append((
                rid,
                d.get('router_name', ''),
                d.get('interface_name', ''),
                now,
                d.get('health_score'),
                d.get('health_category', ''),
                d.get('dbm'),
                d.get('rssi'),
                d.get('rsrp'),
                d.get('rsrq'),
                d.get('sinr'),
                d.get('rssnr'),
                d.get('signal_strength'),
                d.get('cinr'),
                d.get('ecio'),
            ))
        if rows:
            db.executemany(
                "INSERT INTO hourly_samples (router_id, router_name, interface_name, timestamp, "
                "health_score, health_category, dbm, rssi, rsrp, rsrq, sinr, rssnr, signal_strength, cinr, ecio) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                rows
            )
            db.commit()
            print(f"[History] Recorded {len(rows)} samples at {now}")

            # Prune samples older than 24h (keep recent tab manageable)
            cutoff = (datetime.now(timezone.utc) - timedelta(hours=24)).strftime('%Y-%m-%dT%H:%M:%SZ')
            db.execute("DELETE FROM hourly_samples WHERE timestamp < ?", (cutoff,))
            db.commit()
    except Exception as e:
        print(f"[History] ERROR recording samples: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
    finally:
        db.close()


def _rollup_daily_averages():
    """Roll up recent samples into daily averages for completed days."""
    db = _get_db()
    try:
        # Find completed days (yesterday and before) that haven't been rolled up
        today = datetime.now(timezone.utc).strftime('%Y-%m-%d')

        # Get distinct router_id + date combos for dates before today
        rows = db.execute(
            "SELECT DISTINCT router_id, substr(timestamp, 1, 10) as date FROM hourly_samples WHERE substr(timestamp, 1, 10) < ?",
            (today,)
        ).fetchall()

        if not rows:
            return

        for router_id, date in rows:
            # Check if daily already exists
            existing = db.execute(
                "SELECT id FROM daily_samples WHERE router_id = ? AND date = ?",
                (router_id, date)
            ).fetchone()

            # Calculate averages for this router+date
            avg_row = db.execute(
                """SELECT
                    COUNT(*) as cnt,
                    AVG(health_score), AVG(dbm), AVG(rssi), AVG(rsrp),
                    AVG(rsrq), AVG(sinr), AVG(rssnr), AVG(signal_strength),
                    AVG(cinr), AVG(ecio),
                    router_name, interface_name
                FROM hourly_samples
                WHERE router_id = ? AND substr(timestamp, 1, 10) = ?""",
                (router_id, date)
            ).fetchone()

            if not avg_row or avg_row[0] == 0:
                continue

            cnt = avg_row[0]
            avg_health = avg_row[1]
            avg_dbm = avg_row[2]
            avg_rssi = avg_row[3]
            avg_rsrp = avg_row[4]
            avg_rsrq = avg_row[5]
            avg_sinr = avg_row[6]
            avg_rssnr = avg_row[7]
            avg_signal = avg_row[8]
            avg_cinr = avg_row[9]
            avg_ecio = avg_row[10]
            rname = avg_row[11]
            iname = avg_row[12]

            # Determine health category from average score
            cat = ''
            if avg_health is not None:
                if avg_health >= 75:
                    cat = 'excellent'
                elif avg_health >= 50:
                    cat = 'good'
                elif avg_health >= 25:
                    cat = 'fair'
                else:
                    cat = 'poor'

            if existing:
                db.execute(
                    """UPDATE daily_samples SET
                        sample_count = ?, health_score = ?, health_category = ?,
                        dbm = ?, rssi = ?, rsrp = ?, rsrq = ?, sinr = ?,
                        rssnr = ?, signal_strength = ?, cinr = ?, ecio = ?,
                        router_name = ?, interface_name = ?
                    WHERE id = ?""",
                    (cnt, avg_health, cat, avg_dbm, avg_rssi, avg_rsrp, avg_rsrq,
                     avg_sinr, avg_rssnr, avg_signal, avg_cinr, avg_ecio,
                     rname, iname, existing[0])
                )
            else:
                db.execute(
                    """INSERT INTO daily_samples
                        (router_id, router_name, interface_name, date, sample_count,
                         health_score, health_category, dbm, rssi, rsrp, rsrq,
                         sinr, rssnr, signal_strength, cinr, ecio)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (router_id, rname, iname, date, cnt, avg_health, cat,
                     avg_dbm, avg_rssi, avg_rsrp, avg_rsrq, avg_sinr,
                     avg_rssnr, avg_signal, avg_cinr, avg_ecio)
                )

        # Delete hourly samples for completed days (already rolled up)
        db.execute("DELETE FROM hourly_samples WHERE substr(timestamp, 1, 10) < ?", (today,))
        db.commit()
    finally:
        db.close()


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

# --- Background History Collection Task ---
_history_task = None


async def _history_collector():
    """Background task: roll up daily averages once per hour."""
    while True:
        try:
            await asyncio.sleep(3600)
            try:
                _rollup_daily_averages()
            except Exception as e:
                print(f"[History] Error rolling up daily averages: {e}", file=sys.stderr)
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"[History] Background task error: {e}", file=sys.stderr)
            await asyncio.sleep(60)


@asynccontextmanager
async def lifespan(app):
    """Lifespan handler: start/stop background tasks."""
    global _history_task
    _history_task = asyncio.create_task(_history_collector())
    yield
    if _history_task:
        _history_task.cancel()


app = FastAPI(title="Cellular Health Dashboard", lifespan=lifespan)

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
async def get_health(refresh: bool = False, record: bool = False):
    """Return cellular health data as JSON.

    By default, serves cached snapshot instantly. Use ?refresh=true to force
    a fresh API pull (also updates the cache). Use ?record=true to also
    record a history sample (used by scheduled auto-refresh only).
    """
    global _snapshot_cache

    # Serve cached data if available and refresh not requested
    if not refresh and _snapshot_cache["data"] is not None:
        response = dict(_snapshot_cache["data"])
        response["cached"] = True
        response["cached_at"] = _snapshot_cache["timestamp"]
        return JSONResponse(response)

    try:
        # Capture request time BEFORE the slow API call for accurate history timestamps
        request_time = datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, _get_cellular_health)
        # Record history samples only on scheduled refreshes
        devices = result.get("devices", [])
        if devices and record:
            await loop.run_in_executor(None, _record_hourly_samples, devices, request_time)
            await loop.run_in_executor(None, _rollup_daily_averages)
        response_data = {
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "account_name": result["account_name"],
            "count": len(result["devices"]),
            "data": result["devices"],
        }
        # Update cache
        _snapshot_cache["data"] = response_data
        _snapshot_cache["timestamp"] = datetime.now(timezone.utc).isoformat()
        _save_snapshot_to_disk()
        return JSONResponse(response_data)
    except Exception as e:
        import traceback
        traceback.print_exc()
        # Detect SSL verification errors
        err_str = str(e)
        is_ssl_error = False
        cause = e.__cause__ or e.__context__
        while cause:
            if isinstance(cause, ssl.SSLCertVerificationError) or 'CERTIFICATE_VERIFY_FAILED' in str(cause):
                is_ssl_error = True
                break
            cause = getattr(cause, '__cause__', None) or getattr(cause, '__context__', None)
        if not is_ssl_error and 'CERTIFICATE_VERIFY_FAILED' in err_str:
            is_ssl_error = True
        if not is_ssl_error and 'SSL' in err_str.upper() and 'VERIFY' in err_str.upper():
            is_ssl_error = True

        if is_ssl_error:
            return JSONResponse(
                {"status": "error", "error_type": "ssl_error",
                 "message": "SSL certificate verification failed. This often happens behind a corporate proxy. "
                            "You can disable SSL verification for this session."},
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
    """Disable SSL certificate verification permanently (persisted to disk)."""
    global _ssl_verify
    _ssl_verify = False
    _save_settings()
    # Also suppress urllib3 InsecureRequestWarning
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    return JSONResponse({"status": "ok", "ssl_verify": False})


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


@app.get("/api/default-profile")
async def get_default_profile():
    """Get the default startup profile name."""
    settings = {}
    if _SETTINGS_PATH.exists():
        try:
            settings = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, KeyError):
            pass
    return JSONResponse({"default_profile": settings.get("default_profile", "")})


@app.post("/api/default-profile")
async def set_default_profile(request: Request):
    """Set the default startup profile name."""
    body = await request.json()
    name = body.get("name", "").strip()
    settings = {}
    if _SETTINGS_PATH.exists():
        try:
            settings = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, KeyError):
            pass
    settings["default_profile"] = name
    _SETTINGS_PATH.write_text(json.dumps(settings, indent=2), encoding="utf-8")
    return JSONResponse({"status": "ok", "default_profile": name})


# --- History API Endpoints ---

@app.get("/api/history/{router_id}")
async def get_history(router_id: str, tab: str = "hourly", days: int = 30, interface: str = ""):
    """Return historical data for a specific device.

    Query params:
        tab: "hourly" or "daily"
        days: number of days back for daily tab (default 30, max 730)
        interface: optional interface name filter
    """
    db = _get_db()
    try:
        if tab == "hourly":
            if interface:
                rows = db.execute(
                    """SELECT timestamp, health_score, health_category, dbm, rssi,
                              rsrp, rsrq, sinr, rssnr, signal_strength, cinr, ecio
                       FROM hourly_samples
                       WHERE router_id = ? AND interface_name = ?
                       ORDER BY timestamp ASC""",
                    (router_id, interface)
                ).fetchall()
            else:
                rows = db.execute(
                    """SELECT timestamp, health_score, health_category, dbm, rssi,
                              rsrp, rsrq, sinr, rssnr, signal_strength, cinr, ecio
                       FROM hourly_samples
                       WHERE router_id = ?
                       ORDER BY timestamp ASC""",
                    (router_id,)
                ).fetchall()
            data = []
            for r in rows:
                data.append({
                    "timestamp": r[0],
                    "health_score": r[1],
                    "health_category": r[2],
                    "dbm": r[3],
                    "rssi": r[4],
                    "rsrp": r[5],
                    "rsrq": r[6],
                    "sinr": r[7],
                    "rssnr": r[8],
                    "signal_strength": r[9],
                    "cinr": r[10],
                    "ecio": r[11],
                })
            return JSONResponse({"status": "ok", "tab": "hourly", "router_id": router_id, "data": data})

        elif tab == "daily":
            # Return daily averages for the requested range
            days = min(max(1, days), 730)
            start_date = (datetime.now(timezone.utc) - timedelta(days=days)).strftime('%Y-%m-%d')
            if interface:
                rows = db.execute(
                    """SELECT date, sample_count, health_score, health_category, dbm, rssi,
                              rsrp, rsrq, sinr, rssnr, signal_strength, cinr, ecio
                       FROM daily_samples
                       WHERE router_id = ? AND interface_name = ? AND date >= ?
                       ORDER BY date ASC""",
                    (router_id, interface, start_date)
                ).fetchall()
            else:
                rows = db.execute(
                    """SELECT date, sample_count, health_score, health_category, dbm, rssi,
                              rsrp, rsrq, sinr, rssnr, signal_strength, cinr, ecio
                       FROM daily_samples
                       WHERE router_id = ? AND date >= ?
                       ORDER BY date ASC""",
                    (router_id, start_date)
                ).fetchall()
            data = []
            for r in rows:
                data.append({
                    "date": r[0],
                    "sample_count": r[1],
                    "health_score": r[2],
                    "health_category": r[3],
                    "dbm": r[4],
                    "rssi": r[5],
                    "rsrp": r[6],
                    "rsrq": r[7],
                    "sinr": r[8],
                    "rssnr": r[9],
                    "signal_strength": r[10],
                    "cinr": r[11],
                    "ecio": r[12],
                })
            return JSONResponse({"status": "ok", "tab": "daily", "router_id": router_id, "days": days, "data": data})

        else:
            return JSONResponse({"error": "tab must be 'hourly' or 'daily'"}, status_code=400)
    finally:
        db.close()


@app.get("/api/history-status")
async def history_status():
    """Return history collection status: how many samples are stored."""
    db = _get_db()
    try:
        hourly_count = db.execute("SELECT COUNT(*) FROM hourly_samples").fetchone()[0]
        daily_count = db.execute("SELECT COUNT(*) FROM daily_samples").fetchone()[0]
        hourly_devices = db.execute("SELECT COUNT(DISTINCT router_id) FROM hourly_samples").fetchone()[0]
        daily_devices = db.execute("SELECT COUNT(DISTINCT router_id) FROM daily_samples").fetchone()[0]
        oldest_daily = db.execute("SELECT MIN(date) FROM daily_samples").fetchone()[0]
        return JSONResponse({
            "status": "ok",
            "hourly_samples": hourly_count,
            "hourly_devices": hourly_devices,
            "daily_samples": daily_count,
            "daily_devices": daily_devices,
            "oldest_daily": oldest_daily,
        })
    finally:
        db.close()


@app.post("/api/history-clear")
async def clear_history():
    """Delete all history data (both recent and daily samples)."""
    db = _get_db()
    try:
        db.execute("DELETE FROM hourly_samples")
        db.execute("DELETE FROM daily_samples")
        db.commit()
        return JSONResponse({"status": "ok", "message": "All history data cleared"})
    finally:
        db.close()


# --- Runtime mode flags (set by argparse at startup) ---
_readonly_mode = False


@app.get("/api/config")
async def get_config():
    """Return runtime config flags for the frontend."""
    return JSONResponse({
        "readonly": _readonly_mode,
    })


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Cellular Health Dashboard")
    parser.add_argument("-ro", "--readonly", action="store_true",
                        help="Read-only mode: hide Settings panel, use env vars or saved profile")
    parser.add_argument("-p", "--profile", type=str, default=None,
                        help="Profile name to load on startup (also sets default for -ro mode)")
    args = parser.parse_args()

    _readonly_mode = args.readonly

    # Load specified profile (or first available) into env
    if args.profile:
        profiles = _load_profiles()
        if args.profile in profiles:
            for key, val in profiles[args.profile].items():
                if val:
                    os.environ[key] = val
            print(f"Loaded profile: {args.profile}")
        else:
            print(f"WARNING: Profile '{args.profile}' not found. Available: {', '.join(profiles.keys()) or '(none)'}", file=sys.stderr)
    elif _readonly_mode:
        # Read-only mode credential resolution order:
        # 1. If only one profile exists, use it
        # 2. If multiple profiles exist, use the ★ default (error if not set)
        # 3. If no profiles exist, try environment variables
        profiles = _load_profiles()
        profile_names = sorted(profiles.keys())

        if len(profile_names) == 1:
            name = profile_names[0]
            for key, val in profiles[name].items():
                if val:
                    os.environ[key] = val
            print(f"Read-only mode: loaded only profile '{name}'")
        elif len(profile_names) > 1:
            default_name = None
            if _SETTINGS_PATH.exists():
                try:
                    settings = json.loads(_SETTINGS_PATH.read_text(encoding="utf-8"))
                    default_name = settings.get("default_profile", "")
                except (json.JSONDecodeError, KeyError):
                    pass
            if default_name and default_name in profiles:
                for key, val in profiles[default_name].items():
                    if val:
                        os.environ[key] = val
                print(f"Read-only mode: loaded default profile '{default_name}'")
            else:
                print(f"ERROR: Multiple profiles exist but no default (★) is set.", file=sys.stderr)
                print(f"Available profiles: {', '.join(profile_names)}", file=sys.stderr)
                print("Run without -ro and click ★ Default on a profile, then restart.", file=sys.stderr)
                raise SystemExit(1)
        else:
            # No profiles — try env vars
            try:
                check_env()
                print("Read-only mode: using environment variables")
            except SystemExit:
                print("ERROR: No profiles saved and no environment variables set.", file=sys.stderr)
                print("Run without -ro to configure credentials first.", file=sys.stderr)
                raise SystemExit(1)
    else:
        # Normal mode — just warn if creds missing
        try:
            check_env()
        except SystemExit:
            print("WARNING: API credentials not set. Use the Settings panel (gear icon) "
                  "to configure credentials, or set environment variables.")

    mode_str = " (read-only)" if _readonly_mode else ""
    print(f"Cellular Health Dashboard starting{mode_str}...")
    print("Open http://localhost:8055 in your browser")
    uvicorn.run(app, host="0.0.0.0", port=8055, log_level="info")
