---
inclusion: always
description: How this workspace is set up and how to run its Python code on macOS, Linux and Windows.
---

# Project Environment

This repo uses a project-local virtual environment at `.venv/`. Always use it.
Never invoke system Python for project code.

## Interpreter paths

| Platform | Interpreter | Activate |
|---|---|---|
| macOS / Linux | `.venv/bin/python` | `source .venv/bin/activate` |
| Windows PowerShell | `.venv\Scripts\python.exe` | `.venv\Scripts\Activate.ps1` |
| Windows cmd | `.venv\Scripts\python.exe` | `.venv\Scripts\activate.bat` |

When running commands for the user, prefer the full interpreter path over
activating a shell. Activation does not persist between tool calls.

```
.venv/bin/python scripts/get.py                          # macOS / Linux
.venv\Scripts\python.exe scripts\get.py                  # Windows
```

Detect the platform before choosing a path. Do not hardcode `.venv/bin`.

## Setup

`setup_env.py` is the single entry point. It creates the venv, upgrades pip,
installs `requirements.txt`, stores credentials, and verifies the result.

```
python3 setup_env.py                      # full interactive setup (user runs this)
python3 setup_env.py --skip-credentials   # safe to run from a tool call
python3 setup_env.py --credentials-only    # re-enter credentials (needs a terminal)
python3 setup_env.py --check              # report status, change nothing
```

Use `python` instead of `python3` on Windows.

Never run bare `setup_env.py` from a tool call — it prompts for credentials and
will look like it has hung. Use `--skip-credentials`.

For a guided setup walkthrough, the user can pull in `#setup-environment`.

## Credentials

Credentials live in `.env` at the repo root (gitignored, `0600` on POSIX):

- `X_CP_API_ID`, `X_CP_API_KEY` — required
- `X_ECM_API_ID`, `X_ECM_API_KEY` — required
- `NCM_API_TOKEN` — optional, needed only for v3 endpoints

`setup_env.py` also injects them into every venv activate script, so both
activated shells and non-activated runs work on any platform.

Scripts pick them up automatically: importing `scripts/utils/env_check.py` loads
`.env` into `os.environ` using a stdlib parser. Real environment variables take
precedence over `.env`.

Rules:
- Never ask the user to paste API keys into chat. Direct them to
  `setup_env.py --credentials-only`, where input is hidden, or to a dashboard's
  Settings panel.
- Never print, log, echo, or commit credential values.
- Never write credentials into source files.

## Adding dependencies

Add the package to `requirements.txt`, then install it into the venv:

```
.venv/bin/python -m pip install -r requirements.txt
```

If you import a third-party package in new code, confirm it is in
`requirements.txt`. A missing entry breaks setup for everyone who clones fresh.

## Running web apps

Web apps live in `web_apps/<name>/`. Each has a `serve.py` and a fixed port
(see `README.md`). Start them in the background, not the foreground, and tell
the user the URL. Ports in use: `lsof -ti:<port> | xargs kill` on macOS/Linux,
`netstat -ano | findstr :<port>` then `taskkill /PID <pid> /F` on Windows.
