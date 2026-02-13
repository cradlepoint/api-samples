# Private Router Manager

A web application for managing Cradlepoint routers in isolated networks. Upload a CSV of router IPs, configure credentials, and deploy licenses, NCOS firmware, configuration files, or SDK apps—or check online status—across all routers at once.

<img width="1371" height="855" alt="image" src="https://github.com/user-attachments/assets/a163305e-e604-4fc3-bdf9-464e0f5527af" />

## Features

### CSV Management

- **Open** — Load a CSV from the `csv/` folder. Your CSV must include an `ip_address` or `ip address` column.
- **Upload** — Upload a CSV file from your computer.
- **Download** — Download the current table as CSV.
- **New CSV** — Start fresh with a single empty row.
- **Save / Save As** — Save to the `csv/` folder. Credentials and last-opened file are remembered.
- **Add Row / Add Column** — Edit the table directly.

### Credentials & Port

- **Same credentials for all routers** — Use one username/password for every router.
- **Same port for all routers** — Use one port (default 8080) for every router.
- When unchecked, your CSV can have `username`, `password`, and `port` columns per row.
- Credentials are stored locally in `credentials_config.json`.

### Deployment Types

| Type | Purpose |
|------|---------|
| **Online Status** | Check uptime of each router via `/api/status/system/uptime`. Results shown in a new column. Saves CSV when done. |
| **Licenses** | Deploy `.lic` files to each router via the `feature` endpoint. |
| **NCOS** | Deploy firmware `.bin` files or download from Cradlepoint ECM. |
| **Configuration** | Deploy config `.bin` files via `config_save` endpoint. |
| **SDK Apps** | Deploy `.tar.gz` archives via SCP to `/app_upload`. Uses SSH port 22 (configurable). |

Deployment results (Licenses, NCOS, Configuration, SDK Apps) are written into a new CSV column per run. The column header includes timestamp, deployment type, and filename (e.g. `2026-02-13 12:28 - SDK App Deployment - hello_world.tar.gz`). Each row shows the result for that router. The CSV is saved automatically when deployment completes.

### NCOS Download

To download NCOS from Cradlepoint ECM:

1. Set API keys (env vars or `api_keys.json`):
   - `X_CP_API_ID`, `X_CP_API_KEY`
   - `X_ECM_API_ID`, `X_ECM_API_KEY`
2. Enter version (e.g. `7.22.60`) and optional model (e.g. `ibr900`).
3. Search, select a firmware, and download. Files are saved to the `NCOS/` folder.

### SDK Apps

- Supported format: `.tar.gz` archives.
- Deployed via SCP to `/app_upload` on each router.
- **macOS:** Uses bundled `sshpass` from `bin/macos/{arm64,x86_64}/` if present, otherwise system `sshpass`.
- **Linux:** Uses system `sshpass`.
- **Windows:** Uses PuTTY `pscp.exe`.
- "Lost connection" after transfer is treated as success (router may reboot).

## Folders

The app creates required folders automatically if they do not exist:

- `csv/` — CSV router lists
- `logs/` — Reserved for future use
- `licenses/` — License files
- `NCOS/` — Firmware images
- `configs/` — Configuration files
- `sdk_apps/` — SDK app archives

## Running

```bash
pip install -r requirements.txt
python app.py
```

Then open **http://localhost:9000** in your browser.

## Requirements

- Python 3.7+
- Flask, requests
- For SDK Apps: `sshpass` (macOS/Linux) or PuTTY `pscp` (Windows)
