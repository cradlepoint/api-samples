"""
Inventory Dashboard — NCM device inventory with license status.

Uses the installed NCM SDK (`pip install ncm`) for v2 API calls and
httpx for v3 API calls. No external inventory_sdk package required.

Usage:
    .venv/bin/python web_apps/inventory_dashboard/serve.py

Then open http://localhost:8060 in your browser.
"""

import os
import sys
import json
import logging
import asyncio
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import httpx
from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

import ncm

# Add this directory to path for local subscription_types module
sys.path.insert(0, os.path.dirname(__file__))
from subscription_types import resolve_subscription_type, EXCLUDED_SUBSCRIPTIONS, is_pool_subscription

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("inventory_dashboard")

app = FastAPI(title="Inventory Dashboard")

# Serve logos from the shared static folder
STATIC_DIR = Path(__file__).resolve().parent.parent / "script_manager" / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

PROFILES_PATH = Path(__file__).parent / "profiles.json"
SNAPSHOT_PATH = Path(__file__).parent / "inventory_snapshot.json"

# --- v3 API constants ---
_V3_BASE_URL = "https://api.cradlepointecm.com/api/v3"
_V3_PAGE_SIZE = 50
_RETRYABLE_STATUSES = {429, 409, 500, 502, 503, 504}


# --- Credential helpers ---

def _get_credentials() -> dict:
    """Get API credentials from environment."""
    cp_api_id = os.environ.get("X_CP_API_ID") or os.environ.get("CP_API_ID", "")
    cp_api_key = os.environ.get("X_CP_API_KEY") or os.environ.get("CP_API_KEY", "")
    ecm_api_id = os.environ.get("X_ECM_API_ID") or os.environ.get("ECM_API_ID", "")
    ecm_api_key = os.environ.get("X_ECM_API_KEY") or os.environ.get("ECM_API_KEY", "")
    v3_token = os.environ.get("NCM_API_TOKEN", "")

    if not all([cp_api_id, cp_api_key, ecm_api_id, ecm_api_key]):
        raise RuntimeError(
            "Missing required API credentials. Use the Settings panel (gear icon) "
            "to configure credentials, or set X_CP_API_ID, X_CP_API_KEY, "
            "X_ECM_API_ID, X_ECM_API_KEY environment variables."
        )
    return {
        "cp_api_id": cp_api_id,
        "cp_api_key": cp_api_key,
        "ecm_api_id": ecm_api_id,
        "ecm_api_key": ecm_api_key,
        "v3_token": v3_token,
    }


def _build_ncm_client(creds: dict) -> ncm.NcmClient:
    """Build an NCM SDK client from credentials dict."""
    api_keys = {
        'X-CP-API-ID': creds["cp_api_id"],
        'X-CP-API-KEY': creds["cp_api_key"],
        'X-ECM-API-ID': creds["ecm_api_id"],
        'X-ECM-API-KEY': creds["ecm_api_key"],
    }
    if creds.get("v3_token"):
        api_keys['token'] = creds["v3_token"]
    return ncm.NcmClient(api_keys=api_keys)


# --- v3 pagination helper ---

