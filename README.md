# API Samples

A collection of Python scripts and web applications for interacting with Ericsson NetCloud Manager APIs.

## Getting Started

Three steps: clone, run setup, start chatting with Kiro.

### 1. Prerequisites

- Python 3.9 or higher (3.12 recommended) — Windows users, see the [Windows Python Setup Guide](WINDOWS_PYTHON_SETUP.md)
- Git

### 2. Clone the repository

```bash
git clone <repository-url>
cd api-samples
```

### 3. Run setup

**macOS / Linux**

```bash
python3 setup_env.py
```

**Windows (PowerShell)**

```powershell
python setup_env.py
```

That's it. The script checks your Python version, creates the `.venv` virtual
environment, upgrades pip, installs everything in `requirements.txt`, prompts for
your API credentials (input is hidden), and verifies the result.

Then activate the venv:

```bash
source .venv/bin/activate          # macOS / Linux
.venv\Scripts\Activate.ps1         # Windows PowerShell
.venv\Scripts\activate.bat         # Windows cmd
```

### 4. Start chatting with Kiro

Open the folder in Kiro and ask for what you want:

- "Build me a dashboard showing routers with poor signal"
- "Export all my routers to CSV"
- "Which devices have subscriptions expiring in the next 30 days?"

Kiro reads the API docs in `docs/`, uses the venv, and picks up your credentials
automatically.

### Setup script options

| Command | What it does |
|---|---|
| `python3 setup_env.py` | Full setup, prompts for credentials |
| `python3 setup_env.py --skip-credentials` | venv + dependencies only, no prompts |
| `python3 setup_env.py --credentials-only` | Re-enter credentials only |
| `python3 setup_env.py --check` | Report environment status, change nothing |

Use `python` instead of `python3` on Windows.

You can also have Kiro run setup for you: type `#setup-environment` in chat and
it will build the environment, diagnose any failures, and report what's left.

### Where credentials are stored

`setup_env.py` writes them to `.env` at the repo root (gitignored, owner-only
permissions on macOS/Linux) and injects them into every venv activate script —
bash/zsh, fish, csh, PowerShell, and cmd — so they work in any shell on any
platform, activated or not.

| Variable | Required | Purpose |
|---|---|---|
| `X_CP_API_ID` | yes | Cradlepoint API ID |
| `X_CP_API_KEY` | yes | Cradlepoint API key |
| `X_ECM_API_ID` | yes | ECM API ID |
| `X_ECM_API_KEY` | yes | ECM API key |
| `NCM_API_TOKEN` | no | Bearer token, v3 endpoints only |

Dashboard apps also support configuring credentials via the Settings panel in the UI.

### Manual setup (alternative)

If you prefer to do it by hand:

```bash
python3 -m venv .venv                   # macOS/Linux
# or: python -m venv .venv              # Windows
source .venv/bin/activate               # macOS/Linux
# or: .venv\Scripts\Activate.ps1        # Windows PowerShell
python -m pip install -r requirements.txt
```

Then set the API keys:

```bash
export X_CP_API_ID="your_api_id"                # macOS/Linux
```

```powershell
$env:X_CP_API_ID = "your_api_id"                # Windows PowerShell
```

## Project Structure

```
api-samples/
├── setup_env.py         # One-shot environment setup (start here)
├── requirements.txt     # Python dependencies
├── .kiro/               # Kiro steering rules and agent hooks
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

Start here — it diagnoses most problems in one command:

```bash
python3 setup_env.py --check       # python setup_env.py --check on Windows
```

**Missing API keys:** Run `python3 setup_env.py --credentials-only`, or use the Settings panel in dashboard apps.

**ModuleNotFoundError:** Re-run `python3 setup_env.py --skip-credentials` to reinstall dependencies into the venv.

**`python` not recognized (Windows):** Python isn't on your PATH. See the [Windows Python Setup Guide](WINDOWS_PYTHON_SETUP.md).

**`Activate.ps1 cannot be loaded` (Windows PowerShell):** PowerShell's execution policy is blocking the script. Run:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Or use `.venv\Scripts\activate.bat` from cmd instead.

**venv creation fails (Linux):** Install the venv module: `sudo apt install python3-venv`.

**Port already in use:** macOS/Linux `lsof -ti:<port> | xargs kill`. Windows `netstat -ano | findstr :<port>` then `taskkill /PID <pid> /F`.

## License

See the [LICENSE](LICENSE) file for details.
