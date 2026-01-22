# API Samples

A collection of Python scripts for interacting with Ericsson NetCloud Manager APIs.

<<<<<<< HEAD
## Getting Started

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

## Sample Scripts

This repository contains many sample scripts in the `scripts/` folder that demonstrate various API interactions and use cases. These scripts cover a wide range of functionality including:
=======
## Sample Scripts

This repository contains many sample scripts in the `scripts` folder that demonstrate various API interactions and use cases. These scripts cover a wide range of functionality including:
>>>>>>> af5e853d33494a8223053f6d3783621b840a69eb

- Router management and configuration
- Alert creation and management
- User management
- Location tracking and historical data export
- Device metrics and signal samples
- Configuration backups and restoration
- And much more

<<<<<<< HEAD
Browse the `scripts/` folder to explore all available sample scripts.

## CSV Script Manager

For a convenient web-based interface to manage CSV files, API keys, and run scripts, check out the [CSV Script Manager](scripts/csv_script_manager/README.md).
=======
Browse the [scripts](scripts/) folder to explore all available sample scripts.

## CSV Script Manager

For a convenient web-based interface to manage CSV files, API keys, and run scripts, check out the [CSV Script Manager](scripts/csv_script_manager).
>>>>>>> af5e853d33494a8223053f6d3783621b840a69eb

The CSV Script Manager provides:
- Web-based CSV file editor
- API key management
- Script execution interface
- Easy script management

To use it:
```bash
cd scripts/csv_script_manager
<<<<<<< HEAD
python csv_script_manager.py    # Windows
python3 csv_script_manager.py   # macOS/Linux
```

Then open your browser to `http://localhost:8000`
=======
python csv_script_manager.py
```

Then open your browser to http://localhost:8000
>>>>>>> af5e853d33494a8223053f6d3783621b840a69eb

## Postman Collection

For a convenient way to test and explore the Ericsson NetCloud Manager APIs, you can use the **Ericsson NCM API Postman Collection**. This collection contains pre-configured API requests that you can use to interact with the APIs directly from Postman.

### Importing the Collection

1. Open Postman
2. Click **Import** in the top left corner
3. Select **File** or **Upload Files**
4. Navigate to and select the `Ericsson NCM API Postman Collection.json` file from this repository
5. Click **Import**

The collection will now appear in your Postman workspace. You can use it to explore and test the various API endpoints.

## Setup

### Download and Extract the Repository

<<<<<<< HEAD
=======
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

### 1. Create a Python Virtual Environment

>>>>>>> af5e853d33494a8223053f6d3783621b840a69eb
**Windows:**
```cmd
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set API Keys as Environment Variables

**Windows (Command Prompt):**
```cmd
set X_CP_API_ID=your_api_id
set X_CP_API_KEY=your_api_key
set X_ECM_API_ID=your_ecm_api_id
set X_ECM_API_KEY=your_ecm_api_key
```

**Windows (PowerShell):**
```powershell
$env:X_CP_API_ID="your_api_id"
$env:X_CP_API_KEY="your_api_key"
$env:X_ECM_API_ID="your_ecm_api_id"
$env:X_ECM_API_KEY="your_ecm_api_key"
```

To make these persistent in Windows, set them through System Properties > Environment Variables, or add them to your PowerShell profile.

**macOS/Linux:**
```bash
export X_CP_API_ID="your_api_id"
export X_CP_API_KEY="your_api_key"
export X_ECM_API_ID="your_ecm_api_id"
export X_ECM_API_KEY="your_ecm_api_key"
```

To make these persistent, add them to your `~/.zshrc` or `~/.bashrc`:
```bash
echo 'export X_CP_API_ID="your_api_id"' >> ~/.zshrc
echo 'export X_CP_API_KEY="your_api_key"' >> ~/.zshrc
echo 'export X_ECM_API_ID="your_ecm_api_id"' >> ~/.zshrc
echo 'export X_ECM_API_KEY="your_ecm_api_key"' >> ~/.zshrc
```

## Running Scripts

**Windows:**
```cmd
python script_name.py
```

**macOS/Linux:**
```bash
python3 script_name.py
```
