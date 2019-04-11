"""
The following Python code sample shows how to access the
"routers" endpoint of the NCM REST API using the
Python "requests" module with paging. It makes use of NCM
and CP credential headers to authenticate and access the
router data. The router_id is the key and the router_group,
router_name, and router_state are the values.
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


account = ''  # your ncm account id here.
base_url = 'https://www.cradlepointecm.com'


def get_time():
    """ Routers updated within the last 10 minutes. """
    return (datetime.now(timezone.utc).astimezone()
            - timedelta(minutes=10)).isoformat()


def get_router_info(time):
    """ Get router information """

    url = base_url + f'/api/v2/routers/?limit=500&account={account}'

    # we ultimately want to filter on state_updated_at to reduce api calls.
    # url = base_url + f'/api/v2/routers/?limit=500&account={account} \
    # &state_updated_at={time}'

    routers = {}

    while url:
        req = requests.get(url, headers=headers)
        resp = req.json()

        if (len(resp['data']) < 1):
            return routers
        for items in resp['data']:

            if items['group']:
                group = items['group'].replace(
                    'https://www.cradlepointecm.com/api/v2/groups/', '')[:-1]
            else:
                group = None
            routers_list = {'router_group': group,
                            'router_name': items['name'],
                            'router_state': items['state'], }

            router = {items['id']: routers_list}
            routers.update(router)

            url = resp['meta']['next']

    return routers


def dictionary_to_json(routers):
    """ Converts a dictionary to json format. """
    return json.dumps(routers, indent=4, sort_keys=True)


def main():
    time = get_time()
    routers = get_router_info(time)
    results = dictionary_to_json(routers)
    print(results)


if __name__ == '__main__':
    main()
