"""Local dashboard server — serves the inventory report with live refresh.

Usage:
    py serve.py

Then open http://localhost:8050 in your browser.
"""

import json
import logging
import os
from datetime import datetime
from pathlib import Path

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not installed; rely on system env vars

from fastapi import FastAPI
from fastapi.requests import Request
from fastapi.responses import FileResponse, JSONResponse
import uvicorn

from inventory_sdk import (
    InventoryClient,
    enrich_from_snapshot,
    load_snapshot,
    save_snapshot,
    generate_html_report,
    generate_loading_html,
    update_progress_html,
)
from inventory_sdk.html_report import _status_to_row, _build_headers, _fmt_date

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(name)s %(message)s",
    datefmt="%H:%M:%S",
)

app = FastAPI(title="Inventory Dashboard")

HTML_PATH = Path("inventory_report.html")
SNAPSHOT_PATH = Path("inventory_snapshot.json")


def _build_client() -> InventoryClient:
    """Create an InventoryClient from environment or hardcoded keys."""
    return InventoryClient(
        cp_api_id=os.environ["CP_API_ID"],
        cp_api_key=os.environ["CP_API_KEY"],
        ecm_api_id=os.environ["ECM_API_ID"],
        ecm_api_key=os.environ["ECM_API_KEY"],
        v3_bearer_token=os.environ.get("V3_BEARER_TOKEN"),
    )


def _refresh_data() -> dict:
    """Fetch fresh data from the API, update snapshot, generate report."""
    client = _build_client()
    with client:
        def on_progress(step: int, detail: str) -> None:
            update_progress_html(step, detail, HTML_PATH)

        generate_loading_html(HTML_PATH)
        statuses, sw_licenses = client.get_license_status(progress_callback=on_progress)

    previous = load_snapshot(SNAPSHOT_PATH)
    statuses = enrich_from_snapshot(statuses, previous)
    save_snapshot(statuses, SNAPSHOT_PATH)

    generate_html_report(statuses, HTML_PATH, software_licenses=sw_licenses)

    max_addons = max((len(s.add_ons) for s in statuses), default=0)
    headers = _build_headers(max_addons)
    rows = [_status_to_row(s, max_addons) for s in statuses]
    return {"headers": headers, "rows": rows}


@app.get("/")
async def index():
    """Serve the HTML dashboard."""
    if not HTML_PATH.exists():
        _refresh_data()
    return FileResponse(HTML_PATH, media_type="text/html")


@app.get("/api/refresh")
async def refresh():
    """Re-fetch all data from the API and return fresh JSON."""
    data = _refresh_data()
    return JSONResponse(data)


@app.get("/api/status")
async def status():
    """Quick health check."""
    return {"status": "ok", "time": datetime.now().isoformat()}


ENV_PATH = Path(".env")

_CREDENTIAL_KEYS = ["CP_API_ID", "CP_API_KEY", "ECM_API_ID", "ECM_API_KEY", "V3_BEARER_TOKEN"]


@app.get("/api/settings")
async def get_settings():
    """Return current credential status (set/unset, masked values)."""
    result = {}
    for key in _CREDENTIAL_KEYS:
        val = os.environ.get(key, "")
        result[key] = {"set": bool(val), "masked": val[:4] + "…" if len(val) > 4 else ""}
    return JSONResponse(result)


@app.post("/api/settings")
async def save_settings(request: Request):
    """Update credentials in memory and optionally save to .env file."""
    body = await request.json()
    save_to_file = body.get("save_to_file", False)
    creds = body.get("credentials", {})

    for key in _CREDENTIAL_KEYS:
        val = creds.get(key, "").strip()
        if val:
            os.environ[key] = val

    if save_to_file:
        lines = []
        for key in _CREDENTIAL_KEYS:
            val = os.environ.get(key, "")
            if val:
                lines.append(f"{key}={val}")
        ENV_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")

    return JSONResponse({"status": "ok", "saved_to_file": save_to_file})


if __name__ == "__main__":
    # Generate initial report on startup
    print("Fetching initial data…")
    _refresh_data()
    print(f"Dashboard ready at http://localhost:8050")
    uvicorn.run(app, host="0.0.0.0", port=8050, log_level="warning")
