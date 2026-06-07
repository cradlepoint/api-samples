# Web Apps

Interactive web applications for managing, configuring, and monitoring Cradlepoint devices via the NetCloud Manager (NCM) API.

## Available Web Apps

| App | Port | Description |
|-----|------|-------------|
| [inventory_dashboard](inventory_dashboard/) | 8060 | Device inventory with license status, subscription details, and modem info |
| [cellular_health_dashboard](cellular_health_dashboard/) | 8055 | Cellular health metrics — signal strength, RSRP, SINR, health scores |
| [assign_sdk](assign_sdk/) | 9000 | Assign SDK app versions to router groups |
| [config_builder](config_builder/) | 8100 | Build Cradlepoint JSON configurations from templates with per-site variables |
| [cisco_to_cradlepoint_zfw_converter](cisco_to_cradlepoint_zfw_converter/) | 5001 | Convert Cisco router configs to Cradlepoint zone firewall format |
| [ncm_api_key_encryptor](ncm_api_key_encryptor/) | 8000 | Encrypt NCM API keys for embedding in SDK app configurations |
| [netcloud_router_lookup](netcloud_router_lookup/) | 8000 | Look up router info by serial number or MAC address |
| [script_manager](script_manager/) | 8000 | CSV file editor and NCM script runner with a web UI |

## Running a Web App

```bash
python web_apps/<app_name>/serve.py
```

Make sure your API credentials are set (via environment variables or the Settings panel in dashboard apps):

```bash
export X_CP_API_ID="your_id"
export X_CP_API_KEY="your_key"
export X_ECM_API_ID="your_ecm_id"
export X_ECM_API_KEY="your_ecm_key"
export NCM_API_TOKEN="your_v3_token"  # optional, for apps using API v3
```

Dashboard apps (inventory_dashboard, cellular_health_dashboard) include a Settings panel with named credential profiles — no environment variables required if you configure credentials through the UI.

## Dependencies

```bash
pip install ncm fastapi uvicorn httpx
```

Individual apps may have additional dependencies — check each app's README.

## Style Template

All web apps share a consistent design system from `web_app_template/`. Dashboard apps use the template's CSS custom properties, light/dark mode toggle, and responsive layout.
