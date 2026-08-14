# AGENTS.md

Instructions for AI coding agents working in this repo (Claude Code, Codex, Cursor,
Copilot, Kiro, and others).

This file mirrors the Kiro configuration in `.kiro/steering/` and `.kiro/hooks/`.
Kiro loads those conditionally; this file is loaded in full, so each section states
**when it applies**. Read only what is relevant to the task at hand.

| Section | Applies when |
|---|---|
| [Project Environment](#project-environment) | Always |
| [Automation Rules](#automation-rules) | Always |
| [Python Script Standards](#python-script-standards) | Touching `scripts/**/*.py` |
| [NCM API Development](#ncm-api-development) | Touching `scripts/`, `ncm/`, `ncm2/`, `web_apps/` Python |
| [Web UI Standards](#web-ui-standards) | Touching `*.html`, `*.css`, `web_apps/**` |
| [Environment Setup Walkthrough](#environment-setup-walkthrough) | User asks to set up / install / fix imports |
| [Reflexion Workflow](#reflexion-workflow) | On task completion, or when asked for the full loop |

---

## Project Environment

*Always applies.*

This repo uses a project-local virtual environment at `.venv/`. Always use it.
Never invoke system Python for project code.

### Interpreter paths

| Platform | Interpreter | Activate |
|---|---|---|
| macOS / Linux | `.venv/bin/python` | `source .venv/bin/activate` |
| Windows PowerShell | `.venv\Scripts\python.exe` | `.venv\Scripts\Activate.ps1` |
| Windows cmd | `.venv\Scripts\python.exe` | `.venv\Scripts\activate.bat` |

**Default to activating the venv, then calling `python3` (`python` on Windows).**
Activation is the only thing that picks up credentials exported into the activate
scripts, and it is what the user does in their own terminal, so it matches how they
will run the code.

```bash
source .venv/bin/activate && python3 scripts/get.py           # macOS / Linux
.venv\Scripts\Activate.ps1; python scripts\get.py             # Windows PowerShell
.venv\Scripts\activate.bat && python scripts\get.py           # Windows cmd
```

Chain activation into the same command, since activation does not persist between
tool calls. Use `;` rather than `&&` in PowerShell.

The full interpreter path is the fallback, for cases where activation is unavailable
or you specifically need to bypass it:

```bash
.venv/bin/python scripts/get.py                          # macOS / Linux
.venv\Scripts\python.exe scripts\get.py                  # Windows
```

Be aware of what it costs: `.venv/bin/python` runs the right interpreter but skips
the activate script, so any credential only exported there is absent. If `.env` is
missing, that means no credentials at all — long-running servers then boot fine and
fail on every API call with no startup signal. `setup_env.py --check` reports both
conditions.

Detect the platform before choosing either form. Do not hardcode `.venv/bin`.

### Setup

`setup_env.py` is the single entry point. It creates the venv, upgrades pip,
installs `requirements.txt`, stores credentials, and verifies the result.

```bash
python3 setup_env.py                      # full interactive setup (user runs this)
python3 setup_env.py --skip-credentials   # safe to run from a tool call
python3 setup_env.py --credentials-only   # re-enter credentials (needs a terminal)
python3 setup_env.py --check              # report status, change nothing
```

Use `python` instead of `python3` on Windows.

**Never run bare `setup_env.py` from a tool call. Use `--skip-credentials`.**

The reason, since it is easy to talk yourself out of: interactivity is gated on
`interactive = sys.stdin.isatty() and not args.skip_credentials`. Agent tool calls
**do** get a tty, so `isatty()` is True and the bare form takes the interactive
branch. It then blocks in `getpass` on a terminal with no human attached — the user
never sees the prompt, because command output only comes back when the command
exits. The result is a hang until timeout, not a graceful skip.

Do not use the `--skip-credentials` run as evidence about `isatty`. That flag forces
`interactive` to False by itself, so its "non-interactive mode" message says nothing
about whether a terminal was present.

### Missing `.venv`: set it up, do not ask

If `.venv/` does not exist, treat setup as part of the task and run it immediately.
Do not ask permission, do not tell the user to run it themselves, and do not attempt
the original request first and let it fail on a missing interpreter.

Trigger this whenever any of the following is true:

- the session-start environment check reports `venv: MISSING`
- `.venv/` is absent and you are about to run project Python, start a web app, or
  install a dependency
- the user reports broken imports, `ModuleNotFoundError`, or "command not found" for
  the venv interpreter

Procedure:

1. Detect the platform and pick the system launcher — `python3` on macOS/Linux,
   `python` on Windows. The venv interpreter does not exist yet, so system Python is
   correct *for this step only*.
2. From the workspace root, run `python3 setup_env.py --skip-credentials`
   (`python setup_env.py --skip-credentials` on Windows). This creates `.venv`,
   upgrades pip, installs `requirements.txt`, and verifies the imports.
3. Read the output and fix failures, then re-run until it exits cleanly. See
   [Environment Setup Walkthrough](#environment-setup-walkthrough) for the specific
   failure modes and their remedies.
4. Confirm with `setup_env.py --check`.
5. Then carry on with what the user originally asked for, using the venv interpreter.
   Report the setup in a sentence or two — it is a means to an end, not the headline.

**Where this stops.** Steps 1-4 are the whole of what can be automated. Credentials
cannot be, because `--credentials-only` needs a real terminal and keys must never
pass through chat. So when `--check` reports credentials missing, finish by telling
the user to run this themselves:

```bash
python3 setup_env.py --credentials-only       # macOS / Linux
python setup_env.py --credentials-only        # Windows
```

Be straight about the consequence: dependencies are ready and code will import, but
every API call fails until those keys are in place. Do not describe the environment
as "ready" while credentials are still missing.

### Credentials

Credentials live in `.env` at the repo root (gitignored, `0600` on POSIX):

- `X_CP_API_ID`, `X_CP_API_KEY` — required
- `X_ECM_API_ID`, `X_ECM_API_KEY` — required
- `NCM_API_TOKEN` — optional, needed only for v3 endpoints

`setup_env.py` also injects them into every venv activate script it finds
(`activate`, `activate.fish`, `activate.csh`, `Activate.ps1`, `activate.bat`), so
both activated shells and non-activated runs work on any platform. It reports each
script by name with the outcome, reads the values back to confirm they landed, and
warns if a script that exists did not receive them.

The two channels can drift — for example if credentials were last written by an older
version of `setup_env.py`, or if `.env` was deleted. `setup_env.py --check` reports
`.env` presence and per-script credential status; re-run
`setup_env.py --credentials-only` to bring everything back in sync.

Scripts pick them up automatically: importing `scripts/utils/env_check.py` loads
`.env` into `os.environ` using a stdlib parser. Real environment variables take
precedence over `.env`.

Rules:

- **Never ask the user to paste API keys into chat.** Direct them to
  `setup_env.py --credentials-only`, where input is hidden, or to a dashboard's
  Settings panel.
- **Never print, log, echo, or commit credential values.**
- **Never write credentials into source files.**

### Adding dependencies

Add the package to `requirements.txt`, then install it into the venv:

```bash
.venv/bin/python -m pip install -r requirements.txt
```

If you import a third-party package in new code, confirm it is in
`requirements.txt`. A missing entry breaks setup for everyone who clones fresh.

### Running web apps

Web apps live in `web_apps/<name>/`. Each has a `serve.py` and a fixed port — see
`web_apps/README.md` for the port table. Start them in the background, not the
foreground, and tell the user the URL.

Freeing a port in use:

```bash
lsof -ti:<port> | xargs kill                                    # macOS / Linux
netstat -ano | findstr :<port>  &&  taskkill /PID <pid> /F       # Windows
```

Ports 8000 and 8065 are shared by more than one app, so run those one at a time.

---

## Automation Rules

*Always applies. These replicate the `.kiro/hooks/` automations for agents without a
hook system — run them yourself at the described moment.*

### 1. At session start — check the environment

Before doing project work in a fresh session, run the environment status check:

```bash
python3 scripts/utils/env_status.py     # python on Windows
```

It reports venv readiness, dependency state, and whether credentials are present.
If it reports `venv: MISSING`, follow
[Missing `.venv`](#missing-venv-set-it-up-do-not-ask) before anything else.

This is the one script that runs under the system launcher — it is stdlib-only by
design so it can report on a venv that does not exist yet. Everything else goes
through the venv interpreter.

### 2. After running Python — fix errors before moving on

Whenever you run a Python command and the output contains errors (syntax, import,
runtime, or API), diagnose and fix the code, then re-run until it is clean. Do not
report a task complete on top of a failing run. If the error reveals undocumented API
behavior, note it for a docs update per
[Reflexion Workflow](#reflexion-workflow).

### 3. Before finishing a task — reflect and update docs

Review the session. If you discovered a new API behavior, gotcha, or reusable pattern
that is **not** already in `docs/known-issues.md` or `docs/common-patterns.md`, and
the discovery is **generally applicable** (not specific to one app or one user's
config), update the relevant docs file and append an entry to `docs/CHANGELOG.md`.
Otherwise do nothing.

---

## Python Script Standards

*Applies when touching `scripts/**/*.py`.*

Python 3.9+ (3.12 recommended). Always use the project venv — see
[Project Environment](#project-environment).

### Environment variables

Auth vars use the `X_` prefix, matching the HTTP headers with dashes→underscores:

- `X_CP_API_ID`, `X_CP_API_KEY` — Cradlepoint API credentials
- `X_ECM_API_ID`, `X_ECM_API_KEY` — ECM API credentials
- `NCM_API_TOKEN` — Bearer token for the v3 API (optional)

**Do NOT use the unprefixed `CP_API_ID` form.**

Scripts must call `check_env()` from `scripts/utils/env_check.py`, which loads `.env`
on import and prints OS-specific instructions when vars are missing. Windows users:
see `WINDOWS_PYTHON_SETUP.md`.

### File structure template

```python
"""Script description."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.env_check import check_env
from utils.credentials import get_credentials
from utils.session import APISession
from utils.logger import get_logger

def main():
    check_env()  # Exits with instructions if vars missing
    # ... implementation

if __name__ == '__main__':
    main()
```

Available helpers in `scripts/utils/`: `env_check.py`, `env_status.py`,
`credentials.py`, `session.py`, `logger.py`, `timeuuid_endpoint.py`.

### Rules

- **Auth** — never hardcode keys. Use env vars or `scripts/utils/credentials.py`.
- **Error handling** — wrap API calls in try/except. Retry on 408, 429, 503, 504 with
  exponential backoff.
- **Output** — CSV for tabular data, JSON for structured. Print progress on long
  operations. Store exports in `scripts/script_manager/csv_files/`.
- **Dependencies** — check `requirements.txt` before adding new ones.
- **Web servers** — always set `socketserver.TCPServer.allow_reuse_address = True`
  before creating the instance.

---

## NCM API Development

*Applies when touching Python under `scripts/`, `ncm/`, `ncm2/`, or `web_apps/`.*

### Documentation lookup

Before writing code, consult `docs/`:

| File | Covers |
|---|---|
| `api-overview.md` | Auth, base URLs, pagination, filtering |
| `api-v2-endpoints.md` / `api-v3-endpoints.md` | Endpoint details |
| `api-v2-full-reference.md` | Full v2 reference |
| `api-configuration.md` | Device/group config push |
| `api-webhooks.md` | Webhook setup |
| `ncm-sdk-reference.md` | Python SDK methods |
| `common-patterns.md` | Reusable code patterns |
| `known-issues.md` | Gotchas and workarounds |
| `api-deprecations.md` | Deprecated endpoints to avoid |

### Approach selection

1. **NCM SDK** (`from ncm import ncm`) — preferred. Handles pagination, retries, and
   auth. Always read `ncm/ncm/ncm.py` to discover existing methods before writing
   custom code.
2. **`scripts/utils/session.py`** — direct API calls with automatic retry and
   pagination.
3. **Raw `requests`** — only when the SDK and session helper don't cover the case.

### Endpoint routing (task → doc → SDK)

| Task | Doc | SDK methods |
|------|-----|-------------|
| Routers | v2 → routers | `get_routers()`, `get_router_by_id()` |
| Router state | v2 → router_state_samples | `get_router_state_samples()` |
| Push device config | api-configuration | `patch_configuration_managers()`, `put_configuration_managers()` |
| Push group config | api-configuration | `patch_group_configuration()`, `put_group_configuration()` |
| Locations | v2 → locations | `get_locations()`, `get_historical_locations()` |
| Alerts | v2 → alerts | `get_alerts()`, `get_router_alerts()` |
| Webhooks | api-webhooks | Direct API: `alert_push_destinations` |
| Groups | v2 → groups | `get_groups()`, `create_group_by_parent_id()` |
| Net devices | v2 → net_devices | `get_net_devices()`, `get_net_device_metrics()` |
| Cellular health | v2 → net_device_health | `get_net_device_health()` |
| Cellular metrics | v2 → net_device_metrics | `get_net_devices_metrics_for_wan()`, `get_net_devices_metrics_for_mdm()` |
| Signal/usage | v2 → net_device_signal/usage | `get_net_device_signal_samples()`, `get_net_device_usage_samples()` |
| Firmware | v2 → firmwares | `get_firmwares()` |
| Reboot | v2 → reboot_activity | `reboot_device()`, `reboot_group()` |
| Speed tests | v2 → speed_test | `create_speed_test()` |
| Users | v3 → users | `get_users()`, `create_user()` |
| Subscriptions | v3 → subscriptions | `get_subscriptions()`, `regrade()` |
| Private cellular | v3 → private_cellular_* | `get_private_cellular_networks()` |
| NCX sites/resources | v3 → exchange_* | `get_exchange_sites()`, `create_exchange_site()` |
| CSV export | common-patterns | `export_to_csv()` pattern |
| Batch ops | common-patterns | `batch_operation()` pattern |

v3 endpoints require `NCM_API_TOKEN`. If it is absent, say so rather than letting the
call fail opaquely.

### Critical rules

1. **Trailing slash** — ALL v2 URLs must end with `/`.
2. **Config manager ID ≠ Router ID** — look up the config manager ID first.
3. **PATCH vs PUT** — PATCH merges, PUT replaces. Use PATCH for incremental changes.
4. **`_id_` fields** — include the UUID `_id_` inside the object when using UUID keys.
5. **Deprecations** — verify an endpoint isn't deprecated before using it.
6. **Retries** — exponential backoff on transient errors.
7. **Pagination** — always handle it for list endpoints (the SDK does this
   automatically).

### Quality gates

Before considering an NCM app complete:

1. Runs without errors
2. Proper auth on all API calls
3. Trailing slashes on v2 URLs
4. Pagination handled for lists
5. Retry logic implemented
6. No deprecated endpoints used

Then run the reflexion step — see [Reflexion Workflow](#reflexion-workflow).

---

## Web UI Standards

*Applies when touching `*.html`, `*.css`, or anything under `web_apps/`.*

### Style foundation

All web UIs must use the project template as the style base:

- HTML: `web_apps/web_app_template/index.html`
- CSS: `web_apps/script_manager/static/css/style.css`
- JS: `web_apps/script_manager/static/js/app.js`
- Logos: `web_apps/script_manager/static/logo.png` / `logo_dark.png`

Read these files for the full set of CSS custom properties, layout patterns, and
component styles.

### Layout structure

`app-container → app-header → app-main → sidebar + content-area`

Components available in the template CSS: panels, cards, buttons
(primary/secondary/danger/sm), form inputs, modals (standard/large), tables with
sticky headers, file upload areas, toasts, empty states.

### Dark mode (required)

Every web app must support light/dark mode:

- Toggle via a `body.dark-mode` class
- Button with id `darkModeToggle` in the header
- CSS vars in `:root` (light), overridden in `body.dark-mode`
- Logo swap: `body.dark-mode .app-logo { content: url('/static/logo_dark.png'); }`
- Persist the preference in `localStorage`
- Use `var(--*)` properties for all colors — never hardcode

### Responsive

Breakpoints at 1024px and 768px. The sidebar collapses on smaller screens.

### Dashboard pattern

For data-driven dashboards, use `web_apps/cellular_health_dashboard/` as the
reference — `serve.py` (FastAPI) for the backend, `index.html` for the frontend.

Required dashboard features:

1. **Settings modal** (gear icon) — API key inputs (`X_CP_API_ID`, `X_CP_API_KEY`,
   `X_ECM_API_ID`, `X_ECM_API_KEY`, optionally `NCM_API_TOKEN`), named profiles
   (save/load/delete via `profiles.json`), "Apply & Refresh" button, display options
2. **Sortable columns** — click toggles asc/desc with an arrow indicator;
   document-level event delegation; respects grouping
3. **Search box** — full-text across key columns, clicking text cells auto-populates,
   clear button
4. **Stat cards as filters** — summary cards filter the table on click, highlighted
   when active, click again to clear
5. **Export CSV** — filtered/sorted data as a downloadable `.csv`
6. **Export PDF** — jsPDF + AutoTable: branded header, summary stats, color-coded
   columns, alternating rows, page numbers
7. **Grouping** (where applicable) — alternating shading, toggle in Display Options,
   default on, persisted in `localStorage`

Backend routes:

```
GET    /                        → serve index.html
GET    /api/data                → main data endpoint
GET|POST|DELETE /api/profiles   → profile CRUD
POST   /api/profiles/load       → load profile into env
GET    /api/profiles/current    → current env credentials
POST   /api/credentials/apply   → apply without saving
       /static                  → mount for shared logos
```

**All `@app` routes must be defined BEFORE `uvicorn.run()`, which blocks forever.**

These dashboards bind a local port with no authentication. That is fine for localhost
use, but say so if a user asks about exposing one on a network — credentials in the
Settings panel would be reachable by anyone who can hit the port.

Frontend CDN libraries:

- jsPDF: `cdnjs.cloudflare.com/ajax/libs/jspdf/2.5.1/jspdf.umd.min.js`
- AutoTable: `cdnjs.cloudflare.com/ajax/libs/jspdf-autotable/3.8.2/jspdf.plugin.autotable.min.js`
- Inter font: `fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap`

---

## Environment Setup Walkthrough

*Applies when the user asks to "set up", "install dependencies", or says imports or
credentials are broken.*

1. **Pick the launcher.** `python3` on macOS/Linux, `python` on Windows. Never assume
   the venv exists yet — use the system launcher for this step.

2. **Run the non-interactive setup** from the workspace root:

   ```bash
   python3 setup_env.py --skip-credentials       # macOS / Linux
   python setup_env.py --skip-credentials        # Windows
   ```

   This creates `.venv`, upgrades pip, installs `requirements.txt`, and verifies that
   every required package imports. It never prompts, so it is safe from a tool call.

3. **Read the output and fix failures.** Re-run until it exits cleanly.
   - `Python 3.9+ is required` → tell the user to install a newer Python. On Windows,
     point them at `WINDOWS_PYTHON_SETUP.md`.
   - venv creation failed on Linux → `sudo apt install python3-venv`.
   - pip install failed → usually network or proxy. Show the pip error.
   - Missing packages after install → run the suggested `pip install` and retry.

4. **Report status:** `python3 setup_env.py --check`

5. **Credentials — never collect these in chat.** API keys must not end up in the
   conversation transcript. If `--check` reports missing credentials, tell the user to
   run this in their own terminal, where input is hidden:

   ```bash
   python3 setup_env.py --credentials-only       # macOS / Linux
   python setup_env.py --credentials-only        # Windows
   ```

   Also mention that dashboard apps accept credentials through their in-app Settings
   panel as an alternative.

6. **Close with a short summary:** what is ready, what is still missing, and two or
   three concrete prompts they could try next, such as:
   - "Build a dashboard showing routers with poor signal"
   - "Export all my routers to CSV"
   - "Show me which devices have expiring subscriptions"

---

## Reflexion Workflow

*Applies on task completion, or when the user asks for the full self-improving docs
loop.*

```
Request → Consult Docs → Code → Test → Fix → Reflect → Update Docs
              ↑                                            |
              └────────────────────────────────────────────┘
```

1. **Understand** — identify the endpoints needed. Check `docs/api-overview.md` and
   the [endpoint routing table](#endpoint-routing-task--doc--sdk).
2. **Check known issues** — read `docs/known-issues.md` to avoid known pitfalls.
3. **Write code** — follow `docs/common-patterns.md`. Use the NCM SDK when possible.
   Include error handling and retries.
4. **Test** — run the code. Check for syntax, import, and runtime errors. Verify the
   output.
5. **Fix** — diagnose and fix errors iteratively. Note any doc gaps found.
6. **Reflect and update** — see below.

### When to update docs

Update if you:

- discovered undocumented API behavior
- found a documentation error
- created a reusable pattern
- hit a gotcha others should know about

Skip if the discovery is app-specific, a user-specific config issue, or already
documented.

### What to update

| Discovery | Target file |
|-----------|-------------|
| New gotcha | `docs/known-issues.md` → "Discovered Issues Log" |
| Reusable pattern | `docs/common-patterns.md` |
| Doc error/addition | The relevant `docs/*.md` file |
| New endpoint routing | This file's routing table, and `.kiro/steering/ncm-api-development.md` |
| Any change | Log it in `docs/CHANGELOG.md` |

Formats:

- `known-issues.md`: `### [Title] (discovered YYYY-MM-DD)` plus description and
  workaround
- `CHANGELOG.md`: `## YYYY-MM-DD — [Description]` plus a bullet list of changes

---

## Keeping this file in sync

`.kiro/steering/*.md` and this file describe the same rules for different tools. When
you change one, change the other:

| Kiro steering file | Section here |
|---|---|
| `project-setup.md` (always) | Project Environment |
| `code-standards.md` (`scripts/**/*.py`) | Python Script Standards |
| `ncm-api-development.md` (fileMatch) | NCM API Development |
| `web-ui-standards.md` (fileMatch) | Web UI Standards |
| `setup-environment.md` (manual) | Environment Setup Walkthrough |
| `reflexion-workflow.md` (manual) | Reflexion Workflow |

| Kiro hook | Section here |
|---|---|
| `check-environment-on-start.json` (SessionStart) | Automation Rules #1 |
| `fix-errors-after-run.json` (PostToolUse) | Automation Rules #2 |
| `reflexion-update-docs.json` (Stop) | Automation Rules #3 |
