---
inclusion: always
description: How this workspace is set up and how to run its Python code on macOS, Linux and Windows.
---

# Project Environment

Project-local venv at `.venv/`. Always use it; never system Python for project code.
Python 3.9+ (3.12 recommended).

## Running Python

**Prefer activating, then calling `python3` (`python` on Windows).** Activation picks
up credentials exported into the activate scripts and matches how the user runs code
in their own terminal. Activation does not persist between tool calls, so chain it
into the same command (`;` instead of `&&` in PowerShell).

```
source .venv/bin/activate && python3 scripts/get.py       # macOS / Linux
.venv\Scripts\Activate.ps1; python scripts\get.py         # Windows PowerShell
.venv\Scripts\activate.bat && python scripts\get.py       # Windows cmd
```

Direct interpreter path is the fallback when activation is unavailable or you need to
bypass it: `.venv/bin/python` (macOS/Linux), `.venv\Scripts\python.exe` (Windows).
It runs the right interpreter but skips the activate script, so credentials exported
only there are absent — and if `.env` is also missing, there are no credentials at
all. Long-running servers then boot clean and fail on every API call with no startup
signal.

Detect the platform before choosing a form. Do not hardcode `.venv/bin`.

## Credentials

`.env` at the repo root (gitignored, `0600` on POSIX). `setup_env.py` also injects
them into every venv activate script, so both activated and non-activated runs work.

- `X_CP_API_ID`, `X_CP_API_KEY` — required
- `X_ECM_API_ID`, `X_ECM_API_KEY` — required
- `NCM_API_TOKEN` — optional, v3 endpoints only. If absent, say so rather than
  letting a v3 call fail opaquely.

Use the `X_` prefix, matching the HTTP headers with dashes→underscores. **Never the
unprefixed `CP_API_ID` form.** Scripts pick these up automatically: importing
`scripts/utils/env_check.py` loads `.env` into `os.environ`. Real environment
variables take precedence over `.env`.

Rules:
- Never ask the user to paste API keys into chat. Direct them to
  `setup_env.py --credentials-only`, where input is hidden, or a dashboard's Settings
  panel.
- Never print, log, echo, or commit credential values.
- Never write credentials into source files.

## Setup

`setup_env.py` is the single entry point — creates the venv, upgrades pip, installs
`requirements.txt`, stores credentials, verifies the result. Use `python` instead of
`python3` on Windows.

```
python3 setup_env.py --check              # report status, change nothing
python3 setup_env.py --skip-credentials   # safe from a tool call
python3 setup_env.py --credentials-only   # needs a real terminal; user runs this
python3 setup_env.py                      # full interactive setup; user runs this
```

**Never run bare `setup_env.py` from a tool call — it hangs until timeout.** Tool
calls get a tty, so it takes the interactive branch and blocks in `getpass` with no
human attached and no visible prompt. Use `--skip-credentials`.

**If `.venv/` is missing, set it up immediately — do not ask.** Treat it as part of
the task rather than failing the original request on a missing interpreter. Triggers:
the session-start check reports `venv: MISSING`; `.venv/` is absent and you are about
to run project Python, start a web app, or install a dependency; or the user reports
broken imports, `ModuleNotFoundError`, or "command not found" for the venv
interpreter.

Full procedure, failure modes and remedies: `#setup-environment`. Credentials are the
one part that cannot be automated — keys must never pass through chat.

## Adding dependencies

Add to `requirements.txt`, then install into the venv:

```
.venv/bin/python -m pip install -r requirements.txt
```

If you import a third-party package in new code, confirm it is in `requirements.txt`.
A missing entry breaks setup for everyone who clones fresh. Each web app also has its
own `requirements.txt` listing only what that app imports.

## Running web apps

Web apps live in `web_apps/<name>/` and each has a fixed port. **Do not assume the
entry point is `serve.py`** — several apps use a different filename. `ls
web_apps/<name>/` settles it in one call; `web_apps/README.md` has the app, port and
entry-point table. Check, don't guess: that table and the directory have drifted
before.

Start them in the background, tell the user the URL, and pass `-u` when backgrounding
with redirected output. Without `-u` stdout is block-buffered, so the app's own
`print()` banner (including the URL) never reaches the log and a buffered diagnostic
can be lost on kill. Uvicorn still logs to stderr, which makes a working app look
half-broken — confirm by hitting the port rather than reading a missing banner as a
failed start.

Ports 8000 and 8065 are each shared by more than one app, so run those one at a time.
Freeing a port: `lsof -ti:<port> | xargs kill` on macOS/Linux; `netstat -ano | findstr
:<port>` then `taskkill /PID <pid> /F` on Windows.
