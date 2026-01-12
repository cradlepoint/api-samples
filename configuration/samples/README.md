# NCM API Key Encryptor

For encrypting NCM API keys into group or device configurations for use in SDK applications.

## Description

This web application allows you to encrypt NCM API keys (APIv2 and APIv3) into group or device configurations. The encrypted keys can then be used by SDK applications running on the devices.

## Requirements

- Python 3.x
- Flask
- ncm library

## Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the application:
```bash
python3 ncm_api_key_encryptor.py
```

2. Open your browser and navigate to:
```
http://localhost:8000
```

## How It Works

1. **Step 1: Admin NCM APIv2 Keys**
   - Enter your admin API keys that have authorization to the target group or device
   - These keys are used for authentication only and will not be added to configurations
   - Click "Set Admin Keys & Verify" to validate your keys

2. **Step 2: API Keys to Add to Configuration**
   - Enter the API keys you want to encrypt into the group or device configuration
   - You can use either:
     - All 4 APIv2 keys (X-ECM-API-ID, X-ECM-API-KEY, X-CP-API-ID, X-CP-API-KEY)
     - OR an APIv3 Token
   - Select the destination (Group or Device)
   - Enter the ID or Name of the target
   - Click "Submit" to encrypt and set the keys

## Notes

- Admin keys must have authorization to the target group or device
- Admin keys are stored in session and will persist across page refreshes
- Use the "Clear Admin Keys" button to reset the session

