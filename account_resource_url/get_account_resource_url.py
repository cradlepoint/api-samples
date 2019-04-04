import json
import requests

headers = {
    'X-CP-API-ID': '',
    'X-CP-API-KEY': '',
    'X-ECM-API-ID': '',
    'X-ECM-API-KEY': '',
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

def main():
    get_account_resource_url()

if __name__ == '__main__':
    main()
