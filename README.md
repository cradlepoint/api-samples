# API Samples

A collection of Python scripts and web applications for interacting with Ericsson NetCloud Manager APIs.

## Getting Started

### Prerequisites

- Python 3.9 or higher — Windows users, see the [Windows Python Setup Guide](WINDOWS_PYTHON_SETUP.md)
- Git (optional, for cloning the repository)

### Download and Extract the Repository

```bash
git clone <repository-url>
cd api-samples
```

## Setup

Run the setup script to create the virtual environment, install dependencies, and configure API credentials:

**macOS / Linux**

```
python3 setup_env.py && source .venv/bin/activate
```

**Windows**

```
python setup_env.py && .venv\Scripts\activate
```

This handles everything — venv creation, `pip install`, and credential configuration.

### Manual Setup (alternative)

If you prefer to set things up manually:

```bash
python3 -m venv .venv                   # macOS/Linux
# or: python -m venv .venv             # Windows
source .venv/bin/activate               # macOS/Linux
# or: .venv\Scripts\activate            # Windows
pip install -r requirements.txt
```

Set API keys:

```bash
export X_CP_API_ID="your_api_id"
export X_CP_API_KEY="your_api_key"
export X_ECM_API_ID="your_ecm_api_id"
export X_ECM_API_KEY="your_ecm_api_key"
export NCM_API_TOKEN="your_v3_bearer_token"  # optional, for v3 API
```

Dashboard apps also support configuring credentials via the Settings panel in the UI.

## Project Structure

```
api-samples/
├── web_apps/            # Web applications and dashboards
├── scripts/             # Standalone Python scripts and utilities
├── ncm/                 # NCM Python SDK source (also pip installable)
├── ncm2/                # NCM Python SDK v2+v3 variant
├── docs/                # API documentation and references
└── postman-collection/  # Postman API collection
```

## Web Apps & Dashboards

All web applications live in `web_apps/`. See [web_apps/README.md](web_apps/README.md) for full details.

| App | Port | Description |
|-----|------|-------------|
| [inventory_dashboard](web_apps/inventory_dashboard/) | 8060 | Device inventory with license status, subscriptions, modem info |
| [cellular_health_dashboard](web_apps/cellular_health_dashboard/) | 8055 | Cellular health scores and signal metrics |
| [script_manager](web_apps/script_manager/) | 8000 | CSV editor and NCM script runner with web UI |
| [config_builder](web_apps/config_builder/) | 8100 | Build JSON configurations from templates |
| [assign_sdk](web_apps/assign_sdk/) | 9000 | Assign SDK app versions to router groups |
| [cisco_to_cradlepoint_zfw_converter](web_apps/cisco_to_cradlepoint_zfw_converter/) | 5001 | Convert Cisco configs to Cradlepoint zone firewall |
| [ncm_api_key_encryptor](web_apps/ncm_api_key_encryptor/) | 8000 | Encrypt API keys for SDK app configs |
| [netcloud_router_lookup](web_apps/netcloud_router_lookup/) | 8000 | Look up router info by serial/MAC |

### Running a Web App

```bash
python3 web_apps/inventory_dashboard/serve.py    # macOS/Linux
python web_apps/inventory_dashboard/serve.py     # Windows
```

## Sample Scripts

The `scripts/` folder contains standalone Python scripts demonstrating various API interactions:

- Router management and configuration
- User management (v3 API)
- Subscription management and regrades
- Device licensing and unlicensing
- Configuration backups

```bash
python3 scripts/<script_name>.py    # macOS/Linux
python scripts/<script_name>.py     # Windows
```

## Script Manager

Web-based interface for managing CSV files, API keys, and running scripts:

```bash
python3 web_apps/script_manager/script_manager.py    # macOS/Linux
python web_apps/script_manager/script_manager.py     # Windows
```

Open http://localhost:8000 in your browser.

## Postman Collection

Pre-configured API requests for testing NCM endpoints in Postman. Import `postman-collection/Ericsson NCM API Postman Collection.json` into Postman.

## Documentation

The `docs/` folder contains detailed API references:

- [API Overview](docs/api-overview.md) — auth, base URLs, pagination
- [v2 Endpoints](docs/api-v2-endpoints.md) — routers, groups, net_devices, etc.
- [v3 Endpoints](docs/api-v3-endpoints.md) — subscriptions, asset_endpoints, users
- [SDK Reference](docs/ncm-sdk-reference.md) — Python SDK methods
- [Known Issues](docs/known-issues.md) — API gotchas and workarounds
- [Common Patterns](docs/common-patterns.md) — reusable code patterns

## Troubleshooting

**Missing API keys:** Verify environment variables are set, or use the Settings panel in dashboard apps.

**ModuleNotFoundError:** Make sure your venv is activated and `pip install -r requirements.txt` was run.

**Port already in use:** Kill the existing process (`lsof -ti:<port> | xargs kill`) or use a different port.

## License

See the [LICENSE](LICENSE) file for details.
