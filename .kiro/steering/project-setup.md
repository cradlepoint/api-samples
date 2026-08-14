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

**Default to activating the venv, then calling `python3` (`python` on Windows).**
Activation is the only thing that picks up credentials exported into the activate
scripts, and it is what the user does in their own terminal, so it matches how
they will run the code.

```
source .venv/bin/activate && python3 scripts/get.py           # macOS / Linux
.venv\Scripts\Activate.ps1; python scripts\get.py             # Windows PowerShell
.venv\Scripts\activate.bat && python scripts\get.py           # Windows cmd
```

Chain activation into the same command, since activation does not persist between
tool calls. Use `;` rather than `&&` in PowerShell.

The full interpreter path is the fallback, for cases where activation is
unavailable or you specifically need to bypass it:

```
.venv/bin/python scripts/get.py                          # macOS / Linux
.venv\Scripts\python.exe scripts\get.py                  # Windows
```

Be aware of what it costs: `.venv/bin/python` runs the right interpreter but
skips the activate script, so any credential only exported there is absent. If
`.env` is missing, that means no credentials at all — long-running servers then
boot fine and fail on every API call with no startup signal. `setup_env.py --check`
reports both conditions.

Detect the platform before choosing either form. Do not hardcode `.venv/bin`.

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

Never run bare `setup_env.py` from a tool call. Use `--skip-credentials`.

The reason, since it is easy to talk yourself out of: interactivity is gated on
`interactive = sys.stdin.isatty() and not args.skip_credentials`. Agent tool
calls **do** get a tty, so `isatty()` is True and the bare form takes the
interactive branch. It then blocks in `getpass` on a terminal with no human
attached — the user never sees the prompt, because command output only comes back
when the command exits. The result is a hang until timeout, not a graceful skip.

Do not use the `--skip-credentials` run as evidence about `isatty`. That flag
forces `interactive` to False by itself, so its "non-interactive mode" message
says nothing about whether a terminal was present.

For a guided setup walkthrough, the user can pull in `#setup-environment`.

### Missing `.venv`: set it up, do not ask

If `.venv/` does not exist, treat setup as part of the task and run it
immediately. Do not ask permission, do not tell the user to run it themselves,
and do not attempt the original request first and let it fail on a missing
interpreter.

Trigger this whenever any of the following is true:

- the session-start environment check reports `venv: MISSING`
- `.venv/` is absent and you are about to run project Python, start a web app,
  or install a dependency
- the user reports broken imports, `ModuleNotFoundError`, or "command not found"
  for the venv interpreter

Procedure:

1. Detect the platform and pick the system launcher — `python3` on macOS/Linux,
   `python` on Windows. The venv interpreter does not exist yet, so system
   Python is correct *for this step only*.
2. From the workspace root, run:

   ```
   python3 setup_env.py --skip-credentials       # macOS / Linux
   python setup_env.py --skip-credentials        # Windows
   ```

   This creates `.venv`, upgrades pip, installs `requirements.txt`, and verifies
   the imports.
3. Read the output and fix failures, then re-run until it exits cleanly. See
   `#setup-environment` for the specific failure modes and their remedies.
4. Confirm with `setup_env.py --check`.
5. Then carry on with what the user originally asked for, using the venv
   interpreter. Report the setup in a sentence or two — it is a means to an end,
   not the headline.

**Where this stops.** Steps 1-4 are the whole of what can be automated.
Credentials cannot be, because `--credentials-only` needs a real terminal and
keys must never pass through chat. So when `--check` reports credentials
missing, finish by telling the user to run this themselves:

```
python3 setup_env.py --credentials-only       # macOS / Linux
python setup_env.py --credentials-only        # Windows
```

Be straight about the consequence: dependencies are ready and code will import,
but every API call fails until those keys are in place. Do not describe the
environment as "ready" while credentials are still missing.

## Credentials

Credentials live in `.env` at the repo root (gitignored, `0600` on POSIX):

- `X_CP_API_ID`, `X_CP_API_KEY` — required
- `X_ECM_API_ID`, `X_ECM_API_KEY` — required
- `NCM_API_TOKEN` — optional, needed only for v3 endpoints

`setup_env.py` also injects them into every venv activate script it finds
(`activate`, `activate.fish`, `activate.csh`, `Activate.ps1`, `activate.bat`), so
both activated shells and non-activated runs work on any platform. It reports each
script by name with the outcome, reads the values back to confirm they landed, and
warns if a script that exists did not receive them.

The two channels can still drift — for example if credentials were last written by
an older version of `setup_env.py`, or if `.env` was deleted. `setup_env.py --check`
reports `.env` presence and per-script credential status; re-run
`setup_env.py --credentials-only` to bring everything back in sync.

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
