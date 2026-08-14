---
inclusion: manual
description: Run the full project environment setup (venv, dependencies, credentials). Pull in with #setup-environment to have Kiro set up the workspace on demand.
---

# Set Up Project Environment

Run this when the user pulls in `#setup-environment`, or any time they ask to
"set up", "install dependencies", or say that imports or credentials are broken.

## Procedure

1. **Pick the launcher.** `python3` on macOS/Linux, `python` on Windows.
   Never assume the venv exists yet — use the system launcher for this step.

2. **Run the non-interactive setup** from the workspace root:

   ```
   python3 setup_env.py --skip-credentials       # macOS / Linux
   python setup_env.py --skip-credentials        # Windows
   ```

   This creates `.venv`, upgrades pip, installs `requirements.txt`, and verifies
   that every required package imports. It never prompts, so it is safe to run
   from a tool call.

3. **Read the output and fix failures.** Re-run until it exits cleanly.
   - `Python 3.9+ is required` → tell the user to install a newer Python.
     On Windows point them at `WINDOWS_PYTHON_SETUP.md`.
   - venv creation failed on Linux → `sudo apt install python3-venv`.
   - pip install failed → usually network or proxy. Show the pip error.
   - Missing packages after install → run the suggested `pip install` and retry.

4. **Report status:**

   ```
   python3 setup_env.py --check
   ```

5. **Credentials — never collect these in chat.** API keys must not end up in
   the conversation transcript. If `--check` reports missing credentials, tell
   the user to run this in their own terminal, where input is hidden:

   ```
   python3 setup_env.py --credentials-only       # macOS / Linux
   python setup_env.py --credentials-only        # Windows
   ```

   Also mention that dashboard apps accept credentials through their in-app
   Settings panel as an alternative.

6. **Close with a short summary:** what is ready, what is still missing, and two
   or three concrete prompts they could try next, such as:
   - "Build a dashboard showing routers with poor signal"
   - "Export all my routers to CSV"
   - "Show me which devices have expiring subscriptions"

## Rules

- Never print or echo credential values.
- Do not run `setup_env.py` without a flag from a tool call — tool calls get a
  tty, so the bare form prompts for credentials and hangs until timeout with the
  user never seeing the prompt.
- If `.venv/` is missing, run this procedure without asking first. See the
  "Missing `.venv`" section of `project-setup.md`.
- After setup, always invoke project code through the venv interpreter
  (`.venv/bin/python` or `.venv\Scripts\python.exe`), never system Python.
