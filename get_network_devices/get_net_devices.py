"""
The following Python code sample shows how to access the
"net_devices" endpoint of the NCM REST API using the
Python "requests" module with paging. It makes use of NCM
and CP credential headers to authenticate and access the
network_interface data. The router_id is the primary key
and the net_device_is the sub_key. You can have multiple,
router interfaces on each router.
"""

import json
import requests
from datetime import datetime, timezone, timedelta

headers = {
    'X-CP-API-ID': '...',
    'X-CP-API-KEY': '...',
    'X-ECM-API-ID': '...',
    'X-ECM-API-KEY': '...',
    'Accept': '*/*',
    'Content-Type': 'application/json',
}

account = ''  # your ncm account id here...
base_url = 'https://www.cradlepointecm.com'
connection_state = 'connected'
mode = 'wan'


def get_time():
    """ Routers updated within the last 10 minutes. """
    return (datetime.now(timezone.utc).astimezone()
            - timedelta(minutes=10)).isoformat()


def get_network_devices_info(time):
    """ Get network device information """

    url = base_url + \
        f'/api/v2/net_devices/?limit=500\
        &account={account}&mode={mode}&connection_state={connection_state}'

    # we ultimately want to filter on updated_at to reduce api calls.
    # url = base_url + \
    #    f'/api/v2/net_devices/?limit=500&account={account}&mode={mode} \
    #    &connection_state={connection_state}&updated_at={time}'

    network_devices = {}

    while url:
        req = requests.get(url, headers=headers)
        resp = req.json()

        if (len(resp['data']) < 1):
            return network_devices
        for items in resp['data']:

            if items['router']:
                router_id = items['router'].replace(
                    'https://www.cradlepointecm.com/api/v2/routers/', '')[:-1]
            else:
                # net_device_id without a router in in NCM account.
                router_id = 0

            network_devices_list = \
                {'carrier': items['carrier'],
                 'connection_state': items['connection_state'],
                 'hostname': items['hostname'],
                 'network_device_resource_url': items['resource_url'],
                 'type': items['type'],
                 'updated_at': items['updated_at'],
                 'uptime': items['uptime']}

            if router_id in network_devices:
                network_devices[router_id].update(
                    {items['id']: network_devices_list})
            else:
                network_devices.update(
                    {router_id: {items['id']: network_devices_list}})

        url = resp['meta']['next']

    return network_devices  # Returns my network devices


def dictionary_to_json(network_devices):
    """ Converts a dictionary to json format. """
    return json.dumps(network_devices, indent=4, sort_keys=True)


def main():
    time = get_time()
    network_devices = get_network_devices_info(time)
    interfaces = dictionary_to_json(network_devices)
    print(interfaces)


if __name__ == '__main__':
    main()
