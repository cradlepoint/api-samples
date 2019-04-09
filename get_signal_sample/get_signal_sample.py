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
    """ Routers updated within the last 10 minutes. """
    return (datetime.now(timezone.utc).astimezone() - timedelta(hours=1)).isoformat() # within the last hour


def get_network_devices_info(time):
    """ Get network device information """

    url = base_url + \
        f'/api/v2/net_device_signal_samples/?limit=500&net_device__in={net_device_id}&created_at__gt={time}'

    network_devices = {}

    while url:
        req = requests.get(url, headers=headers)
        resp = req.json()

        if (len(resp['data']) < 1):
            return network_devices
        for items in resp['data']:

            network_devices_list = {'cinr': items['cinr'],
                                    'created_at': items['created_at'],
                                    'created_at_timeuuid': items['created_at_timeuuid'],
                                    'dbm': items['dbm'],
                                    'ecio': items['ecio'],
                                    'net_device': items['net_device'],
                                    'rsrp': items['rsrp'],
                                    'rsrq': items['rsrq'],
                                    'rssi': items['rssi'],
                                    'rssnr': items['rssnr'],
                                    'signal_percent': items['signal_percent'],
                                    'sinr': items['sinr'],
                                    'uptime': items['uptime']}

            network_device = {net_device_id: network_devices_list}
            network_devices.update(network_device)

        url = resp['meta']['next']

    return network_devices # This will return the latest sample.


def main():
    time = get_time()
    network_devices = get_network_devices_info(time)

    # This prints the output in an easy to ready json format.
    dump = json.dumps(network_devices)
    parsed = json.loads(dump)
    print(json.dumps(parsed, indent=4, sort_keys=True))


if __name__ == '__main__':
    main()
