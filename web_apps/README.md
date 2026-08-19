# Web Apps

Interactive web applications for managing, configuring, and monitoring Cradlepoint devices via the NetCloud Manager (NCM) API.

## Available Web Apps

| App | Port | Entry point | Description |
|-----|------|-------------|-------------|
| [inventory_dashboard](inventory_dashboard/) | 8060 | `serve.py` | Device inventory with license status, subscription details, and modem info |
| [cellular_health_dashboard](cellular_health_dashboard/) | 8055 | `serve.py` | Cellular health metrics — signal strength, RSRP, SINR, health scores |
| [alert_dashboard](alert_dashboard/) | 8065 | `serve.py` | Alert dashboard with type/account filters, ACK tracking, auto-refresh, and export |
| [geo_ip_blocker](geo_ip_blocker/) | 8065 | `serve.py` | Convert country IP ranges into zone firewall deny rules and push to groups |
| [host_identity_copier](host_identity_copier/) | 8070 | `serve.py` | Copy host address identities from a master group to many destination groups |
| [config_builder](config_builder/) | 8100 | `config_builder.py` | Build Cradlepoint JSON configurations from templates with per-site variables |
| [assign_sdk](assign_sdk/) | 9000 | `serve.py` | Assign SDK app versions to router groups |
| [script_manager](script_manager/) | 8000 | `script_manager.py` | CSV file editor and NCM script runner with a web UI |
| [ncm_api_key_encryptor](ncm_api_key_encryptor/) | 8000 | `ncm_api_key_encryptor.py` | Encrypt NCM API keys for embedding in SDK app configurations |
| [netcloud_router_lookup](netcloud_router_lookup/) | 8000 | `router_lookup.py` | Search routers across multiple accounts |
| [rma_wizard](rma_wizard/) | 8080 | `rma_wizard.py` | Step-by-step wizard for migrating configuration from a failed router to its RMA replacement |
| [cisco_to_cradlepoint_zfw_converter](cisco_to_cradlepoint_zfw_converter/) | 5001 | `app.py` | Convert Cisco router configs to Cradlepoint zone firewall format |
| [web_app_template](web_app_template/) | 8000 | `serve.py` | Style/layout starting point for new apps, not a tool in itself |

Some ports are shared by more than one app (8000 and 8065), so run those apps one at a time.

## Running a Web App

Most apps use `serve.py`, but five have a differently named entry point — see the
table above.

```bash
python3 web_apps/<app_name>/serve.py    # macOS/Linux
python web_apps/<app_name>/serve.py     # Windows

python3 web_apps/config_builder/config_builder.py    # non-serve.py example
```

These apps bind a local port with no authentication. That's fine for `localhost`, but
don't expose one on a shared network — anyone who can reach the port can read the
credentials held in its Settings panel.

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
