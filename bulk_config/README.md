# bulk_config.py

Bulk configure devices in NCM from router_grid.csv file using column headers. Also sets custom1 and custom2 fields when values are provided in the CSV.

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

## Custom Fields

The script automatically sets custom1 and custom2 fields for each router when these columns are present in the CSV and contain non-empty values. Simply add `custom1` and/or `custom2` columns to your router_grid.csv file.

## Example

For the included router_grid.csv with columns `id`, `name`, `desc`, `asset_id`, `primary_lan_ip`, `2ghz_ssid`, `5ghz_ssid`, `custom1`, `custom2`:

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

**Custom Fields Example:**
If your CSV includes custom1 and custom2 columns:
```csv
id,name,desc,asset_id,primary_lan_ip,2ghz_ssid,5ghz_ssid,custom1,custom2
1234567,Router1,Test Router,ASSET001,192.168.1.1,WiFi_2G,WiFi_5G,Location A,Department IT
```
The script will automatically set the custom1 field to "Location A" and custom2 field to "Department IT" for that router.

## Requirements

- Python 3.5+
- NCM API credentials
- router_grid.csv file exported from NCM Device View
- Device-level configuration built using NCM Edit Config screen