# Cellular Health Dashboard

A web dashboard that displays cellular health metrics for all devices in your NCM sub-account.

## Features

- Real-time cellular signal metrics (RSSI, RSRP, RSRQ, SINR, RSSNR)
- Signal quality classification (Excellent / Good / Fair / Poor)
- Device status (Online / Offline)
- Group-based filtering
- Full-text search across device name, group, carrier, MAC
- Light and dark mode
- Responsive layout

## Requirements

- Python 3.12+ (use the project `.venv`)
- NCM API v2 credentials set as environment variables

## Setup

1. Ensure environment variables are set:
   ```bash
   export X_CP_API_ID="your_cp_api_id"
   export X_CP_API_KEY="your_cp_api_key"
   export X_ECM_API_ID="your_ecm_api_id"
   export X_ECM_API_KEY="your_ecm_api_key"
   ```

   Or run `setup_env.py` to configure them automatically.

2. Install dependencies (if not already):
   ```bash
   .venv/bin/python -m pip install -r requirements.txt       # macOS/Linux
   .venv\Scripts\python -m pip install -r requirements.txt   # Windows
   ```

3. Run the dashboard:
   ```bash
   .venv/bin/python scripts/cellular_health_dashboard/serve.py       # macOS/Linux
   .venv\Scripts\python scripts/cellular_health_dashboard/serve.py   # Windows
   ```

4. Open http://localhost:8055 in your browser.

## API Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /` | Dashboard HTML |
| `GET /api/health` | Cellular health data JSON |
| `GET /api/status` | Health check |

## Data Sources

The dashboard pulls from three NCM v2 endpoints:
- `/routers/` — device names, states, groups
- `/net_devices/` — interface info, carrier details
- `/net_device_health/` — signal metrics (RSSI, RSRP, etc.)
