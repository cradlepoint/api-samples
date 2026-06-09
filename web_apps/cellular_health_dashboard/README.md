# Cellular Health Dashboard

<img width="1532" height="843" alt="image" src="https://github.com/user-attachments/assets/f4db1ec7-37a5-460d-91d5-bebb1a46cc0b" />

<img width="1532" height="843" alt="image" src="https://github.com/user-attachments/assets/7fb24232-8c16-40af-a1bf-7a96348a41a3" />

<img width="1532" height="843" alt="image" src="https://github.com/user-attachments/assets/1516e632-ae45-466e-bc91-a70fdb160fa2" />

A web dashboard that displays cellular health metrics for all devices in your NCM sub-account. Includes historical tracking, auto-refresh, credential profiles, and read-only mode for shared deployments.

## Features

- Real-time cellular signal metrics (RSSI, RSRP, RSRQ, SINR, health score)
- Signal quality classification (Excellent / Good / Fair / Poor) with color-coded indicators
- Device status (Online / Offline) with stat card filters
- Per-device history charts (Recent 24h + Daily long-term averages)
- Auto-refresh with configurable interval (records history samples on schedule)
- Sortable columns (default: lowest health score first)
- Full-text search across device name, carrier, model, MAC
- Click any text cell to auto-search that value
- CSV and PDF export (filtered/sorted data)
- Named credential profiles with per-profile history isolation
- Read-only mode (`-ro`) for shared/kiosk deployments
- SSL verification bypass for corporate proxy environments
- Light and dark mode with persistent preference
- Server-side snapshot cache for instant page loads
- Responsive layout

## Requirements

- Python 3.12+ (use the project `.venv`)
- NCM API v2 credentials

## Setup

1. Install dependencies (if not already):
   ```bash
   .venv/bin/python -m pip install -r requirements.txt
   ```

2. Run the dashboard:
   ```bash
   .venv/bin/python web_apps/cellular_health_dashboard/serve.py
   ```

3. Open http://localhost:8055 in your browser.

4. Click the **gear icon** to open Settings. Enter your API credentials or load a saved profile, then click **Apply & Refresh**.

## Command-Line Options

```bash
# Normal mode (full UI with settings panel)
python serve.py

# Read-only mode (hides settings, uses saved profile)
python serve.py -ro

# Read-only with specific profile override
python serve.py -ro -p "Production"
```

### Read-Only Mode Credential Resolution

1. If only one saved profile exists → uses it automatically
2. If multiple profiles exist → requires a ★ Default profile (set via Settings)
3. If no profiles exist → falls back to environment variables
4. `-p "Name"` flag overrides all of the above

## Settings Panel

- **Credential profiles** — Save, Load, Delete, and set a ★ Default for read-only mode
- **Auto Refresh** — Enable/disable with configurable interval (minutes)
- **Display Options** — Group interfaces by device, clear history
- **SSL bypass** — Auto-detected on certificate errors, persisted to disk

## History

History is collected automatically on each scheduled auto-refresh tick:

- **Recent tab** — all samples from the last 24 hours (one per refresh interval)
- **Daily tab** — long-term daily averages (selectable range: 7d to 2 years)
- **Per-profile** — each credential set maintains its own history database
- **Per-interface** — each modem interface is tracked independently

Storage: SQLite databases in the `history/` subfolder, keyed by API credential hash.

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Dashboard HTML |
| `GET /api/health` | Cellular health data (cached or live with `?refresh=true`) |
| `GET /api/health?refresh=true&record=true` | Force live pull + record history sample |
| `GET /api/status` | Health check |
| `GET /api/config` | Runtime config (readonly mode flag) |
| `GET /api/profiles` | List saved profiles |
| `POST /api/profiles` | Save/overwrite profile |
| `POST /api/profiles/load` | Load profile into env |
| `DELETE /api/profiles/{name}` | Delete profile |
| `GET /api/profiles/current` | Current active credentials |
| `POST /api/credentials/apply` | Apply credentials without saving |
| `GET /api/default-profile` | Get default startup profile |
| `POST /api/default-profile` | Set default startup profile |
| `GET /api/history/{router_id}` | History data (tab=hourly/daily, interface filter) |
| `GET /api/history-status` | History DB stats |
| `POST /api/history-clear` | Clear all history data |
| `POST /api/ssl-noverify` | Disable SSL verification (persisted) |
| `GET /api/debug` | Raw API response samples for debugging |

## Data Sources

The dashboard joins data from four NCM v2 endpoints:

1. `/net_device_health/` — health score + category
2. `/net_device_metrics/` — signal metrics (RSRP, SINR, dBm, etc.)
3. `/net_devices/?expand=router` — interface info, carrier, inline router object
4. `/accounts/` — account name

## Files

| File | Purpose |
|------|---------|
| `serve.py` | FastAPI backend |
| `index.html` | Single-page frontend |
| `profiles.json` | Saved credential profiles |
| `settings.json` | Persisted settings (SSL verify, default profile) |
| `snapshot_cache.json` | Last API response for instant page loads |
| `history/` | Per-profile SQLite history databases |
