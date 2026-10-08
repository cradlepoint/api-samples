---
inclusion: manual
description: Run the full project environment setup (venv, dependencies, credentials). Pull in with #setup-environment to have Kiro set up the workspace on demand.
---

# Set Up Project Environment

The full setup procedure. Run it when the user pulls in `#setup-environment`, asks to
"set up" or "install dependencies", reports broken imports or credentials, or whenever
`.venv/` is missing (see `#project-setup` for the triggers — in that case run this
without asking first).

Interpreter paths, credential variable names and the handling rules live in
`#project-setup` and are not repeated here.

## Procedure

1. **Pick the launcher.** `python3` on macOS/Linux, `python` on Windows. The venv
   interpreter does not exist yet, so system Python is correct *for this step only*.

2. **Run the non-interactive setup** from the workspace root:

   ```
   python3 setup_env.py --skip-credentials       # macOS / Linux
   python setup_env.py --skip-credentials        # Windows
   ```

   This creates `.venv`, upgrades pip, installs `requirements.txt`, and verifies that
   every required package imports. It never prompts, so it is safe from a tool call.
   Add `--upgrade` to refresh already-installed packages, `--quiet` to trim output.

3. **Read the output and fix failures.** Re-run until it exits cleanly.
   - `Python 3.9+ is required` → tell the user to install a newer Python. On Windows
     point them at `WINDOWS_PYTHON_SETUP.md`.
   - venv creation failed on Linux → `sudo apt install python3-venv`.
   - pip install failed → usually network or proxy. Show the pip error.
   - Missing packages after install → run the suggested `pip install` and retry.

4. **Report status:** `python3 setup_env.py --check`. This reports `.env` presence and
   per-script credential status. The two channels can drift — if credentials were last
   written by an older `setup_env.py`, or `.env` was deleted — and
   `--credentials-only` brings them back in sync.

5. **Credentials — never collect these in chat.** API keys must not enter the
   transcript. If `--check` reports them missing, tell the user to run this in their
   own terminal, where input is hidden:

   ```
   python3 setup_env.py --credentials-only       # macOS / Linux
   python setup_env.py --credentials-only        # Windows
   ```

   Mention that dashboard apps also accept credentials through their in-app Settings
   panel.

6. **Close with a short summary:** what is ready, what is still missing, and two or
   three concrete prompts to try next, such as:
   - "Build a dashboard showing routers with poor signal"
   - "Export all my routers to CSV"
   - "Show me which devices have expiring subscriptions"

   Steps 1–4 are the whole of what can be automated. Do not call the environment
   "ready" while credentials are missing — be straight that dependencies are installed
   and code will import, but every API call fails until the keys are in place. When
   setup was incidental to another request, report it in a sentence or two; it is a
   means to an end, not the headline.

## Why the bare command is forbidden

`#project-setup` says never to run bare `setup_env.py` from a tool call. The reason,
since it is easy to talk yourself out of: interactivity is gated on
`interactive = sys.stdin.isatty() and not args.skip_credentials`. Agent tool calls
**do** get a tty, so `isatty()` is True and the bare form takes the interactive
branch. It then blocks in `getpass` on a terminal with no human attached — the user
never sees the prompt, because command output only comes back when the command exits.
The result is a hang until timeout, not a graceful skip.

Do not treat a successful `--skip-credentials` run as evidence about `isatty`. That
flag forces `interactive` to False by itself, so its "non-interactive mode" message
says nothing about whether a terminal was present.
