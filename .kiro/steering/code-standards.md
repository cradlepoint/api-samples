---
inclusion: fileMatch
fileMatchPattern: "scripts/**/*.py"
description: Code standards for NCM scripts — venv, env vars, file structure, auth, error handling.
---

# Code Standards for NCM Scripts

## Virtual Environment

Always use the project venv, never system Python. Python 3.9+ (3.12 recommended).

- macOS / Linux: `.venv/bin/python`, `.venv/bin/python -m pip`
- Windows: `.venv\Scripts\python.exe`, `.venv\Scripts\python.exe -m pip`

Detect the platform rather than hardcoding `.venv/bin`. See `#project-setup`.

## Required Environment Variables

Auth vars (prefix `X_`, matching HTTP headers with dashes→underscores):
- `X_CP_API_ID`, `X_CP_API_KEY` — Cradlepoint API credentials
- `X_ECM_API_ID`, `X_ECM_API_KEY` — ECM API credentials
- `NCM_API_TOKEN` — Bearer token for v3 API (optional)

**Do NOT use unprefixed `CP_API_ID` form.**

Setup: run `python3 setup_env.py` (`python setup_env.py` on Windows). It writes
`.env` at the repo root and injects the vars into every venv activate script
(bash/zsh, fish, csh, PowerShell, cmd). Windows users see `WINDOWS_PYTHON_SETUP.md`.

Scripts must call `check_env()` from `scripts/utils/env_check.py`, which loads
`.env` on import and prints OS-specific instructions when vars are missing.

## File Structure Template

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

## Rules

- **Auth**: Never hardcode keys. Use env vars or `scripts/utils/credentials.py`.
- **Error handling**: Wrap API calls in try/except. Retry on 408, 429, 503, 504 with backoff.
- **Output**: CSV for tabular, JSON for structured. Print progress on long ops. Store exports in `scripts/script_manager/csv_files/`.
- **Dependencies**: Check `requirements.txt` before adding new ones.
- **Web servers**: Always set `socketserver.TCPServer.allow_reuse_address = True` before creating instance.
