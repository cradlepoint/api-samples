# Custom Alert Dashboard

A web dashboard that displays **custom alerts** from the NCM API with configurable timeframe, auto-refresh, acknowledgment tracking, and export capabilities.

<img width="1484" height="842" alt="image" src="https://github.com/user-attachments/assets/66eada90-6517-42c2-b500-9ff50dace94e" />

## Features

- **Custom alerts only** — filters for `type=custom_alert` from the NCM `/alerts/` endpoint
- **Configurable time range** — default 30 days, max 90 days
- **Auto-refresh** — enabled by default at 60-second intervals; incremental (only fetches new alerts since last check)
- **Manual refresh** — full reload of the entire time range
- **Click-to-expand** — each alert row expands to show all details (persists across refreshes)
- **ACK checkbox** — acknowledge alerts with timestamp; stored to `acks.json` with the full alert object
- **Router name resolution** — batch-resolves router IDs to human-readable names
- **Title extraction** — extracts the `title` field from the alert `info` object
- **Uptime display** — extracts and formats device uptime from alert info
- **Search** — full-text filter across all alert fields
- **Export** — CSV, JSON, and HTML download buttons (exports the current filtered set)
- **Dark mode** — toggle with localStorage persistence
- **Settings modal** — API credential management with named profiles (save/load/delete)
- **SSL bypass** — option to disable SSL verification for corporate proxy environments

## Usage

```bash
.venv/bin/python web_apps/custom_alert_dashboard/serve.py
```

Then open http://localhost:8065 in your browser.

## Requirements

- Python 3.12+
- FastAPI, uvicorn, ncm SDK (all in project `requirements.txt`)
- NCM API v2 credentials (set via environment variables or the Settings panel)

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `X_CP_API_ID` | Yes | Cradlepoint API ID |
| `X_CP_API_KEY` | Yes | Cradlepoint API Key |
| `X_ECM_API_ID` | Yes | ECM API ID |
| `X_ECM_API_KEY` | Yes | ECM API Key |

Credentials can also be configured through the Settings gear icon in the dashboard header.

## Files

| File | Purpose |
|------|---------|
| `serve.py` | FastAPI backend — API endpoints, alert fetching, profile/ack management |
| `index.html` | Single-page frontend — full dashboard UI |
| `profiles.json` | Saved credential profiles (auto-created) |
| `acks.json` | Acknowledged alerts with timestamps (auto-created) |
| `settings.json` | Persisted settings like SSL verify state (auto-created) |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Serve dashboard HTML |
| GET | `/api/alerts?days=30&since=` | Fetch custom alerts (full or incremental) |
| GET | `/api/acks` | Get all acknowledged alerts |
| POST | `/api/acks` | Acknowledge/unacknowledge an alert |
| GET | `/api/profiles` | List saved profiles |
| POST | `/api/profiles` | Save a profile |
| POST | `/api/profiles/load` | Load a profile into env |
| DELETE | `/api/profiles/{name}` | Delete a profile |
| GET | `/api/profiles/current` | Get current credentials |
| POST | `/api/credentials/apply` | Apply credentials without saving |
| POST | `/api/ssl-noverify` | Disable SSL verification |
| GET | `/api/status` | Health check |
