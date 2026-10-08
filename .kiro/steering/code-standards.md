---
inclusion: fileMatch
fileMatchPattern: "scripts/**/*.py"
description: Code standards for NCM scripts — file structure, helpers, auth, error handling, output.
---

# Code Standards for NCM Scripts

Venv usage, interpreter paths, credential variable names and setup are in
`#project-setup`. Windows users: `WINDOWS_PYTHON_SETUP.md`.

Every script must call `check_env()` from `scripts/utils/env_check.py`. It loads
`.env` on import and prints OS-specific instructions when variables are missing.

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

Helpers in `scripts/utils/`: `env_check.py`, `env_status.py`, `credentials.py`,
`session.py`, `logger.py`, `timeuuid_endpoint.py`.

## Rules

- **Auth**: never hardcode keys. Use env vars or `scripts/utils/credentials.py`.
- **Error handling**: wrap API calls in try/except. Retry on 408, 429, 503, 504 with
  exponential backoff.
- **Output**: CSV for tabular, JSON for structured. Print progress on long operations.
  Store exports in `web_apps/script_manager/csv_files/`.
- **Dependencies**: check `requirements.txt` before adding new ones.
- **Web servers**: always set `socketserver.TCPServer.allow_reuse_address = True`
  before creating the instance.
