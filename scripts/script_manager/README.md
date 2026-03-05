# Script Manager

A web-based CSV file editor and script manager for processing CSV files with Python scripts, specifically designed for NCM (Network Control Manager) API operations.

## Features

- **CSV File Management**: Load, edit, and save CSV files through a modern web interface
- **Script Management**: Create, edit, download, and execute Python scripts that process CSV files
- **API Key Management**: Securely set and manage API keys through the web interface
- **GitHub Integration**: Download scripts directly from GitHub URLs (supports individual files and folders)
- **NCM Library Integration**: Uses the `ncm` Python package for NCM API operations
- **Cross-Platform**: Works on Windows, macOS, and Linux

## Screenshots

<img width="1505" height="854" alt="image" src="https://github.com/user-attachments/assets/c9f60c4b-6058-4207-86c6-e8a8191d5841" />
<img width="1505" height="854" alt="image" src="https://github.com/user-attachments/assets/c512ead8-e481-4361-be73-7dc497fc13b0" />
<img width="1505" height="854" alt="image" src="https://github.com/user-attachments/assets/5f83ff59-57ec-49a2-ba69-f7c12ffb939d" />
<img width="1505" height="854" alt="image" src="https://github.com/user-attachments/assets/57599c80-f6dc-4b78-9ed9-0dc81e04f8a6" />
<img width="1505" height="854" alt="image" src="https://github.com/user-attachments/assets/7f37d4e6-15b2-4c46-887e-7b12b8ee5285" />



## Installation

1. **Clone or download this repository**

2. **Navigate to the project folder**:
   
   **Windows:**
   ```bash
   cd script_manager
   ```
   Or right-click in the project folder in File Explorer and select "Open in Terminal" or "Open PowerShell window here".
   
   **macOS/linux:**
   ```bash
   cd script_manager
   ```
   Or right-click on the project folder in Finder and select Services > New Terminal at Folder.

3. **Install Python dependencies**:
   
   **Windows/macOS/Linux:**
   ```bash
   pip install -r requirements.txt
   ```
   
   This will install:
   - `requests` - For HTTP requests and downloading scripts from GitHub
   - `ncm` - Cradlepoint NCM API client library

4. **Run the application**:
   
   **Windows:**
   ```bash
   python script_manager.py
   ```
   
   **macOS/Linux:**
   ```bash
   python script_manager.py
   ```

5. **Open your web browser** and navigate to:
   ```
   http://localhost:8000
   ```

## Usage

### Working with CSV Files

1. **Load a CSV file**: Click on a file from the list or upload a new one
2. **Edit data**: Modify cells directly in the web interface
3. **Save changes**: Click the save button to persist your changes
4. **Download**: Export your CSV file at any time

### Managing Scripts

1. **View available scripts**: All Python scripts in the `scripts/` directory are automatically listed
2. **Create new scripts**: Use the script editor to create new Python scripts
3. **Download from GitHub**: Paste a GitHub URL to download scripts directly
4. **Run scripts**: Select a script and CSV file, then execute them together
5. **Download results**: After running a script, you can download the results or updated CSV files

### Setting API Keys

The web interface allows you to securely set API keys as environment variables:

- `X_CP_API_ID` / `X_CP_API_KEY` - Cradlepoint API credentials
- `X_ECM_API_ID` / `X_ECM_API_KEY` - NCM API credentials
- `TOKEN` / `NCM_API_TOKEN` - NCM API token

**Note**: API keys are stored in environment variables for the current session only. They are not persisted between application restarts.

### Script Format

Scripts should follow a standardized format with detailed docstrings. See [SCRIPT_FORMAT_GUIDE.md](SCRIPT_FORMAT_GUIDE.md) for complete documentation on:
- Required docstring format
- CSV column naming conventions
- API key handling
- Script structure guidelines

## Project Structure

```
script_manager/
├── script_manager.py        # Main application file
├── requirements.txt         # Python dependencies
├── csv_files/               # Directory for CSV files
├── scripts/                 # Directory for Python scripts
│   ├── Configure Devices.py
│   ├── Create NCX Resources.py
│   ├── Create NCX Sites.py
│   ├── Create Users.py
│   ├── Get Router Status.py
│   ├── Regrade Subscriptions.py
│   ├── Set Router Fields.py
│   ├── Unlicense Devices.py
│   └── Unregister Routers.py
├── static/                  # Web interface files
│   ├── index.html
│   ├── css/
│   └── js/
└── README.md
```

## NCM Library

The application uses the `ncm` Python package (installed via `requirements.txt`) for interacting with the NCM API. This package is available on PyPI and provides support for both NCM API v2 and v3.

## Requirements

- Python 3.6 or higher
- `requests` library (installed via `requirements.txt`)
- `ncm` library (installed via `requirements.txt`)

## License

See [LICENSE](LICENSE) file for details.
