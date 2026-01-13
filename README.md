# API Samples

A collection of Python scripts for interacting with Ericsson NetCloud Manager APIs.

## Setup

### 1. Create a Python Virtual Environment

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**
```cmd
python -m venv venv
venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Set API Keys as Environment Variables

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

## Running Scripts

**macOS/Linux:**
```bash
python3 script_name.py
```

**Windows:**
```cmd
python script_name.py
```

## Web Interface

For a convenient web-based interface to manage CSV files, API keys, and run scripts, check out the [CSV Script Manager](csv_script_manager/README.md).

The CSV Script Manager provides:
- Web-based CSV file editor
- API key management
- Script execution interface
- Easy script management

To use it:
```bash
cd csv_script_manager
python3 csv_script_manager.py  # macOS/Linux
python csv_script_manager.py    # Windows
```

Then open your browser to `http://localhost:8000`

