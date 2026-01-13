# CSV Script Manager

A web-based CSV file editor and script manager for processing CSV files with Python scripts.

## Features

- Load, edit, and save CSV files through a web interface
- Manage and execute Python scripts that process CSV files
- Download scripts from GitHub URLs
- Set and manage API keys

## Usage

Run the script to start the web server:

```bash
python3 csv_script_manager.py
```

Then open your browser to `http://localhost:8000`

## Requirements

- Python 3.6+
- requests (installed automatically with ncm package)

## Directory Structure

- `csv_files/` - Stores CSV files
- `scripts/` - Python scripts for processing CSV files
- `static/` - Web interface files

