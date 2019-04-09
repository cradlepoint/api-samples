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


net_device_id = '' # your network device id goes here.
base_url = 'https://www.cradlepointecm.com'


def get_time():
    return (datetime.now(timezone.utc).astimezone() - timedelta(hours=1)).isoformat() # within the last hour


def get_network_devices_info(time):
    """ Get network device information """

    url = base_url + \
        f'/api/v2/net_device_usage_samples/?limit=500&net_device__in={net_device_id}&created_at__gt={time}'

    network_devices = {}

    while url:
        req = requests.get(url, headers=headers)
        resp = req.json()

        if (len(resp['data']) < 1):
            return network_devices
        for items in resp['data']:

            network_devices_list = {'bytes_in': items['bytes_in'],
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


def main():
    time = get_time()
    network_devices = get_network_devices_info(time)

    # This prints the output in an easy to ready json format.
    dump = json.dumps(network_devices)
    parsed = json.loads(dump)
    print(json.dumps(parsed, indent=4, sort_keys=True))


if __name__ == '__main__':
    main()
