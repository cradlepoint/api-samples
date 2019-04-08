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


base_url = 'https://www.cradlepointecm.com'

def get_time():
    """ Routers updated within the last 10 minutes. """
    return (datetime.now(timezone.utc).astimezone() - timedelta(minutes=10)).isoformat()


def get_alert_info(time):
    """ Get network device information """

    # The allowed operations are gt, lt.
    url = base_url + f'/api/v2/alerts/?limit=500&created_at__gt={time}'

    alerts = {}

    while url:
        req = requests.get(url, headers=headers)
        resp = req.json()

        if (len(resp['data']) < 1):
            return alerts
        for items in resp['data']:

            if items['router']:
                router_id = items['router'].replace(
                    'https://www.cradlepointecm.com/api/v2/routers/', '')[:-1]
            else:
                # Routers no longer in my account but still a net_device_id in my account.
                router_id = 0

            network_devices_list = {'created_at': items['created_at'],
                                    'friendly_info': items['friendly_info'],
                                    'info': items['info'],
                                    'type': items['type'],
                                    }

            alert = {router_id: network_devices_list}
            alerts.update(alert)

            url = resp['meta']['next']

        return alerts

def main():
    time = get_time()
    alerts = get_alert_info(time)

    # This prints the output in an easy to ready json format.
    dump = json.dumps(alerts)
    parsed = json.loads(dump)
    print(json.dumps(parsed, indent=4, sort_keys=True))


if __name__ == '__main__':
    main()
