"""
Use this script to generate a CSV of routers this CSV to set some configuration fields of each router (name, description, asset id, custom1, custom2).

To generate a CSV:
    python router_fields.py [group_id_or_name] [--csv <csv_file>]

To sync the values in the csv file to the routers in the account:
    python router_fields.py --csv <csv_file> --sync

requires ncm package `pip3 install ncm`

Requires NCM api keys. See https://docs.cradlepoint.com/r/NCM-APIv2-Overview/NetCloud-Manager-API-v2-Overview

WARNING!!!: This script makes changes to router connectivity settings and can result in 
routers going offline! This script comes with no warranty or guarantee. The 
author of this script assume no liability for the use of this script. Please 
use at your own risk! See https://github.com/cradlepoint/api-samples/blob/master/LICENSE for more information.
"""

import logging
import os
import sys
from ncm.ncm import NcmClient
import csv

# Configure logging
LOGGER = logging.getLogger("routers")
fmt = '%(asctime)s | %(levelname)8s | %(message)s'
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(logging.Formatter(fmt))
LOGGER.addHandler(stream_handler)
LOGGER.setLevel(logging.DEBUG)

api_keys = {
    'X-CP-API-ID': os.environ.get('X_CP_API_ID'),
    'X-CP-API-KEY': os.environ.get('X_CP_API_KEY'),
    'X-ECM-API-ID': os.environ.get('X_ECM_API_ID'),
    'X-ECM-API-KEY': os.environ.get('X_ECM_API_KEY'),
}


n = NcmClient(api_keys)

def groups_id_by_name(group_name):
    kwargs = {}
    if group_name:
        group_name = group_name if isinstance(group_name, list) else [group_name]
        kwargs["name__in"] = ','.join(group_name)
    groups = n.get_groups(**kwargs)
    return [group['id'] for group in groups]

def get_routers(group=None):
    kwargs = {}
    if group:
        group = group if group and isinstance(group, list) else [group]
        group_ids = []
        group_names = []
        for g in group:
            try:
                int(g)
                group_ids.append(g)
            except ValueError:
                group_names.append(g)
        group_ids.extend(groups_id_by_name(group_names))
        kwargs['group__in'] = ','.join(group_ids)

    return n.get_routers(**kwargs)

def read_csv(file=sys.stdin):
    routers = []
    reader = csv.DictReader(file)
    headers = reader.fieldnames
    if headers != ["id", "name", "description", "asset_id", "custom1", "custom2"]:
        raise ValueError("CSV headers do not match expected headers")
    for row in reader:
        routers.append({
            'id': row['id'],
            'name': row['name'],
            'description': row['description'],
            'asset_id': row['asset_id'],
            'custom1': row['custom1'],
            'custom2': row['custom2'],
        })
    print(routers)
    return routers

def update_routers(routers):
    for router in routers:
        n.set_router_fields(router['id'], 
                            name = router.get('name') or '', 
                            description = router.get('description') or '', 
                            asset_id = router.get('asset_id') or '', 
                            custom1 = router.get('custom1') or '', 
                            custom2 = router.get('custom2') or '')

def generate_csv(file=sys.stdout, group=None):
    writer = csv.writer(file)
    writer.writerow(["id", "name", "description", "asset_id", "custom1", "custom2"])
    routers = get_routers(group)
    if routers:
        for router in routers:
            writer.writerow([
                router['id'],
                router['name'],
                router.get('description', ''),
                router.get('asset_id', ''),
                router.get('custom1', ''),
                router.get('custom2', '')
            ])

if __name__ == "__main__":
    import argparse
    # if no args are passed then get all the routers in the account and output in csv format the information
    parser = argparse.ArgumentParser(description='Get routers information')
    parser.add_argument('group', nargs='?', help='Filter router by group name or id, if not provided all routers will be returned')
    parser.add_argument('--sync', '-s', action='store_true', help='sync from specified file. This will trigger changes in your NCM account.')
    parser.add_argument('--csv', '-c', default='-', help='output to csv file')
    args = parser.parse_args()
    if not args.sync:
        f = sys.stdout
        if args.csv and args.csv != '-':
            f = open(args.csv, "w")
        generate_csv(f, args.group)
    else:
        i = input("This will update the routers in your NCM account. Are you sure you want to continue? (yes/no): ")
        if i.lower() != 'yes':
            sys.exit(1)
        f = sys.stdin
        if args.csv and args.csv != '-':
            f = open(args.csv, "r")
        routers = read_csv(f)
        update_routers(routers)