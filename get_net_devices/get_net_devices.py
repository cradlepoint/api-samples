import csv
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

account = '' # your ncm account id here...
base_url = 'https://www.cradlepointecm.com'


def get_time():
    """ Routers updated within the last 10 minutes. """
    return (datetime.now(timezone.utc).astimezone() - timedelta(minutes=10)).isoformat()


def get_network_devices_info(time):
    """ Get network device information """

    url = base_url + \
        f'/api/v2/net_devices/?limit=500&account={account}&mode=wan&connection_state=connected'

    """
    url = base_url + \
        f'/api/v2/net_devices/?limit=500&account={account}&mode=wan&connection_state=connected&updated_at={time}'

    Now let’s add a filter to our query on the “updated_at” field, which indicates when a state change occurs.
    If we rewrite our script so that it pulls the full router set on the first poll, then filters on state_updated_at
    for all subsequent polls, to retrieve only the records whose state has changed since the last poll, we reduce our
    number of calls to effectively one call per 15 minutes.

    This is a drop from 5,760 API calls/day to 96 API calls/day, a 60x improvement.

    {
        "exception": {
            "type": "error",
            "message": "The &#39;updated_at&#39; field does not allow filtering."
        },
        "errors": [
            {
                "path": "/api/v2/net_devices/"
            }
        ]
    }

    This feature is pending in a feature request...
    """

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
                # Routers no longer in my account but still a net_device_id in my account.
                router_id = 0

            network_devices_list = {'carrier': items['carrier'],
                                    'connection_state': items['connection_state'],
                                    'hostname': items['hostname'],
                                    'network_device_resource_url': items['resource_url'],
                                    'type': items['type'],
                                    'updated_at': items['updated_at'],
                                    'uptime': items['uptime']}

            if router_id in network_devices:
                network_devices[router_id].update(
                    {items['id']: network_devices_list})  # Router ID is the Key
            else:
                network_devices.update({router_id: {items['id']: network_devices_list}})

        url = resp['meta']['next']

    return network_devices  # Returns my network devices


def main():
    time = get_time()
    network_devices = get_network_devices_info(time)

    # This prints the output in an easy to ready json format.
    dump = json.dumps(network_devices)
    parsed = json.loads(dump)
    print(json.dumps(parsed, indent=4, sort_keys=True))


if __name__ == '__main__':
    main()
