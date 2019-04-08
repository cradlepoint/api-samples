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

account = ''  # Your ncm account id here.
base_url = 'https://www.cradlepointecm.com'


def get_time():
    """ Routers updated within the last 10 minutes. """
    return (datetime.now(timezone.utc).astimezone() - timedelta(minutes=10)).isoformat()


def get_router_info(time):
    """ Get router information """

    url = base_url + f'/api/v2/routers/?limit=500&account={account}'

    """
    url = base_url + f'/api/v2/routers/?limit=500&account={account}&state_updated_at={time}'

    {
    "exception": {
        "type": "error",
        "message": "&#39;exact&#39; is not an allowed filter on the &#39;state_updated_at&#39; field."
    },
    "errors": [
        {
            "path": "/api/v2/routers/"
        }
    ]
    }
    """

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

    return routers  # Returns my routers


def main():
    time = get_time()
    routers = get_router_info(time)

    # This prints the output in an easy to ready json format.
    dump = json.dumps(routers)
    parsed = json.loads(dump)
    print(json.dumps(parsed, indent=4, sort_keys=True))


if __name__ == '__main__':
    main()