def _get_all_v3(path: str, token: str, params: dict | None = None) -> list[dict]:
    """Fetch all pages from a v3 cursor-paginated endpoint."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.api+json",
    }
    params = params or {}
    params.setdefault("page[size]", _V3_PAGE_SIZE)
    results = []
    url = f"{_V3_BASE_URL}{path}"

    with httpx.Client(timeout=30.0) as client:
        while url:
            for attempt in range(5):
                resp = client.get(url, headers=headers, params=params)
                if resp.status_code not in _RETRYABLE_STATUSES:
                    break
                wait = float(resp.headers.get("Retry-After", 2 ** attempt))
                log.warning("v3 rate limited (%d), retry in %.1fs", resp.status_code, wait)
                time.sleep(wait)
            resp.raise_for_status()
            body = resp.json()

            for item in body.get("data", []):
                attrs = item.get("attributes", {})
                record = {"id": item.get("id"), **attrs}
                # Extract relationship IDs
                rels = item.get("relationships", {})
                if "subscriptions" in rels:
                    sub_data = rels["subscriptions"].get("data", [])
                    if isinstance(sub_data, list):
                        record["subscription_ids"] = [s.get("id") for s in sub_data if s.get("id")]
                    elif isinstance(sub_data, dict) and sub_data.get("id"):
                        record["subscription_ids"] = [sub_data["id"]]
                results.append(record)

            url = body.get("links", {}).get("next")
            params = None  # params baked into cursor URL

    return results


# --- Snapshot helpers ---

def _load_snapshot() -> dict[str, dict]:
    """Load previous snapshot keyed by normalized MAC."""
    if not SNAPSHOT_PATH.exists():
        return {}
    try:
        raw = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
        return {e.get("_mac_key", ""): e for e in raw if e.get("_mac_key")}
    except (json.JSONDecodeError, KeyError):
        return {}


def _save_snapshot(devices: list[dict]) -> None:
    """Save device state snapshot."""
    records = []
    for d in devices:
        mac_key = (d.get("mac") or "").upper().replace(":", "").replace("-", "")
        records.append({**d, "_mac_key": mac_key})
    SNAPSHOT_PATH.write_text(json.dumps(records, indent=2, default=str), encoding="utf-8")


_RESTORABLE_FIELDS = [
    "router_id", "router_name", "account", "group", "device_type", "product",
    "state", "config_status", "ip_address", "locality", "firmware", "target_firmware",
    "description", "custom1", "custom2", "imei", "iccid", "carrier", "modem_model",
    "modem_fw", "connection_state", "service_type",
]


def _enrich_from_snapshot(devices: list[dict], previous: dict[str, dict]) -> list[dict]:
    """Restore missing fields from snapshot and detect license state changes."""
    now = datetime.now(timezone.utc).isoformat()
    enriched = []
    for d in devices:
        mac_key = (d.get("mac") or "").upper().replace(":", "").replace("-", "")
        prev = previous.get(mac_key)

        # Restore missing fields from snapshot (for unlicensed devices that lost v2 data)
        if not d.get("router_id") and prev:
            for field in _RESTORABLE_FIELDS:
                if not d.get(field) and prev.get(field):
                    d[field] = prev[field]

        # License state change tracking
        if prev:
            if d.get("license_state") != prev.get("license_state"):
                d["license_state_date"] = now
                d["previous_license_state"] = prev.get("license_state", "")
            else:
                d["license_state_date"] = prev.get("license_state_date", "")
                d["previous_license_state"] = prev.get("previous_license_state", "")
        else:
            d["license_state_date"] = now

        enriched.append(d)
    return enriched


# --- Data formatting ---

def _fmt_date(dt) -> str:
    """Format a datetime string or object as YYYY-MM-DD."""
    if dt is None:
        return ""
    if isinstance(dt, str):
        return dt[:10] if len(dt) >= 10 else dt
    if isinstance(dt, datetime):
        return dt.strftime("%Y-%m-%d")
    return str(dt)


def _normalize_mac(mac: str) -> str:
    """Normalize a MAC to bare uppercase hex."""
    return (mac or "").upper().replace(":", "").replace("-", "").replace(".", "")


def _display_mac(mac_raw: str) -> str:
    """Format a MAC as AA:BB:CC:DD:EE:FF."""
    clean = _normalize_mac(mac_raw)
    if len(clean) == 12:
        return ":".join(clean[i:i+2] for i in range(0, 12, 2))
    return mac_raw or ""


def _extract_id_from_url(url: str | None) -> str:
    """Extract the numeric ID from an NCM v2 resource URL."""
    if not url:
        return ""
    return str(url).rstrip("/").split("/")[-1]


# --- Main data fetch and join ---

def _get_inventory_data(progress_callback=None) -> dict:
    """Fetch all inventory data using NCM SDK (v2) + httpx (v3), join, and return."""
    cb = progress_callback or (lambda step, detail: None)
    t0 = time.time()

    creds = _get_credentials()
    client = _build_ncm_client(creds)
    v3_token = creds.get("v3_token", "")

    # Step 1: Get account name
    accounts = client.get_accounts()
    account_name = accounts[0].get("name", "Unknown") if accounts else "Unknown"

    # Step 2: Fetch v2 data using NCM SDK (handles pagination)
    cb(0, "Fetching routers (v2)...")
    routers = client.get_routers()
    log.info("Fetched %d routers (%.1fs)", len(routers), time.time() - t0)
    cb(2, f"{len(routers)} routers fetched")

    cb(0, "Fetching net devices (v2)...")
    net_devices = client.get_net_devices(is_asset="true")
    log.info("Fetched %d net_devices (%.1fs)", len(net_devices), time.time() - t0)
    cb(3, f"{len(net_devices)} net devices fetched")

    cb(0, "Fetching groups & accounts (v2)...")
    groups = client.get_groups()
    log.info("Fetched %d groups (%.1fs)", len(groups), time.time() - t0)
    cb(4, f"{len(groups)} groups fetched")

    # Step 3: Fetch v3 data if token available
    assets = []
    subs = []
    if v3_token:
        cb(0, "Fetching asset endpoints (v3)...")
        assets = _get_all_v3("/asset_endpoints", v3_token)
        log.info("Fetched %d asset_endpoints (%.1fs)", len(assets), time.time() - t0)
        cb(0, f"{len(assets)} asset endpoints fetched")

        cb(0, "Fetching subscriptions (v3)...")
        subs = _get_all_v3("/subscriptions", v3_token)
        log.info("Fetched %d subscriptions (%.1fs)", len(subs), time.time() - t0)
        cb(1, f"{len(subs)} subscriptions fetched")

        # Resolve assignment-level subscription IDs
        all_sub_ids = set()
        for a in assets:
            for sid in a.get("subscription_ids", []):
                if sid:
                    all_sub_ids.add(sid)

        # Batch-fetch assignment subscriptions (50 per request)
        id_list = list(all_sub_ids)
        for i in range(0, len(id_list), 50):
            batch = ",".join(id_list[i:i+50])
            extra = _get_all_v3("/subscriptions", v3_token, {"filter[id]": batch})
            subs.extend(extra)
        log.info("Resolved %d assignment subscriptions (%.1fs)", len(subs), time.time() - t0)

    cb(5, "Joining data...")

    # --- Build lookup dicts ---
    sub_by_id = {s["id"]: s for s in subs}

    router_by_mac = {}
    for r in routers:
        mac = _normalize_mac(r.get("mac", ""))
        if mac:
            router_by_mac[mac] = r

    modem_by_router_url = {}
    for nd in net_devices:
        router_url = nd.get("router", "")
        if router_url and router_url not in modem_by_router_url:
            modem_by_router_url[router_url] = nd

    group_by_url = {}
    for g in groups:
        url = g.get("resource_url", "")
        if url:
            group_by_url[url] = g

    account_by_url = {}
    for a in accounts:
        url = a.get("resource_url", "")
        if url:
            account_by_url[url] = a

    # --- Join: asset_endpoints as primary, left-join v2 ---
    seen_macs = set()
    devices = []

    def _license_state(base_sub, has_router):
        if base_sub is None:
            return False, "unlicensed"
        if base_sub.get("name") == "NON-COMPLIANT":
            return False, "grace-period" if has_router else "unlicensed"
        return True, "licensed"

    for asset in assets:
        mac_norm = _normalize_mac(asset.get("mac_address", ""))
        seen_macs.add(mac_norm)

        router = router_by_mac.get(mac_norm)
        modem = modem_by_router_url.get(router.get("resource_url", "")) if router else None
        grp = group_by_url.get(router.get("group", "")) if router else None
        acct = account_by_url.get(router.get("account", "")) if router else None

        # Resolve subscriptions
        sub_ids = asset.get("subscription_ids", [])
        matched = [sub_by_id[sid] for sid in sub_ids if sid in sub_by_id]
        base = matched[0] if matched else None
        addons = [
            {"type": resolve_subscription_type(s.get("name")) or s.get("name", ""), "end": _fmt_date(s.get("end_time"))}
            for s in matched[1:]
        ]

        is_licensed, license_state = _license_state(base, router is not None)
        show_sub = is_licensed or license_state == "grace-period"

        devices.append({
            "router_id": router.get("id", "") if router else "",
            "router_name": router.get("name", "") if router else "",
            "account": acct.get("name", "") if acct else "",
            "group": grp.get("name", "") if grp else "",
            "mac": _display_mac(router.get("mac", "") if router else asset.get("mac_address", "")),
            "serial_number": asset.get("serial_number", ""),
            "hardware_series": asset.get("hardware_series", ""),
            "product": router.get("full_product_name", "") if router else "",
            "device_type": router.get("device_type", "") if router else "",
            "state": router.get("state", "") if router else "",
            "created_at": _fmt_date(router.get("created_at")) if router else "",
            "updated_at": _fmt_date(router.get("updated_at")) if router else "",
            "config_status": router.get("config_status", "") if router else "",
            "ip_address": router.get("ipv4_address", "") if router else "",
            "locality": router.get("locality", "") if router else "",
            "firmware": router.get("actual_firmware", "") if router else "",
            "target_firmware": router.get("target_firmware", "") if router else "",
            "upgrade_pending": router.get("upgrade_pending", False) if router else False,
            "reboot_required": router.get("reboot_required", False) if router else False,
            "imei": modem.get("imei", "") if modem else "",
            "iccid": modem.get("iccid", "") if modem else "",
            "imsi": modem.get("imsi", "") if modem else "",
            "mdn": modem.get("mdn", "") if modem else "",
            "meid": modem.get("meid", "") if modem else "",
            "carrier": modem.get("carrier", "") if modem else "",
            "carrier_id": modem.get("carrier_id", "") if modem else "",
            "modem_name": modem.get("name", "") if modem else "",
            "modem_fw": modem.get("modem_fw", "") if modem else "",
            "modem_model": modem.get("mfg_model", "") if modem else "",
            "modem_product": modem.get("mfg_product", "") if modem else "",
            "connection_state": modem.get("connection_state", "") if modem else "",
            "service_type": modem.get("service_type", "") if modem else "",
            "rfband": modem.get("rfband", "") if modem else "",
            "ltebandwidth": modem.get("ltebandwidth", "") if modem else "",
            "homecarrid": modem.get("homecarrid", "") if modem else "",
            "description": router.get("description", "") if router else "",
            "custom1": router.get("custom1", "") if router else "",
            "custom2": router.get("custom2", "") if router else "",
            "is_licensed": is_licensed,
            "license_state": license_state,
            "license_state_date": "",
            "previous_license_state": "",
            "state_updated_at": _fmt_date(router.get("state_updated_at")) if router else "",
            "subscription_type": resolve_subscription_type(base.get("name")) if base and show_sub else "",
            "subscription_start": _fmt_date(base.get("start_time")) if base and show_sub else "",
            "subscription_end": _fmt_date(base.get("end_time")) if base and show_sub else "",
            "add_ons": addons if show_sub else [],
        })

    # Include v2-only routers not in v3
    for r in routers:
        mac_norm = _normalize_mac(r.get("mac", ""))
        if mac_norm and mac_norm in seen_macs:
            continue
        modem = modem_by_router_url.get(r.get("resource_url", ""))
        grp = group_by_url.get(r.get("group", ""))
        acct = account_by_url.get(r.get("account", ""))
        devices.append({
            "router_id": r.get("id", ""),
            "router_name": r.get("name", ""),
            "account": acct.get("name", "") if acct else "",
            "group": grp.get("name", "") if grp else "",
            "mac": _display_mac(r.get("mac", "")),
            "serial_number": r.get("serial_number", ""),
            "hardware_series": "",
            "product": r.get("full_product_name", ""),
            "device_type": r.get("device_type", ""),
            "state": r.get("state", ""),
            "created_at": _fmt_date(r.get("created_at")),
            "updated_at": _fmt_date(r.get("updated_at")),
            "config_status": r.get("config_status", ""),
            "ip_address": r.get("ipv4_address", ""),
            "locality": r.get("locality", ""),
            "firmware": r.get("actual_firmware", ""),
            "target_firmware": r.get("target_firmware", ""),
            "upgrade_pending": r.get("upgrade_pending", False),
            "reboot_required": r.get("reboot_required", False),
            "imei": modem.get("imei", "") if modem else "",
            "iccid": modem.get("iccid", "") if modem else "",
            "imsi": modem.get("imsi", "") if modem else "",
            "mdn": modem.get("mdn", "") if modem else "",
            "meid": modem.get("meid", "") if modem else "",
            "carrier": modem.get("carrier", "") if modem else "",
            "carrier_id": modem.get("carrier_id", "") if modem else "",
            "modem_name": modem.get("name", "") if modem else "",
            "modem_fw": modem.get("modem_fw", "") if modem else "",
            "modem_model": modem.get("mfg_model", "") if modem else "",
            "modem_product": modem.get("mfg_product", "") if modem else "",
            "connection_state": modem.get("connection_state", "") if modem else "",
            "service_type": modem.get("service_type", "") if modem else "",
            "rfband": modem.get("rfband", "") if modem else "",
            "ltebandwidth": modem.get("ltebandwidth", "") if modem else "",
            "homecarrid": modem.get("homecarrid", "") if modem else "",
            "description": r.get("description", ""),
            "custom1": r.get("custom1", ""),
            "custom2": r.get("custom2", ""),
            "is_licensed": False,
            "license_state": "unlicensed",
            "license_state_date": "",
            "previous_license_state": "",
            "state_updated_at": _fmt_date(r.get("state_updated_at")),
            "subscription_type": "",
            "subscription_start": "",
            "subscription_end": "",
            "add_ons": [],
        })

    # Enrich from snapshot
    previous = _load_snapshot()
    devices = _enrich_from_snapshot(devices, previous)
    _save_snapshot(devices)

    # Build software license summary
    sub_assigned_count: dict[str, int] = {}
    for asset in assets:
        for sid in asset.get("subscription_ids", []):
            if sid:
                sub_assigned_count[sid] = sub_assigned_count.get(sid, 0) + 1

    licenses = []
    seen_sub_ids = set()
    for s in subs:
        if s["id"] in seen_sub_ids:
            continue
        seen_sub_ids.add(s["id"])
        if s.get("name") in EXCLUDED_SUBSCRIPTIONS:
            continue
        pool = is_pool_subscription(s.get("name"))
        licenses.append({
            "subscription_type": resolve_subscription_type(s.get("name")) or s.get("name", ""),
            "quantity": s.get("quantity"),
            "assigned": -1 if pool else sub_assigned_count.get(s["id"], 0),
            "start": _fmt_date(s.get("start_time")),
            "end": _fmt_date(s.get("end_time")),
        })

    log.info("Inventory complete: %d devices, %d licenses (%.1fs)", len(devices), len(licenses), time.time() - t0)

    return {
        "account_name": account_name,
        "devices": devices,
        "licenses": licenses,
    }


# --- Profile helpers ---

def _load_profiles() -> dict:
    if PROFILES_PATH.exists():
        try:
            return json.loads(PROFILES_PATH.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return {}
    return {}


def _save_profiles(profiles: dict) -> None:
    PROFILES_PATH.write_text(json.dumps(profiles, indent=2), encoding="utf-8")


# --- Routes ---

@app.get("/", response_class=HTMLResponse)
async def index():
    html_path = Path(__file__).parent / "index.html"
    return HTMLResponse(html_path.read_text(encoding="utf-8"))


@app.get("/api/data")
async def get_data():
    try:
        result = _get_inventory_data()
        return JSONResponse({
            "status": "ok",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "account_name": result["account_name"],
            "device_count": len(result["devices"]),
            "data": result["devices"],
            "licenses": result["licenses"],
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)


@app.get("/api/data/stream")
async def get_data_stream():
    """Stream inventory data via SSE with progress updates."""
    progress_queue: asyncio.Queue = asyncio.Queue()

    def on_progress(step: int, detail: str):
        progress_queue.put_nowait((step, detail))

    async def event_generator():
        yield f"event: progress\ndata: {json.dumps({'step': 0, 'message': 'Starting data fetch...'})}\n\n"

        loop = asyncio.get_event_loop()
        task = loop.run_in_executor(None, lambda: _get_inventory_data(progress_callback=on_progress))

        while not task.done():
            try:
                step, detail = await asyncio.wait_for(progress_queue.get(), timeout=0.2)
                yield f"event: progress\ndata: {json.dumps({'step': step, 'message': detail})}\n\n"
            except asyncio.TimeoutError:
                pass

        while not progress_queue.empty():
            step, detail = progress_queue.get_nowait()
            yield f"event: progress\ndata: {json.dumps({'step': step, 'message': detail})}\n\n"

        try:
            result = task.result()
            payload = {
                "status": "ok",
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "account_name": result["account_name"],
                "device_count": len(result["devices"]),
                "data": result["devices"],
                "licenses": result["licenses"],
            }
            yield f"event: data\ndata: {json.dumps(payload)}\n\n"
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"event: error\ndata: {json.dumps({'status': 'error', 'message': str(e)})}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@app.get("/api/status")
async def status():
    return {"status": "ok", "time": datetime.now(timezone.utc).isoformat()}


@app.get("/api/profiles")
async def list_profiles():
    profiles = _load_profiles()
    return JSONResponse({name: {k: v[:4] + "…" if v and len(v) > 4 else "" for k, v in creds.items()} for name, creds in profiles.items()})


@app.post("/api/profiles")
async def save_profile(request: Request):
    body = await request.json()
    name = body.get("name", "").strip()
    creds = body.get("credentials", {})
    overwrite = body.get("overwrite", False)
    if not name:
        return JSONResponse({"error": "Profile name required"}, status_code=400)
    profiles = _load_profiles()
    if name in profiles and not overwrite:
        return JSONResponse({"error": "exists", "message": f"Profile '{name}' already exists"}, status_code=409)
    profiles[name] = {k: creds.get(k, "") for k in ["X_CP_API_ID", "X_CP_API_KEY", "X_ECM_API_ID", "X_ECM_API_KEY", "NCM_API_TOKEN"]}
    _save_profiles(profiles)
    return JSONResponse({"status": "ok", "name": name})


@app.post("/api/profiles/load")
async def load_profile(request: Request):
    body = await request.json()
    name = body.get("name", "").strip()
    profiles = _load_profiles()
    if name not in profiles:
        return JSONResponse({"error": f"Profile '{name}' not found"}, status_code=404)
    for key, val in profiles[name].items():
        if val:
            os.environ[key] = val
    return JSONResponse({"status": "ok", "name": name})


@app.delete("/api/profiles/{name}")
async def delete_profile(name: str):
    profiles = _load_profiles()
    if name not in profiles:
        return JSONResponse({"error": f"Profile '{name}' not found"}, status_code=404)
    del profiles[name]
    _save_profiles(profiles)
    return JSONResponse({"status": "ok", "deleted": name})


@app.get("/api/profiles/current")
async def current_credentials():
    key_pairs = [("X_CP_API_ID", "CP_API_ID"), ("X_CP_API_KEY", "CP_API_KEY"), ("X_ECM_API_ID", "ECM_API_ID"), ("X_ECM_API_KEY", "ECM_API_KEY"), ("NCM_API_TOKEN", "NCM_API_TOKEN")]
    result = {}
    for primary, fallback in key_pairs:
        val = os.environ.get(primary, "") or os.environ.get(fallback, "")
        result[primary] = {"set": bool(val), "value": val}
    return JSONResponse(result)


@app.post("/api/credentials/apply")
async def apply_credentials(request: Request):
    body = await request.json()
    creds = body.get("credentials", {})
    for key in ["X_CP_API_ID", "X_CP_API_KEY", "X_ECM_API_ID", "X_ECM_API_KEY", "NCM_API_TOKEN"]:
        val = creds.get(key, "").strip()
        if val:
            os.environ[key] = val
    return JSONResponse({"status": "ok"})


if __name__ == "__main__":
    print("Inventory Dashboard starting...")
    print("Open http://localhost:8060 in your browser")
    uvicorn.run(app, host="0.0.0.0", port=8060, log_level="info")
