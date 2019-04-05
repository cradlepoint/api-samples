import requests
import json
import time
import sys

headers = {
    'X-CP-API-ID': '...',
    'X-CP-API-KEY': '...',
    'X-ECM-API-ID': '...',
    'X-ECM-API-KEY': '...',
    'Accept': '*/*',
    'Content-Type': 'application/json',
}

base_url = 'https://www.cradlepointecm.com'
account = 'jjohnson' # your account name goes here...

def get_account_resource_url():
    """ Returns account resource_url value for use in other functions """

    url = base_url + f'/api/v2/accounts/?limit=500&name={account}'

    req = requests.get(url, headers=headers)
    resp = req.json()

    if (len(resp['data']) < 1):
        return None
    return resp['data'][0]['resource_url'].replace('https://www.cradlepointecm.com/api/v2/accounts/','')[:-1]

def speed_test(account_url):

    payload = {
        'account': f'{base_url}/api/v2/accounts/{account_url}/',
        'config': {
            'host': '23.239.20.41',
            'port': 12865,
            'size': None,
            'time': 5,
            'test_type': 'TCP Download',
            'test_timeout': 30,
            'max_test_concurrency': 5,
            'net_device_ids': [28025680]
        }
    }

    try:
        req = requests.post(base_url + '/api/v2/speed_test/', headers=headers, json=payload)
        resp = req.json()

        print('Created Job ID: ' + str(resp["id"]))
        print("This could take a few minutes. Please Wait...")

        while resp["state"] != "complete":
            req = requests.get(resp["resource_uri"], headers=headers)
            resp = req.json()

            if resp["state"] == "started":
                time.sleep(10)

            elif resp["state"] == "complete":
                for key, value in resp.items():
                    if key == "results":
                        for result in value:
                            print('duration: ' + result['results']['duration'])
                            print('throughput: ' + result['results']['throughput'])
                            print('state: ' + result['state'])
            else:
                print(resp)

    except Exception as e:
        raise

def main():
    account_url = get_account_resource_url()
    speed_test(account_url)

if __name__ == '__main__':
    main()
