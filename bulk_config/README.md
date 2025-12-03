# bulk_config.py

Bulk configure devices in NCM from router_grid.csv file using column headers.

## Setup

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

1. Export router_grid.csv from the Device View in NCM
2. Use NCM's device-level Edit Config screen to build your configuration
3. Copy the pending config output and paste it into the build_config return value
4. Update router_grid.csv to contain the columns that need to be applied to the device level config
5. Update build_config to reference router_grid column headers with row_data.get('column_name')
6. Update csv_file variable if using a different filename than 'router_grid.csv'
7. Update API keys with your NCM API credentials
8. Run the script:
   ```bash
   python bulk_config.py
   ```

## Example

For the included router_grid.csv with columns `id`, `name`, `desc`, `asset_id`, `primary_lan_ip`, `2ghz_ssid`, `5ghz_ssid`:

```python
"system": {
    "system_id": row_data.get('name', ''),
    "asset_id": row_data.get('asset_id', ''),
    "desc": row_data.get('desc', '')
},
"lan": {
    "00000000-0d93-319d-8220-4a1fb0372b51": {
        "ip_address": row_data.get('primary_lan_ip', '')
    }
},
"wlan": {
    "radio": {
        "0": {
            "bss": {
                "0": {
                    "ssid": row_data.get('2ghz_ssid', '')
                }
            }
        },
        "1": {
            "bss": {
                "0": {
                    "ssid": row_data.get('5ghz_ssid', '')
                }
            }
        }
    }
}
```

## Requirements

- Python 3.5+
- NCM API credentials
- router_grid.csv file exported from NCM Device View
- Device-level configuration built using NCM Edit Config screen