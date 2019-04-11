"""
The following Python code sample shows how to access the
"net_device_usage_samples" endpoint of the NCM REST API
using the Python "requests" module with paging. It makes
use of NCM and CP credential headers to authenticate and
access the router data. The net_device_id is the key and
the alert data is the value.
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


net_device_id = ''  # your network device id goes here.
base_url = 'https://www.cradlepointecm.com'


def get_time():
    """ network devices updated within the last hour. """
    return (datetime.now(timezone.utc).astimezone()
            - timedelta(hours=1)).isoformat()


def get_network_devices_info(time):
    """ Get network device information """

    url = base_url + \
        f'/api/v2/net_device_usage_samples/?limit=500\
        &net_device__in={net_device_id}&created_at__gt={time}'

    network_devices = {}

    while url:
        req = requests.get(url, headers=headers)
        resp = req.json()

        if (len(resp['data']) < 1):
            return network_devices
        for items in resp['data']:

            network_devices_list = \
                {'bytes_in': items['bytes_in'],
                 'bytes_out': items['bytes_out'],
                 'created_at': items['created_at'],
                 'created_at_timeuuid': items['created_at_timeuuid'],
                 'net_device': items['net_device'],
                 'period': items['period'],
                 'uptime': items['uptime']}

            network_device = {net_device_id: network_devices_list}
            network_devices.update(network_device)

        url = resp['meta']['next']

    return network_devices


def dictionary_to_json(network_devices):
    """ Converts a dictionary to json format. """
    return json.dumps(network_devices, indent=4, sort_keys=True)


def main():
    time = get_time()
    network_devices = get_network_devices_info(time)
    print(dictionary_to_json(network_devices))


if __name__ == '__main__':
    main()
