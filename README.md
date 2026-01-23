# API Samples

A collection of Python scripts for interacting with Ericsson NetCloud Manager APIs.

## Getting Started

### Prerequisites

- Python 3.7 or higher
- Git (optional, for cloning the repository)

### Download and Extract the Repository

**Using Git (Recommended):**
```bash
git clone <repository-url>
cd api-samples
```

**Downloading as ZIP:**
1. Download the repository as a ZIP file
2. Extract the ZIP file to your desired location
3. Navigate to the extracted `api-samples` folder

```bash
cd path/to/extracted/api-samples
```

## Setup

### 1. Create a Python Virtual Environment

Creating a virtual environment isolates project dependencies from your system Python installation.

**Windows:**
```cmd
python -m venv .venv
.venv\Scripts\activate
```

**macOS (zsh):**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

After activation, you should see `(.venv)` at the beginning of your command prompt, indicating the virtual environment is active.

### 2. Install Dependencies

With your virtual environment activated, install the required packages:

```bash
pip install -r requirements.txt
```

This will install all required dependencies including:
- `ncm` - Ericsson NetCloud Manager Python library
- `flask` - Web framework (for CSV Script Manager)
- `werkzeug` - WSGI utilities
- `python-dateutil` - Date parsing utilities

### 3. Set API Keys as Environment Variables

You need to set your NCM API credentials as environment variables. The scripts will automatically use these when running.

**Windows:**
```cmd
set X_CP_API_ID=your_api_id
set X_CP_API_KEY=your_api_key
set X_ECM_API_ID=your_ecm_api_id
set X_ECM_API_KEY=your_ecm_api_key
set TOKEN=your_ncm_api_v3_token
```

To make these persistent in Windows, go to System Properties > Environment Variables and add them there.

**macOS (zsh):**
```bash
export X_CP_API_ID="your_api_id"
export X_CP_API_KEY="your_api_key"
export X_ECM_API_ID="your_ecm_api_id"
export X_ECM_API_KEY="your_ecm_api_key"
export TOKEN="your_ncm_api_v3_token"
```

To make these persistent, add them to your `~/.zshrc`:
```bash
echo 'export X_CP_API_ID="your_api_id"' >> ~/.zshrc
echo 'export X_CP_API_KEY="your_api_key"' >> ~/.zshrc
echo 'export X_ECM_API_ID="your_ecm_api_id"' >> ~/.zshrc
echo 'export X_ECM_API_KEY="your_ecm_api_key"' >> ~/.zshrc
echo 'export TOKEN="your_ncm_api_v3_token"' >> ~/.zshrc
source ~/.zshrc
```

## Sample Scripts

This repository contains many sample scripts in the `scripts/` folder that demonstrate various API interactions and use cases. These scripts cover a wide range of functionality including:

- Router management and configuration
- Alert creation and management
- User management
- Location tracking and historical data export
- Device metrics and signal samples
- Configuration backups and restoration
- Subscription management
- Device licensing operations
- And much more

Browse the [scripts](scripts/) folder to explore all available sample scripts.

### Running Scripts

Make sure your virtual environment is activated before running scripts.

**Windows:**
```cmd
python script_name.py
```

**macOS:**
```bash
python3 script_name.py
```

Many scripts accept command-line arguments. Check the script's docstring or run it with `--help` (if supported) for usage information.

## CSV Script Manager

For a convenient web-based interface to manage CSV files, API keys, and run scripts, check out the CSV Script Manager.
> Want just the CSV Script Manager?  [Get it here!](https://github.com/phate999/csv_script_manager)

The CSV Script Manager provides:
- Web-based CSV file editor
- API key management interface
- Script execution interface
- Easy script management and organization
- Displays script instructions from docstrings

### Using CSV Script Manager

1. Navigate to the CSV Script Manager directory:
   ```bash
   cd scripts/csv_script_manager
   ```

2. Make sure your virtual environment is activated

3. Start the web server:

   **Windows:**
   ```cmd
   python csv_script_manager.py
   ```

   **macOS:**
   ```bash
   python3 csv_script_manager.py
   ```

4. Open your browser to `http://localhost:8000`

5. Use the web interface to:
   - Load and edit CSV files
   - Set API keys (stored in session)
   - Select and run scripts
   - View script documentation

### Available Scripts in CSV Script Manager

The CSV Script Manager includes several pre-configured scripts:

- **ncm_bulk_configure_devices.py** - Bulk configure multiple devices with custom configurations
- **ncm_v3_create_users.py** - Create and manage users in NCM API v3
- **ncm_v3_regrade_subscriptions_by_mac.py** - Apply or regrade device subscriptions by MAC address
- **ncm_v3_unlicense_devices_by_mac.py** - Unlicense devices by MAC address
- **ncm_get_router_status.py** - Get router status and information using identifiers
- **ncm_unregister_routers_batch.py** - Unregister routers in batches with logging

Each script includes detailed documentation in its docstring explaining the required CSV format and usage.

## Postman Collection

For a convenient way to test and explore the Ericsson NetCloud Manager APIs, you can use the **Ericsson NCM API Postman Collection**. This collection contains pre-configured API requests that you can use to interact with the APIs directly from Postman.

### Importing the Collection

1. Open Postman
2. Click **Import** in the top left corner
3. Select **File** or **Upload Files**
4. Navigate to and select the `Ericsson NCM API Postman Collection.json` file from this repository
5. Click **Import**

The collection will now appear in your Postman workspace. You can use it to explore and test the various API endpoints.

## Troubleshooting

### Virtual Environment Issues

**Problem:** `python` or `python3` command not found
- **Windows:** Make sure Python is installed and added to PATH
- **macOS:** Use `python3` explicitly, or install Python via Homebrew

**Problem:** Virtual environment activation fails
- Make sure you're in the correct directory when creating the virtual environment

### API Key Issues

**Problem:** Scripts report missing API keys
- Verify environment variables are set correctly
- Make sure your virtual environment is activated
- Check that variable names match exactly (case-sensitive on macOS)
- For CSV Script Manager, use the API Keys tab in the web interface

### Import Errors

**Problem:** `ModuleNotFoundError` when running scripts
- Make sure your virtual environment is activated
- Verify dependencies are installed: `pip install -r requirements.txt`
- Some scripts may require additional dependencies - check the script's docstring

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

See the [LICENSE](LICENSE) file for details.
