---
inclusion: auto
description: Code standards for NCM scripts — virtual environment usage, required environment variables, file structure template, authentication, error handling, and output conventions.
---

# Code Standards for NCM Scripts

## Virtual Environment

**Always use the project `.venv`**. Never run scripts with the system Python.

When running any script or command, use:
```bash
.venv/bin/python scripts/my_script.py
```

When installing packages:
```bash
.venv/bin/pip install -r requirements.txt
```

The venv uses Python 3.12 and is located at the project root `.venv/`.

## Required Environment Variables

All scripts require these environment variables for API authentication:

| Variable | Description |
|----------|-------------|
| `X_CP_API_ID` | Cradlepoint API ID |
| `X_CP_API_KEY` | Cradlepoint API Key |
| `X_ECM_API_ID` | ECM API ID |
| `X_ECM_API_KEY` | ECM API Key |

Optional (for v3 API):

| Variable | Description |
|----------|-------------|
| `NCM_API_TOKEN` | Bearer token for API v3 |

**Important**: The env var names use the `X_` prefix (matching the HTTP header names
`X-CP-API-ID`, etc. with dashes replaced by underscores). Do NOT use the unprefixed
`CP_API_ID` form — that is incorrect.

### If env vars are not set, scripts must detect this and print setup instructions.

Use the helper at `scripts/utils/env_check.py` (see below) to validate at script startup.

### How to set env vars by OS:

**Recommended: Use the setup script**
```bash
.venv/bin/python setup_env.py
```
This prompts for all keys (including v3 token), injects them into the `.venv/bin/activate`
scripts, and they load automatically every time you `source .venv/bin/activate`.
Run it again anytime to update credentials.

**Manual setup — macOS / Linux (bash/zsh):**
```bash
export X_CP_API_ID="your_cp_api_id"
export X_CP_API_KEY="your_cp_api_key"
export X_ECM_API_ID="your_ecm_api_id"
export X_ECM_API_KEY="your_ecm_api_key"
export NCM_API_TOKEN="your_v3_token"  # optional, for v3 API
```
To persist, add these to `~/.zshrc` (macOS) or `~/.bashrc` (Linux).

**Windows (PowerShell):**
```powershell
$env:X_CP_API_ID = "your_cp_api_id"
$env:X_CP_API_KEY = "your_cp_api_key"
$env:X_ECM_API_ID = "your_ecm_api_id"
$env:X_ECM_API_KEY = "your_ecm_api_key"
$env:NCM_API_TOKEN = "your_v3_token"  # optional, for v3 API
```
To persist, use System Properties → Environment Variables, or add to your PowerShell profile.

**Windows (Command Prompt):**
```cmd
set X_CP_API_ID=your_cp_api_id
set X_CP_API_KEY=your_cp_api_key
set X_ECM_API_ID=your_ecm_api_id
set X_ECM_API_KEY=your_ecm_api_key
set NCM_API_TOKEN=your_v3_token  &REM optional, for v3 API
```

## File Structure

All new scripts should follow this structure:
```python
"""
Script description.
"""
import os
import sys

# Add project root to path if needed
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.env_check import check_env
from utils.credentials import get_credentials
from utils.session import APISession
from utils.logger import get_logger

def main():
    """Main entry point."""
    check_env()  # Always call first — exits with instructions if vars missing
    # ... implementation

if __name__ == '__main__':
    main()
```

## Authentication

- Never hardcode API keys in source files
- Use environment variables (preferred) or `scripts/utils/credentials.py` as fallback
- For the NCM SDK: pass keys as a dictionary
- For direct API calls: use `scripts/utils/session.py`

## Error Handling

- Always wrap API calls in try/except
- Implement retry logic for transient errors (408, 429, 503, 504)
- Log errors with context (which endpoint, what parameters)

## Output

- Use CSV for tabular data exports
- Use JSON for structured data
- Print progress for long-running operations
- Store output files in `scripts/script_manager/csv_files/` when using script_manager

## Dependencies

- Core: `requests`, `ncm` (SDK)
- Check `requirements.txt` before adding new dependencies
- If a new dependency is needed, add it to `requirements.txt`

## Web Servers (socketserver / http.server)

When using Python's built-in `socketserver.TCPServer` for development web apps:
- **Always set `allow_reuse_address = True`** before creating the server instance.
  Without this, the port stays locked after Ctrl+C and the script fails with
  "Port already in use" on restart.

```python
socketserver.TCPServer.allow_reuse_address = True
with socketserver.TCPServer(("", PORT), MyHandler) as httpd:
    httpd.serve_forever()
```
