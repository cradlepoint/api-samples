# Cellular Health Dashboard

Cellular health metrics for all devices in an NCM account. Includes history tracking, auto-refresh, credential profiles, and read-only mode.

<img width="1532" height="843" alt="image" src="https://github.com/user-attachments/assets/f4db1ec7-37a5-460d-91d5-bebb1a46cc0b" />

<img width="1532" height="843" alt="image" src="https://github.com/user-attachments/assets/7fb24232-8c16-40af-a1bf-7a96348a41a3" />

<img width="1532" height="843" alt="image" src="https://github.com/user-attachments/assets/1516e632-ae45-466e-bc91-a70fdb160fa2" />

## Quick Start

**Windows:**
```powershell
.venv\Scripts\activate
python web_apps\cellular_health_dashboard\serve.py
```

**macOS / Linux:**
```bash
source .venv/bin/activate
python web_apps/cellular_health_dashboard/serve.py
```

Open http://localhost:8055 → click the gear icon → enter API credentials → Apply & Refresh.

## Command-Line Options

```bash
python serve.py          # Normal mode (full UI)
python serve.py -ro      # Read-only (hides settings, uses saved profile)
python serve.py -ro -p "Name"  # Read-only with specific profile
```

**Read-only credential resolution:** single profile → uses it; multiple profiles → requires ★ Default; no profiles → env vars.

## Features

- Health score, RSSI, RSRP, RSRQ, SINR for all devices
- Signal quality indicators (Excellent/Good/Fair/Poor)
- Stat card filters, sortable columns, full-text search
- Per-device history charts (Recent 24h + Daily long-term)
- Auto-refresh with configurable interval
- CSV and PDF export
- Named credential profiles with per-profile history
- SSL bypass for corporate proxies (auto-detected, persisted)
- Light/dark mode
- Server-side cache for instant page loads

## Settings Panel

- **Profiles** — Save, Load, Delete, ★ Default (for read-only mode)
- **Auto Refresh** — toggle + interval in minutes
- **Clear History** — wipe all recorded samples

## History

Recorded on each auto-refresh tick. Per-interface, per-profile.

- **Recent** — last 24 hours of samples
- **Daily** — averaged daily values (up to 2 years)

Stored in `history/` as SQLite databases keyed by credential hash.

## Data Sources

Joins four NCM v2 endpoints: `net_device_health`, `net_device_metrics`, `net_devices` (expand=router), `accounts`.

## Files

| File | Purpose |
|------|---------|
| `serve.py` | FastAPI backend |
| `index.html` | Single-page frontend |
| `profiles.json` | Saved credential profiles |
| `settings.json` | Persisted settings (SSL, default profile) |
| `snapshot_cache.json` | Cached API response for instant loads |
| `history/` | Per-profile SQLite history databases |
