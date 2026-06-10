# Inventory Dashboard

Live web dashboard for Ericsson NetCloud Manager device inventory and license status.

Combines v2 API (routers, net devices, groups, accounts) with v3 API (asset endpoints, subscriptions) into a single unified view showing license state, modem details, and subscription information for every device.

<img width="1532" height="843" alt="image" src="https://github.com/user-attachments/assets/12c68386-97c0-463d-b304-863bfca9406c" />

## Features

- Full device inventory with license state (licensed, grace-period, unlicensed)
- 45+ columns including modem detail (IMEI, ICCID, carrier, modem FW, etc.)
- Stat cards as clickable filters (Total, Online, Offline, Licensed, Grace Period, Unlicensed)
- Full-text search across all key fields
- Click any text cell to auto-populate search
- Sortable columns (click header to toggle asc/desc)
- Pagination (100 devices per page)
- CSV export of filtered/sorted data
- PDF export with branded header, summary stats, color-coded columns
- Settings modal with API credential management and named profiles
- Auto-loads first saved profile on startup
- Light/dark mode with localStorage persistence
- Column visibility toggle (show/hide modem detail columns)
- Group-by-account display option
- Snapshot cache preserves device history when devices lose v2 data after unlicensing
- Real-time progress indicator during data loading (SSE streaming)
- 324+ subscription type codes mapped to friendly names

## Prerequisites

```bash
pip install ncm fastapi uvicorn httpx
```

## Usage

```bash
python3 web_apps/inventory_dashboard/serve.py    # macOS/Linux
python web_apps/inventory_dashboard/serve.py     # Windows
```

Then open http://localhost:8060 in your browser.

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `X_CP_API_ID` | Yes | Cradlepoint API ID |
| `X_CP_API_KEY` | Yes | Cradlepoint API Key |
| `X_ECM_API_ID` | Yes | ECM API ID |
| `X_ECM_API_KEY` | Yes | ECM API Key |
| `NCM_API_TOKEN` | Recommended | Bearer token for v3 API (subscriptions, asset_endpoints) |

Credentials can also be configured via the Settings panel (gear icon) in the UI.

## Files

```
web_apps/inventory_dashboard/
├── serve.py               — FastAPI backend (all API logic in one file)
├── index.html             — Single-page frontend (inline JS/CSS)
├── subscription_types.py  — Subscription code → friendly name mapping
├── profiles.json          — Saved credential profiles
└── inventory_snapshot.json — Device state cache (auto-generated)
```

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Serve dashboard HTML |
| GET | `/api/data` | Fetch full inventory (blocking) |
| GET | `/api/data/stream` | Fetch inventory via SSE with progress |
| GET | `/api/status` | Health check |
| GET | `/api/profiles` | List saved profiles |
| POST | `/api/profiles` | Save/overwrite a profile |
| POST | `/api/profiles/load` | Load a profile into environment |
| DELETE | `/api/profiles/{name}` | Delete a profile |
| GET | `/api/profiles/current` | Return current env credentials |
| POST | `/api/credentials/apply` | Apply credentials without saving |

## How It Works

1. Fetches routers, net devices, and groups from NCM v2 API (using the `ncm` pip package)
2. Fetches asset endpoints and subscriptions from NCM v3 API (using `httpx`)
3. Joins all data by normalized MAC address
4. Resolves subscription assignment IDs to full subscription details
5. Enriches from local snapshot (restores data for devices that lost v2 visibility)
6. Returns combined inventory with license state detection
