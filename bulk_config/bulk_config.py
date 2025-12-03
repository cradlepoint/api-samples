"""bulk_config.py - bulk configure devices in NCM from router_grid.csv file.

Reads router_grid.csv with column headers and applies configurations
using the NCM library's patch_configuration_managers method.

To use this script:
1. Export router_grid.csv from the Device View in NCM
2. Use NCM's device-level Edit Config screen to build your configuration
3. Copy the pending config output and paste it into the build_config return value
4. Update router_grid.csv to contain the columns that need to be applied to the device level config
5. Update build_config to reference router_grid column headers with row_data.get('column_name')
6. Update csv_file variable if using a different filename than 'router_grid.csv'
7. Update API keys below with your NCM API credentials
"""

import csv
from typing import Dict, List, Any
import ncm

# Update this filename if using a different CSV file
csv_file = 'router_grid.csv'

# Update these API keys with your NCM credentials
api_keys = {
    "X-CP-API-ID": "YOUR_CP_API_ID",
    "X-CP-API-KEY": "YOUR_CP_API_KEY",
    "X-ECM-API-ID": "YOUR_ECM_API_ID",
    "X-ECM-API-KEY": "YOUR_ECM_API_KEY"
}
n2 = ncm.NcmClientv2(api_keys=api_keys)

def build_config(row_data: Dict[str, str]) -> List[Any]:
    """Return router configuration with values from CSV row.

    To update this configuration:
    1. Go to NCM device-level Edit Config screen
    2. Make your changes and view pending config
    3. Copy the pending config JSON and paste below the return \ line
    4. Replace static values with row_data.get('column_name') for CSV columns

    Args:
        row_data (dict): Dictionary with CSV column headers as keys.

    Returns:
        list: Router configuration list.
    """
    return \
        [
        {
            "lan": {
                "00000000-0d93-319d-8220-4a1fb0372b51": {
                    "dhcpd": {
                        "cur6_hop_limit": 64,
                        "dad_transmits": 1,
                        "dhcp6_mode": "slaacdhcp",
                        "lease6_time": 3600,
                        "max_rtr_adv_interval": 600,
                        "min_rtr_adv_interval": 3,
                        "ns_retransmit_interval": 1000,
                        "options": [],
                        "ra6_advr_interval": 600,
                        "ra_mtu": 1500,
                        "reachable6_time": 30000,
                        "router_lifetime": 1800,
                        "valid6_lifetime": 3600
                    },
                    "ip_address": row_data.get('primary_lan_ip', ''),
                    "stp": {
                        "priority": 32768
                    },
                    "vrrp": {
                        "advert_int": 1,
                        "auth_type": "none",
                        "init_state": "master",
                        "ipverify": {
                            "test_id": ""
                        },
                        "priority": 100,
                        "vrid": 10
                    },
                    "wired_8021x": {
                        "eap": {
                            "reauth_period": 3600
                        },
                        "radius": {
                            "auth_servers": {
                                "0": {
                                    "ip_address": "127.0.0.1",
                                    "mac": "00:00:00:00:00:00",
                                    "port": 1812
                                },
                                "1": {
                                    "ip_address": "127.0.0.1",
                                    "mac": "00:00:00:00:00:00",
                                    "port": 1812
                                }
                            },
                            "acct_servers": {
                                "0": {
                                    "ip_address": "127.0.0.1",
                                    "mac": "00:00:00:00:00:00",
                                    "port": 1813
                                },
                                "1": {
                                    "ip_address": "127.0.0.1",
                                    "mac": "00:00:00:00:00:00",
                                    "port": 1813
                                }
                            },
                            "allowed_macs": {
                                "0": {
                                    "enabled": False,
                                    "macs": []
                                }
                            }
                        }
                    },
                    "ip6_prefixlen": 64,
                    "passthrough_cycle_time": 10,
                    "_id_": "00000000-0d93-319d-8220-4a1fb0372b51"
                }
            },
            "system": {
                "system_id": row_data.get('name', ''),
                "asset_id": row_data.get('asset_id', ''),
                "desc": row_data.get('desc', '')
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
        },
        []
    ]


def load_csv(filename: str) -> Dict[int, Dict[str, str]]:
    """Return a dictionary of router_ids containing config values from csv.

    Args:
        filename (str): Name of csv file.

    Returns:
        dict: Dictionary of router configs keyed by router_id.
    """
    router_configs = {}
    try:
        with open(filename, 'rt', encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    router_id = int(row['id'])
                    router_configs[router_id] = row
                except (ValueError, KeyError) as e:
                    print(f'Skipping invalid row: {row}, error: {e}')
    except Exception as e:
        print(f'Exception reading csv file: {e}')
    return router_configs


def main() -> None:
    """Main function to process router configurations."""
    rows = load_csv(csv_file)

    for router_id, row_data in rows.items():
        try:
            config = {'configuration': build_config(row_data)}
            n2.patch_configuration_managers(
                router_id=router_id, config_man_json=config)
            print(f'Successfully patched config to router: {router_id}')
        except Exception as e:
            print(f'Error patching config for router {router_id}: {e}')

    print('Done!')


if __name__ == '__main__':
    main()
