"""
bulk_config.py - bulk configure devices in NCM from .csv file

 1. Create routers.csv with router IDs listed in column A and other
     device-specific values in subsequent columns (B, C, D, etc)
 2. Use NCM Config Editor to build a config template, then click
     "View Pending Changes" and copy the config
 3. Paste your config below in the build_config() function and replace
     config values with corresponding csv column letters
 4. Enter API Keys and run script

     Example config for a csv file with hostname in column B:

        [{
             "system": {
                 "system_id": column["B"]
            }
        },
            []
        ]

"""

import requests
import csv

csv_file = 'routers.csv'
api_keys = {
    'X-ECM-API-ID': 'YOUR',
    'X-ECM-API-KEY': 'KEYS',
    'X-CP-API-ID': 'GO',
    'X-CP-API-KEY': 'HERE'
}


def build_config(column):
    """
    Returns router configuration with values from row
    :param column: mapping of values from csv columns for router_id
    :type column: dict
    :return: router configuration (list)
    """
    # > > > Paste configuration *BELOW* the next line (don't touch "return \") < < <
    return \
        [{
            "system": {
                "system_id": column["B"]
            }
        },
            []
        ]
    # > > > Paste configuration ^ ABOVE HERE ^  < < <
    # > > > Replace config values with corresponding csv column letters  < < <


def load_csv(filename):
    """
    Returns a dictionary of router_ids containing corresponding config values from csv
    :param filename: name of csv file
    :type filename: str
    :return: list of rows from csv file
    """
    router_configs = {}
    try:
        with open(filename, 'rt') as f:
            rows = csv.reader(f)
            for row in rows:
                column = {"A": row[0]}
                i = 1
                while True:
                    try:
                        column[chr(i + 97).upper()] = row[i]
                        column[chr(i + 97).lower()] = row[i]
                        i += 1
                    except:
                        break
                router_configs[column["A"]] = column
    except Exception as e:
        print(f'Exception reading csv file: {e}')
    return router_configs


server = 'https://www.cradlepointecm.com/api/v2'
rows = load_csv(csv_file)
for router_id in rows:
    config_url = f'{server}/configuration_managers/?router={router_id}'
    get_config = requests.get(config_url, headers=api_keys)
    if get_config.status_code < 300:
        get_config = get_config.json()
        config_data = get_config["data"]
        config_id = config_data[0]["id"]
        config = build_config(rows[router_id])
        patch_config = requests.patch(f'{server}/configuration_managers/'
                                      f'{config_id}/', headers=api_keys,
                                      json={"configuration": config})
        if patch_config.status_code < 300:
            print(f'Sucessfully patched config to router: {router_id}')
        else:
            print(f'Error patching config {router_id}: {patch_config.text}')
    else:
        print(f'Error getting configuration_managers/ ID for {router_id}: '
              f'{get_config.text}')
print('Done!')
