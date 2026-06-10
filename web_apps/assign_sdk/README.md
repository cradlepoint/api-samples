# Assign SDK App to Groups

A web-based tool for assigning SDK application versions to router groups via the NCM API v2.

<img width="1532" height="843" alt="image" src="https://github.com/user-attachments/assets/7d2ad7aa-3983-48b9-9291-f02119d53f10" />

## Quick Start

```bash
python3 serve.py    # macOS/Linux
python serve.py     # Windows
```

That's it. On first run the script will:

1. Install the `requests` package if it's not already available
2. Prompt for your API credentials if they're not set
3. Save credentials to a `.env` file so you won't be asked again
4. Start the web server at http://localhost:9000

## Features

- Lists all SDK apps and their versions from `device_apps/` and `device_app_versions/`
- Displays all groups with checkbox selection and pagination
- "Select All" selects groups across all pages, not just the current page
- Assigns the selected app version to all selected groups via `device_app_bindings/`
- Logs all assignment results (success/failure) to a datetime-stamped log file

## Requirements

- Python 3.10+
- NCM API v2 credentials

## API Credentials

Credentials are resolved in this order:

1. Hardcoded values in `serve.py` (if you fill in the placeholders)
2. Environment variables (`CP_API_ID`, `CP_API_KEY`, `ECM_API_ID`, `ECM_API_KEY`)
3. `.env` file in this directory (auto-created on first run)

## Files

| File | Purpose |
|------|---------|
| `serve.py` | Web server, API logic, and credential management |
| `index.html` | Frontend UI |
| `requirements.txt` | Python dependencies (optional — auto-installed if missing) |

## Log Files

Each assignment run creates a log file in the `logs/` directory:

```
logs/assign_sdk_YYYYMMDD_HHMMSS.log
```
