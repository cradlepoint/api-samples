"""
The following Python code sample shows how to access the
"routers" endpoint of the NCM REST API using the
Python "requests" module with paging. It makes use of NCM
and CP credential headers to authenticate and access the
router data. The router_id is the key and the router_group,
router_name, and router_state are the values.
"""

import json
import sys
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
from datetime import datetime, timezone, timedelta

# these values need to be substituted by the caller.
headers = {
    'X-CP-API-ID': 'Your CP-API-ID goes here',
    'X-CP-API-KEY': 'Your CP-API-KEY goes here',
    'X-ECM-API-ID': 'Your ECM-API-ID goes here',
    'X-ECM-API-KEY': 'Your ECM-API-KEY goes here',
    'Accept': '*/*',
    'Content-Type': 'application/json',
}

account = ''  # your ncm account id here as a string.
base_url = 'https://www.cradlepointecm.com'
updated_in = 0  # Routers updated within the last 0 (now) minutes.


def get_time():
    """ Returns the correct time format minus the updated_in minutes. """
    return (datetime.now(timezone.utc).astimezone()
            - timedelta(minutes=updated_in)).isoformat()


def get_router_info(now):
    """ Get router information """

    url = base_url + f'/api/v2/routers/?limit=500&account={account}\
    &state_updated_at__lt={now}'

    routers = {}

    while url:
        try:
            """ This will make all HTTP requests from the same session
            retry for a total of 3 times, sleeping between retries with an
            increasing backoff of 0s, 2s, 4s, and so on... It will retry
            on basic connectivity issues and the listed HTTP status codes. """

            session = requests.session()
            retries = Retry(total=3,  # Total number of retries to allow.
                            backoff_factor=1,
                            status_forcelist=[408, 502, 503, 504],
                            )
            session.mount('https://', HTTPAdapter(max_retries=retries))

            response = session.get(url, headers=headers, timeout=3)

            if response.status_code == 401:
                print("Check your headers...")
                sys.exit(1)

            elif response.status_code == 400:
                print("Check your account id...")
                sys.exit(1)

            elif response.status_code == 200:
                # if you get 200/ok back, store the response in json format.
                resp = response.json()

                if (len(resp['data']) < 1):
                    return routers

                for items in resp['data']:

                    if items['group']:
                        group = items['group'].replace(
                            'https://www.cradlepointecm.com/api/v2/groups/',
                            '')[:-1]
                    else:
                        group = None
                    routers_dict = {'router_group': group,
                                    'router_name': items['name'],
                                    'router_state': items['state'],
                                    }

                    router = {items['id']: routers_dict}
                    routers.update(router)

                    url = resp['meta']['next']

            else:
                print(str(response.status_code) + ": " + str(response.text))
                sys.exit(1)

        except requests.exceptions.HTTPError as errh:
            print("HTTP Error:", errh)

        except requests.exceptions.ConnectionError as errc:
            print("Connection Error:", errc)

        except requests.exceptions.Timeout as errt:
            print("Timeout Error:", errt)

        except requests.exceptions.RequestException as err:
            print("General Error:", err)

        except Exception as e:
            print("Gotta Catch 'Em All:", e)
            raise

        return routers


def dictionary_to_json(routers):
    """ Converts a dictionary to json format. """
    return json.dumps(routers, indent=4, sort_keys=True)


if __name__ == '__main__':
    now = get_time()
    routers = get_router_info(now)
    results = dictionary_to_json(routers)
    print(results)
