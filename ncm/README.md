# NCM API Client Documentation

## Overview

This module provides easy access to the Cradlepoint NCM API with support for both v2 and v3 APIs. It includes a singleton pattern for simple usage and module-level function access for convenience.

## Installation

> pip install -U ncm  

## Requirements

Cradlepoint NCM API Keys are required to make API calls:
- **For v2 API**: X-CP-API-ID, X-CP-API-KEY, X-ECM-API-ID, X-ECM-API-KEY
- **For v3 API**: Bearer token

## Usage Options

### 1. Zero-Configuration Usage (Recommended)

```python
import ncm

# Set these environment variables once:
# export X_CP_API_ID="b89a24a3"
# export X_CP_API_KEY="4b1d77fe271241b1cfafab993ef0891d"
# export X_ECM_API_ID="c71b3e68-33f5-4e69-9853-14989700f204"
# export X_ECM_API_KEY="f1ca6cd41f326c00e23322795c063068274caa30"
# export NCM_API_TOKEN="your-bearer-token"  # For v3 API

# Then just use it - no setup required!
accounts = ncm.get_accounts()
devices = ncm.get_devices()
routers = ncm.get_routers()
```

### 2. Explicit Configuration (Alternative)

```python
import ncm

# Option A: Set up API keys explicitly
api_keys = {
   'X-CP-API-ID': 'b89a24a3',
   'X-CP-API-KEY': '4b1d77fe271241b1cfafab993ef0891d',
   'X-ECM-API-ID': 'c71b3e68-33f5-4e69-9853-14989700f204',
   'X-ECM-API-KEY': 'f1ca6cd41f326c00e23322795c063068274caa30'
}
ncm.set_api_keys(api_keys)

# Option B: Manual environment variable loading
ncm.set_api_keys()  # Manually loads from environment
```

### 3. Traditional Class Instantiation

```python
import ncm
api_keys = {...}  # Same as above
client = ncm.NcmClient(api_keys=api_keys)
accounts = client.get_accounts()
```

### 4. Mixed v2/v3 API Usage

```python
import ncm
api_keys = {
   'X-CP-API-ID': 'b89a24a3',
   'X-CP-API-KEY': '4b1d77fe271241b1cfafab993ef0891d',
   'X-ECM-API-ID': 'c71b3e68-33f5-4e69-9853-14989700f204',
   'X-ECM-API-KEY': 'f1ca6cd41f326c00e23322795c063068274caa30',
   'token': 'your-v3-bearer-token'  # For v3 API
}
client = ncm.NcmClient(api_keys=api_keys)
# Methods will automatically route to the appropriate API version
```

### 5. Backward Compatibility (Legacy Scripts)

```python
from ncm import ncm  # Old import pattern still works!

api_keys = {
    'X-ECM-API-ID': os.environ.get("X_ECM_API_ID"),
    'X-ECM-API-KEY': os.environ.get("X_ECM_API_KEY"),
    'X-CP-API-ID': os.environ.get("X_CP_API_ID"),
    'X-CP-API-KEY': os.environ.get("X_CP_API_KEY"),
    'Authorization': f'Bearer {os.environ.get("TOKEN")}'
}

# All existing patterns work unchanged:
ncm_client = ncm.NcmClientv3(api_key=token, log_events=True)
ncm_client.set_api_keys(api_keys)  # Instance method still works

# New convenience pattern also available:
ncm.set_api_keys(api_keys)  # Module-level method
routers = ncm.get_routers()  # Direct method access
```

## Features

- ✅ Zero-configuration usage with automatic environment variable loading
- ✅ Singleton pattern for easy module-level access
- ✅ Automatic API version routing (v3 prioritized over v2)
- ✅ Module-level function access (`ncm.method_name()`)
- ✅ Automatic initialization on import if environment variables are set
- ✅ Full backward compatibility with existing scripts
- ✅ Support for both import patterns: `"import ncm"` and `"from ncm import ncm"`
- ✅ Optimized pagination (default limit 500 vs API default 20)
- ✅ Support for `limit='all'` to get all records without paging
- ✅ Automatic chunking of `"__in"` filters beyond 100 item limit

## Documentation

Full documentation of the Cradlepoint NCM API is available at: [https://developer.cradlepoint.com](https://developer.cradlepoint.com)
