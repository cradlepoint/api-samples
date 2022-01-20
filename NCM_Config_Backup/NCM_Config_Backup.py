"""NCM_Config_Backup.py - Backup NCM group and device configurations.

Creates timestamped folders containing JSON text files of group and device
configurations.
Option to include/exclude devices with default (blank) configurations (can
be useful for inventory/accounting)
Enter API Keys below and run script!
"""
import requests
import json
import os
from datetime import datetime
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import re


server = 'https://www.cradlepointecm.com/api/v2'

include_blank_configs = True

api_keys = {'X-ECM-API-ID': 'YOUR',
            'X-ECM-API-KEY': 'KEYS',
            'X-CP-API-ID': 'GO',
            'X-CP-API-KEY': 'HERE',
            'Content-Type': 'application/json'}

# Create Backup Directories
backups_dir = os.getcwd() + '/NCM Config Backups'
if not os.path.exists(backups_dir):
    os.makedirs(backups_dir)
timestamp = datetime.now().strftime("%m-%d-%Y %I.%M.%S%p").lower()
my_backup_dir = f'{backups_dir}/{timestamp}'
os.makedirs(my_backup_dir)  # Timestamped Backup Directory
routers_dir = f'{my_backup_dir}/routers'
groups_dir = f'{my_backup_dir}/groups'
os.makedirs(routers_dir)  # Subdirectory for routers
os.makedirs(groups_dir)  # Subdirectory for groups

print('\n¸,ø¤°º¤ø,¸¸,ø¤º°`°  NCM Config Backup  °º¤ø,¸¸,ø¤º°`°º¤ø,¸\n')
print(f'Creating Backups Here: \n{my_backup_dir}/\n')
print('Backing up device configurations...\n')


""" This will make all HTTP requests from the same session
retry for a total of 10 times, sleeping between retries with an
exponentially increasing backoff of 1s, 2s, 4s, and so on... It
will retry on basic connectivity issues and the listed HTTP
status codes. """

session = requests.session()
retries = Retry(total=10,  # Total number of retries to allow.
                backoff_factor=1,
                status_forcelist=[408, 429, 502, 503, 504],
                )
session.mount('https://', HTTPAdapter(max_retries=retries))

routers_backed_up = 0
routers_url = f'{server}/routers/'
while routers_url:
    get_routers = session.get(routers_url, headers=api_keys)
    if get_routers.status_code < 300:
        get_routers = get_routers.json()
        routers = get_routers["data"]
        routers = [x for x in routers if x["state"] != "initialized"]
        for router in routers:
            config_url = f'{server}/configuration_managers/?router=' \
                f'{router["id"]}'
            get_config = session.get(config_url, headers=api_keys)
            if get_config.status_code < 300:
                get_config = get_config.json()
                try:
                    config = get_config["data"][0]["configuration"]
                    if include_blank_configs or config != [{}, []]:
                        router_name = re.sub(r'[\\/*?:"<>|]', "_",
                                             router["name"])
                        with open(f'{routers_dir}/{router["id"]} - '
                                  f'{router_name}.json', 'wt') as f:
                            f.write(json.dumps(config))
                        print(f'Backed up config for router : {router["id"]} - '
                              f'{router["name"]}')
                        routers_backed_up += 1
                except Exception as e:
                    print(f'Exception backing up config for {router["id"]} - '
                          f'{router["name"]}: {e}')
            else:
                print(f'Error getting config for {router["id"]} - '
                      f'{router["name"]}: {get_config.text}')
        routers_url = get_routers["meta"]["next"]
    else:
        print(f'Error getting routers: {get_routers.text}')
        break

print(f'\nBacked up {routers_backed_up} router configurations.')

print('\nBacking up group configurations...\n')

groups_backed_up = 0
groups_url = f'{server}/groups/'
while groups_url:
    get_groups = session.get(groups_url, headers=api_keys)
    if get_groups.status_code < 300:
        get_groups = get_groups.json()
        groups = get_groups["data"]
        for group in groups:
            config = group["configuration"]
            if include_blank_configs or config != [{}, []]:
                group_name = re.sub(r'[\\/*?:"<>|]', "_", group["name"])
                with open(f'{groups_dir}/{group["id"]} - {group_name}.json',
                          'wt') as f:
                    f.write(json.dumps(config))
                print(f'Backed up config for group : {group["id"]} - '
                      f'{group["name"]}')
                groups_backed_up += 1
        groups_url = get_groups["meta"]["next"]
    else:
        print(f'Error getting groups: {get_groups.text}')

print(f'\nBacked up {routers_backed_up} router configurations.')
print(f'\nBacked up {groups_backed_up} group configurations.')

print('\nNCM Config Backup Complete!')
