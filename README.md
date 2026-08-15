# API Samples

A collection of Python scripts and web applications for interacting with Ericsson NetCloud Manager APIs.

## Getting Started

Fork, clone your fork in Kiro, run setup, then start chatting. If you build
something worth sharing, open a pull request back to this repo.

### 1. Prerequisites

- Python 3.9 or higher (3.12 recommended) — Windows users, see the [Windows Python Setup Guide](WINDOWS_PYTHON_SETUP.md)
- Git
- A GitHub account
- [Kiro](https://kiro.dev)

### 2. Fork the repository

Forking gives you your own copy to experiment in, and it's what lets you
contribute changes back later.

1. Go to [github.com/cradlepoint/api-samples](https://github.com/cradlepoint/api-samples)
2. Click **Fork** (top right), then **Create fork**

You now have `https://github.com/<your-username>/api-samples`.

### 3. Clone your fork in Kiro

In Kiro, open the Command Palette (`Cmd+Shift+P` on macOS, `Ctrl+Shift+P` on
Windows/Linux), run **Git: Clone**, and paste your fork's URL:

```
https://github.com/<your-username>/api-samples.git
```

Pick a local folder, then choose **Open** when Kiro offers to open the cloned
repository.

Prefer the terminal? Same result:

```bash
git clone https://github.com/<your-username>/api-samples.git
cd api-samples
```

Then add the original repo as `upstream` so you can pull in later changes:

```bash
git remote add upstream https://github.com/cradlepoint/api-samples.git
```

Clone your fork, not this repo directly — you won't have push access here, and
you'd have nowhere to put your branch when it's time to open a pull request.

### 4. Run setup

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

### 5. Build apps by chatting with Kiro

Open the Kiro chat panel and describe what you want in plain language:

- "Build me a dashboard showing routers with poor signal"
- "Export all my routers to CSV"
- "Which devices have subscriptions expiring in the next 30 days?"
- "Add a CSV export button to the inventory dashboard"

Kiro reads the API references in `docs/`, follows the conventions in `.kiro/steering/`,
uses the `.venv` interpreter, and picks up your credentials automatically. New web
apps get scaffolded into `web_apps/` using the shared style template, so they match
the existing dashboards.

A few things that make the results better:

- Point at files with `#File` or `#Folder` when you want Kiro to follow an existing
  pattern — for example, "build a dashboard like #Folder web_apps/cellular_health_dashboard"
- Type `#setup-environment` if the environment needs repairing
- Ask for a spec first on anything large: "write a spec for a firmware compliance
  dashboard." You review requirements and design before code gets written.

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
├── docs/                # API documentation and references
└── postman-collection/  # Postman API collection
```

## Web Apps & Dashboards

All web applications live in `web_apps/`. See [web_apps/README.md](web_apps/README.md) for full details.

| App | Port | Entry point | Description |
|-----|------|-------------|-------------|
| [inventory_dashboard](web_apps/inventory_dashboard/) | 8060 | `serve.py` | Device inventory with license status, subscriptions, modem info |
| [cellular_health_dashboard](web_apps/cellular_health_dashboard/) | 8055 | `serve.py` | Cellular health scores and signal metrics — RSRP, SINR, health scores |
| [alert_dashboard](web_apps/alert_dashboard/) | 8065 | `serve.py` | Custom alerts with type/account filters, ACK tracking, auto-refresh, export |
| [geo_ip_blocker](web_apps/geo_ip_blocker/) | 8065 | `serve.py` | Turn country IP ranges into zone firewall deny rules and push to groups |
| [host_identity_copier](web_apps/host_identity_copier/) | 8070 | `serve.py` | Copy host address identities from a master group to many destinations |
| [config_builder](web_apps/config_builder/) | 8100 | `config_builder.py` | Build Cradlepoint JSON configurations from templates with per-site variables |
| [assign_sdk](web_apps/assign_sdk/) | 9000 | `serve.py` | Assign SDK app versions to router groups |
| [script_manager](web_apps/script_manager/) | 8000 | `script_manager.py` | CSV editor and NCM script runner with web UI |
| [ncm_api_key_encryptor](web_apps/ncm_api_key_encryptor/) | 8000 | `ncm_api_key_encryptor.py` | Encrypt API keys for embedding in SDK app configs |
| [netcloud_router_lookup](web_apps/netcloud_router_lookup/) | 8000 | `router_lookup.py` | Search routers across multiple accounts |
| [cisco_to_cradlepoint_zfw_converter](web_apps/cisco_to_cradlepoint_zfw_converter/) | 5001 | `app.py` | Convert Cisco router configs to Cradlepoint zone firewall format |
| [web_app_template](web_apps/web_app_template/) | 8000 | `serve.py` | Style/layout starting point for new apps, not a tool in itself |

Ports 8000 and 8065 are each shared by more than one app, so run those one at a time.

### Running a Web App

Most apps use `serve.py`, but five don't — check the Entry point column above.

```bash
python3 web_apps/inventory_dashboard/serve.py           # macOS/Linux
python web_apps/inventory_dashboard/serve.py            # Windows

python3 web_apps/config_builder/config_builder.py       # non-serve.py example
```

Then open the app's port in your browser, e.g. http://localhost:8060.

These apps bind a local port with no authentication, which is fine on `localhost`.
Don't expose one on a shared network — anyone who can reach the port can read the
credentials stored in its Settings panel.

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

## Contributing Back

Built something useful in your fork? Open a pull request.

### 1. Work on a branch

```bash
git checkout -b my-new-dashboard
```

### 2. Commit and push to your fork

```bash
git add web_apps/my_new_dashboard/
git commit -m "Add dashboard for firmware compliance"
git push -u origin my-new-dashboard
```

Stage specific paths rather than `git add -A`. This repo keeps local credential and
state files in the working tree, and a couple of them are still tracked from an
earlier commit, so a blanket add can pick up API keys. Check `git status` before you
commit.

### 3. Open the pull request

Either use the GitHub CLI:

```bash
gh pr create --repo cradlepoint/api-samples --web
```

Or visit your fork on GitHub and click **Compare & pull request**. Set the base to
`cradlepoint/api-samples` and describe what you built and how you tested it.

You can ask Kiro to do the whole sequence for you — "commit this on a branch and open
a PR against upstream" — and it will handle the branch, commit, push, and PR.

### Keeping your fork current

```bash
git fetch upstream
git checkout master
git merge upstream/master
git push
```

### Before you submit

- No credentials in the diff — no `.env`, no `profiles.json` or `config.json` with real keys
- A new app includes a short `readme.md` and any extra deps in `requirements.txt`
- New web apps follow the shared style template, including light/dark mode
- The code runs against a real NCM tenant

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
