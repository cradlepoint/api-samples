"""
The following Python code sample shows how to access the
"alerts" endpoint of the NCM REST API using the
Python "requests" module with paging. It makes use of NCM
and CP credential headers to authenticate and access the
router data. The router_id is the key and the alert data
is the value.
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

base_url = 'https://www.cradlepointecm.com'


def get_time():
    """ Alerts within the last 10 minutes. """
    return (datetime.now(timezone.utc).astimezone()
            - timedelta(minutes=10)).isoformat()


def get_alert_info(time):
    """ Gets network device and alert information """

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


def dictionary_to_json(alert):
    """ Converts a dictionary to json format. """
    return json.dumps(alert, indent=4, sort_keys=True)


def main():
    time = get_time()
    alert = get_alert_info(time)
    alerts = dictionary_to_json(alert)
    print(alerts)


if __name__ == '__main__':
    main()
