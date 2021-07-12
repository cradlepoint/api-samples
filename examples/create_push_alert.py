"""Create, test and add a push alert rule to an alert rule.

This is an example script showing how to create an alert push destination
rule, tests it and create an alert rule with the push destination.
The endpoints used are /api/v2/alert_push_destinations,
/api/v2/test_alert_push_destinations and /api/v2/alert_rules.

The alert_push_destinations endpoint requires a push server url and secret.
"""
import requests
import json
import sys

server = 'https://www.cradlepointecm.com/api/v2'
headers = {
            "X-CP-API-ID": "",
            "X-CP-API-KEY": "",
            "X-ECM-API-ID": "",
            "X-ECM-API-KEY": "",
            'Content-Type': 'application/json'
           }


def post(url, body):
    """Do an HTTP post on `url`.

    Args:
        -url- the url to run the post request on
        -body- the body of the post request

    Returns:
        output- the data as a python dict.

    Forces a program exit on HTTP error.

    """
    r = requests.post(url, headers=headers, data=json.dumps(body))
    if r.status_code not in (200, 201):
        print(f"Request failed with HTTP status {r.status_code}",
              file=sys.stderr)
        print(r.text, file=sys.stderr)
        sys.exit(1)
    return json.loads(r.content.decode("utf-8"))


'''Create alert push destination rule'''
url = f'{server}/alert_push_destinations/'
body = {
    "endpoint": {  # Paste your server URL below
        "url": "ExampleURL.com"
    },
    "authentication": {  # Paste your server secret below
        "secret": "ExampleSecret"
    },
    "name": "ExampleName"
}
dst_id = post(url, body).get('destination_config_id')

'''Verify alert push destination by sending a test alert'''
url = f'{server}/test_alert_push_destinations/'
body = {"destination_config_id": dst_id}
req = post(url, body)
if req.get('success') is False:
    print("Test alert failed with error:", req.get('details'))
    sys.exit(1)

'''Create an alert rule with the push destination'''
url = f'{server}/alert_rules/'
body = {
  "schedule": "daily",
  # An associated_account or associated_group must be specified
  # for the alert to take effect.
  "associated_accounts": [],
  "associated_groups": [],
  "filter_criteria": {
    "alert_type__in": ["account_locked"]
  },
  "http_destinations": [dst_id]
}
req = post(url, body)
print("Alert rule created successfully.")
